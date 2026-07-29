# Verificación del walking skeleton de infra (operador)

**Dominio:** `04-infra.md`. **Decisiones referenciadas:** #6–#11 en
`docs/mvp/decisiones.md`. Este doc es la versión-operador de `scripts/smoke_infra.sh`
— el script ES la verificación ejecutable; este texto explica qué hace y por qué.

## Prerrequisitos

- Docker + Docker Compose v2 (`docker compose version`).
- `uv sync` corrido al menos una vez en la raíz del repo (instala el workspace,
  incluyendo `chimera-engine` con `psycopg`, y pytest).
- Nada escuchando en `127.0.0.1:5544` (Postgres del compose) ni en `:8000` (api).

## Reproducir en un comando

```bash
bash scripts/smoke_infra.sh
```

Con `--down`, el script baja el stack al terminar (`docker compose down`, **sin**
`-v` — conserva el volumen `pgdata`). Sin esa flag, el stack queda arriba para
inspección manual; bajalo vos con `docker compose down` (agregá `-v` solo si además
querés borrar `pgdata`). `KEEP=1` fuerza dejarlo arriba aunque pases `--down`.

## Cómo funciona el secreto `*_FILE`

`compose.yaml` nunca tiene una contraseña literal (decisión #7). `postgres` recibe
`POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password`; `api`/`worker` reciben
`CHIMERA_DB_PASSWORD_FILE` apuntando al mismo secreto montado. `docker/api-entrypoint.sh`
(infra-owned, no toca `engine/`) lee ese archivo en runtime y arma
`CHIMERA_DATABASE_URL=postgresql://chimera:<pw>@postgres:5432/chimera` antes de
ejecutar `uvicorn`. El archivo real `secrets/postgres_password.txt` está gitignored;
`scripts/smoke_infra.sh` lo crea a partir de `secrets/postgres_password.txt.example`
si falta, para que un clon nuevo del repo funcione sin pasos manuales.

> Para un bring-up **manual** (sin el smoke): `cp secrets/postgres_password.txt.example
secrets/postgres_password.txt`. El `.example` es **una sola línea** con un password
> **URL-safe** (sin `@ : / #`, espacios ni saltos de línea): tanto `postgres`
> (`POSTGRES_PASSWORD_FILE`) como el entrypoint leen el archivo _entero_, y el entrypoint
> lo embebe en `CHIMERA_DATABASE_URL` — un comentario o un carácter no-URL rompería el DSN
> (decisión #13). Para uso real, sustituílo por un secreto fuerte que cumpla esa regla.

## Qué prueba el smoke (y qué NO)

El smoke solo ejercita `GET /health`, `GET /runs/{run_id}/events` (SSE), `GET /runs`
(supervivencia de la lista) y el conteo de entry points en el contenedor — no ejercita
`POST /runs` (ese flujo lo cubre `tests/smoke/test_runtime_api_e2e.py`; el endpoint vive
en `api/src/chimera_api/runs.py`, dominio 01). Por eso el "evento
real de punta a punta" honesto para infra es:

```
host (uv run python -c ...)          contenedor api (mismo postgres:5432)
  create_event_store()                        │
     .append(...)  ──────► postgres ◄───────── event_stream() / SSE
     (loopback 127.0.0.1:5544)                 │
                                                ▼
                                    curl /runs/{id}/events?live=false
```

1. **Bring-up**: `docker compose up -d --build postgres api` (NO `studio` — no hace
   falta para el evento y mantiene el smoke rápido; `studio` se verifica aparte,
   Task 2).
2. **Espera acotada** (~60s) a que `postgres` esté `healthy` (healthcheck
   `pg_isready`) y `api` responda `{"status":"ok"}` en `/health`.
   2.5. **Registry no-vacío**: `docker compose exec api` enumera los entry points
   del grupo `blite.capabilities` y falla si no hay ninguno. El runtime descubre
   capabilities por entry points instalados (ADR-008); una imagen sin ellas hace
   que TODO run vivo muera en `resolve` con `KeyError` — pasó cuando la imagen
   instalaba solo `chimera-api` (auditoría Fase 2, decisión #95): por eso
   `docker/api.Dockerfile` sincroniza el workspace completo
   (`uv sync --all-packages --all-extras --no-dev`).
3. **Contrato de integración real**: corre
   `tests/integration/test_postgres_event_store.py` con
   `CHIMERA_TEST_DATABASE_URL` apuntando al Postgres del compose (puerto loopback
   `5544`, decisión #9) — el contrato completo del `EventStore` (append, seq,
   concurrencia optimista, rechazo post-terminal) contra Postgres de verdad, no un
   mock.
4. **El evento único**: el host escribe UN evento (`type="smoke.event"`, un
   `stream_id` único `smoke-<timestamp>`) vía
   `create_event_store()` (la MISMA factory que usa el api — sin DSN cae a
   in-memory, con `CHIMERA_DATABASE_URL` cae a `PostgresEventStore`, lee
   `engine/src/blite/events/__init__.py`) apuntando al mismo Postgres del compose.
   El `run_id` también se agrega al `payload` del evento — la proyección SSE
   (`chimera_api/projection.py`, fuera de alcance de infra) no repite el
   `stream_id` en `data` porque ya está implícito en la ruta
   `/runs/{run_id}/events`; ponerlo en el payload deja al smoke verificarlo con
   `curl` sin tocar el api.
5. **La lectura real por el contenedor**: `curl` a
   `http://localhost:8000/runs/<run_id>/events?live=false` — el contenedor `api`
   (conectado al MISMO `postgres:5432` vía Docker network) sirve el frame SSE
   (`id: <global_seq>` / `event: smoke.event` / `data: {...}`) de vuelta. El script
   verifica que el frame contenga `smoke.event` y el `run_id`.

   > Por qué `smoke.event` y no `run.created`: la proyección de runs
   > (`blite.runtime.projection.project_runs`) es fail-loud por doctrina (freeze
   > §3 — `max_steps`/`policy_digest` obligatorios en el payload); un
   > `run.created` mínimo del smoke quedaba en pgdata como píldora envenenada y
   > `GET /runs` (E1) devolvía 500 para siempre — se reprodujo en vivo en la
   > auditoría Fase 2. La proyección ignora tipos fuera del ciclo `run.*`, así
   > que `smoke.event` prueba el mismo camino sin fingir un run.

6. **La lista sobrevive**: `curl` a `GET /runs` debe responder 200 y NO listar el
   stream del smoke — el smoke es invisible para la proyección por construcción.

Esto ejercita genuinamente engine (escritura) → Postgres del compose → contenedor
api (lectura) → SSE — sin inventar rutas que no existen todavía.

### Qué queda deferido (y por qué)

- **`POST /runs` / `POST /invoke` E2E completo**: el smoke no ejercita `POST /runs`
  (ese flujo lo cubre `tests/smoke/test_runtime_api_e2e.py`; `POST /invoke` sigue sin
  existir). `docs/mvp/04-infra.md` §3 ya anticipa "el smoke E2E
  del dominio runtime-api (POST /runs → SSE → certificado)" como el siguiente nivel;
  este script cubre la porción que infra puede probar por sí solo con honestidad.
- **`worker`**: config-presente-e-inerte (decisión #6) — mismo imagen que `api`,
  comando `procrastinate worker`, pero no hay app procrastinate registrada en el
  engine todavía. El smoke NO lo levanta (fallaría al arrancar por diseño hasta que
  01 la registre).
- **`studio`**: se construye y sirve por separado (Task 2, `docker/studio.Dockerfile`
  - `docker/studio-nginx.conf`, decisión #8). No es necesario para probar el evento
    engine→postgres→api y se deja fuera de este smoke para mantenerlo rápido.

## Salida esperada

El script imprime cada paso con prefijo `[smoke]`, el bloque `--- SSE frame ---` con
la respuesta cruda de `curl`, y termina con una línea `SMOKE: PASS` (exit 0) o
`SMOKE: FAIL — <motivo>` (exit no-cero). Cualquier falla de bring-up, timeout de
salud, test de integración, escritura del evento o verificación del frame SSE hace
fallar el script — nunca imprime `PASS` a medias.
