# syntax=docker/dockerfile:1
# Proyector de observabilidad (perfil `otel`) — imagen PROPIA, no la del api.
#
# Comparte el contexto del workspace pero instala SOLO su paquete: el proyector
# no necesita el engine y no debe poder importarlo aunque quisiera (C-11). Una
# imagen que llevara `blite` dentro haría de la frontera una promesa en vez de
# un hecho.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY . .
RUN uv sync --locked --package chimera-otel --no-dev

ENV PATH="/app/.venv/bin:${PATH}"

# Cursor propio, FUERA del event store (S-F §2).
ENV CHIMERA_OTEL_CURSOR=/var/lib/chimera-otel/cursor.json

RUN groupadd --system chimera && useradd --system --gid chimera --no-create-home chimera \
    && mkdir -p /var/lib/chimera-otel \
    && chown -R chimera:chimera /app /var/lib/chimera-otel
USER chimera

ENTRYPOINT ["python", "-m", "chimera_otel"]
