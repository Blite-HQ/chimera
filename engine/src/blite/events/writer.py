"""
Event log writer.

This module is the ONLY place that writes to the append-only event log (INV-5).
All other modules (gateway, runtime, serving, verification, guardrails, authz,
protocols, certificate) are forbidden from importing this module.

Only blite.events.* may import blite.events.writer.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Event:
    """An immutable event record. Written once, never mutated (INV-5)."""

    type: str
    """Event type identifier (e.g., "capability.invoked", "override.requested")."""

    payload: dict[str, Any] = field(default_factory=dict[str, Any])
    """Generic event payload. Must not contain secrets."""

    timestamp: float = field(default_factory=time.time)
    """Unix timestamp of event creation (set by writer, not caller)."""


# In-process append-only log (in-memory for skeleton; replace with persistent store).
_LOG: list[Event] = []


def append(event: Event) -> None:
    """Append an event to the log. The only write operation (INV-5)."""
    _LOG.append(event)


def read_all() -> tuple[Event, ...]:
    """Read all events as an immutable snapshot (no mutation allowed)."""
    return tuple(_LOG)
