"""Las 6 etapas reales del chokepoint — C2/M2 (freeze §8, execution/01 §1.2).

identity: rechaza SOLO identidad inválida (coherencia de dominio) — jamás
política. authorization: `required_permission` del manifest v2 contra los
permisos de la Identity — la decisión se estampa y las etapas posteriores
solo la LEEN. guardrails: Signals no-decisionales registrados como eventos
(INV-3: jamás deciden). provenance:pre/post: `capability.job.submitted/
completed` con el actor REAL del cruce (AX1). verification: seam delegado
(INV-2) + consistencia fail-closed. mediation/egress ya eran reales.
"""

from __future__ import annotations

from typing import Any

from blite.events import create_event_store
from blite.gateway.context import GatewayContext
from blite.gateway.pipeline import Rejection
from blite.gateway.stages import (
    AuthorizationStage,
    GuardrailsStage,
    IdentityStage,
    MediationStage,
    ProvenancePostStage,
    ProvenancePreStage,
    VerificationStage,
)
from blite.guardrails import Signal
from blite.identity.identity import Identity
from blite.runtime.content_store import InMemoryContentStore
from blite.runtime.digests import digest_via
from blite.runtime.dispatch import ProfileDispatcher
from blite.runtime.registry import EntryPointRegistry
from blite_capability.manifest import CapabilityManifest


class _EchoCapability:
    def __init__(self, *, explode: bool = False) -> None:
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
        if self._explode:
            msg = "boom"
            raise RuntimeError(msg)
        return {"echo": inputs}


def _identity(
    permissions: frozenset[str] = frozenset({"capability:invoke"}),
) -> Identity:
    return Identity(
        id="user:ax1", kind="human", domain_id="domain-a", permissions=permissions
    )


def _ctx(**overrides: Any) -> GatewayContext:
    base: dict[str, Any] = {
        "identity": _identity(),
        "capability_id": "cap.echo",
        "inputs": {"x": 1},
        "run_id": "run-1",
        "step_id": "step-2",
        "domain_id": "domain-a",
    }
    base.update(overrides)
    return GatewayContext.model_validate(base)


def _registry(*, explode: bool = False) -> EntryPointRegistry:
    return EntryPointRegistry({"cap.echo": _EchoCapability(explode=explode)})


# ── identity ────────────────────────────────────────────────────────────────


def test_identity_pasa_un_ctx_coherente() -> None:
    result = IdentityStage().handle(_ctx())
    assert isinstance(result, GatewayContext)


def test_identity_rechaza_dominio_incoherente() -> None:
    """execution/01: identity rechaza SOLO identidad inválida — un cruce que
    declara un dominio distinto al de la Identity ES identidad inválida."""
    result = IdentityStage().handle(_ctx(domain_id="domain-b"))
    assert isinstance(result, Rejection)
    assert result.stage == "identity"


# ── authorization ───────────────────────────────────────────────────────────


def test_authorization_estampa_la_decision_con_permiso_presente() -> None:
    result = AuthorizationStage(_registry()).handle(_ctx(authz=None))
    assert isinstance(result, GatewayContext)
    assert result.authz is not None
    assert result.authz.allowed
    assert result.authz.decided_by == "authorization"


def test_authorization_sin_permiso_corta_antes_de_despachar() -> None:
    ctx = _ctx(identity=_identity(frozenset({"otro:permiso"})), authz=None)
    result = AuthorizationStage(_registry()).handle(ctx)
    assert isinstance(result, Rejection)
    assert result.stage == "authorization"
    assert "capability:invoke" in result.reason


def test_authorization_capability_desconocida_es_rejection() -> None:
    result = AuthorizationStage(_registry()).handle(
        _ctx(capability_id="cap.fantasma", authz=None)
    )
    assert isinstance(result, Rejection)
    assert result.stage == "authorization"


# ── guardrails ──────────────────────────────────────────────────────────────


def _flagging_guard(ctx: GatewayContext) -> Signal:
    return Signal(
        detector="test-guard",
        kind="gateway.payload_shape",
        target=ctx.capability_id,
        flagged=True,
    )


def test_guardrails_registra_la_senal_como_evento_y_jamas_decide() -> None:
    """INV-3: la señal flagged se REGISTRA (`signal.recorded`, actor real)
    pero NO corta la cadena — non_decisional hecho mecanismo."""
    store = create_event_store()
    stage = GuardrailsStage(guards=(_flagging_guard,), store=store)
    result = stage.handle(_ctx())
    assert isinstance(result, GatewayContext)
    events = store.read_stream("run-1")
    assert [e.type for e in events] == ["signal.recorded"]
    assert events[0].actor_id == "user:ax1"
    assert events[0].payload["flagged"] is True


def test_guardrails_que_explota_es_rejection_fail_closed() -> None:
    def _broken(ctx: GatewayContext) -> Signal:
        msg = "detector roto"
        raise RuntimeError(msg)

    result = GuardrailsStage(guards=(_broken,), store=create_event_store()).handle(
        _ctx()
    )
    assert isinstance(result, Rejection)
    assert result.stage == "guardrails"


# ── provenance:pre / provenance:post ────────────────────────────────────────


def test_provenance_pre_emite_submitted_antes_de_despachar_con_actor_real() -> None:
    store = create_event_store()
    content = InMemoryContentStore()
    result = ProvenancePreStage(store, content).handle(_ctx())
    assert isinstance(result, GatewayContext)
    events = store.read_stream("run-1")
    assert [e.type for e in events] == ["capability.job.submitted"]
    payload = events[0].payload
    assert payload["job_id"] == "step-2:job"
    assert payload["step_id"] == "step-2"
    assert payload["capability_id"] == "cap.echo"
    assert payload["input_digest"] == digest_via(content, {"x": 1}, "domain-a")
    assert events[0].actor_id == "user:ax1"


def test_provenance_pre_sin_run_o_step_es_rejection() -> None:
    """PR1 exige rastro: un cruce sin procedencia (run/step) no despacha."""
    result = ProvenancePreStage(create_event_store(), InMemoryContentStore()).handle(
        _ctx(run_id=None, step_id=None)
    )
    assert isinstance(result, Rejection)
    assert result.stage == "provenance:pre"


def test_provenance_post_emite_completed_con_output_digest() -> None:
    store = create_event_store()
    content = InMemoryContentStore()
    ctx = _ctx(outputs={"echo": {"x": 1}})
    result = ProvenancePostStage(store, content).handle(ctx)
    assert isinstance(result, GatewayContext)
    events = store.read_stream("run-1")
    assert [e.type for e in events] == ["capability.job.completed"]
    payload = events[0].payload
    assert payload["job_id"] == "step-2:job"
    assert payload["output_digest"] == digest_via(
        content, {"echo": {"x": 1}}, "domain-a"
    )
    assert events[0].actor_id == "user:ax1"


# ── mediation (extensión: journaliza el job fallido) ────────────────────────


def test_mediation_que_explota_journaliza_job_failed_antes_del_rejection() -> None:
    from blite.authz import AuthzDecision

    store = create_event_store()
    stage = MediationStage(_registry(explode=True), ProfileDispatcher(), store=store)
    allowed = AuthzDecision(
        allowed=True, reason="permiso presente", decided_by="authorization"
    )
    result = stage.handle(_ctx(authz=allowed))
    assert isinstance(result, Rejection)
    assert result.stage == "mediation"
    events = store.read_stream("run-1")
    assert [e.type for e in events] == ["capability.job.failed"]
    assert events[0].payload["error_kind"] == "RuntimeError"
    assert events[0].actor_id == "user:ax1"


# ── verification ────────────────────────────────────────────────────────────


def test_verification_sin_outputs_es_rejection_fail_closed() -> None:
    """Consistencia del cruce: llegar a verification sin outputs = chokepoint
    roto (mediation nunca estampó) — jamás seguir en silencio."""
    result = VerificationStage().handle(_ctx(outputs=None))
    assert isinstance(result, Rejection)
    assert result.stage == "verification"


def test_verification_es_seam_delegado_no_decide() -> None:
    """INV-2/R-Pol1: la verificación del run vive en el delegate post-invoke;
    la etapa es el seam por invocación — con outputs presentes, pasa."""
    result = VerificationStage().handle(_ctx(outputs={"echo": 1}))
    assert isinstance(result, GatewayContext)
