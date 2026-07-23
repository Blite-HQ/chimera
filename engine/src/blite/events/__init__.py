"""Events — append-only audit log (public read interface; write via events.writer only — INV-5)."""

from __future__ import annotations

import os

from blite.events.event import Event
from blite.events.store import ConcurrentAppendError, EventStore


def create_event_store(dsn: str | None = None) -> EventStore:
    """Construct an EventStore behind the single port (INV-5).

    Con DSN (argumento o `CHIMERA_DATABASE_URL`) devuelve el store Postgres
    durable (nota 01 §1.5); sin DSN, el in-memory de Fase 1. Only
    blite.events.* may import writer/postgres (INV-5); everyone else gets an
    EventStore through this factory — los callers no cambian con el swap.
    """
    resolved = dsn or os.environ.get("CHIMERA_DATABASE_URL")
    if resolved:
        from blite.events.postgres import PostgresEventStore

        return PostgresEventStore(resolved)
    from blite.events.writer import InMemoryEventStore

    return InMemoryEventStore()


__all__ = ["ConcurrentAppendError", "Event", "EventStore", "create_event_store"]
