"""
Brazos de ablación como SUB-RUNS — V2/M19 · C-4 (freeze §13).

La letra: «dos brazos de ablación = sub-runs (§13: califican — producen claims
propios); cada brazo emite SU `run.metrics.recorded` en SU stream».

Por qué sub-runs y no dos runs sueltos: un brazo produce claims propios que un
certificado citará, y §13 reserva exactamente ese criterio para lo que
califica como sub-run. Además la comparación necesita un raíz que los ATE — sin
él, «cuántico vs clásico» son dos corridas sin relación declarada, y el panel
tendría que adivinar cuáles comparar.

Lo que este módulo NO hace: elegir qué comparar. Recibe los brazos ya
declarados (variante + capability + inputs) y los corre bajo el raíz con la
herencia fail-closed de `policy_digest` que §13 regla 3 exige. Qué vale la pena
ablar es decisión de quien diseña el experimento, jamás del runtime.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from blite.content import ContentStore
from blite.events.store import EventStore
from blite.runtime.dispatch import Dispatcher
from blite.runtime.loop import PostInvokeDelegate
from blite.runtime.metrics import (
    AblationVariant,
    RunMetricsRecordedPayload,
    record_run_metrics,
)
from blite.runtime.registry import Registry
from blite.runtime.subrun import contribute_sub_run_claims, spawn_sub_run

_DEFAULT_MAX_STEPS = 8


@dataclass(frozen=True)
class AblationArm:
    """Un brazo declarado: qué variante es y con qué se computa.

    `cut_cost` es el resultado científico del brazo — lo declara quien corre el
    experimento porque el log de verificación no lo conoce; `None` cuando el
    brazo no produce un costo de corte (y entonces el brazo no aparece como
    fila de ablación, en vez de aparecer con un cero fabricado).
    """

    variant: AblationVariant
    capability_id: str
    inputs: dict[str, Any]
    post_invoke: PostInvokeDelegate | None = None
    cut_cost: float | None = None
    extra: dict[str, Any] = field(default_factory=dict[str, Any])


@dataclass(frozen=True)
class ArmOutcome:
    """Lo que quedó registrado de un brazo: su stream propio y su cierre."""

    sub_run_id: str
    variant: AblationVariant
    status: str
    metrics: RunMetricsRecordedPayload | None
    sub_run_provenance_hash: str | None


def run_ablation_arms(  # noqa: PLR0913 — misma superficie que `spawn_sub_run`, que envuelve, más los brazos
    store: EventStore,
    registry: Registry,
    dispatcher: Dispatcher,
    content: ContentStore,
    *,
    root_run_id: str,
    root_policy_digest: str,
    actor_id: str,
    domain_id: str,
    arms: Sequence[AblationArm],
    max_steps: int = _DEFAULT_MAX_STEPS,
) -> tuple[ArmOutcome, ...]:
    """Corre cada brazo como sub-run del raíz y cierra su métrica.

    Orden de operaciones por brazo, y el porqué de cada uno:
    1. `spawn_sub_run` — herencia fail-closed de `policy_digest` (§13 regla 3):
       un certificado jamás se compone de claims verificados bajo policies
       distintas, y comparar dos brazos bajo exigencias distintas sería
       precisamente eso.
    2. `record_run_metrics` con la variante y el `wall_ms` MEDIDO del brazo —
       el resto (latencia de verificación, patas, abstenciones) se deriva del
       stream del propio brazo.
    3. `contribute_sub_run_claims` — solo si el brazo COMPLETÓ (§13 regla 2 lo
       exige): el raíz recibe sus claims con `sub_run_provenance_hash`, así el
       certificado del raíz ampara transitivamente el trabajo del brazo. Un
       brazo que falló no aporta claims y se reporta como lo que fue.
    """
    outcomes: list[ArmOutcome] = []
    for index, arm in enumerate(arms):
        sub_run_id = f"{root_run_id}--arm-{index}-{arm.variant}"
        started = time.perf_counter()
        row = spawn_sub_run(
            store,
            registry,
            dispatcher,
            content,
            parent_run_id=root_run_id,
            parent_policy_digest=root_policy_digest,
            sub_run_id=sub_run_id,
            actor_id=actor_id,
            domain_id=domain_id,
            max_steps=max_steps,
            capability_id=arm.capability_id,
            inputs=arm.inputs,
            post_invoke=arm.post_invoke,
        )
        wall_ms = (time.perf_counter() - started) * 1000.0

        metrics = record_run_metrics(
            store,
            run_id=sub_run_id,
            domain_id=domain_id,
            variant=arm.variant,
            cut_cost=arm.cut_cost,
            wall_ms=wall_ms,
        )

        sub_run_hash: str | None = None
        if row.status == "completed":
            sub_run_hash = contribute_sub_run_claims(
                store,
                root_run_id=root_run_id,
                sub_run_id=sub_run_id,
                domain_id=domain_id,
                actor_id=actor_id,
            )

        outcomes.append(
            ArmOutcome(
                sub_run_id=sub_run_id,
                variant=arm.variant,
                status=row.status,
                metrics=metrics,
                sub_run_provenance_hash=sub_run_hash,
            )
        )
    return tuple(outcomes)
