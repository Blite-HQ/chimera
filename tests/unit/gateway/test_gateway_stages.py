"""Etapas reales `mediation`/`egress` — freeze §8 + §5/EX-14 (acuerdo 2026-07-22).

mediation: despacho SOLO vía Registry + Dispatcher (INV-1); fail-closed como
`Rejection` ante capability desconocida, despacho que explota o ausencia de
decisión de authz (defensa en profundidad). egress: gobernado ÚNICAMENTE por
`AuthzDecision` (Inv-E) — decisión ausente o `allowed=False` ⇒ rechazo.
"""

from __future__ import annotations

from typing import Any

from blite.authz import AuthzDecision
from blite.gateway.context import GatewayContext
from blite.gateway.pipeline import Rejection, Stage
from blite.gateway.stages import EgressStage, MediationStage
from blite.identity.identity import Identity
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
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        if self._explode:
            msg = "boom"
            raise RuntimeError(msg)
        return {"echo": inputs}


_ALLOWED = AuthzDecision(
    allowed=True, reason="permission granted", decided_by="authorization"
)
_DENIED = AuthzDecision(
    allowed=False, reason="missing permission", decided_by="authorization"
)


def _ctx(
    *, authz: AuthzDecision | None = _ALLOWED, capability_id: str = "cap.echo"
) -> GatewayContext:
    return GatewayContext(
        identity=Identity(
            id="user:test",
            kind="human",
            domain_id="domain-a",
            permissions=frozenset(),
        ),
        capability_id=capability_id,
        inputs={"x": 1},
        authz=authz,
    )


def _mediation(*, explode: bool = False) -> MediationStage:
    registry = EntryPointRegistry({"cap.echo": _EchoCapability(explode=explode)})
    return MediationStage(registry, ProfileDispatcher())


def test_mediation_dispatches_via_registry_and_stamps_outputs() -> None:
    stage = _mediation()
    assert isinstance(stage, Stage)

    result = stage.handle(_ctx())

    assert isinstance(result, GatewayContext)
    assert result.outputs == {"echo": {"x": 1}}


def test_mediation_returns_a_new_ctx_never_mutates() -> None:
    ctx = _ctx()
    result = _mediation().handle(ctx)

    assert isinstance(result, GatewayContext)
    assert ctx.outputs is None
    assert result is not ctx


def test_mediation_without_authz_decision_refuses_to_dispatch() -> None:
    # Defensa en profundidad: ni llamada por fuera del Pipeline despacha
    # sin decisión positiva (Inv-E).
    result = _mediation().handle(_ctx(authz=None))

    assert isinstance(result, Rejection)
    assert result.stage == "mediation"


def test_mediation_with_denied_decision_refuses_to_dispatch() -> None:
    result = _mediation().handle(_ctx(authz=_DENIED))

    assert isinstance(result, Rejection)


def test_mediation_unknown_capability_is_a_rejection_not_an_exception() -> None:
    result = _mediation().handle(_ctx(capability_id="cap.missing"))

    assert isinstance(result, Rejection)
    assert "cap.missing" in result.reason


def test_mediation_capability_failure_is_a_rejection_not_an_exception() -> None:
    result = _mediation(explode=True).handle(_ctx())

    assert isinstance(result, Rejection)
    assert "RuntimeError" in result.reason


def test_egress_releases_only_with_an_allowed_authz_decision() -> None:
    stage = EgressStage()
    assert isinstance(stage, Stage)
    ctx = _ctx()

    assert stage.handle(ctx) is ctx


def test_egress_without_decision_fails_closed() -> None:
    result = EgressStage().handle(_ctx(authz=None))

    assert isinstance(result, Rejection)
    assert result.stage == "egress"


def test_egress_with_denied_decision_rejects_with_its_reason() -> None:
    result = EgressStage().handle(_ctx(authz=_DENIED))

    assert isinstance(result, Rejection)
    assert result.reason == "missing permission"
