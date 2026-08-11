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

import json
import logging
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, cast

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
_LOGGER = logging.getLogger(__name__)

CutCostFrom = Callable[[Mapping[str, Any]], float | None]
"""Cómo LEER el costo de corte de la salida del brazo. Ver `AblationArm`."""


@dataclass(frozen=True)
class AblationArm:
    """Un brazo declarado: qué variante es y con qué se computa.

    El costo de corte es el resultado científico del brazo y el log de
    verificación no lo conoce, así que lo declara quien corre el experimento.
    Hay dos formas de declararlo, y son EXCLUYENTES:

    - `cut_cost` — el valor, cuando el llamante ya lo sabe (un baseline
      congelado, un número de corpus).
    - `cut_cost_from` — cómo leerlo de la SALIDA del brazo, cuando el costo es
      precisamente lo que el brazo computa. Sin esto, el llamante tendría que
      correr la capability una vez para conocer el costo y otra como brazo —
      y el `wall_ms` registrado sería el de la segunda corrida, midiendo un
      trabajo que ya estaba hecho.

    Ninguna de las dos ⇒ el brazo no aporta fila de ablación, en vez de
    aparecer con un cero fabricado.
    """

    variant: AblationVariant
    capability_id: str
    inputs: dict[str, Any]
    post_invoke: PostInvokeDelegate | None = None
    cut_cost: float | None = None
    cut_cost_from: CutCostFrom | None = None
    extra: dict[str, Any] = field(default_factory=dict[str, Any])

    def __post_init__(self) -> None:
        if self.cut_cost is not None and self.cut_cost_from is not None:
            msg = (
                f"brazo {self.variant}: `cut_cost` y `cut_cost_from` son "
                "excluyentes — dos respuestas a cuál es el costo de corte, y la "
                "que gane en silencio sería la que el panel muestre"
            )
            raise ValueError(msg)


# ── Regla de brazos (V2) — extraída de `scripts/run_ablation.py` (ceremonia
# #177): `chimera_api.runs` necesita la MISMA regla para el modo ablación de
# `POST /runs`, y no puede importar `scripts/run_ablation.py` (no es un
# paquete instalable — no está en `tool.uv.workspace` ni en el `include` de
# pyright). El script queda como CLIENTE delgado de lo de acá; su
# comportamiento no cambia (`tests/unit/experiment/test_run_ablation.py` lo
# ejercita cargando el script por ruta, como siempre).
#
# Lo que vive acá es DATO, nunca ciencia: `capability_id` es un string, jamás
# un import de `capabilities/*` (ADR-008 — `blite` no importa paquetes de
# capability). Qué comparar sigue siendo decisión de quien diseña el
# experimento; esta función solo declara el conjunto con productor real.

DEFAULT_LAYERS = 2
"""Profundidad QAOA por defecto del brazo cuántico — el valor que
`scripts/run_ablation.py` ya usaba antes de esta extracción; el productor
del experimento lo fija, no el runtime."""

DEFAULT_SEED = 1
"""Semilla por defecto del brazo cuántico — mismo origen que `DEFAULT_LAYERS`."""


def expected_energy_of(salida: Mapping[str, Any]) -> float | None:
    """⟨C⟩ del brazo cuántico — el valor ESPERADO, no el best-of-samples.

    Las tres barras tienen que ser la misma CLASE de número o el panel
    compara peras con manzanas: `energy` es el mejor de 2048 muestras (en
    instancias chicas alcanza el óptimo casi siempre — artefacto de muestreo,
    fix 4b) y `mitigated_energy` es un valor esperado. Poner los dos en el
    mismo eje haría ver a la mitigación peor de lo que es por una razón que
    no tiene nada que ver con mitigar.
    """
    valor = salida.get("expected_energy")
    return None if valor is None else float(valor)


def exact_energy_of(salida: Mapping[str, Any]) -> float | None:
    """El corte del solver exacto — la barra de referencia del panel.

    CP-SAT no muestrea ni estima: su `energy` ES el óptimo, así que es
    directamente comparable contra los ⟨C⟩ de los otros brazos (que son
    esperanzas del MISMO observable).
    """
    valor = salida.get("energy")
    return None if valor is None else float(valor)


def mitigated_energy_of(salida: Mapping[str, Any]) -> float | None:
    """Costo de corte del brazo ZNE — el valor MITIGADO, no el crudo.

    Si la mejora no sobrevivió al control negativo, el brazo NO aporta costo:
    publicar un número que el propio control desautoriza sería exactamente lo
    que arXiv:2607.09360 advierte (ver `blite_cap_quantum.zne`).
    """
    if not salida.get("improvement_survives_control", False):
        return None
    valor = salida.get("mitigated_energy")
    return None if valor is None else float(valor)


def build_arms(matrix: list[list[int]], *, layers: int, seed: int) -> list[AblationArm]:
    """Los brazos con productor REAL. `mitigated` es V9 y no se declara —
    un brazo declarado sin productor sería una barra vacía CON nombre, peor
    que una barra ausente.

    El caller NO elige brazos: este es el ÚNICO productor del set de
    variantes — ni el script ni el API (`chimera_api.runs`) exponen forma de
    pasar otra cosa."""
    return [
        AblationArm(
            variant="quantum",
            capability_id="blite.quantum.qaoa",
            inputs={"matrix": matrix, "layers": layers, "seed": seed},
            cut_cost_from=expected_energy_of,
        ),
        AblationArm(
            variant="classical",
            capability_id="blite.solvers.qubo",
            inputs={"matrix": matrix},
            cut_cost_from=exact_energy_of,
        ),
        AblationArm(
            variant="zne",
            capability_id="blite.quantum.zne",
            inputs={"matrix": matrix, "layers": layers, "seed": seed},
            cut_cost_from=mitigated_energy_of,
        ),
    ]


def _arm_output(
    store: EventStore, content: ContentStore, sub_run_id: str, domain_id: str
) -> Mapping[str, Any] | None:
    """La salida del brazo, recuperada del content store por su digest.

    `None` (no `{}`) cuando el brazo no dejó salida recuperable: un dict vacío
    haría que `cut_cost_from` leyera "sin costo" y el brazo apareciera como si
    hubiera corrido sin producir nada.
    """
    completado = next(
        (
            event
            for event in reversed(store.read_stream(sub_run_id))
            if event.type == "run.completed"
        ),
        None,
    )
    if completado is None:
        return None
    digest = completado.payload.get("output_digest")
    if not isinstance(digest, str) or not digest:
        return None
    try:
        crudo = content.get(digest, {"domain_id": domain_id})
    except Exception:  # noqa: BLE001 — una salida no recuperable deja al brazo SIN costo, jamás con uno inventado
        _LOGGER.warning(
            "brazo %s: la salida %s no es recuperable — sin costo de corte",
            sub_run_id,
            digest[:12],
        )
        return None
    salida: Any = json.loads(crudo)
    if not isinstance(salida, dict):
        return None
    # El `isinstance` estrecha a `dict[Unknown, Unknown]`; el cast declara lo
    # que el contrato ya garantiza (la salida de una capability es un objeto
    # JSON) — mismo criterio que `metrics::_verifier_class_of`.
    return cast("dict[str, Any]", salida)


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

        cut_cost = arm.cut_cost
        if arm.cut_cost_from is not None:
            salida = _arm_output(store, content, sub_run_id, domain_id)
            cut_cost = None if salida is None else arm.cut_cost_from(salida)

        metrics = record_run_metrics(
            store,
            run_id=sub_run_id,
            domain_id=domain_id,
            variant=arm.variant,
            cut_cost=cut_cost,
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
