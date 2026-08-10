"""Fuente de datos: SOLO-SELECT sobre `events`, con cursor propio (S-F §2).

Dos reglas que no son detalle de implementación:

1. **El proyector no puede escribir.** Ni al event store ni a nada suyo dentro
   de él. El usuario de Postgres que usa tiene `SELECT` sobre `events` y nada
   más (`docker/otel-projector-grants.sql`): el append-only no se roza, y no
   depende de que el código se porte bien.
2. **El cursor vive FUERA del event store** — un archivo del proyector. Meterlo
   en la base que observa sería exactamente la dependencia que C-11 evita.

Misma doctrina notify-then-catchup de §2: `global_seq` es la verdad y el catch-up
puede reanudarse desde cualquier cursor. Caerse y reproyectar da el MISMO
resultado (§4), así que perder el cursor cuesta trabajo repetido, jamás
corrección.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

_SELECT_BATCH = """
    SELECT stream_id, seq, global_seq, type, actor_id, domain_id, payload, occurred_at
    FROM events
    WHERE global_seq > %s
    ORDER BY global_seq
    LIMIT %s
"""


class _Connection(Protocol):  # pragma: no cover - contrato de psycopg
    def cursor(self) -> Any: ...


class CursorFile:
    """El cursor persistido, fuera del event store."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def read(self) -> int:
        if not self._path.is_file():
            return 0
        try:
            return int(json.loads(self._path.read_text(encoding="utf-8"))["global_seq"])
        except (ValueError, KeyError, OSError):
            # Un cursor ilegible se trata como «desde el principio»: reproyectar
            # es idempotente (§4), así que la opción segura es barata.
            return 0

    def write(self, global_seq: int) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps({"global_seq": global_seq}) + "\n", encoding="utf-8"
        )


def row_to_event(row: Sequence[Any]) -> dict[str, Any]:
    """Fila de `events` → dict del wire (el mismo que consume `projection`)."""
    stream_id, seq, global_seq, type_, actor_id, domain_id, payload, occurred_at = row
    return {
        "stream_id": stream_id,
        "seq": int(seq),
        "global_seq": int(global_seq),
        "type": type_,
        "actor_id": actor_id,
        "domain_id": domain_id,
        "payload": payload
        if isinstance(payload, dict)
        else json.loads(payload or "{}"),
        "occurred_at": occurred_at.isoformat()
        if hasattr(occurred_at, "isoformat")
        else occurred_at,
    }


def read_batch(
    connection: _Connection, after: int, limit: int = 500
) -> list[dict[str, Any]]:
    """Lee el siguiente lote por `global_seq`. Solo SELECT."""
    cursor = connection.cursor()
    cursor.execute(_SELECT_BATCH, (after, limit))
    return [row_to_event(row) for row in cursor.fetchall()]


def group_by_run(events: Sequence[Mapping[str, Any]]) -> Iterator[list[dict[str, Any]]]:
    """Agrupa por stream preservando el orden de aparición.

    Un trace por run (§3): los eventos de un lote pueden venir intercalados de
    varios runs, y proyectar el lote «tal cual» mezclaría trazas.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        grouped.setdefault(str(event.get("stream_id", "")), []).append(dict(event))
    yield from grouped.values()
