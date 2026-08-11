"""Loop del runtime — pipeline fijo de Fase 1 (nota execution/02 §11, freeze §3/§13).

Contrato: run.created (con max_steps/policy_digest obligatorios) → run.started
→ steps discretos (`run.step.*` con RunStep como payload, status de conjunto
cerrado) → capability.job.* 1:1 con el step de invocación (submitted ANTES de
ejecutar — PR1) → terminal. Guard de max_steps: el loop se corta con
run.failed, jamás se cuelga (nota 02 §6/§9). Despacho SOLO vía Registry +
Dispatcher (ADR-008); digests recuperables byte a byte vía ContentStore.
"""

from __future__ import annotations

from typing import Any, Literal

import pytest

from blite.events import create_event_store
from blite.gateway.approval import ApprovalRequestedPayload
from blite.runtime.content_store import InMemoryContentStore
from blite.runtime.dispatch import ProfileDispatcher
from blite.runtime.loop import MAX_STEPS_EXCEEDED, execute_run
from blite.runtime.projection import project_runs
from blite.runtime.registry import EntryPointRegistry
from blite_capability.manifest import CapabilityManifest


class _EchoCapability:
    """Doble genérico (ADR-029): duplica el valor de entrada."""

    def __init__(self, *, explode: bool = False) -> None:
        self.invocations = 0
        self._explode = explode

    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id="cap.echo",
            description="generic test capability",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            side_effects="pure",
            required_permission="capability:invoke",
            interaction="request_response",
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        self.invocations += 1
        if self._explode:
            msg = "simulated capability failure"
            raise RuntimeError(msg)
        return {"doubled": inputs["x"] * 2}


class _ExternalCapability:
    """Doble genérico con `side_effects` externo (TAREA A, freeze §13 —
    escalación de reintentos): dispara siempre, para ejercer el camino de
    fallo de invocación con un `side_effects` distinto de `pure`."""

    def __init__(
        self, *, side_effects: Literal["reversible-external", "irreversible-external"]
    ) -> None:
        self._side_effects: Literal["reversible-external", "irreversible-external"] = (
            side_effects
        )
        self.invocations = 0

    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id="cap.external",
            description="generic test capability with external side effects",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            side_effects=self._side_effects,
            required_permission="capability:invoke",
            interaction="request_response",
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        self.invocations += 1
        msg = "simulated external side-effect failure"
        raise RuntimeError(msg)


def _run(
    capability: _EchoCapability | _ExternalCapability,
    *,
    max_steps: int = 8,
    capability_id: str = "cap.echo",
) -> tuple[Any, Any, Any]:
    store = create_event_store()
    content = InMemoryContentStore()
    registry = EntryPointRegistry({"cap.echo": capability})
    row = execute_run(
        store,
        registry,
        ProfileDispatcher(),
        content,
        run_id="run-1",
        actor_id="user:steven",
        domain_id="domain-a",
        max_steps=max_steps,
        policy_digest="pol-digest-1",
        capability_id=capability_id,
        inputs={"x": 21},
    )
    return row, store, content


def test_happy_path_emits_the_full_frozen_sequence_in_order() -> None:
    row, store, _ = _run(_EchoCapability())

    events = store.read_stream("run-1")
    assert [e.type for e in events] == [
        "run.created",
        "run.started",
        "run.step.started",
        "run.step.completed",
        "run.step.started",
        "capability.job.submitted",
        "capability.job.completed",
        "run.step.completed",
        "run.completed",
    ]
    assert row.status == "completed"
    assert row.output_digest is not None


def test_run_created_carries_everything_the_projection_needs() -> None:
    _, store, _ = _run(_EchoCapability())

    created = store.read_stream("run-1")[0]
    assert created.actor_id == "user:steven"
    assert created.payload["max_steps"] == 8
    assert created.payload["policy_digest"] == "pol-digest-1"

    # Replay regenera la proyección desde el log solo (freeze §3 stress-final).
    replayed = project_runs(store.read_all())["run-1"]
    assert replayed.status == "completed"
    assert replayed.policy_digest == "pol-digest-1"


def test_steps_are_deterministic_and_job_correlates_1_to_1() -> None:
    _, store, _ = _run(_EchoCapability())

    events = store.read_stream("run-1")
    started = [e for e in events if e.type == "run.step.started"]
    # Replay-igualdad estructural (nota 02 §9): mismos step_id, mismo orden.
    assert [e.payload["step_id"] for e in started] == ["step-1", "step-2"]
    assert [e.payload["kind"] for e in started] == ["resolve", "invoke"]
    assert all(e.payload["status"] == "running" for e in started)

    submitted = next(e for e in events if e.type == "capability.job.submitted")
    completed = next(e for e in events if e.type == "capability.job.completed")
    assert submitted.payload["step_id"] == "step-2"
    assert submitted.payload["capability_id"] == "cap.echo"
    assert completed.payload["job_id"] == submitted.payload["job_id"]


def test_output_digest_is_recoverable_byte_for_byte() -> None:
    row, _, content = _run(_EchoCapability())

    recovered = content.get(row.output_digest, {"domain_id": "domain-a"})
    assert recovered == b'{"doubled":42}'


def test_max_steps_guard_cuts_the_loop_instead_of_hanging() -> None:
    capability = _EchoCapability()
    row, store, _ = _run(capability, max_steps=1)

    assert row.status == "failed"
    assert row.error_kind == MAX_STEPS_EXCEEDED
    # El guard corta ANTES del step de invocación: la capability jamás corre.
    assert capability.invocations == 0
    types = [e.type for e in store.read_stream("run-1")]
    assert types[-1] == "run.failed"
    assert "capability.job.submitted" not in types


def test_unknown_capability_fails_the_resolve_step_and_the_run() -> None:
    row, store, _ = _run(_EchoCapability(), capability_id="cap.missing")

    assert row.status == "failed"
    assert row.error_kind == "KeyError"
    types = [e.type for e in store.read_stream("run-1")]
    assert types == [
        "run.created",
        "run.started",
        "run.step.started",
        "run.step.failed",
        "run.failed",
    ]


def test_capability_failure_is_recorded_with_submitted_before_the_job_failed() -> None:
    row, store, _ = _run(_EchoCapability(explode=True))

    assert row.status == "failed"
    assert row.error_kind == "RuntimeError"
    types = [e.type for e in store.read_stream("run-1")]
    # PR1: capability.job.submitted se emite ANTES de ejecutar — el rastro
    # existe aunque la ejecución explote.
    assert types[-4:] == [
        "capability.job.submitted",
        "capability.job.failed",
        "run.step.failed",
        "run.failed",
    ]
    # freeze §13: `pure` se reintenta libre — NUNCA escala a humano. Sin esto
    # un fallo `pure` sería indistinguible de uno externo en el rastro.
    assert "approval.requested" not in types


def test_irreversible_external_failure_escalates_to_a_human() -> None:
    """freeze §13 (Reintentos e idempotencia): `irreversible-external` sin
    idempotencia garantizada — el manifest hoy no declara ningún campo de
    idempotencia, así que "sin garantía" es el estado de TODO side_effects
    externo — NO tiene reintento automático en Fase 1: escala a humano. La
    escalación reusa el par elicitation `approval.requested`/`approval.
    responded` YA existente (A6), jamás un evento nuevo — un `run.failed`
    externo deja de ser indistinguible de cualquier otro."""
    row, store, _ = _run(_ExternalCapability(side_effects="irreversible-external"))

    assert row.status == "failed"
    assert row.error_kind == "RuntimeError"
    events = store.read_stream("run-1")
    types = [e.type for e in events]
    # La escalación queda ENTRE el step fallido y el terminal — append-only,
    # nunca reemplazada ni perdida.
    assert types[-3:] == ["run.step.failed", "approval.requested", "run.failed"]

    escalation = next(e for e in events if e.type == "approval.requested")
    # Anti-drift (mismo patrón que test_agentic_loop.py): el dict emitido
    # valida contra la forma congelada del wire, no solo "algo se emitió".
    payload = ApprovalRequestedPayload.model_validate(escalation.payload)
    assert payload.run_id == "run-1"
    assert payload.step_id == "step-2"  # el step de invoke, no el de resolve


def test_reversible_external_failure_escalates_to_a_human() -> None:
    """Mismo contrato que el caso irreversible — freeze §13 no distingue
    `reversible-external` de `irreversible-external` para la regla de
    reintento: ambos carecen de idempotencia garantizada hoy."""
    row, store, _ = _run(_ExternalCapability(side_effects="reversible-external"))

    assert row.status == "failed"
    events = store.read_stream("run-1")
    types = [e.type for e in events]
    assert "approval.requested" in types

    escalation = next(e for e in events if e.type == "approval.requested")
    payload = ApprovalRequestedPayload.model_validate(escalation.payload)
    assert payload.run_id == "run-1"
    assert payload.step_id == "step-2"


def test_run_id_in_the_system_namespace_is_rejected_before_any_append() -> None:
    store = create_event_store()
    registry = EntryPointRegistry({"cap.echo": _EchoCapability()})

    with pytest.raises(ValueError, match="system:"):
        execute_run(
            store,
            registry,
            ProfileDispatcher(),
            InMemoryContentStore(),
            run_id="system:registry",
            actor_id="user:steven",
            domain_id="domain-a",
            max_steps=8,
            policy_digest="pol-digest-1",
            capability_id="cap.echo",
            inputs={},
        )
    assert store.read_all() == ()


class _RemoteJobCapability:
    """Doble genérico cuyo manifest declara un perfil SIN estrategia en Fase 1."""

    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id="cap.remote",
            description="generic test capability",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            side_effects="pure",
            required_permission="capability:invoke",
            interaction="job",
            execution_profile="remote-job",
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        msg = "remote-job jamás debe ejecutarse in-process (freeze §1)"
        raise AssertionError(msg)


def test_dispatch_resolves_by_the_manifests_execution_profile() -> None:
    """Manifest v2 (C1): el loop despacha por `manifest.execution_profile` —
    un perfil sin estrategia falla el run (NotImplementedError), jamás
    fallback silencioso a in-process (freeze §1)."""
    store = create_event_store()
    registry = EntryPointRegistry({"cap.remote": _RemoteJobCapability()})
    row = execute_run(
        store,
        registry,
        ProfileDispatcher(),
        InMemoryContentStore(),
        run_id="run-1",
        actor_id="user:steven",
        domain_id="domain-a",
        max_steps=8,
        policy_digest="pol-digest-1",
        capability_id="cap.remote",
        inputs={"x": 21},
    )
    assert row.status == "failed"
    failed = [e for e in store.read_stream("run-1") if e.type == "run.failed"]
    assert failed[0].payload["error_kind"] == "NotImplementedError"
