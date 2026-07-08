"""Events — append-only audit log (public read interface; write via events.writer only — INV-5)."""

from __future__ import annotations

from blite.events.event import Event
from blite.events.store import ConcurrentAppendError, EventStore


def create_event_store() -> EventStore:
    """Construct the Fase 1 in-memory EventStore.

    Only blite.events.* may import blite.events.writer (INV-5); everyone
    else gets an EventStore through this factory.
    """
    from blite.events.writer import InMemoryEventStore

    return InMemoryEventStore()


__all__ = ["ConcurrentAppendError", "Event", "EventStore", "create_event_store"]
