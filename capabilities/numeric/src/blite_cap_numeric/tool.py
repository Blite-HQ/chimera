"""
MatrixOps — Perform generic matrix operations (multiply, invert, decompose, normalize).

Registered as entry point: blite.capabilities["blite.numeric.matrix_ops"]
Heavy dependencies are loaded lazily (install via extras):
  uv add blite-cap-numeric[full]
"""

from __future__ import annotations

from typing import Any

from blite_capability.manifest import CapabilityManifest

_MANIFEST = CapabilityManifest(
    id="blite.numeric.matrix_ops",
    description="Perform generic matrix operations (multiply, invert, decompose, normalize).",
    input_schema={
        "type": "object",
        "properties": {
            "matrix": {"type": "array"},
            "operation": {
                "type": "string",
                "enum": ["multiply", "invert", "normalize", "eigenvalues"],
            },
        },
        "required": ["matrix", "operation"],
    },
    output_schema={
        "type": "object",
        "properties": {"result": {"type": "array"}},
        "required": ["result"],
    },
    tags=("numeric", "linear-algebra", "classical"),
    side_effects="pure",
    required_permission="capability:invoke",
    interaction="request_response",
)


class MatrixOps:
    """Generic capability: Perform generic matrix operations (multiply, invert, decompose, normalize)."""

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
                f"MatrixOps: optional dependency missing. "
                f"Install blite-cap-numeric[full]: {exc}"
            ) from exc

    def _invoke_impl(self, inputs: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(
            "MatrixOps: implementation not yet provided. Install blite-cap-numeric[full]."
        )


_EXACT_EVOLVE_MANIFEST = CapabilityManifest(
    id="blite.numeric.exact_evolve",
    description=(
        "Evolve a quantum state under a fixed Hermitian operator (given as "
        "Pauli terms) using exact diagonalization via sparse matrix "
        "exponentiation."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "n_sites": {
                "type": "integer",
                "minimum": 1,
                "maximum": 14,
                "description": "Number of sites the operator acts on",
            },
            "terms": {
                "type": "array",
                "description": (
                    "Operator terms as Pauli strings with coefficients; "
                    "index i (left to right) is site i"
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "pauli": {"type": "string"},
                        "coefficient": {"type": "number"},
                    },
                    "required": ["pauli", "coefficient"],
                },
            },
            "time": {"type": "number", "description": "Evolution time"},
            "initial_bitstring": {
                "type": "string",
                "description": (
                    "Initial computational-basis state, one character per "
                    "site ('0'/'1'); defaults to all-zero"
                ),
            },
            "observables": {
                "type": "array",
                "description": "Observables to evaluate at the evolved state",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "pauli": {"type": "string"},
                    },
                    "required": ["label", "pauli"],
                },
            },
        },
        "required": ["n_sites", "terms", "time", "observables"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "expectations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "value": {"type": "number"},
                    },
                    "required": ["label", "value"],
                },
            },
            "norm": {
                "type": "number",
                "description": "State vector norm after evolution (unitarity check)",
            },
            "method": {"type": "string"},
            "backend": {"type": "string"},
        },
        "required": ["expectations", "norm", "method", "backend"],
    },
    tags=("numeric", "linear-algebra", "time-evolution"),
    side_effects="pure",
    required_permission="capability:invoke",
    interaction="request_response",
)


class ExactEvolve:
    """Generic capability: exact time evolution of a Hermitian operator via
    sparse diagonalization (`scipy.sparse.linalg.expm_multiply`)."""

    @property
    def manifest(self) -> CapabilityManifest:
        return _EXACT_EVOLVE_MANIFEST

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Invoke the capability. Heavy deps loaded lazily on first call."""
        return self._run(inputs)

    def _run(self, inputs: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._invoke_impl(inputs)
        except ImportError as exc:
            raise ImportError(
                f"ExactEvolve: optional dependency missing. "
                f"Install blite-cap-numeric[full]: {exc}"
            ) from exc

    def _invoke_impl(self, inputs: dict[str, Any]) -> dict[str, Any]:
        from blite_cap_numeric.exact_evolve import exact_evolve

        return exact_evolve(inputs)
