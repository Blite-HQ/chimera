# syntax=docker/dockerfile:1
# Imagen compartida por `api` y `worker` (mismo binario, distinto command:).
# Build context = raíz del repo (workspace uv completo: root pyproject.toml,
# uv.lock, engine/, api/, sdk/, capabilities/*).
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copia el repo completo (respeta .dockerignore) e instala el workspace
# COMPLETO con extras (--all-packages --all-extras): el registry del runtime
# descubre capabilities por entry points instalados (ADR-008) — con
# `--package chimera-api` la imagen quedaba SIN capabilities y todo run vivo
# moría en resolve con KeyError (auditoría Fase 2, decisión #95). --no-dev
# deja fuera solo el tooling (pytest/ruff/pyright).
COPY . .
RUN uv sync --locked --all-packages --all-extras --no-dev

COPY docker/api-entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENV PATH="/app/.venv/bin:${PATH}"

RUN groupadd --system chimera && useradd --system --gid chimera --no-create-home chimera \
    && chown -R chimera:chimera /app
USER chimera

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD []
