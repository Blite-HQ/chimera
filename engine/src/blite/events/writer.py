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

from blite.events.event import Event
from blite.events.store import ConcurrentAppendError


class InMemoryEventStore:
    """In-memory EventStore — one process, not durable, Fase 1 only."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: list[Event] = []
        self._stream_seq: dict[str, int] = {}

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
            new_seq = current_seq + 1
            event = Event(
                id=uuid4(),
                stream_id=stream_id,
                seq=new_seq,
                global_seq=len(self._events) + 1,
                type=type,
                actor_id=actor_id,
                domain_id=domain_id,
                payload=payload,
                occurred_at=datetime.now(tz=UTC),
            )
            self._events.append(event)
            self._stream_seq[stream_id] = new_seq
            return event

    def read_stream(self, stream_id: str, from_seq: int = 0) -> tuple[Event, ...]:
        return tuple(
            e for e in self._events if e.stream_id == stream_id and e.seq > from_seq
        )

    def read_all(self, from_global_seq: int = 0) -> tuple[Event, ...]:
        return tuple(e for e in self._events if e.global_seq > from_global_seq)
