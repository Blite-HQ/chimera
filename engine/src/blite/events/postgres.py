"""
PostgresEventStore — el MISMO puerto `EventStore`, durable (nota 01 §1.5).

INV-5: igual que `writer.py`, SOLO `blite.events.*` puede importar este
módulo; el resto recibe el store vía `blite.events.create_event_store()`
(contrato import-linter). La concurrencia optimista vive en el esquema
(`UNIQUE (stream_id, seq)`, init_v2.sql): la posición esperada se ancla en
el propio INSERT y el conflicto EXPLOTA como `ConcurrentAppendError` — sin
locks, jamás un no-op silencioso. El rechazo post-terminal reusa las MISMAS
reglas de `blite.events.rules` que el store in-memory (una sola fuente).
"""

from __future__ import annotations

from typing import Any

from psycopg import errors
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from blite.events.event import Event
from blite.events.rules import (
    TERMINAL_RUN_EVENTS,
    PostTerminalAppendError,
    rejects_post_terminal,
)
from blite.events.store import ConcurrentAppendError

_COLUMNS = (
    "id, stream_id, seq, global_seq, type, actor_id, domain_id, "
    "payload, occurred_at, prev_hash, hash"
)

# seq se decide DENTRO del statement (posición actual + 1); el WHERE ancla la
# posición esperada — cero filas insertadas = la posición real no es la
# esperada (conflicto o expected_seq adelantado: jamás un hueco). El UNIQUE
# (stream_id, seq) del esquema queda como red de fondo ante la carrera de dos
# escritores que leyeron la misma posición.
_INSERT = f"""
WITH position AS (
    SELECT COALESCE(MAX(seq), 0) AS current
    FROM events
    WHERE stream_id = %(stream_id)s
)
INSERT INTO events (stream_id, seq, type, actor_id, domain_id, payload)
SELECT %(stream_id)s, position.current + 1, %(type)s, %(actor_id)s,
       %(domain_id)s, %(payload)s
FROM position
WHERE %(expected_seq)s::bigint IS NULL OR position.current = %(expected_seq)s
RETURNING {_COLUMNS}
"""

_TERMINAL_EXISTS = (
    "SELECT EXISTS (SELECT 1 FROM events "
    "WHERE stream_id = %(stream_id)s AND type = ANY(%(terminals)s))"
)

_READ_STREAM = (
    f"SELECT {_COLUMNS} FROM events "
    "WHERE stream_id = %(stream_id)s AND seq > %(from_seq)s ORDER BY seq"
)

_READ_ALL = (
    f"SELECT {_COLUMNS} FROM events "
    "WHERE global_seq > %(from_global_seq)s ORDER BY global_seq"
)


def _row_to_event(row: tuple[Any, ...]) -> Event:
    return Event(
        id=row[0],
        stream_id=row[1],
        seq=row[2],
        global_seq=row[3],
        type=row[4],
        actor_id=row[5],
        domain_id=row[6],
        payload=row[7],
        occurred_at=row[8],
        prev_hash=row[9],
        hash=row[10],
    )


class PostgresEventStore:
    """EventStore durable sobre la tabla `events` de init_v2.sql."""

    def __init__(self, conninfo: str, *, min_size: int = 1, max_size: int = 4) -> None:
        self._pool = ConnectionPool(
            conninfo, min_size=min_size, max_size=max_size, open=True
        )

    def close(self) -> None:
        self._pool.close()

    def append(
        self,
        *,
        stream_id: str,
        type: str,
        actor_id: str,
        domain_id: str,
        payload: dict[str, Any],
        expected_seq: int | None = None,
    ) -> Event:
        with self._pool.connection() as conn, conn.cursor() as cur:
            # [S-F] escritura post-terminal = RECHAZO (freeze §2), misma regla
            # que el store in-memory. Chequeo e INSERT van en la misma
            # transacción; un terminal jamás desaparece (append-only), así que
            # el chequeo no puede dar un falso rechazo. (Edge Fase 1: dos
            # escritores concurrentes, terminal en vuelo — el walking skeleton
            # tiene un solo escritor.)
            if rejects_post_terminal(type):
                cur.execute(
                    _TERMINAL_EXISTS,
                    {"stream_id": stream_id, "terminals": list(TERMINAL_RUN_EVENTS)},
                )
                row = cur.fetchone()
                if row is not None and row[0]:
                    raise PostTerminalAppendError(
                        f"stream {stream_id!r} ya tiene su evento terminal: "
                        f"{type!r} se rechaza"
                    )
            try:
                cur.execute(
                    _INSERT,
                    {
                        "stream_id": stream_id,
                        "type": type,
                        "actor_id": actor_id,
                        "domain_id": domain_id,
                        "payload": Jsonb(payload),
                        "expected_seq": expected_seq,
                    },
                )
            except errors.UniqueViolation as exc:
                raise ConcurrentAppendError(
                    f"append concurrente sobre {stream_id!r} (UNIQUE stream_id, seq)"
                ) from exc
            inserted = cur.fetchone()
            if inserted is None:
                raise ConcurrentAppendError(
                    f"expected_seq={expected_seq} no es la posición actual "
                    f"del stream {stream_id!r}"
                )
            return _row_to_event(inserted)

    def read_stream(self, stream_id: str, from_seq: int = 0) -> tuple[Event, ...]:
        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_READ_STREAM, {"stream_id": stream_id, "from_seq": from_seq})
            return tuple(_row_to_event(row) for row in cur.fetchall())

    def read_all(self, from_global_seq: int = 0) -> tuple[Event, ...]:
        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_READ_ALL, {"from_global_seq": from_global_seq})
            return tuple(_row_to_event(row) for row in cur.fetchall())
