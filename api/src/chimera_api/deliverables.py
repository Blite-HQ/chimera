"""Deliverables del certificado — V8/M23b (N4, #70b).

El honest-empty ESTRUCTURAL que cierra: `assemble_bundle` acepta
`deliverables=` desde siempre y NADIE se lo pasaba, así que
`predicate.deliverables` salía vacío y `GET /runs/{id}/artifacts` devolvía `[]`
para todo run — no por falta de datos, sino porque el cable no existía.

Qué es un deliverable acá, y por qué: el ARTEFACTO DE SALIDA del run. Es el
único que el log identifica sin ambigüedad (`run.completed.output_digest`) y
cuyos bytes son recuperables byte a byte del content store (freeze §12) — o
sea, el único que un tercero puede re-verificar contra el digest que el
certificado cita. Declarar como deliverable algo que no se puede recuperar
sería un enlace roto dentro de un certificado.

Fail-closed sin ruido: un run sin `output_digest`, o cuyo blob no esté visible
en el dominio del caller, simplemente no aporta deliverable — el certificado
se emite igual, con la lista vacía. Un certificado no se cae porque un
artefacto no esté; se cae si MIENTE sobre uno que sí citó.
"""

from __future__ import annotations

import logging

from blite.content import ContentStore
from blite.events.event import Event
from blite.events.rules import TERMINAL_RUN_EVENTS

_LOGGER = logging.getLogger(__name__)

RUN_COMPLETED = "run.completed"


def deliverable_ref(run_id: str) -> str:
    """Ref estable del artefacto de salida — legible y única por run."""
    return f"runs/{run_id}/output.json"


def collect_deliverables(
    content: ContentStore, *, run_id: str, stream: tuple[Event, ...]
) -> tuple[tuple[str, bytes], ...]:
    """`(artifact_ref, bytes)` del artefacto de salida del run, o vacío.

    El digest que `assemble_bundle` recomputa sobre estos bytes coincide con
    el `output_digest` del log por construcción: ambos son sha256 de los MISMOS
    bytes (el content store direcciona bytes; la canonicalización la hizo el
    runtime al guardarlos). Esa coincidencia es lo que hace verificable la cita.
    """
    completado = next(
        (
            event
            for event in reversed(stream)
            if event.type == RUN_COMPLETED and event.type in TERMINAL_RUN_EVENTS
        ),
        None,
    )
    if completado is None:
        return ()
    digest = completado.payload.get("output_digest")
    if not isinstance(digest, str) or not digest:
        return ()
    # El dominio sale del PROPIO run (SO2, freeze §12): los bytes se
    # escribieron bajo el dominio del run, así que leerlos bajo una constante
    # del proceso sería una lectura fuera de dominio disfrazada de default.
    try:
        blob = content.get(digest, {"domain_id": stream[0].domain_id})
    except Exception:  # noqa: BLE001 — un artefacto no recuperable NO se cita: el certificado se emite sin él, jamás con un enlace roto
        _LOGGER.warning(
            "run %s: el artefacto de salida %s no es recuperable — "
            "el certificado se emite sin deliverable",
            run_id,
            digest[:12],
        )
        return ()
    return ((deliverable_ref(run_id), blob),)
