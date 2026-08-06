"""
Registro de adapters de guardrail — ítem C12 (trust/16 §1.3-1.4).

**Qué faltaba.** `GuardrailsStage` ya existe y `Signal.kind` ya obliga a la
convención `{etapa}.{mecanismo}`, pero los detectores llegaban como una tupla
de callables anónimos: nada decía QUÉ detectores corrieron ni con qué
versión, así que dos corridas con detectores distintos producían rastros
indistinguibles. Un registro versionado con digest cierra eso — la misma
regla que ya vale para verificadores, anclas y policies: si no se puede citar
lo que corrió, la evidencia no es auditable.

**El pick decidido (trust/16 §1.4):** `HHEM-2.1-Open` para detección de
alucinación con `AlignScore` como respaldo — los dos riesgos OWASP peor
cubiertos (ASI01/ASI06). Se declaran como IDs con su `kind`; sus pesos NO
viven aquí.

**Frontera que el gate de arquitectura impone (y que este módulo respeta).**
HHEM y AlignScore son MODELOS, y el contrato `AX3-b` prohíbe a
`blite.guardrails` importar `transformers`/SDKs de modelo: un detector
model-backed no puede vivir dentro de este paquete. Por eso el registro
recibe la puntuación por un CALLABLE inyectado — el modelo corre detrás del
puerto de `blite.protocols`, mediado como cualquier otra llamada de modelo
(AX3). No es una incomodidad del diseño: es lo que impide que un «detector»
se convierta en una vía por la que un modelo entra sin mediación.

**Y lo más importante, que no cambia:** una `Signal` INFORMA. Ningún
detector, por bueno que sea su score, decide egreso (Inv-E/D18) — el registro
no tiene ninguna forma de expresar «bloquear».
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from blite.certificate.canonical import JSONValue, canonicalize
from blite.guardrails.signal import Signal

HHEM_DETECTOR_ID = "hhem-2.1-open@vectara"
"""Pick primario de trust/16 §1.4 — detección de alucinación. Model-backed:
corre DETRÁS del puerto (ver docstring del módulo, AX3-b)."""

ALIGNSCORE_DETECTOR_ID = "alignscore@base"
"""Respaldo declarado cuando el primario no está disponible en el despliegue."""

HALLUCINATION_KIND = "egress.hallucination"
"""`{etapa}.{mecanismo}` (trust/16): la etapa donde la señal se levanta y el
mecanismo que la produce. `Signal` valida la convención."""

ScoreFn = Callable[[str, str], float]
"""`(target, content) -> score ∈ [0,1]`. El detector no ve el modelo: ve una
función que puntúa, y esa función la provee quien SÍ puede mediar la llamada."""


@runtime_checkable
class Detector(Protocol):
    """Un adapter de guardrail citable: id versionado + kind + su señal."""

    @property
    def detector_id(self) -> str: ...

    @property
    def kind(self) -> str: ...

    def detect(self, target: str, content: str) -> Signal: ...


@dataclass(frozen=True)
class ScoreDetector:
    """Detector genérico sobre una función de puntuación inyectada.

    `threshold` marca `flagged`, pero el score SIEMPRE viaja: un umbral es
    una decisión del despliegue y esconder el número detrás de él haría que
    ajustarlo pareciera un cambio de detector."""

    detector_id: str
    kind: str
    score_fn: ScoreFn
    threshold: float = 0.5

    def detect(self, target: str, content: str) -> Signal:
        score = float(self.score_fn(target, content))
        return Signal(
            detector=self.detector_id,
            kind=self.kind,
            target=target,
            flagged=score >= self.threshold,
            score=score,
            detail={"threshold": self.threshold},
        )


@dataclass(frozen=True)
class DetectorRegistry:
    """Los detectores DECLARADOS de un despliegue, citables por digest."""

    detectors: tuple[Detector, ...] = ()

    @property
    def declared(self) -> tuple[dict[str, str], ...]:
        return tuple(
            {"detector_id": d.detector_id, "kind": d.kind} for d in self.detectors
        )

    @property
    def digest(self) -> str:
        """Pinnea QUÉ detectores corrieron. Sin esto, dos corridas con
        detectores distintos dejan rastros indistinguibles y «pasó los
        guardrails» no dice cuáles."""
        entries: list[JSONValue] = [
            {"detector_id": d.detector_id, "kind": d.kind} for d in self.detectors
        ]
        return hashlib.sha256(canonicalize(entries)).hexdigest()

    def with_detector(self, detector: Detector) -> DetectorRegistry:
        """Registro nuevo con un detector más — inmutable, como todo lo que
        se pinnea por digest."""
        if any(d.detector_id == detector.detector_id for d in self.detectors):
            msg = (
                f"{detector.detector_id!r} ya está registrado — dos versiones "
                "del mismo detector con el mismo id harían el digest ambiguo"
            )
            raise ValueError(msg)
        return DetectorRegistry(detectors=(*self.detectors, detector))


__all__ = [
    "ALIGNSCORE_DETECTOR_ID",
    "HALLUCINATION_KIND",
    "HHEM_DETECTOR_ID",
    "Detector",
    "DetectorRegistry",
    "ScoreDetector",
    "ScoreFn",
]
