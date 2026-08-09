"""
QaoaSolver — Solve a QUBO matrix using the Quantum Approximate Optimization Algorithm (QAOA).

Registered as entry point: blite.capabilities["blite.quantum.qaoa"]
Heavy dependencies are loaded lazily (install via extras):
  uv add blite-cap-quantum[qaoa]
"""

from __future__ import annotations

from typing import Any, cast

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
            "initial_angles": {
                "type": "object",
                "description": (
                    "Explicit variational angle schedule to start from (or to "
                    "evaluate at, with optimize=false); same shape as the "
                    "'angles' output so a run's angles can be fed back verbatim"
                ),
                "properties": {
                    "betas": {"type": "array", "items": {"type": "number"}},
                    "gammas": {"type": "array", "items": {"type": "number"}},
                },
                "required": ["betas", "gammas"],
            },
            "optimize": {
                "type": "boolean",
                "default": True,
                "description": (
                    "When false, evaluate at initial_angles instead of running "
                    "the classical angle optimizer (initial_angles required)"
                ),
            },
            "init_strategy": {
                "type": "string",
                "enum": ["constant", "interp"],
                "default": "constant",
                "description": (
                    "Where the angle optimizer starts: a constant schedule, or "
                    "a level-by-level climb interpolating the previous level's "
                    "optimum (mutually exclusive with initial_angles)"
                ),
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
            "angles": {
                "type": "object",
                "description": (
                    "Variational angle schedule actually bound into the sampled "
                    "circuit — re-injectable as initial_angles"
                ),
                "properties": {
                    "betas": {"type": "array", "items": {"type": "number"}},
                    "gammas": {"type": "array", "items": {"type": "number"}},
                },
                "required": ["betas", "gammas"],
            },
            "init_strategy": {
                "type": "string",
                "description": (
                    "How the starting angles were chosen: 'constant', 'interp', "
                    "or 'given' when the caller supplied them"
                ),
            },
            "optimized": {
                "type": "boolean",
                "description": "Whether the classical angle optimizer ran",
            },
            "warm_start_levels": {
                "type": "array",
                "description": (
                    "One entry per level climbed, present only under "
                    "init_strategy='interp'"
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "p": {"type": "integer"},
                        "betas": {"type": "array", "items": {"type": "number"}},
                        "gammas": {"type": "array", "items": {"type": "number"}},
                        "expected_energy": {"type": "number"},
                    },
                    "required": ["p", "betas", "gammas", "expected_energy"],
                },
            },
        },
        "required": ["assignment", "angles", "init_strategy", "optimized"],
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
        from blite_cap_quantum.qaoa import CONSTANT_INIT, solve_qaoa

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
        optimize = inputs.get("optimize", True)
        if not isinstance(optimize, bool):
            # Un string no vacío es verdadero en Python: `"false"` colado acá
            # re-optimizaría en silencio los ángulos que se pidió NO tocar.
            msg = f"QaoaSolver: optimize debe ser booleano, no {optimize!r}"
            raise ValueError(msg)
        init_strategy = inputs.get("init_strategy", CONSTANT_INIT)
        if not isinstance(init_strategy, str):
            msg = f"QaoaSolver: init_strategy debe ser texto, no {init_strategy!r}"
            raise ValueError(msg)
        return solve_qaoa(
            inputs.get("matrix"),
            layers=layers,
            seed=seed,
            reference_optimum=reference,
            initial_angles=inputs.get("initial_angles"),
            optimize=optimize,
            init_strategy=init_strategy,
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


_ZNE_MANIFEST = CapabilityManifest(
    id="blite.quantum.zne",
    description=(
        "Estimate a noise-free expectation value by digital zero-noise "
        "extrapolation: run the circuit at amplified noise levels via unitary "
        "folding and extrapolate to zero, together with an equal-cost "
        "negative control that says whether the improvement is real."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "matrix": {"type": "array", "description": "QUBO coefficient matrix"},
            "layers": {"type": "integer", "default": 1},
            "seed": {"type": "integer", "default": 1},
            "initial_angles": {
                "type": "object",
                "description": (
                    "Variational angle schedule to evaluate at; same shape as "
                    "the 'angles' output of the QAOA capability"
                ),
                "properties": {
                    "betas": {"type": "array", "items": {"type": "number"}},
                    "gammas": {"type": "array", "items": {"type": "number"}},
                },
                "required": ["betas", "gammas"],
            },
            "optimize": {"type": "boolean", "default": True},
            "scale_factors": {
                "type": "array",
                "items": {"type": "integer"},
                "default": [1, 3, 5],
                "description": (
                    "Odd noise amplification factors; the first must be 1 (the "
                    "raw measurement that acts as baseline)"
                ),
            },
            "extrapolator": {
                "type": "string",
                "enum": ["linear", "richardson"],
                "default": "richardson",
            },
            "one_qubit_noise": {"type": "number", "default": 0.002},
            "two_qubit_noise": {"type": "number", "default": 0.02},
            "shots": {"type": "integer", "default": 2048},
        },
        "required": ["matrix"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "ideal_energy": {
                "type": "number",
                "description": "Exact expectation value with no noise (statevector)",
            },
            "unmitigated_energy": {
                "type": "number",
                "description": "Raw measurement under noise at amplification 1",
            },
            "mitigated_energy": {
                "type": "number",
                "description": "Value extrapolated to zero noise",
            },
            "scaled_energies": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "scale_factor": {"type": "integer"},
                        "energy": {"type": "number"},
                    },
                    "required": ["scale_factor", "energy"],
                },
            },
            "extrapolation_weights": {
                "type": "array",
                "items": {"type": "number"},
                "description": (
                    "Coefficients combining the measurements into the "
                    "extrapolated value — published so a third party can "
                    "recompute it from the raw measurements"
                ),
            },
            "improvement": {
                "type": "number",
                "description": (
                    "Fraction of the error against the ideal that the "
                    "extrapolation removed; negative when it made things worse"
                ),
            },
            "negative_control": {
                "type": "object",
                "description": (
                    "Equal-cost control run on inflated circuits unrelated to "
                    "the problem structure — its apparent improvement is what "
                    "the real one must beat"
                ),
                "properties": {
                    "kind": {"type": "string"},
                    "reference": {"type": "string"},
                    "unmitigated_energy": {"type": "number"},
                    "mitigated_energy": {"type": "number"},
                    "improvement": {"type": "number"},
                },
                "required": ["kind", "reference", "improvement"],
            },
            "improvement_survives_control": {
                "type": "boolean",
                "description": (
                    "False means the improvement is not attributable to the "
                    "method and must not be published as a result"
                ),
            },
            "mitigation": {
                "type": "object",
                "description": "Provenance of the mitigation applied to this value",
                "properties": {
                    "method": {"type": "string"},
                    "model_digest": {"type": "string"},
                    "training_digest": {"type": ["string", "null"]},
                    "noise_model_digest": {"type": "string"},
                    "baseline": {"type": "string"},
                },
                "required": [
                    "method",
                    "model_digest",
                    "training_digest",
                    "noise_model_digest",
                    "baseline",
                ],
            },
            "noise": {
                "type": "object",
                "description": "Declarative noise descriptor the digest covers",
            },
            "angles": {"type": "object"},
        },
        "required": [
            "ideal_energy",
            "unmitigated_energy",
            "mitigated_energy",
            "improvement",
            "negative_control",
            "improvement_survives_control",
            "mitigation",
        ],
    },
    tags=("quantum", "mitigation", "extrapolation", "expectation-value"),
    side_effects="pure",
    required_permission="capability:invoke",
    interaction="request_response",
)


class ZeroNoiseExtrapolation:
    """Generic capability: digital zero-noise extrapolation (unitary folding +
    polynomial extrapolation) with a mandatory equal-cost negative control."""

    @property
    def manifest(self) -> CapabilityManifest:
        return _ZNE_MANIFEST

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Invoke the capability. Heavy deps loaded lazily on first call."""
        return self._run(inputs)

    def _run(self, inputs: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._invoke_impl(inputs)
        except ImportError as exc:
            raise ImportError(
                f"ZeroNoiseExtrapolation: optional dependency missing. "
                f"Install blite-cap-quantum[qaoa]: {exc}"
            ) from exc

    def _invoke_impl(self, inputs: dict[str, Any]) -> dict[str, Any]:
        from blite_cap_quantum.zne import (
            DEFAULT_SCALE_FACTORS,
            EXTRAPOLATOR_RICHARDSON,
            mitigate_expectation,
        )

        optimize = inputs.get("optimize", True)
        if not isinstance(optimize, bool):
            msg = f"ZeroNoiseExtrapolation: optimize debe ser booleano, no {optimize!r}"
            raise ValueError(msg)
        crudas = inputs.get("scale_factors", list(DEFAULT_SCALE_FACTORS))
        if not isinstance(crudas, list) or not crudas:
            msg = (
                "ZeroNoiseExtrapolation: scale_factors debe ser una lista no "
                f"vacía de enteros impares, no {crudas!r}"
            )
            raise ValueError(msg)
        escalas: list[int] = []
        for valor in cast("list[object]", crudas):
            # Un float acá se truncaría en silencio a un factor distinto del
            # pedido, y el `mitigation.model_digest` diría otra cosa que la
            # corrida: mejor explotar en la frontera.
            if isinstance(valor, bool) or not isinstance(valor, int):
                msg = (
                    "ZeroNoiseExtrapolation: scale_factors debe traer enteros, "
                    f"llegó {valor!r}"
                )
                raise ValueError(msg)
            escalas.append(valor)
        return mitigate_expectation(
            inputs.get("matrix"),
            layers=int(inputs.get("layers", 1)),
            seed=int(inputs.get("seed", 1)),
            initial_angles=inputs.get("initial_angles"),
            optimize=optimize,
            scale_factors=[int(e) for e in escalas],
            extrapolator=str(inputs.get("extrapolator", EXTRAPOLATOR_RICHARDSON)),
            one_qubit_noise=float(inputs.get("one_qubit_noise", 0.002)),
            two_qubit_noise=float(inputs.get("two_qubit_noise", 0.02)),
            shots=int(inputs.get("shots", 2048)),
        )
