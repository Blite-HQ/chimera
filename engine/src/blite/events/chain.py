"""
La vista canónica del evento y los dos hashes que se computan sobre ella —
anexo de canonicalización (CONGELADO) §3/§4. [C5/M8 pieza 1]

**Una sola fuente de la fórmula.** Este anexo existe porque «sin spec exacta
de bytes, dos implementaciones honestas producen hashes distintos y la
verificación offline muere». Tener la fórmula escrita en tres archivos es la
versión interna de ese mismo bug: por eso el emisor (`certificate.assemble`),
el juez (`certificate.bundle_check`), el writer del log y el encadenado de
sub-runs la toman de aquí.

Lo que NO se comparte, a propósito: el juez recomputa desde el stream
EMPAQUETADO en el bundle y mantiene sus propias copias de techos y orden de
niveles (D20 — el verificador offline no confía en el emisor). Compartir el
ALGORITMO de bytes es obligatorio; compartir el JUICIO sería el error.

Las dos fórmulas (§4 del anexo):

    linea_i          = C(view(e_i)) ‖ 0x0A
    provenance_hash  = SHA-256("blite/provenance/v1\\n" ‖ linea_1 … linea_n)

    hash_i           = SHA-256("blite/event/v1\\n" ‖ hash_{i-1}^hex ‖ "\\n"
                               ‖ C(view(e_i))),   génesis hash_0^hex = ""

`view(e)` excluye `global_seq` (cursor de almacenamiento, depende del
interleaving) y `prev_hash`/`hash` (capa de integridad — evitan la
circularidad y dejan el MISMO `C()` para la cadena). Campo nuevo en la vista
⇒ bump del prefijo de dominio, jamás un campo «aditivo» silencioso bajo la
misma versión (lección §4.3.1 del AGT).
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, cast

from blite.certificate.canonical import JSONValue, canonicalize
from blite.events.event import Event

PROVENANCE_PREFIX = b"blite/provenance/v1\n"
EVENT_CHAIN_PREFIX = b"blite/event/v1\n"

GENESIS_PREV_HASH = ""
"""Génesis del encadenado: cadena vacía en hex (elección EXPLÍCITA del anexo
§4 — el AGT tiene `""` en Python y `"0"*64` en TypeScript por no elegir, y
sus dos implementaciones no se verifican entre sí)."""


def rfc3339(value: datetime) -> str:
    """RFC 3339 UTC con EXACTAMENTE 6 fraccionales y sufijo `Z` (anexo §3).

    Construido explícitamente: `isoformat()` omite los microsegundos cuando
    son cero y emite `+00:00` — dos eventos honestos darían digests
    distintos según la hora en que ocurrieron."""
    aware = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    utc = aware.astimezone(UTC)
    return f"{utc:%Y-%m-%dT%H:%M:%S}.{utc.microsecond:06d}Z"


def view_of(  # noqa: PLR0913 — son los 8 campos de la vista congelada, ni uno más
    *,
    id: object,
    stream_id: str,
    seq: int,
    type: str,
    actor_id: str,
    domain_id: str,
    payload: dict[str, Any],
    occurred_at: datetime,
) -> dict[str, Any]:
    """`view(e)` del anexo §3 desde los campos sueltos — EXACTAMENTE estos 8.

    Existe para que el writer pueda encadenar el evento ANTES de construirlo
    sin fabricar un `Event` de mentira ni copiar la vista: una segunda copia
    de esta forma es justo el drift que el anexo existe para matar."""
    return {
        "id": str(id),
        "stream_id": stream_id,
        "seq": seq,
        "type": type,
        "actor_id": actor_id,
        "domain_id": domain_id,
        "payload": payload,
        "occurred_at": rfc3339(occurred_at),
    }


def event_view(event: Event) -> dict[str, Any]:
    """`view(e)` desde un `Event` del log."""
    return view_of(
        id=event.id,
        stream_id=event.stream_id,
        seq=event.seq,
        type=event.type,
        actor_id=event.actor_id,
        domain_id=event.domain_id,
        payload=event.payload,
        occurred_at=event.occurred_at,
    )


def provenance_hash_of_views(views: Sequence[Mapping[str, Any]]) -> str:
    """`provenance_hash` sobre vistas ya canónicas (anexo §4), hex lowercase.

    Framing por líneas: streameable (el verificador offline no carga el run
    entero) y sin ambigüedad de fronteras — la lección PAE de DSSE aplicada
    al caso multi-mensaje."""
    return hashlib.sha256(
        PROVENANCE_PREFIX
        + b"".join(
            canonicalize(cast("JSONValue", dict(view))) + b"\n" for view in views
        )
    ).hexdigest()


def provenance_hash_of_events(events: Sequence[Event]) -> str:
    """`provenance_hash` sobre eventos — el mismo cómputo, desde el log."""
    return provenance_hash_of_views([event_view(event) for event in events])


def chain_hash(*, prev_hash: str, view: Mapping[str, Any]) -> str:
    """`hash_i` del encadenado por evento (anexo §4, Fase 2), hex lowercase."""
    return hashlib.sha256(
        EVENT_CHAIN_PREFIX
        + prev_hash.encode("utf-8")
        + b"\n"
        + canonicalize(cast("JSONValue", dict(view)))
    ).hexdigest()


def chain_head_of_views(views: Sequence[Mapping[str, Any]]) -> str:
    """Recomputa la cadena entera desde las vistas y devuelve el HEAD.

    Que la cadena sea recomputable desde las puras vistas es lo que permite
    verificarla offline sin empaquetar un hash por evento: el bundle lleva
    solo el head, y quien audite lo reconstruye."""
    head = GENESIS_PREV_HASH
    for view in views:
        head = chain_hash(prev_hash=head, view=view)
    return head


__all__ = [
    "EVENT_CHAIN_PREFIX",
    "GENESIS_PREV_HASH",
    "PROVENANCE_PREFIX",
    "chain_hash",
    "chain_head_of_views",
    "event_view",
    "provenance_hash_of_events",
    "provenance_hash_of_views",
    "rfc3339",
]
