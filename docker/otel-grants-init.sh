#!/bin/sh
# Crea el rol SOLO-SELECT del proyector (S-F §2) — init script de postgres.
#
# La frontera «el proyector no escribe» no se deja al código: se deja al motor.
# Este rol no tiene INSERT/UPDATE/DELETE sobre nada; el append-only ni se roza
# aunque el proyector tenga un bug.
#
# La contraseña viaja por archivo de secreto (EG-3: jamás literal en el YAML).
#
# OJO: los init scripts de la imagen oficial corren SOLO sobre un volumen
# NUEVO. En un `pgdata` ya inicializado hay que correrlo a mano:
#   docker compose exec -T postgres sh /docker-entrypoint-initdb.d/20-otel-grants.sh
set -eu

PASSWORD_FILE="${CHIMERA_OTEL_PASSWORD_FILE:-/run/secrets/otel_password}"
if [ ! -f "$PASSWORD_FILE" ]; then
  echo "otel-grants: no hay $PASSWORD_FILE — se omite el rol del proyector." >&2
  exit 0
fi
OTEL_PASSWORD=$(cat "$PASSWORD_FILE")

psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set ON_ERROR_STOP=1 \
     --set otel_password="$OTEL_PASSWORD" <<'EOSQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'chimera_otel') THEN
    CREATE ROLE chimera_otel LOGIN;
  END IF;
END
$$;

ALTER ROLE chimera_otel WITH PASSWORD :'otel_password';

-- Primero se quita todo, después se concede lo único que necesita: leer
-- `events`. En ese orden, para que un GRANT heredado no sobreviva.
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM chimera_otel;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM chimera_otel;
REVOKE ALL ON SCHEMA public FROM chimera_otel;

GRANT CONNECT ON DATABASE chimera TO chimera_otel;
GRANT USAGE ON SCHEMA public TO chimera_otel;
GRANT SELECT ON TABLE events TO chimera_otel;
EOSQL

echo "otel-grants: rol chimera_otel listo (SELECT sobre events y nada más)."
