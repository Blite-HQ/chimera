"""
App factory del walking skeleton — spec confianza-api-sse (freeze §9).

`GET /runs/{run_id}/events` (SSE) con reanudación `Last-Event-ID` →
catch-up desde el cursor y tail por polling del puerto `EventStore`. El
notify-then-catchup real (LISTEN/NOTIFY) llega con el store Postgres detrás
del MISMO puerto (nota 01 §1.5) — este módulo no cambia.

Autenticación: JWT en cookie ya DECIDIDO (freeze §9 P1-9); su implementación
es la sesión de seguridad del API (carril Steven) — aquí no se inventa auth.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from blite.events import create_event_store
from blite.events.store import EventStore
from blite.runtime.registry import Registry
from chimera_api.certificate import create_certificate_router
from chimera_api.projection import sse_frame
from chimera_api.runs import build_run_resources, create_runs_router

DEFAULT_POLL_INTERVAL_S = 0.5

_CORS_ORIGINS_ENV_VAR = "CHIMERA_CORS_ORIGINS"


def _cors_origins_from_env() -> list[str]:
    """Orígenes explícitos permitidos vía CORS (CSV), solo para dev local.

    En compose, `studio` le habla a `api` same-origin a través del reverse-
    proxy de nginx (`docker/studio-nginx.conf`, Task 2) — CORS no aplica ahí
    y esta var queda sin setear. Solo hace falta cuando `vite` (origin
    propio, p.ej. `:5173`) le pega directo a `uvicorn` (`:8000`) sin proxy de
    por medio (dev local, `api/README.md`). Vacío/ausente ⇒ sin
    CORSMiddleware — mismo comportamiento same-origin-only de siempre.
    """
    raw = os.environ.get(_CORS_ORIGINS_ENV_VAR, "")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


_SSE_HEADERS = {
    # La pata `proxy_buffering off` del reverse proxy vive en el compose
    # (frontera Geovanni); estas cabeceras declaran la intención extremo a extremo.
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}


def _parse_cursor(raw: str | None) -> int:
    """`Last-Event-ID` inválido ⇒ catch-up completo (jamás matar el stream:
    F5 + catch-up ES la feature "cero eventos perdidos", freeze §9)."""
    if raw is None:
        return 0
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


async def event_stream(
    store: EventStore,
    run_id: str,
    *,
    cursor: int = 0,
    live: bool = True,
    poll_interval: float = DEFAULT_POLL_INTERVAL_S,
    is_disconnected: Callable[[], Awaitable[bool]] | None = None,
) -> AsyncIterator[str]:
    """Frames SSE del run: catch-up desde `cursor` y, si `live`, tail por polling.

    Solo el stream del run (proyección, no fuente): el Studio jamás ve
    eventos de otros runs. `live=False` = snapshot (catch-up y cerrar) —
    modo de inspección/curl; el contrato del Studio usa el default vivo.
    """
    position = cursor
    while True:
        for event in store.read_stream(run_id):
            if event.global_seq > position:
                position = event.global_seq
                yield sse_frame(event)
        if not live:
            return
        if is_disconnected is not None and await is_disconnected():
            return
        await asyncio.sleep(poll_interval)


def create_app(
    store: EventStore | None = None,
    *,
    registry: Registry | None = None,
    poll_interval: float = DEFAULT_POLL_INTERVAL_S,
) -> FastAPI:
    event_store = store if store is not None else create_event_store()
    app = FastAPI(title="chimera-api", version="0.1.0")

    cors_origins = _cors_origins_from_env()
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    resources = build_run_resources(event_store, registry=registry)
    app.include_router(create_runs_router(resources))
    app.include_router(create_certificate_router(resources))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/runs/{run_id}/events")
    async def run_events(
        run_id: str, request: Request, live: bool = True
    ) -> StreamingResponse:
        frames = event_stream(
            event_store,
            run_id,
            cursor=_parse_cursor(request.headers.get("last-event-id")),
            live=live,
            poll_interval=poll_interval,
            is_disconnected=request.is_disconnected,
        )
        return StreamingResponse(
            frames, media_type="text/event-stream", headers=_SSE_HEADERS
        )

    return app
