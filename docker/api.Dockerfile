# syntax=docker/dockerfile:1
# Imagen compartida por `api` y `worker` (mismo binario, distinto command:).
# Build context = raíz del repo (workspace uv completo: root pyproject.toml,
# uv.lock, engine/, api/, sdk/, capabilities/*).
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copia el repo completo (respeta .dockerignore) e instala LA DISTRIBUCIÓN
# (P9/M14): `distributions/chimera` es un paquete que declara exactamente qué
# capabilities y qué extras viajan, y el registry del runtime las descubre por
# entry points instalados (ADR-008).
#
# Historia, porque el camino corto es un error conocido: `--package chimera-api`
# dejaba la imagen SIN capabilities y todo run vivo moría en resolve con
# KeyError (decisión #95), así que se pasó a `--all-packages --all-extras`.
# Eso resolvió el bug y trajo otro: `--all-extras` arrastra TODOS los extras
# declarados —química cuántica (pyscf), pennylane, el SDK de D-Wave, xgboost,
# un solver comercial— que ninguna capability instalada importa. El punto medio
# correcto es declarar la distribución: entry points completos, extras curados.
COPY . .
RUN uv sync --locked --package chimera-distribution --no-dev

COPY docker/api-entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENV PATH="/app/.venv/bin:${PATH}"

RUN groupadd --system chimera && useradd --system --gid chimera --no-create-home chimera \
    && chown -R chimera:chimera /app
USER chimera

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD []
