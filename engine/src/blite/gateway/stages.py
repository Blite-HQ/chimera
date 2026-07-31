"""
Etapas reales del chokepoint: `mediation` y `egress`. [S-G · Steven]

freeze §8 + nota execution/01: `mediation` es el ÚNICO punto donde el
gateway despacha — resuelve la capability vía Registry y ejecuta vía
Dispatcher (INV-1: el mismo camino que el runtime, jamás un import directo).
Fail-closed en todo: sin decisión de authz no hay despacho (defensa en
profundidad — el Pipeline ya garantiza el orden, esta etapa NO confía en
eso); capability desconocida, perfil sin estrategia o invocación que explota
⇒ `Rejection`, jamás una excepción que se escape del chokepoint.

`egress` (freeze §5/EX-14, acuerdo con Dylan 2026-07-22): su firma acepta
`AuthzDecision` ÚNICAMENTE — no sabe leer verdicts de verificación (Inv-E)
ni señales de guardrails; un `Signal` no puede llegar ni por tipo (el ctx
congelado lo rechaza en validación) ni por firma (`_release` exige
`AuthzDecision`). `allowed=False` o decisión ausente ⇒ rechazo.
"""

from __future__ import annotations

from blite.authz import AuthzDecision
from blite.gateway.context import GatewayContext
from blite.gateway.pipeline import Rejection
from blite.runtime.dispatch import Dispatcher
from blite.runtime.registry import Registry

_DEFAULT_PROFILE = "in-process"


class MediationStage:
    """El despacho mediado — Registry + Dispatcher detrás del chokepoint."""

    def __init__(self, registry: Registry, dispatcher: Dispatcher) -> None:
        self._registry = registry
        self._dispatcher = dispatcher

    @property
    def name(self) -> str:
        return "mediation"

    def handle(self, ctx: GatewayContext) -> GatewayContext | Rejection:
        if ctx.authz is None or not ctx.authz.allowed:
            # Defensa en profundidad: el Pipeline corta antes, pero esta
            # etapa no despacha sin decisión positiva NI aunque la llamen sola.
            return Rejection(
                stage=self.name,
                reason="despacho sin decisión positiva de authorization (Inv-E)",
            )
        try:
            capability = self._registry.get(ctx.capability_id)
        except KeyError:
            return Rejection(
                stage=self.name,
                reason=f"capability {ctx.capability_id!r} no está en el registry",
            )
        try:
            # El perfil default es "in-process" (trust/06 §4) hasta que el
            # manifest exponga execution_profile (trabajo pendiente del SDK).
            strategy = self._dispatcher.resolve(_DEFAULT_PROFILE)
            outputs = strategy.execute(capability, ctx.inputs)
        except Exception as exc:  # noqa: BLE001 — frontera de capability: fail-closed como Rejection, jamás excepción fuera del chokepoint
            return Rejection(
                stage=self.name,
                reason=f"despacho falló: {type(exc).__name__}",
            )
        return ctx.model_copy(update={"outputs": outputs})


class EgressStage:
    """La puerta de salida — gobernada SOLO por la autorización (Inv-E)."""

    @property
    def name(self) -> str:
        return "egress"

    def handle(self, ctx: GatewayContext) -> GatewayContext | Rejection:
        return self._release(ctx, ctx.authz)

    def _release(
        self, ctx: GatewayContext, decision: AuthzDecision | None
    ) -> GatewayContext | Rejection:
        """La firma tipa `AuthzDecision` únicamente (freeze §5/EX-14) — un
        `{flagged: false}` no equivale a un pass ni por descuido de tipos."""
        if decision is None:
            return Rejection(
                stage=self.name,
                reason="egreso sin decisión de authorization — fail-closed",
            )
        if not decision.allowed:
            return Rejection(stage=self.name, reason=decision.reason)
        return ctx
