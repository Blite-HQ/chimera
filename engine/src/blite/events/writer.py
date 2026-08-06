"""
Event log writer — the ONLY module that holds append-only log state.

INV-5: all other modules (gateway, runtime, serving, verification,
guardrails, authz, protocols, certificate, identity) are forbidden from
importing this module (pyproject.toml import-linter contract). They get an
EventStore through blite.events.create_event_store() instead.

This is the Fase 1 in-memory implementation; note 01 SS1.5 replaces it with
a Postgres-backed implementation behind the same EventStore port in a later
session without changing this file's callers.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from blite.events.chain import GENESIS_PREV_HASH, chain_hash, view_of
from blite.events.event import Event
from blite.events.rules import (
    TERMINAL_RUN_EVENTS,
    PostTerminalAppendError,
    rejects_post_terminal,
)
from blite.events.store import ConcurrentAppendError


class InMemoryEventStore:
    """In-memory EventStore — one process, not durable, Fase 1 only."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: list[Event] = []
        self._stream_seq: dict[str, int] = {}
        self._stream_head: dict[str, str] = {}
        self._terminal_streams: set[str] = set()

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
        with self._lock:
            current_seq = self._stream_seq.get(stream_id, 0)
            if expected_seq is not None and expected_seq != current_seq:
                raise ConcurrentAppendError(
                    f"expected_seq={expected_seq} but stream {stream_id!r} is at {current_seq}"
                )
            # [S-F] escritura post-terminal = RECHAZO (freeze §2): run.step.*/
            # capability.job.* tras el terminal romperían el recompute del
            # provenance_hash de un certificado ya emitido.
            if stream_id in self._terminal_streams and rejects_post_terminal(type):
                raise PostTerminalAppendError(
                    f"stream {stream_id!r} ya tiene su evento terminal: {type!r} se rechaza"
                )
            new_seq = current_seq + 1
            # Hash-chain por evento (anexo §4, C5/M8 pieza 1): se computa
            # AQUÍ, en el writer, porque es el único punto donde el evento
            # queda definido (id/seq/occurred_at ya asignados) y todavía no
            # es visible para nadie — encadenar después sería reescribir el
            # log, que es exactamente lo que la cadena existe para detectar.
            prev_hash = self._stream_head.get(stream_id, GENESIS_PREV_HASH)
            fields: dict[str, Any] = {
                "id": uuid4(),
                "stream_id": stream_id,
                "seq": new_seq,
                "type": type,
                "actor_id": actor_id,
                "domain_id": domain_id,
                "payload": payload,
                "occurred_at": datetime.now(tz=UTC),
            }
            event_hash = chain_hash(prev_hash=prev_hash, view=view_of(**fields))
            event = Event(
                **fields,
                global_seq=len(self._events) + 1,
                prev_hash=prev_hash,
                hash=event_hash,
            )
            self._events.append(event)
            self._stream_seq[stream_id] = new_seq
            self._stream_head[stream_id] = event_hash
            if type in TERMINAL_RUN_EVENTS:
                self._terminal_streams.add(stream_id)
            return event

    def read_stream(self, stream_id: str, from_seq: int = 0) -> tuple[Event, ...]:
        return tuple(
            e for e in self._events if e.stream_id == stream_id and e.seq > from_seq
        )

    def read_all(self, from_global_seq: int = 0) -> tuple[Event, ...]:
        return tuple(e for e in self._events if e.global_seq > from_global_seq)
