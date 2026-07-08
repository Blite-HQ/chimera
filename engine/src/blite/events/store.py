"""
EventStore — the only port through which the log is written or read.

knowledge/trust/01-event-sourcing-postgres.md SS1.5: append/read_stream/
read_all. `expected_seq` is optimistic concurrency (message-db/EventStoreDB
pattern): the caller passes the last seq it observed; the store computes
`seq = expected_seq + 1`. A conflicting write raises ConcurrentAppendError —
explicit, not a silent overwrite.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from blite.events.event import Event


class ConcurrentAppendError(Exception):
    """Raised when `expected_seq` no longer matches the stream's current position."""


@runtime_checkable
class EventStore(Protocol):
    """The single write/read port for the append-only event log (INV-5)."""

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
        """Append one event; assigns id/seq/global_seq/occurred_at."""
        ...

    def read_stream(self, stream_id: str, from_seq: int = 0) -> tuple[Event, ...]:
        """Read one stream's events with seq > from_seq, in seq order."""
        ...

    def read_all(self, from_global_seq: int = 0) -> tuple[Event, ...]:
        """Read all events with global_seq > from_global_seq — the SSE/projection cursor."""
        ...
