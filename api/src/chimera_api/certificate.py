"""
`GET /runs/{run_id}/certificate` — el bundle se PROYECTA del stream de un run
ya terminado. Plan `docs/mvp/01-runtime-api.md` §2 (decisiones
`docs/mvp/decisiones.md` #9 llave efímera por proceso, #10 verbo GET, #12
409 si el run aún no terminó).

Este router es un lector puro sobre `RunResources` (misma instancia que el
router de `/runs`, Task B): no muta nada, solo lee el `EventStore` y el
`RunTicket` que `POST /runs` dejó, y delega el ensamblaje real a
`blite.certificate.assemble.assemble_bundle` — el ensamblador es el único
lugar que sabe proyectar el stream a un Bundle firmado.

Fail-closed en dos capas: un run vivo (sin evento terminal) jamás se
certifica (409), y un `AssembleError` del ensamblador — stream sin evidencia
amparando la conclusión declarada, típicamente un `run.failed` — se mapea a
409 honesto: no hay certificado que emitir, jamás uno fabricado. Un run
REFUTADO (assignment subóptimo) NO cae en este camino: `assemble_bundle`
emite un certificado de refutación (titular AL0) válido — refutar es un
veredicto de primera clase, no un error.
"""

# pyright: reportUnusedFunction=false
# ^ Los handlers de FastAPI se registran por DECORADOR (`@router.get/post`), no
#   por llamada: pyright los ve como funciones locales que nadie usa. Silenciar
#   la regla acá —y solo acá— evita 15 falsos positivos sin apagar la
#   comprobación en el resto del proyecto, donde una función sin usar SÍ es
#   señal de código muerto.

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from blite.certificate.assemble import AssembleError, assemble_bundle
from blite.events.rules import TERMINAL_RUN_EVENTS, provenance_slice
from chimera_api.runs import RunResources


def create_certificate_router(resources: RunResources) -> APIRouter:
    """Router de `/runs/{run_id}/certificate` cerrado sobre la MISMA infra de
    vida-de-app que `/runs` (mismo `store`, mismos `run_tickets`)."""
    router = APIRouter()

    @router.get("/runs/{run_id}/certificate")
    def get_certificate(run_id: str) -> dict[str, Any]:
        ticket = resources.run_tickets.get(run_id)
        if ticket is None:
            raise HTTPException(status_code=404, detail="run desconocido")

        stream = resources.store.read_stream(run_id)
        # [V2/M19] El corte NO es "el último evento del stream": freeze §2
        # [stress-final] admite familias de CIERRE post-terminales
        # (`run.metrics.recorded`, ● de cierre del case) que quedan FUERA del
        # hash. Comprobar `stream[-1]` daba 409 en cuanto el cierre métrico
        # existió — y pasarle el stream completo a `assemble_bundle` habría metido
        # un evento post-terminal DENTRO del provenance_hash. Por eso: el run está
        # terminado si TIENE terminal, y lo que se certifica es el corte.
        if not stream or not any(e.type in TERMINAL_RUN_EVENTS for e in stream):
            raise HTTPException(
                status_code=409,
                detail="el run aún no terminó — un run vivo no se certifica",
            )

        try:
            return assemble_bundle(
                stream=provenance_slice(stream),
                conclusions=ticket.conclusions,
                policy_yaml=resources.policy_bytes,
                signing_key=resources.signing_key,
                keyid=resources.keyid,
                anchor_descriptors=ticket.anchor_descriptors,
            )
        except AssembleError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    return router
