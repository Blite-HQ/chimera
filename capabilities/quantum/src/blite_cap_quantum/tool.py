"""
QaoaSolver — Solve a QUBO matrix using the Quantum Approximate Optimization Algorithm (QAOA).

Registered as entry point: blite.capabilities["blite.quantum.qaoa"]
Heavy dependencies are loaded lazily (install via extras):
  uv add blite-cap-quantum[qaoa]
"""

from __future__ import annotations

from typing import Any

from blite_capability.manifest import CapabilityManifest

_MANIFEST = CapabilityManifest(
    id="blite.quantum.qaoa",
    description="Solve a QUBO matrix using the Quantum Approximate Optimization Algorithm (QAOA).",
    input_schema={
        "type": "object",
        "properties": {
            "matrix": {"type": "array", "description": "QUBO coefficient matrix"},
            "layers": {
                "type": "integer",
                "default": 2,
                "description": "Number of QAOA layers (p)",
            },
            "backend": {
                "type": "string",
                "enum": ["aer_simulator", "runtime"],
                "default": "aer_simulator",
            },
        },
        "required": ["matrix"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "assignment": {"type": "array", "description": "Binary assignment vector"},
            "energy": {"type": "number"},
            "approximation_ratio": {"type": "number"},
        },
        "required": ["assignment"],
    },
    tags=("quantum", "qaoa", "optimization", "qubo"),
)


class QaoaSolver:
    """Generic capability: Solve a QUBO matrix using the Quantum Approximate Optimization Algorithm (QAOA)."""

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
                f"QaoaSolver: optional dependency missing. "
                f"Install blite-cap-quantum[qaoa]: {exc}"
            ) from exc

    def _invoke_impl(self, inputs: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(
            "QaoaSolver: implementation not yet provided. Install blite-cap-quantum[qaoa]."
        )
