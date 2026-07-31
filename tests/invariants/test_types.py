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


def test_event_has_non_null_actor_id() -> None:
    """AX1: every Event carries a required actor_id AND the gateway stamps
    the verified identity end-to-end.

    Flipped from xfail in C2/M2 (Fase 1 Mejorado, freeze §8 «Ruta del flip
    AX1»): the gateway's identity stage + provenance stages now stamp the
    crossing's real Identity on every capability.job.* event — the exact
    condition the placeholder tracked (knowledge/trust/08 SS1.4 step 2).
    The assertion is HARDENED to actor provenance, never deleted: events
    emitted by the crossing carry the verified identity's id, not a
    runtime service default.
    """
    from blite.events.event import Event
    from blite.gateway.crossing import RunCrossing, build_run_pipeline
    from blite.identity.identity import Identity
    from blite.runtime.content_store import InMemoryContentStore
    from blite.runtime.dispatch import ProfileDispatcher
    from blite.runtime.loop import CrossingRequest
    from blite.runtime.registry import EntryPointRegistry

    assert "actor_id" in Event.model_fields, "Event is missing the actor_id field (AX1)"
    assert Event.model_fields["actor_id"].is_required(), (
        "actor_id must be a required field (AX1)"
    )

    store = create_event_store()
    event = store.append(
        stream_id="run:ax1-check",
        type="test.invariant",
        actor_id="test-actor",
        domain_id="d-default",
        payload={},
    )
    assert event.actor_id, "actor_id must not be empty (AX1)"

    # Provenance of the actor: a full gateway crossing stamps the VERIFIED
    # identity on the job events — the wiring the xfail used to wait for.
    class _Echo:
        @property
        def manifest(self) -> CapabilityManifest:
            return CapabilityManifest(
                id="cap.ax1-echo",
                description="generic echo for the AX1 gate",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                side_effects="pure",
                required_permission="capability:invoke",
                interaction="request_response",
            )

        def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
            return {"echo": inputs}

    crossing_store = create_event_store()
    identity = Identity(
        id="user:ax1-verified",
        kind="human",
        domain_id="d-default",
        permissions=frozenset({"capability:invoke"}),
    )
    crossing = RunCrossing(
        build_run_pipeline(
            registry=EntryPointRegistry({"cap.ax1-echo": _Echo()}),
            dispatcher=ProfileDispatcher(),
            store=crossing_store,
            content=InMemoryContentStore(),
        ),
        identity,
    )
    outputs = crossing(
        CrossingRequest(
            run_id="ax1-crossing",
            step_id="step-1",
            domain_id="d-default",
            capability_id="cap.ax1-echo",
            inputs={"x": 1},
        )
    )
    assert isinstance(outputs, dict), "the crossing must complete (AX1 gate)"
    job_events = [
        e
        for e in crossing_store.read_stream("ax1-crossing")
        if e.type.startswith("capability.job.")
    ]
    assert job_events, "the crossing must journal the job events (AX1)"
    assert all(e.actor_id == "user:ax1-verified" for e in job_events), (
        "every crossing event must carry the gateway-verified actor (AX1)"
    )


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
