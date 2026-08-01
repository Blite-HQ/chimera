"""
QuboSolver — Solve a QUBO (Quadratic Unconstrained Binary Optimization) matrix to a binary assignment.

Registered as entry point: blite.capabilities["blite.solvers.qubo"]
Heavy dependencies are loaded lazily (install via extras):
  uv add blite-cap-solvers[ortools]
"""

from __future__ import annotations

from typing import Any

from blite_capability.manifest import CapabilityManifest

# UNA sola fuente para el eje `backend`: el enum del manifest y el guard de
# `_invoke_impl` se derivan de esta tupla. Antes divergian — el manifest
# anunciaba "gurobi" e `invoke` lo rechazaba (hallazgo 12 del handoff S3):
# un manifest que promete lo que la implementacion niega es una mentira de
# contrato, y el planner elige sobre el manifest. El extra `gurobi` del
# pyproject queda como bundle de dependencia declarado, sin prometer despacho.
_BACKENDS_SOPORTADOS = ("auto", "ortools")

_MANIFEST = CapabilityManifest(
    id="blite.solvers.qubo",
    description="Solve a QUBO (Quadratic Unconstrained Binary Optimization) matrix to a binary assignment.",
    input_schema={
        "type": "object",
        "properties": {
            "matrix": {
                "type": "array",
                "description": "QUBO coefficient matrix (list of lists of floats)",
            },
            "backend": {
                "type": "string",
                "enum": list(_BACKENDS_SOPORTADOS),
                "default": "auto",
            },
        },
        "required": ["matrix"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "assignment": {
                "type": "array",
                "description": "Binary assignment vector (list of 0 or 1 integers)",
            },
            "energy": {
                "type": "number",
                "description": "Objective value of the solution",
            },
        },
        "required": ["assignment"],
    },
    tags=("solver", "optimization", "qubo", "classical"),
    side_effects="pure",
    required_permission="capability:invoke",
    interaction="request_response",
)


class QuboSolver:
    """Generic capability: Solve a QUBO (Quadratic Unconstrained Binary Optimization) matrix to a binary assignment."""

    @property
    def manifest(self) -> CapabilityManifest:
        return _MANIFEST

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Invoke the capability. Heavy deps loaded lazily on first call."""
        return self._run(inputs)

    def _run(self, inputs: dict[str, Any]) -> dict[str, Any]:
        # Lazy import of heavy dependency
        try:
            return self._invoke_impl(inputs)
        except ImportError as exc:
            raise ImportError(
                f"QuboSolver: optional dependency missing. "
                f"Install blite-cap-solvers[ortools]: {exc}"
            ) from exc

    def _invoke_impl(self, inputs: dict[str, Any]) -> dict[str, Any]:
        from blite_cap_solvers.qubo import solve_qubo

        backend = inputs.get("backend", "auto")
        if backend not in _BACKENDS_SOPORTADOS:
            soportados = " u ".join(repr(b) for b in _BACKENDS_SOPORTADOS)
            msg = f"QuboSolver: backend {backend!r} no implementado — use {soportados}"
            raise ValueError(msg)
        return solve_qubo(inputs.get("matrix"))
