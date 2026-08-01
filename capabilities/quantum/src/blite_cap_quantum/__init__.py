"""Herramientas cuánticas: QAOA para optimización (`QaoaSolver`, Qiskit +
Aer con seed) y evolución temporal por circuito de Trotter-Suzuki
(`TrotterEvolve`). Los extras `vqe`/`vqc`/`dwave` del pyproject están
declarados SIN implementación — descoped, ver README."""

from .tool import QaoaSolver, TrotterEvolve

__all__ = ["QaoaSolver", "TrotterEvolve"]
