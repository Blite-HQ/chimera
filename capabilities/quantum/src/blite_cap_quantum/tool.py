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
            "seed": {
                "type": "integer",
                "default": 1,
                "description": "Sampler seed for reproducible runs",
            },
            "reference_optimum": {
                "type": "number",
                "description": "Known optimum used to report approximation_ratio",
            },
        },
        "required": ["matrix"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "assignment": {"type": "array", "description": "Binary assignment vector"},
            "energy": {
                "type": "number",
                "description": "Best objective value found across measurement shots (best-of-samples)",
            },
            "expected_energy": {
                "type": "number",
                "description": "Expected objective value under the variational distribution at optimized angles (exact, statevector-computed)",
            },
            "sampled_mean_energy": {
                "type": "number",
                "description": "Sample-mean objective over measurement shots (empirical estimator of expected_energy)",
            },
            "approximation_ratio": {
                "type": "number",
                "description": "energy divided by reference_optimum, when provided",
            },
            "expected_ratio": {
                "type": "number",
                "description": "expected_energy divided by reference_optimum, when provided",
            },
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
        from blite_cap_quantum.qaoa import solve_qaoa

        backend = inputs.get("backend", "aer_simulator")
        if backend != "aer_simulator":
            msg = (
                f"QaoaSolver: backend {backend!r} no implementado este mes — "
                "use 'aer_simulator' (freeze: en vivo solo Aer+seed)"
            )
            raise ValueError(msg)
        layers = inputs.get("layers", 2)
        if isinstance(layers, bool) or not isinstance(layers, int):
            msg = f"QaoaSolver: layers debe ser entero, no {layers!r}"
            raise ValueError(msg)
        seed = inputs.get("seed", 1)
        if isinstance(seed, bool) or not isinstance(seed, int):
            msg = f"QaoaSolver: seed debe ser entero, no {seed!r}"
            raise ValueError(msg)
        reference = inputs.get("reference_optimum")
        if reference is not None and (
            isinstance(reference, bool) or not isinstance(reference, int | float)
        ):
            msg = f"QaoaSolver: reference_optimum debe ser numérico, no {reference!r}"
            raise ValueError(msg)
        return solve_qaoa(
            inputs.get("matrix"),
            layers=layers,
            seed=seed,
            reference_optimum=reference,
        )
