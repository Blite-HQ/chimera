"""
Type-level invariant tests.

These tests use assert_type() and runtime assertions to fix critical
type signatures. Pyright checks them statically in CI.

Run: uv run pyright tests/invariants/test_types.py
"""

from __future__ import annotations

import dataclasses
from typing import Any, assert_type

import pytest

from blite_capability.capability import Capability
from blite_capability.manifest import CapabilityManifest
from blite_capability.registry import discover_capabilities

# ── CapabilityManifest invariants ─────────────────────────────────────────────


def test_manifest_is_frozen() -> None:
    """CapabilityManifest must be immutable (frozen dataclass — ADR-029)."""
    m = CapabilityManifest(
        id="test.capability",
        description="A generic test capability",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.id = "mutated"  # type: ignore[misc]


def test_manifest_field_types() -> None:
    """Manifest fields have the correct static types."""
    m = CapabilityManifest(
        id="blite.solvers.qubo",
        description="Solve a QUBO matrix",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
    )
    assert_type(m.id, str)
    assert_type(m.description, str)
    assert_type(m.input_schema, dict[str, Any])
    assert_type(m.output_schema, dict[str, Any])
    assert_type(m.version, str)
    assert_type(m.tags, tuple[str, ...])


def test_manifest_schemas_are_dicts() -> None:
    """Schemas must be plain dicts — no domain-specific containers (ADR-029)."""
    m = CapabilityManifest(
        id="blite.graphs.partition",
        description="Partition a graph into balanced components",
        input_schema={"type": "object", "properties": {"adjacency": {"type": "array"}}},
        output_schema={
            "type": "object",
            "properties": {"partition": {"type": "array"}},
        },
    )
    assert isinstance(m.input_schema, dict)
    assert isinstance(m.output_schema, dict)


# ── Registry invariants ───────────────────────────────────────────────────────


def test_registry_return_type() -> None:
    """discover_capabilities() must return a plain dict."""
    caps = discover_capabilities()
    assert_type(caps, dict[str, Capability])
    assert isinstance(caps, dict)


# ── Event writer invariants ───────────────────────────────────────────────────


def test_event_log_is_append_only() -> None:
    """The event writer exposes append and read_all but NOT update or delete (INV-5)."""
    from blite.events import writer

    assert callable(writer.append), "writer.append must be callable"
    assert callable(writer.read_all), "writer.read_all must be callable"
    assert not hasattr(writer, "update"), (
        "writer must NOT have an update function (INV-5)"
    )
    assert not hasattr(writer, "delete"), (
        "writer must NOT have a delete function (INV-5)"
    )


@pytest.mark.xfail(
    reason=(
        "AX1 (base lógica, Identidad): every action must be attributable to "
        "exactly one actor. Event has no actor_id yet — the identity module "
        "does not exist. Tracked placeholder; flip to a real assertion once "
        "the gateway stamps identity on every event. Do not delete this test "
        "to make it pass — that would silently drop AX1 enforcement."
    ),
    strict=False,
)
def test_event_has_non_null_actor_id() -> None:
    """AX1: every Event must carry a required, non-empty actor_id."""
    from blite.events.writer import Event

    fields = {f.name: f for f in dataclasses.fields(Event)}
    assert "actor_id" in fields, "Event is missing the actor_id field (AX1)"

    event = Event(type="test.invariant", payload={}, actor_id="test-actor")  # type: ignore[call-arg]
    assert event.actor_id, "actor_id must not be empty (AX1)"  # type: ignore[attr-defined]


def test_event_append_produces_immutable_event() -> None:
    """Appended events must be immutable (frozen=True — INV-5)."""
    from blite.events.writer import Event, append, read_all

    before_count = len(read_all())
    event = Event(type="test.invariant", payload={"key": "value"})
    append(event)
    after = read_all()
    assert len(after) == before_count + 1
    assert after[-1].type == "test.invariant"

    # Frozen: mutation should raise FrozenInstanceError
    with pytest.raises(dataclasses.FrozenInstanceError):
        after[-1].type = "mutated"  # type: ignore[misc]
