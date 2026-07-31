"""
Etapas reales del chokepoint — las 8 de `STAGE_ORDER` (freeze §8). [C2/M2]

Historia: `mediation`/`egress` eran reales desde S-G (Steven); C2/M2 (freeze
§8 supersede C-5/#106) materializa las 6 restantes según los deberes de
execution/01 §1.2:

- `identity`: rechaza SOLO identidad inválida (coherencia de dominio del
  cruce) — jamás una decisión de política. El actor que estampa es el que
  las etapas de provenance escriben en los eventos (AX1).
- `authorization`: `required_permission` del manifest v2 (C1) contra los
  permisos de la Identity — estampa `AuthzDecision`; deny corta ANTES de
  gastar el despacho. Reautorización a mitad de pipeline NO existe (§8).
- `guardrails`: corre detectores inyectados que producen `Signal`s
  no-decisionales, registradas como eventos `signal.recorded` (catálogo §14
  ●SignalRecorded) — jamás deciden (INV-3); un detector roto es Rejection
  fail-closed (un chokepoint con guardrail roto no despacha).
- `provenance:pre`/`provenance:post`: `capability.job.submitted/completed`
  (PR1: el submitted existe ANTES de ejecutar) con el actor REAL del cruce y
  digests por la MISMA puerta canónica que el loop (`blite.runtime.digests`).
- `mediation`: despacho vía Registry + Dispatcher (INV-1); con store, un
  despacho que explota journaliza `capability.job.failed` ANTES del
  `Rejection` (INV-4: la etapa emite su evento ella misma).
- `verification`: el seam POR INVOCACIÓN — la verificación del run vive en
  el delegate post-invoke del runtime (INV-2/R-Pol1); acá solo consistencia
  fail-closed (outputs presentes) y el gancho inyectable.

`egress` (freeze §5/EX-14): su firma acepta `AuthzDecision` ÚNICAMENTE — no
sabe leer verdicts de verificación (Inv-E) ni señales de guardrails.
`allowed=False` o decisión ausente ⇒ rechazo.

INV-5: este módulo habla con el log SOLO por el puerto `EventStore` — jamás
importa `blite.events.writer`/`postgres`.
"""

from __future__ import annotations

from collections.abc import Callable

from blite.authz import AuthzDecision
from blite.content import ContentStore
from blite.events.store import EventStore
from blite.gateway.context import GatewayContext
from blite.gateway.pipeline import Rejection
from blite.guardrails import Signal
from blite.runtime.digests import digest_via
from blite.runtime.dispatch import Dispatcher
from blite.runtime.registry import Registry

Guard = Callable[[GatewayContext], Signal]
"""Un detector inyectable de la etapa guardrails — produce una `Signal`
no-decisional (INV-3); jamás un verdict ni una decisión de egreso."""

VerificationHook = Callable[[GatewayContext], None]
"""Gancho por invocación del seam `verification` — observa el ctx (p. ej.
para registrar señales de consistencia); la verificación DECISORIA del run
vive en el delegate post-invoke del runtime (INV-2)."""


def _domain(ctx: GatewayContext) -> str:
    return ctx.domain_id if ctx.domain_id is not None else ctx.identity.domain_id


def _job_id(step_id: str) -> str:
    """La MISMA convención del loop (freeze §3: step↔job 1:1)."""
    return f"{step_id}:job"


class IdentityStage:
    """Quién cruza — coherencia de la identidad, jamás política (execution/01)."""

    @property
    def name(self) -> str:
        return "identity"

    def handle(self, ctx: GatewayContext) -> GatewayContext | Rejection:
        if ctx.domain_id is not None and ctx.domain_id != ctx.identity.domain_id:
            return Rejection(
                stage=self.name,
                reason=(
                    f"identidad {ctx.identity.id!r} pertenece al dominio "
                    f"{ctx.identity.domain_id!r}, no a {ctx.domain_id!r} — "
                    "identidad inválida para este cruce (AX1b/SO2)"
                ),
            )
        return ctx


class AuthorizationStage:
    """¿Este actor puede invocar esta capability? — manifest v2 vs Identity."""

    def __init__(self, registry: Registry) -> None:
        self._registry = registry

    @property
    def name(self) -> str:
        return "authorization"

    def handle(self, ctx: GatewayContext) -> GatewayContext | Rejection:
        try:
            manifest = self._registry.get(ctx.capability_id).manifest
        except KeyError:
            return Rejection(
                stage=self.name,
                reason=(
                    f"capability {ctx.capability_id!r} no está en el registry — "
                    "sin manifest no hay permiso que evaluar (fail-closed)"
                ),
            )
        required = manifest.required_permission
        if required not in ctx.identity.permissions:
            return Rejection(
                stage=self.name,
                reason=(
                    f"la identidad {ctx.identity.id!r} no porta el permiso "
                    f"{required!r} que el manifest exige (freeze §8)"
                ),
            )
        decision = AuthzDecision(
            allowed=True,
            reason=f"permiso {required!r} presente en la intersección efectiva",
            decided_by="authorization",
        )
        return ctx.model_copy(update={"authz": decision})


class GuardrailsStage:
    """Detectores no-decisionales — informan como eventos, jamás deciden."""

    def __init__(
        self, guards: tuple[Guard, ...] = (), store: EventStore | None = None
    ) -> None:
        self._guards = guards
        self._store = store

    @property
    def name(self) -> str:
        return "guardrails"

    def handle(self, ctx: GatewayContext) -> GatewayContext | Rejection:
        for guard in self._guards:
            try:
                signal = guard(ctx)
            except Exception as exc:  # noqa: BLE001 — un detector roto NO despacha: fail-closed, jamás en silencio
                return Rejection(
                    stage=self.name,
                    reason=f"guardrail explotó: {type(exc).__name__}",
                )
            if self._store is not None and ctx.run_id is not None:
                # ●SignalRecorded (§14): la señal queda en el rastro con el
                # actor real del cruce; flagged o no, INFORMA — jamás corta.
                self._store.append(
                    stream_id=ctx.run_id,
                    type="signal.recorded",
                    actor_id=ctx.identity.id,
                    domain_id=_domain(ctx),
                    payload=signal.model_dump(),
                )
        return ctx


class ProvenancePreStage:
    """PR1: `capability.job.submitted` existe ANTES de ejecutar."""

    def __init__(self, store: EventStore, content: ContentStore) -> None:
        self._store = store
        self._content = content

    @property
    def name(self) -> str:
        return "provenance:pre"

    def handle(self, ctx: GatewayContext) -> GatewayContext | Rejection:
        if ctx.run_id is None or ctx.step_id is None:
            return Rejection(
                stage=self.name,
                reason=(
                    "cruce sin run_id/step_id — la procedencia del job no es "
                    "registrable (PR1 fail-closed)"
                ),
            )
        self._store.append(
            stream_id=ctx.run_id,
            type="capability.job.submitted",
            actor_id=ctx.identity.id,
            domain_id=_domain(ctx),
            payload={
                "job_id": _job_id(ctx.step_id),
                "step_id": ctx.step_id,
                "capability_id": ctx.capability_id,
                "input_digest": digest_via(self._content, ctx.inputs, _domain(ctx)),
            },
        )
        return ctx


class ProvenancePostStage:
    """El cierre del rastro del job: `capability.job.completed` + digest."""

    def __init__(self, store: EventStore, content: ContentStore) -> None:
        self._store = store
        self._content = content

    @property
    def name(self) -> str:
        return "provenance:post"

    def handle(self, ctx: GatewayContext) -> GatewayContext | Rejection:
        if ctx.run_id is None or ctx.step_id is None or ctx.outputs is None:
            return Rejection(
                stage=self.name,
                reason=(
                    "cruce sin run_id/step_id/outputs — el cierre del job no es "
                    "registrable (fail-closed)"
                ),
            )
        self._store.append(
            stream_id=ctx.run_id,
            type="capability.job.completed",
            actor_id=ctx.identity.id,
            domain_id=_domain(ctx),
            payload={
                "job_id": _job_id(ctx.step_id),
                "step_id": ctx.step_id,
                "output_digest": digest_via(self._content, ctx.outputs, _domain(ctx)),
            },
        )
        return ctx


class VerificationStage:
    """El seam por invocación — la verificación del run es del delegate (INV-2)."""

    def __init__(self, hook: VerificationHook | None = None) -> None:
        self._hook = hook

    @property
    def name(self) -> str:
        return "verification"

    def handle(self, ctx: GatewayContext) -> GatewayContext | Rejection:
        if ctx.outputs is None:
            return Rejection(
                stage=self.name,
                reason=(
                    "verification alcanzada sin outputs — mediation nunca "
                    "estampó: chokepoint roto (fail-closed)"
                ),
            )
        if self._hook is not None:
            try:
                self._hook(ctx)
            except Exception as exc:  # noqa: BLE001 — el gancho roto no pasa en silencio: fail-closed
                return Rejection(
                    stage=self.name,
                    reason=f"hook de verificación explotó: {type(exc).__name__}",
                )
        return ctx


class MediationStage:
    """El despacho mediado — Registry + Dispatcher detrás del chokepoint."""

    def __init__(
        self,
        registry: Registry,
        dispatcher: Dispatcher,
        store: EventStore | None = None,
    ) -> None:
        self._registry = registry
        self._dispatcher = dispatcher
        self._store = store

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
            # Manifest v2 (C1): el perfil viene del manifest — un perfil sin
            # estrategia es Rejection, jamás fallback silencioso (freeze §1).
            strategy = self._dispatcher.resolve(capability.manifest.execution_profile)
            outputs = strategy.execute(capability, ctx.inputs)
        except Exception as exc:  # noqa: BLE001 — frontera de capability: fail-closed como Rejection, jamás excepción fuera del chokepoint
            error_kind = type(exc).__name__
            if self._store is not None and ctx.run_id and ctx.step_id:
                # INV-4: la etapa journaliza su propio evento ANTES de cortar —
                # el rastro del job fallido sobrevive al Rejection.
                self._store.append(
                    stream_id=ctx.run_id,
                    type="capability.job.failed",
                    actor_id=ctx.identity.id,
                    domain_id=_domain(ctx),
                    payload={
                        "job_id": _job_id(ctx.step_id),
                        "step_id": ctx.step_id,
                        "error_kind": error_kind,
                    },
                )
            return Rejection(
                stage=self.name,
                reason=f"despacho falló: {error_kind}",
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
