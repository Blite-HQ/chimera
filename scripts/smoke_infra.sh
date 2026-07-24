#!/usr/bin/env bash
# smoke_infra.sh — UN evento real de punta a punta por el walking skeleton.
#
# Qué prueba (honesto, ver docs/mvp/infra-verificacion.md):
#   engine (create_event_store) --escribe--> postgres (compose, loopback 5544)
#     --lee-- api (contenedor, mismo postgres:5432) --SSE-- curl
# NO hay POST /runs ni /invoke todavía (dominio 01) — ver decisiones #6-#11 en
# docs/mvp/decisiones.md. Este script NO los inventa.
#
# Uso:
#   bash scripts/smoke_infra.sh            # levanta, prueba, deja el stack arriba
#   bash scripts/smoke_infra.sh --down      # además baja el stack al terminar (sin -v: conserva pgdata)
#   KEEP=1 bash scripts/smoke_infra.sh      # fuerza dejarlo arriba aunque se pase --down
#
# Teardown por defecto: el stack queda ARRIBA al salir (útil para demo/inspección
# manual). Para bajarlo: `docker compose down` (agregar `-v` solo si además querés
# borrar el volumen `pgdata`). Con `--down` (y sin KEEP=1) este script lo baja por vos,
# SIN `-v`.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DOWN_AT_EXIT=0
for arg in "$@"; do
  case "$arg" in
    --down) DOWN_AT_EXIT=1 ;;
    *)
      echo "smoke_infra.sh: argumento desconocido: $arg" >&2
      exit 2
      ;;
  esac
done

HEALTH_TIMEOUT_S=60
POLL_INTERVAL_S=2
API_URL="http://localhost:8000"
PG_HOST="127.0.0.1"
PG_PORT="5544"

_log() { printf '[smoke] %s\n' "$*"; }

_fail() {
  _log "SMOKE: FAIL — $*"
  exit 1
}

cleanup() {
  local exit_code=$?
  if [ "$DOWN_AT_EXIT" -eq 1 ] && [ "${KEEP:-0}" != "1" ]; then
    _log "bajando el stack (docker compose down, sin -v: pgdata se conserva)…"
    docker compose down || true
  else
    _log "stack dejado arriba. Para bajarlo: docker compose down (agregar -v para borrar pgdata también)."
  fi
  exit "$exit_code"
}
trap cleanup EXIT

# 1. Resolver la contraseña de postgres (secreto real, gitignored).
SECRET_FILE="$ROOT/secrets/postgres_password.txt"
SECRET_EXAMPLE="$ROOT/secrets/postgres_password.txt.example"
if [ ! -f "$SECRET_FILE" ]; then
  _log "secrets/postgres_password.txt no existe — copiando desde el .example"
  cp "$SECRET_EXAMPLE" "$SECRET_FILE"
fi
# El archivo real es EXACTAMENTE lo que postgres (POSTGRES_PASSWORD_FILE) y
# docker/api-entrypoint.sh (CHIMERA_DB_PASSWORD_FILE) leen con `cat`/`<` — el
# archivo COMPLETO, no solo la última línea. El .example trae un comentario
# `#` de documentación en la primera línea (válido como plantilla), pero si
# ese comentario sobrevive al `cp` en el archivo REAL, postgres lo incluiría
# como parte de la contraseña real (initdb) mientras que un lector ingenuo
# tipo `tail -n1` vería solo `change-me-local-only` → mismatch → "password
# authentication failed" (se reprodujo en vivo). Para que host y contenedores
# usen la MISMA contraseña, normalizamos el archivo real (nunca el .example)
# a una sola línea sin comentarios ni líneas vacías antes de levantar nada.
if grep -q '^#' "$SECRET_FILE" 2>/dev/null; then
  _log "normalizando secrets/postgres_password.txt (quitando comentarios) para que coincida con lo que postgres/api-entrypoint leen"
  grep -v '^#' "$SECRET_FILE" | grep -v '^[[:space:]]*$' > "$SECRET_FILE.tmp"
  mv "$SECRET_FILE.tmp" "$SECRET_FILE"
fi
PW="$(cat "$SECRET_FILE")"
if [ -z "$PW" ]; then
  _fail "secrets/postgres_password.txt está vacío"
fi

DB_URL="postgresql://chimera:${PW}@${PG_HOST}:${PG_PORT}/chimera"

# 2. Levantar postgres + api (studio NO es necesario para el evento E2E).
_log "docker compose up -d --build postgres api"
docker compose up -d --build postgres api

# 3. Esperar: postgres healthy AND api /health == {"status":"ok"}.
_log "esperando postgres healthy y api /health (timeout ${HEALTH_TIMEOUT_S}s)…"
elapsed=0
postgres_ready=0
api_ready=0
while [ "$elapsed" -lt "$HEALTH_TIMEOUT_S" ]; do
  if [ "$postgres_ready" -eq 0 ]; then
    status="$(docker compose ps --format '{{.Health}}' postgres 2>/dev/null || true)"
    if [ "$status" = "healthy" ]; then
      postgres_ready=1
      _log "postgres: healthy"
    fi
  fi
  if [ "$api_ready" -eq 0 ]; then
    if body="$(curl -fsS "${API_URL}/health" 2>/dev/null)" && [ "$body" = '{"status":"ok"}' ]; then
      api_ready=1
      _log "api: /health == ${body}"
    fi
  fi
  if [ "$postgres_ready" -eq 1 ] && [ "$api_ready" -eq 1 ]; then
    break
  fi
  sleep "$POLL_INTERVAL_S"
  elapsed=$((elapsed + POLL_INTERVAL_S))
done

if [ "$postgres_ready" -ne 1 ] || [ "$api_ready" -ne 1 ]; then
  _log "docker compose ps:"
  docker compose ps || true
  _log "logs api (últimas 50 líneas):"
  docker compose logs --tail=50 api || true
  _fail "timeout de ${HEALTH_TIMEOUT_S}s esperando postgres healthy (${postgres_ready}) y api /health (${api_ready})"
fi

# 4. Contrato de integración contra el Postgres REAL del compose.
# `--no-cov`: los `addopts` del repo (pyproject.toml) traen `--cov-fail-under=30`
# pensado para la suite COMPLETA (gate separado, `uv run pytest`); un archivo
# suelto de integración cubre ~5% del árbol y haría fallar el gate de cobertura
# aunque los tests reales pasen — falso negativo. El smoke NO es uno de los 4
# gates, así que desactivar cobertura aquí es correcto y no toca su config.
_log "uv run pytest tests/integration/test_postgres_event_store.py -q --no-cov"
if ! CHIMERA_TEST_DATABASE_URL="$DB_URL" uv run pytest tests/integration/test_postgres_event_store.py -q --no-cov; then
  _fail "tests/integration/test_postgres_event_store.py no pasó contra el postgres del compose"
fi

# 5. UN evento real: engine escribe vía create_event_store() -> postgres(compose).
RUN_ID="smoke-$(date +%s)"
_log "escribiendo un evento real: stream_id=${RUN_ID}"
if ! CHIMERA_DATABASE_URL="$DB_URL" RUN_ID="$RUN_ID" uv run python -c '
import os
from blite.events import create_event_store

run_id = os.environ["RUN_ID"]
store = create_event_store()
event = store.append(
    stream_id=run_id,
    type="run.created",
    actor_id="user:smoke",
    domain_id="d-default",
    # run_id va también en el payload: la proyección SSE (chimera_api.projection,
    # fuera de alcance de infra) NO repite el stream_id en `data` -- ya está
    # implícito en la ruta /runs/{run_id}/events. Lo incluimos en el payload
    # (el payload viaja íntegro en el frame) para poder verificarlo por curl.
    payload={"resumen": "smoke_infra.sh", "run_id": run_id},
)
print(f"escrito: seq={event.seq} global_seq={event.global_seq} type={event.type}")
'; then
  _fail "no se pudo escribir el evento vía create_event_store()"
fi

# 6. api lee el MISMO evento del MISMO postgres, servido como frame SSE.
_log "curl ${API_URL}/runs/${RUN_ID}/events?live=false"
SSE_BODY="$(curl -fsS "${API_URL}/runs/${RUN_ID}/events?live=false")" \
  || _fail "curl a /runs/${RUN_ID}/events falló"

echo "--- SSE frame ---"
echo "$SSE_BODY"
echo "-----------------"

if ! printf '%s' "$SSE_BODY" | grep -q "run.created"; then
  _fail "el frame SSE no contiene event: run.created"
fi
if ! printf '%s' "$SSE_BODY" | grep -q "$RUN_ID"; then
  _fail "el frame SSE no contiene el RUN_ID ${RUN_ID}"
fi

_log "SMOKE: PASS — evento ${RUN_ID} (run.created) confirmado engine -> postgres(compose) -> api SSE"
