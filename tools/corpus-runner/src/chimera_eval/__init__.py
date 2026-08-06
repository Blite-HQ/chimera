"""`chimera_eval` — el corpus runner del TERCER plano (evaluación).

Los tres planos (`docs/tres-planos.md`, knowledge/trust/17 §1.6) no se
sustituyen entre sí:

- **Verificación** responde «¿este claim es correcto contra un ancla no-modelo?»
  por-claim, en el camino crítico, y produce `Attestation`.
- **Guardrail** responde «¿esta salida luce sospechosa?» por-paso, informa,
  produce `Signal`, y jamás decide.
- **Evaluación** (esto) responde «¿qué tan bueno es el sistema EN AGREGADO?»
  offline, en batch, fuera del camino crítico, y produce KPIs.

Ningún resultado agregado, por alto que sea, sustituye una `Attestation`
faltante en un run individual. Este paquete vive FUERA de `blite.*` y solo lee.
"""

from chimera_eval.dataset import Dataset, Sample, json_dataset
from chimera_eval.runner import EvalLog, SampleResult, config_digest, run_task
from chimera_eval.score import (
    NUMERIC_VALUE,
    Score,
    ScoreValue,
    accuracy,
    decisive_error_rate,
    over_refusal_rate,
)
from chimera_eval.task import Task

__all__ = [
    "NUMERIC_VALUE",
    "Dataset",
    "EvalLog",
    "Sample",
    "SampleResult",
    "Score",
    "ScoreValue",
    "Task",
    "accuracy",
    "config_digest",
    "decisive_error_rate",
    "json_dataset",
    "over_refusal_rate",
    "run_task",
]
