"""Herramientas cuánticas: QAOA para optimización (`QaoaSolver`, Qiskit +
Aer con seed), evolución temporal por circuito de Trotter-Suzuki
(`TrotterEvolve`) y kernel de fidelidad por overlap de statevectors
(`FidelityKernel`). Los extras `vqe`/`vqc`/`dwave` del pyproject están
declarados SIN implementación — descoped, ver README."""

from .tool import FidelityKernel, QaoaSolver, TrotterEvolve

__all__ = ["FidelityKernel", "QaoaSolver", "TrotterEvolve"]
