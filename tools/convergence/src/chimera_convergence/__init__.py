"""Auditor de convergencia entre dos pasadas independientes.

Instrumento de PROCESO, no de producto: sirve para decidir si dos revisiones
del mismo material coinciden lo suficiente como para actuar sobre el resultado.
El método viene de `docs/protocolo-convergencia.md`.
"""

from chimera_convergence.document import evaluate, load, render
from chimera_convergence.matrix import (
    Attestation,
    Axis,
    Counts,
    MatrixError,
    Quadrant,
    Severity,
    Verdict,
    tally,
    verdict,
)

__all__ = [
    "Attestation",
    "Axis",
    "Counts",
    "MatrixError",
    "Quadrant",
    "Severity",
    "Verdict",
    "evaluate",
    "load",
    "render",
    "tally",
    "verdict",
]
