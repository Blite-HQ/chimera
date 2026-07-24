# syntax=docker/dockerfile:1
# Imagen compartida por `api` y `worker` (mismo binario, distinto command:).
# Build context = raíz del repo (workspace uv completo: root pyproject.toml,
# uv.lock, engine/, api/, sdk/, capabilities/*).
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copia el repo completo (respeta .dockerignore) e instala SOLO chimera-api
# + sus deps de workspace (chimera-engine -> psycopg, procrastinate, fastapi,
# uvicorn). --no-dev mantiene la imagen liviana.
COPY . .
RUN uv sync --locked --package chimera-api --no-dev

COPY docker/api-entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENV PATH="/app/.venv/bin:${PATH}"

RUN groupadd --system chimera && useradd --system --gid chimera --no-create-home chimera \
    && chown -R chimera:chimera /app
USER chimera

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD []
