"""Herramientas cuánticas: QAOA para optimización (`QaoaSolver`, Qiskit +
Aer con seed), evolución temporal por circuito de Trotter-Suzuki
(`TrotterEvolve`), kernel de fidelidad por overlap de statevectors
(`FidelityKernel`) y extrapolación a ruido cero con control negativo
(`ZeroNoiseExtrapolation`). Los extras `vqe`/`vqc`/`dwave` del pyproject
están declarados SIN implementación — descoped, ver README."""

from .tool import (
    FidelityKernel,
    QaoaSolver,
    TrotterEvolve,
    ZeroNoiseExtrapolation,
)

__all__ = [
    "FidelityKernel",
    "QaoaSolver",
    "TrotterEvolve",
    "ZeroNoiseExtrapolation",
]
