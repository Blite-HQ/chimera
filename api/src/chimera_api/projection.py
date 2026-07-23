"""
Proyección para UI + frame SSE — spec confianza-api-sse (freeze §9).

El Studio consume PROYECCIONES, jamás la tabla cruda: `data:` es un subset
del Event (sin prev_hash/hash) con el payload íntegro — la regla de forma
del freeze §9 ("ningún resultado sin su bloque `verification`") se honra NO
recortando lo que el emisor estampó. `resumen` sale del payload si el emisor
lo trae; si no, degrada al `type` (convención UI adaptable, nota 18 §5).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from blite.events.event import Event


def _rfc3339(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def project_event(event: Event) -> dict[str, Any]:
    """Evento proyectado para UI (trust/07 §1.3, fila timeline + procedencia)."""
    projected: dict[str, Any] = {
        "global_seq": event.global_seq,
        "type": event.type,
        "actor_id": event.actor_id,
        "occurred_at": _rfc3339(event.occurred_at),
        "resumen": str(event.payload.get("resumen", event.type)),
        "payload": event.payload,
    }
    step_id = event.payload.get("step_id")
    if step_id is not None:
        projected["step_id"] = step_id
    return projected


def sse_frame(event: Event) -> str:
    """`id:` = global_seq · `event:` = type · `data:` = proyección en UNA línea."""
    data = json.dumps(project_event(event), ensure_ascii=False, separators=(",", ":"))
    return f"id: {event.global_seq}\nevent: {event.type}\ndata: {data}\n\n"
