"""`Task` — qué se evalúa, con qué corpus, resolviendo con qué y puntuando cómo.

`solver` y `scorer` son callables INYECTADOS: el núcleo del runner no importa
`blite` ni `chimera_api`. La atadura al plano de verificación vive en una tarea
concreta (`chimera_eval.tasks.*`), no acá — misma frontera que trust/17 §4.1 le
exige a esta herramienta («fuera del engine, lado lectura, jamás produce ni
decide»).

Un `solver` puede no invocar ningún modelo: la evaluación de esta casa corre
sobre verificadores deterministas. En Inspect eso es un caso de primera clase
(`--model none`); acá es EL caso.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from chimera_eval.dataset import Dataset
from chimera_eval.score import JSONValue, Score, empty_metadata

SolverOutput = JSONValue
Solver = Callable[..., SolverOutput]
Scorer = Callable[..., Score]


@dataclass(frozen=True)
class Task:
    """Una evaluación reproducible."""

    name: str
    version: str
    dataset: Dataset
    solver: Solver
    solver_id: str
    scorer: Scorer
    scorer_id: str
    params: Mapping[str, JSONValue] = field(default_factory=empty_metadata)
    """Los ejes de ablación. Entran al `config_digest`: dos variantes de la
    misma tarea son dos logs distintos y comparables, no una sobrescritura."""

    def __post_init__(self) -> None:
        for field_name in ("name", "version", "solver_id", "scorer_id"):
            if not str(getattr(self, field_name)).strip():
                msg = (
                    f"Task.{field_name} no puede ir vacío — sin él dos logs del "
                    "«mismo» task no son comparables"
                )
                raise ValueError(msg)
