"""El runner y su log — la mitad de ejecución de la forma.

Dos cosas que Inspect no da gratis y que acá son contrato:

1. **`config_digest`.** `EvalSpec` captura `revision` y `packages` granulares
   pero ningún digest de configuración (trust/17 §1.1): la reproducibilidad
   había que computarla de todos modos. Acá la identidad de una evaluación ES
   su digest.
2. **Cero reloj en el log.** Dos corridas idénticas producen bytes idénticos.
   Un `EvalLog` con timestamp obliga a comparar ablaciones a ojo.

Y una doctrina que es de esta casa: un fallo del PROCESO no es un resultado del
sujeto evaluado (mismo criterio que `VerificationProcessError` en el engine).
"""

from __future__ import annotations

import json
import platform
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from chimera_eval.dataset import canonical_json, digest_of
from chimera_eval.score import (
    JSONValue,
    Score,
    accuracy,
    decisive_error_rate,
    over_refusal_rate,
)
from chimera_eval.task import Task

_CONFIG_DIGEST_DOMAIN = "chimera/eval-config/v1"


@dataclass(frozen=True)
class SampleResult:
    """Lo que pasó con UNA muestra: o puntuó, o el proceso se cayó. Nunca ambas."""

    sample_id: str
    score: Score | None = None
    error: str | None = None

    def as_json(self) -> dict[str, JSONValue]:
        return {
            "sample_id": self.sample_id,
            "score": None
            if self.score is None
            else {
                "value": self.score.value,
                "answer": self.score.answer,
                "explanation": self.score.explanation,
                "metadata": dict(self.score.metadata),
            },
            "error": self.error,
        }


@dataclass(frozen=True)
class EvalLog:
    """Un resultado de evaluación, autocontenido y comparable."""

    task: str
    task_version: str
    dataset_name: str
    dataset_digest: str
    solver_id: str
    scorer_id: str
    config_digest: str
    params: Mapping[str, JSONValue]
    packages: Mapping[str, str]
    results: tuple[SampleResult, ...]
    metrics: Mapping[str, float]
    revision: str | None = None
    """Commit + flag de árbol sucio. Lo inyecta el CLI: la librería no
    ejecuta git — un log debe poder producirse fuera de un repo."""

    def as_json(self) -> dict[str, JSONValue]:
        return {
            "task": self.task,
            "task_version": self.task_version,
            "dataset_name": self.dataset_name,
            "dataset_digest": self.dataset_digest,
            "solver_id": self.solver_id,
            "scorer_id": self.scorer_id,
            "config_digest": self.config_digest,
            "params": dict(self.params),
            "packages": dict(self.packages),
            "revision": self.revision,
            "results": [r.as_json() for r in self.results],
            "metrics": dict(self.metrics),
        }

    def to_json(self) -> str:
        return (
            json.dumps(self.as_json(), sort_keys=True, indent=2, ensure_ascii=False)
            + "\n"
        )


def _default_packages() -> dict[str, str]:
    return {"python": platform.python_version()}


def config_digest(task: Task) -> str:
    """Identidad de la CONFIGURACIÓN: qué se evaluó y con qué, jamás el resultado."""
    return digest_of(
        {
            "task": task.name,
            "task_version": task.version,
            "dataset_digest": task.dataset.digest(),
            "solver_id": task.solver_id,
            "scorer_id": task.scorer_id,
            "params": dict(task.params),
        },
        _CONFIG_DIGEST_DOMAIN,
    )


def _metrics(scores: Sequence[Score], process_errors: int) -> dict[str, float]:
    """Las tasas se calculan sobre lo MEDIDO, y los errores se reportan aparte.

    Meterlos en el denominador diluiría el KPI con muestras que nadie puntuó;
    meterlos como `I` o `N` inventaría un error o una abstención que no ocurrió.
    """
    return {
        "scored": float(len(scores)),
        "process_errors": float(process_errors),
        "accuracy": accuracy(scores),
        "over_refusal_rate": over_refusal_rate(scores),
        "decisive_error_rate": decisive_error_rate(scores),
    }


def run_task(
    task: Task,
    *,
    revision: str | None = None,
    packages: Mapping[str, str] | None = None,
) -> EvalLog:
    """Corre `task` de principio a fin y devuelve su log."""
    results: list[SampleResult] = []
    scores: list[Score] = []

    for sample in task.dataset.samples:
        try:
            output = task.solver(sample)
            score = task.scorer(sample, output)
        except Exception as exc:  # noqa: BLE001 — se REPORTA, no se traduce a veredicto
            results.append(
                SampleResult(sample_id=sample.id, error=f"{type(exc).__name__}: {exc}")
            )
            continue
        results.append(SampleResult(sample_id=sample.id, score=score))
        scores.append(score)

    process_errors = sum(1 for r in results if r.error is not None)
    return EvalLog(
        task=task.name,
        task_version=task.version,
        dataset_name=task.dataset.name,
        dataset_digest=task.dataset.digest(),
        solver_id=task.solver_id,
        scorer_id=task.scorer_id,
        config_digest=config_digest(task),
        params=dict(task.params),
        packages=dict(packages) if packages is not None else _default_packages(),
        results=tuple(results),
        metrics=_metrics(scores, process_errors),
        revision=revision,
    )


__all__ = [
    "EvalLog",
    "SampleResult",
    "canonical_json",
    "config_digest",
    "run_task",
]
