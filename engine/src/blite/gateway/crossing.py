"""
RunCrossing — el Pipeline completo como `GatewayCrossing` inyectable. [C2/M2]

freeze §8 (supersede C-5/#106): «El `Pipeline` se INYECTA en `execute_run`
(como `proposer`); un contrato `layers` nuevo vigila la dirección». Este
módulo es el adapter del lado ALTO de la capa: `blite.gateway` puede
importar `blite.runtime` (capas), el runtime JAMÁS importa gateway — por
eso los tipos del seam (`CrossingRequest`/`CrossingRejected`) viven en el
runtime y acá solo se construyen.

Interpretación §13 registrada (C-5): **UN cruce por invocación de
capability** — resolve es parte de mediation; el loop llama este adapter
una vez por par resolve→invoke, jamás una vez por etapa.
"""

from __future__ import annotations

from typing import Any

from blite.content import ContentStore
from blite.events.store import EventStore
from blite.gateway.context import GatewayContext
from blite.gateway.pipeline import Pipeline, Rejection
from blite.gateway.stages import (
    AuthorizationStage,
    EgressStage,
    Guard,
    GuardrailsStage,
    IdentityStage,
    MediationStage,
    ProvenancePostStage,
    ProvenancePreStage,
    VerificationHook,
    VerificationStage,
)
from blite.identity.identity import Identity
from blite.runtime.dispatch import Dispatcher
from blite.runtime.loop import CrossingRejected, CrossingRequest
from blite.runtime.registry import Registry


def build_run_pipeline(
    *,
    registry: Registry,
    dispatcher: Dispatcher,
    store: EventStore,
    content: ContentStore,
    guards: tuple[Guard, ...] = (),
    verification_hook: VerificationHook | None = None,
) -> Pipeline:
    """Las 8 etapas REALES en el orden congelado (freeze §8) — fail-closed
    en construcción: una tupla que no calce con `STAGE_ORDER` explota acá."""
    return Pipeline(
        (
            IdentityStage(),
            AuthorizationStage(registry),
            GuardrailsStage(guards, store),
            ProvenancePreStage(store, content),
            MediationStage(registry, dispatcher, store),
            VerificationStage(verification_hook),
            ProvenancePostStage(store, content),
            EgressStage(),
        )
    )


class RunCrossing:
    """Cierra `Pipeline` + `Identity` sobre la firma que el runtime conoce.

    La Identity es POR CRUCE (viene del JWT verificado en el borde HTTP —
    freeze §9 P1-9); las etapas de provenance estampan `identity.id` como
    actor de los eventos del job (la ruta del flip AX1, freeze §8).
    """

    def __init__(self, pipeline: Pipeline, identity: Identity) -> None:
        self._pipeline = pipeline
        self._identity = identity

    def __call__(self, request: CrossingRequest) -> dict[str, Any] | CrossingRejected:
        ctx = GatewayContext(
            identity=self._identity,
            capability_id=request.capability_id,
            inputs=request.inputs,
            run_id=request.run_id,
            step_id=request.step_id,
            domain_id=request.domain_id,
        )
        result = self._pipeline.run(ctx)
        if isinstance(result, Rejection):
            return CrossingRejected(stage=result.stage, reason=result.reason)
        if result.outputs is None:
            # Defensa en profundidad: un egreso sin outputs es chokepoint roto.
            return CrossingRejected(
                stage="egress", reason="cruce completó sin outputs (fail-closed)"
            )
        return result.outputs
