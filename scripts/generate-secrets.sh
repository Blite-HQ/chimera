#!/usr/bin/env bash
# generate-secrets.sh — genera los secretos locales que el compose exige.
#
# P5/M27 (research R2: «script generador + *_FILE», patrón Supabase). El
# compose de Chimera ya es `*_FILE`-only —más estricto que el referente— pero
# no había forma de PRODUCIR esos archivos: un tercero clonaba el repo y
# chocaba con un `postgres_password.txt` inexistente sin saber qué poner.
#
# Doctrina de este script:
#   - JAMÁS sobreescribe un secreto existente (rotar es una decisión explícita,
#     nunca un efecto de correr un script de setup dos veces);
#   - la protección la da el DIRECTORIO (700), no el modo del archivo — ver
#     abajo, es una decisión con causa, no descuido;
#   - aleatoriedad del sistema (`openssl rand`, con fallback a /dev/urandom) —
#     nunca una contraseña de ejemplo "temporal" que termine en producción.
#
# **Por qué los archivos son 644 y no 600** (verificado contra el stack REAL,
# 2026-08-03): el compose los monta como bind-mount en `/run/secrets/`, y los
# contenedores corren como usuario NO-root (`chimera`, uid 999 — ver
# docker/api.Dockerfile). Un secreto 600 propiedad del uid del desarrollador es
# ILEGIBLE para ese usuario: `docker compose up` moría con
# `cat: /run/secrets/postgres_password: Permission denied`. La primera versión
# de este script tenía ese bug y el quickstart entero fallaba en el paso 3.
#
# La alternativa (hacer `chown 999` en el host) es peor: deja el archivo
# ilegible para el propio desarrollador. Con `secrets/` en 700, ningún otro
# usuario del host puede siquiera atravesar el directorio para llegar al
# archivo — la superficie protegida es la misma, y el contenedor arranca.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRETS_DIR="${REPO_ROOT}/secrets"
FORCE="${1:-}"

random_secret() {
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -base64 32 | tr -d '\n/+=' | cut -c1-32
    else
        LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 32
    fi
}

write_secret() {
    local nombre="$1" destino="${SECRETS_DIR}/$1"
    if [ -f "$destino" ] && [ "$FORCE" != "--force" ]; then
        echo "  = ${nombre} ya existe — intacto (usá --force para rotarlo)"
        return
    fi
    # umask antes de crear: el archivo NACE con sus permisos finales, sin una
    # ventana intermedia. 022 => 644 (ver la nota de arriba: el contenedor
    # corre como uid 999 y necesita leerlo; el candado es el directorio 700).
    ( umask 022 && random_secret > "$destino" )
    echo "  + ${nombre} generado (644, dentro de secrets/ en 700)"
}

echo "==> Generando secretos en ${SECRETS_DIR}/"
mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"

write_secret "postgres_password.txt"

cat <<'FIN'

==> Listo. Notas:
    - `secrets/` está en .gitignore: estos archivos NUNCA se commitean.
    - Rotar un secreto: volvé a correr con --force y recreá el stack
      (`docker compose down -v && docker compose up -d`) — Postgres fija la
      contraseña al inicializar el volumen, así que rotarla sin borrar el
      volumen deja el servicio sin poder autenticar.
    - La API key del modelo NO se genera acá (es de un proveedor externo):
      guardala en un archivo propio y apuntá CHIMERA_MODEL_API_KEY_FILE a él.
      Solo hace falta para CHIMERA_MODEL_BACKEND=record|live; el modo replay
      es air-gapped por construcción.

Siguiente paso: docs/QUICKSTART.md
FIN
