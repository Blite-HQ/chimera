#!/bin/sh
set -eu
if [ -n "${CHIMERA_DB_PASSWORD_FILE:-}" ] && [ -f "$CHIMERA_DB_PASSWORD_FILE" ]; then
  pw="$(cat "$CHIMERA_DB_PASSWORD_FILE")"
  export CHIMERA_DATABASE_URL="postgresql://chimera:${pw}@postgres:5432/chimera"
fi
if [ "$#" -gt 0 ]; then exec "$@"; fi          # worker: `procrastinate worker`
exec uvicorn chimera_api.main:app --host 0.0.0.0 --port 8000
