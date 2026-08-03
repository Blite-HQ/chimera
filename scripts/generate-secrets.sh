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
#   - permisos 600 desde el nacimiento (nunca un chmod posterior que deje una
#     ventana con el archivo legible);
#   - aleatoriedad del sistema (`openssl rand`, con fallback a /dev/urandom) —
#     nunca una contraseña de ejemplo "temporal" que termine en producción.
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
    # umask antes de crear: el archivo NACE con 600, no se ajusta después.
    ( umask 077 && random_secret > "$destino" )
    echo "  + ${nombre} generado (600)"
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
