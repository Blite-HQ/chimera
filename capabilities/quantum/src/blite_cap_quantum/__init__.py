"""Herramientas cuánticas: QAOA para optimización (`QaoaSolver`, Qiskit +
Aer con seed). Los extras `vqe`/`vqc`/`dwave` del pyproject están declarados
SIN implementación — descoped, ver README."""

from .tool import QaoaSolver

__all__ = ["QaoaSolver"]
