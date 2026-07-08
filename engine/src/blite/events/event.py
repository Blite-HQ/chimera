"""
Event — the append-only log's single record shape (v2).

docs/contract-freeze.md SS2 / knowledge/trust/01-event-sourcing-postgres.md
SS1.5: replaces the Fase-1 dataclass in blite.events.writer. `actor_id` is
now required (AX1's material prerequisite — see the still-xfail
test_event_has_non_null_actor_id in tests/invariants/test_types.py: the
field existing is not the same as the gateway guaranteeing a real identity
fills it). `global_seq` is the cross-stream cursor for SSE catch-up;
`prev_hash`/`hash` stay reserved and empty until the Fase 2 hash-chain.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Event(BaseModel):
    """A single immutable, append-only log record."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    stream_id: str
    seq: int
    global_seq: int
    type: str
    actor_id: str
    domain_id: str
    payload: dict[str, Any]
    occurred_at: datetime
    prev_hash: str | None = None
    hash: str | None = None
