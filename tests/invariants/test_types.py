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

from blite.events import create_event_store
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
        side_effects="pure",
        required_permission="capability:invoke",
        interaction="request_response",
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
        side_effects="pure",
        required_permission="capability:invoke",
        interaction="request_response",
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
        side_effects="pure",
        required_permission="capability:invoke",
        interaction="request_response",
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
    """The EventStore port exposes append/read_stream/read_all but NOT update or delete (INV-5)."""
    from blite.events.writer import InMemoryEventStore

    assert callable(InMemoryEventStore.append), "append must be callable"
    assert callable(InMemoryEventStore.read_stream), "read_stream must be callable"
    assert callable(InMemoryEventStore.read_all), "read_all must be callable"
    assert not hasattr(InMemoryEventStore, "update"), (
        "InMemoryEventStore must NOT have an update method (INV-5)"
    )
    assert not hasattr(InMemoryEventStore, "delete"), (
        "InMemoryEventStore must NOT have a delete method (INV-5)"
    )


@pytest.mark.xfail(
    reason=(
        "AX1 (base lógica, Identidad): every action must be attributable to "
        "exactly one actor. Event.actor_id is now a required Pydantic field "
        "(ficha B2, sesión 7) and EventStore.append() requires it as a "
        "mandatory keyword argument — but nothing yet GUARANTEES every "
        "caller receives a gateway-verified identity to pass in; that "
        "wiring (gateway identity stage stamps InvocationContext.actor_id "
        "on every request) is post-freeze, knowledge/trust/08 SS1.4 step 2. "
        "Tracked placeholder; flip to a real assertion once the gateway "
        "stamps identity end-to-end. Do not delete this test to make it "
        "pass — that would silently drop AX1 enforcement."
    ),
    strict=False,
)
def test_event_has_non_null_actor_id() -> None:
    """AX1: every Event must carry a required, non-empty actor_id."""
    from blite.events.event import Event

    assert "actor_id" in Event.model_fields, "Event is missing the actor_id field (AX1)"

    store = create_event_store()
    event = store.append(
        stream_id="run:ax1-check",
        type="test.invariant",
        actor_id="test-actor",
        domain_id="d-default",
        payload={},
    )
    assert event.actor_id, "actor_id must not be empty (AX1)"


def test_event_append_produces_immutable_event() -> None:
    """Appended events must be immutable (frozen=True — INV-5)."""
    from pydantic import ValidationError

    store = create_event_store()
    before = store.read_all()
    event = store.append(
        stream_id="run:immutable-check",
        type="test.invariant",
        actor_id="test-actor",
        domain_id="d-default",
        payload={"key": "value"},
    )
    after = store.read_all()
    assert len(after) == len(before) + 1
    assert after[-1].type == "test.invariant"
    assert event.type == "test.invariant"

    with pytest.raises(ValidationError):
        after[-1].type = "mutated"
