"""El cruce del gateway INYECTADO en `execute_run` — C2/M2 (freeze §8 C-5).

Interpretación §13 registrada: UN cruce por invocación de capability
(resolve es parte de mediation). El `Pipeline` entra como el `proposer`
(inyección, jamás import runtime→gateway — contrato `layers`); los eventos
del job los emiten las etapas de provenance CON el actor real del cruce
(AX1); un `Rejection` mapea a `run.step.failed` + `run.failed
{error_kind: "GatewayRejection", stage, reason}`.
"""

from __future__ import annotations

from typing import Any

from blite.events import create_event_store
from blite.gateway.approval import ApprovalRequestedPayload
from blite.gateway.crossing import RunCrossing, build_run_pipeline
from blite.identity.identity import Identity
from blite.runtime.content_store import InMemoryContentStore
from blite.runtime.dispatch import ProfileDispatcher
from blite.runtime.loop import GATEWAY_REJECTION_ERROR_KIND, execute_run
from blite.runtime.registry import EntryPointRegistry
from blite_capability.manifest import CapabilityManifest


class _EchoCapability:
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
        return {"doubled": inputs["x"] * 2}


class _ExplodingExternalCapability:
    """Doble con `side_effects="irreversible-external"` que SIEMPRE falla al
    invocar — TAREA A (freeze §13): ejerce la escalación cuando la
    invocación real ocurre DENTRO de `MediationStage`, no en el dispatch
    directo de `loop.py` (los dos caminos de fallo de invocación)."""

    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id="cap.external",
            description="generic test capability with external side effects",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            side_effects="irreversible-external",
            required_permission="capability:invoke",
            interaction="request_response",
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        msg = "simulated external side-effect failure"
        raise RuntimeError(msg)


def _identity(permissions: frozenset[str]) -> Identity:
    return Identity(
        id="user:jwt-real",
        kind="human",
        domain_id="domain-a",
        permissions=permissions,
    )


def _run_with_crossing(
    permissions: frozenset[str],
    *,
    capability: Any = None,
    capability_id: str = "cap.echo",
) -> tuple[Any, Any]:
    store = create_event_store()
    content = InMemoryContentStore()
    registry = EntryPointRegistry(
        {capability_id: capability if capability is not None else _EchoCapability()}
    )
    dispatcher = ProfileDispatcher()
    pipeline = build_run_pipeline(
        registry=registry, dispatcher=dispatcher, store=store, content=content
    )
    row = execute_run(
        store,
        registry,
        dispatcher,
        content,
        run_id="run-1",
        actor_id="user:jwt-real",
        domain_id="domain-a",
        max_steps=8,
        policy_digest="pol-digest-1",
        capability_id=capability_id,
        inputs={"x": 21},
        crossing=RunCrossing(pipeline, _identity(permissions)),
    )
    return row, store


def test_el_cruce_completo_conserva_la_secuencia_congelada() -> None:
    """Con el Pipeline inyectado, la secuencia observable del run es la MISMA
    del pipeline fijo — el cruce emite los `capability.job.*`, el loop los
    `run.*`/`run.step.*`."""
    row, store = _run_with_crossing(frozenset({"capability:invoke"}))
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


def test_los_eventos_del_job_llevan_el_actor_real_del_cruce() -> None:
    """AX1: `capability.job.*` los emite provenance con la Identity del cruce
    — jamás `service:runtime` (la ruta del flip AX1, freeze §8)."""
    _, store = _run_with_crossing(frozenset({"capability:invoke"}))
    job_events = [
        e for e in store.read_stream("run-1") if e.type.startswith("capability.job.")
    ]
    assert job_events, "el cruce debió emitir eventos de job"
    assert all(e.actor_id == "user:jwt-real" for e in job_events)


def test_el_digest_del_step_y_el_del_job_coinciden() -> None:
    """Una sola puerta canónica (blite.runtime.digests): el input_digest del
    run.step.started(invoke) == el del capability.job.submitted."""
    _, store = _run_with_crossing(frozenset({"capability:invoke"}))
    events = store.read_stream("run-1")
    submitted = next(e for e in events if e.type == "capability.job.submitted")
    invoke_started = [e for e in events if e.type == "run.step.started"][1]
    assert submitted.payload["input_digest"] == invoke_started.payload["input_digest"]


def test_rejection_mapea_a_step_failed_y_run_failed() -> None:
    """Sin el permiso del manifest, authorization corta: run.step.failed +
    run.failed {error_kind: GatewayRejection, stage, reason} — aditivo."""
    row, store = _run_with_crossing(frozenset({"otro:permiso"}))
    events = store.read_stream("run-1")
    assert [e.type for e in events][-2:] == ["run.step.failed", "run.failed"]
    failed = events[-1]
    assert failed.payload["error_kind"] == GATEWAY_REJECTION_ERROR_KIND
    assert failed.payload["stage"] == "authorization"
    assert "capability:invoke" in failed.payload["reason"]
    assert row.status == "failed"
    # La capability jamás se despachó: cero capability.job.* en el rastro.
    assert not [e for e in events if e.type.startswith("capability.job.")]
    # Rejection de authorization: la capability NUNCA se intentó — nada
    # externo pasó, así que la escalación de §13 no aplica (TAREA A).
    assert "approval.requested" not in [e.type for e in events]


def test_mediation_failure_of_an_external_capability_escalates_to_a_human() -> None:
    """TAREA A (freeze §13): con cruce inyectado, una invocación que
    REALMENTE se intentó y falló llega como `CrossingRejected(stage=
    "mediation")` (`MediationStage`, `blite/gateway/stages.py`) — no como
    una excepción cruda. La escalación tiene que reconocer ESE `stage`,
    no solo el camino de dispatch directo sin cruce."""
    row, store = _run_with_crossing(
        frozenset({"capability:invoke"}),
        capability=_ExplodingExternalCapability(),
        capability_id="cap.external",
    )
    events = store.read_stream("run-1")
    types = [e.type for e in events]

    assert row.status == "failed"
    failed = events[-1]
    assert failed.payload["error_kind"] == GATEWAY_REJECTION_ERROR_KIND
    assert failed.payload["stage"] == "mediation"

    assert "approval.requested" in types
    escalation = next(e for e in events if e.type == "approval.requested")
    payload = ApprovalRequestedPayload.model_validate(escalation.payload)
    assert payload.run_id == "run-1"
