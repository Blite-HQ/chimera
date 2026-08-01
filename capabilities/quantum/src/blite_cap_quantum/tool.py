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
    side_effects="pure",
    required_permission="capability:invoke",
    interaction="request_response",
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


_TROTTER_MANIFEST = CapabilityManifest(
    id="blite.quantum.trotter_evolve",
    description=(
        "Evolve a quantum state under a fixed Hermitian operator (given as "
        "Pauli terms) using a Trotter-Suzuki product-formula circuit."
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
            "steps": {
                "type": "integer",
                "minimum": 1,
                "default": 16,
                "description": "Number of Trotter steps",
            },
            "order": {
                "type": "integer",
                "enum": [1, 2],
                "default": 1,
                "description": "Trotter-Suzuki product-formula order",
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
            "steps": {"type": "integer"},
            "order": {"type": "integer"},
            "circuit_depth": {"type": "integer"},
            "circuit_digest": {
                "type": "string",
                "description": "sha256 hex digest of the synthesized circuit's QASM3 export",
            },
        },
        "required": [
            "expectations",
            "norm",
            "method",
            "backend",
            "steps",
            "order",
            "circuit_depth",
            "circuit_digest",
        ],
    },
    tags=("quantum", "time-evolution", "trotter", "circuit"),
    side_effects="pure",
    required_permission="capability:invoke",
    interaction="request_response",
)


class TrotterEvolve:
    """Generic capability: circuit-based time evolution of a Hermitian
    operator via a Trotter-Suzuki product formula (Qiskit + Statevector)."""

    @property
    def manifest(self) -> CapabilityManifest:
        return _TROTTER_MANIFEST

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Invoke the capability. Heavy deps loaded lazily on first call."""
        return self._run(inputs)

    def _run(self, inputs: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._invoke_impl(inputs)
        except ImportError as exc:
            raise ImportError(
                f"TrotterEvolve: optional dependency missing. "
                f"Install blite-cap-quantum[qaoa]: {exc}"
            ) from exc

    def _invoke_impl(self, inputs: dict[str, Any]) -> dict[str, Any]:
        from blite_cap_quantum.trotter import trotter_evolve

        return trotter_evolve(inputs)


_FIDELITY_KERNEL_MANIFEST = CapabilityManifest(
    id="blite.quantum.fidelity_kernel",
    description=(
        "Compute a fidelity-based quantum kernel (Gram matrix) between sets "
        "of feature vectors via statevector overlaps — one matrix product "
        "over cached statevectors, never one circuit per pair."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "x": {"type": "array", "description": "List of feature vectors"},
            "y": {
                "type": "array",
                "description": (
                    "Optional second list of feature vectors; when absent, "
                    "the symmetric Gram matrix of x with itself is computed"
                ),
            },
            "feature_map": {
                "type": "string",
                "enum": ["angle"],
                "default": "angle",
            },
            "reps": {
                "type": "integer",
                "default": 1,
                "description": "Number of feature-map repetition layers",
            },
            "psd_repair": {
                "type": "string",
                "enum": ["clip", "none"],
                "default": "clip",
                "description": "PSD repair method applied to the self-Gram matrix",
            },
        },
        "required": ["x"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "kernel": {"type": "array", "description": "The kernel (Gram) matrix"},
            "lambda_min": {
                "type": ["number", "null"],
                "description": "Smallest eigenvalue before repair (self-Gram only)",
            },
            "psd_repair": {
                "type": "string",
                "description": "PSD repair method actually applied",
            },
            "repaired": {"type": "boolean"},
            "n_qubits": {"type": "integer"},
        },
        "required": ["kernel", "lambda_min", "psd_repair", "repaired", "n_qubits"],
    },
    tags=("quantum", "kernel", "machine-learning", "fidelity"),
    side_effects="pure",
    required_permission="capability:invoke",
    interaction="request_response",
)


class FidelityKernel:
    """Generic capability: fidelity-based quantum kernel via statevector
    overlaps (Qiskit `Statevector`, one matrix product — no per-pair
    circuits)."""

    @property
    def manifest(self) -> CapabilityManifest:
        return _FIDELITY_KERNEL_MANIFEST

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Invoke the capability. Heavy deps loaded lazily on first call."""
        return self._run(inputs)

    def _run(self, inputs: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._invoke_impl(inputs)
        except ImportError as exc:
            raise ImportError(
                f"FidelityKernel: optional dependency missing. "
                f"Install blite-cap-quantum[qaoa]: {exc}"
            ) from exc

    def _invoke_impl(self, inputs: dict[str, Any]) -> dict[str, Any]:
        from blite_cap_quantum.fidelity_kernel import fidelity_kernel

        return fidelity_kernel(inputs)
