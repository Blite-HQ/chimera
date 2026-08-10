"""El vocabulario `C/I/P/N` y las tasas que se calculan sobre él.

Portado de Inspect (UK AISI) como CONVENCIÓN, sin dependencia — trust/17 §1.2
y §2. Lo que se porta es la observación, no el framework: `N` (NOANSWER,
abstención) es un resultado distinto de `I` (INCORRECT), y esa distinción es
justamente la que el KPI de over-refusal necesita (trust/05 §1.3).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

ScoreValue = Literal["C", "I", "P", "N"]
"""CORRECT · INCORRECT · PARTIAL · NOANSWER."""

NUMERIC_VALUE: Mapping[ScoreValue, float] = {
    "C": 1.0,
    "P": 0.5,
    "I": 0.0,
    "N": 0.0,
}
"""Peso escalar de cada valor.

`I` y `N` valen lo MISMO acá, y no es un descuido: una métrica escalar de
acierto no puede distinguir «se equivocó» de «se abstuvo». Por eso
`over_refusal_rate` existe como KPI aparte y no como un ajuste de este mapa.
"""

JSONValue = (
    str | int | float | bool | None | Mapping[str, "JSONValue"] | Sequence["JSONValue"]
)


def empty_metadata() -> Mapping[str, JSONValue]:
    """Fábrica tipada para los `default_factory`.

    `field(default_factory=dict)` deja el tipo en `dict[Unknown, Unknown]` y
    el gate estricto lo rechaza — con razón: un mapa sin tipo de valor deja
    pasar cualquier cosa al JSON del log.
    """
    return {}


@dataclass(frozen=True)
class Score:
    """El resultado de puntuar UNA muestra."""

    value: ScoreValue
    answer: str
    explanation: str
    metadata: Mapping[str, JSONValue] = field(default_factory=empty_metadata)

    def __post_init__(self) -> None:
        if self.value not in NUMERIC_VALUE:
            msg = f"Score.value debe ser uno de C/I/P/N, no {self.value!r}"
            raise ValueError(msg)


def _rate(scores: Sequence[Score], predicate: ScoreValue) -> float:
    if not scores:
        return 0.0
    return sum(1 for s in scores if s.value == predicate) / len(scores)


def accuracy(scores: Sequence[Score]) -> float:
    """Media de los pesos escalares. NO distingue error de abstención."""
    if not scores:
        return 0.0
    return sum(NUMERIC_VALUE[s.value] for s in scores) / len(scores)


def over_refusal_rate(scores: Sequence[Score]) -> float:
    """`count(N) / total` — el KPI de sobre-rechazo (trust/05 §1.3).

    Alto = la verificación se abstiene de más: cuesta UTILIDAD sin costar
    corrección. Se lee junto a `decisive_error_rate`, jamás en su lugar.
    """
    return _rate(scores, "N")


def decisive_error_rate(scores: Sequence[Score]) -> float:
    """`count(I) / total` — el sistema se pronunció y se equivocó.

    Es el error CARO: un veredicto decisivo equivocado cuesta confianza, que
    es lo único que esta plataforma vende.
    """
    return _rate(scores, "I")
