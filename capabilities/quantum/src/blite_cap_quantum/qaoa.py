"""QAOA sobre un QUBO (Q simétrica, maximización) — proposer cuántico.

Pipeline (qiskit 2.x sin qiskit_algorithms): QuadraticProgram(minimize −Q)
→ `to_ising` → `QAOAAnsatz(reps=layers)` → optimización clásica de ángulos
(COBYLA sobre la expectativa exacta por statevector — determinista) → muestreo
final en Aer con seed pinneada → decode best-of-samples (cada bitstring medido
se evalúa clásicamente contra Q y gana el mejor).

Determinismo del demo (freeze §15.4 "en vivo solo Aer+seed"): mismo input ⇒
misma partición. El muestreador puede proponer soluciones malas — eso es
información para el Verifier, no vergüenza (quantum/02 §1.3 Ruta A).

Fix 4b (task4b-brief.md): además del best-of-samples (`energy`, óptimo
casi trivial en instancias chicas — no es una métrica de benchmarking
válida), se expone el valor esperado EXACTO ⟨C⟩ de la distribución
variacional en los ángulos óptimos (`expected_energy`) y su estimador
muestral sobre los shots (`sampled_mean_energy`) — ver `_sampled_mean_energy`
y la nota de convención de signo en `solve_qaoa`.
"""

from __future__ import annotations

# Qiskit/scipy no publican stubs completos — se silencian SOLO los reportes de
# tipos desconocidos de terceros; las firmas propias siguen bajo strict.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
from typing import Any, cast

_MAX_QUBITS = 20
_SHOTS = 2048
_COBYLA_MAX_ITER = 200
_INITIAL_ANGLE = 0.1


def _validate_matrix(raw: Any) -> list[list[float]]:
    if not isinstance(raw, list) or not raw:
        msg = "QaoaSolver: input 'matrix' (lista de listas, no vacía) es requerida"
        raise ValueError(msg)
    rows = cast("list[object]", raw)
    n = len(rows)
    if n > _MAX_QUBITS:
        msg = f"matrix de {n} variables excede el presupuesto de {_MAX_QUBITS} qubits"
        raise ValueError(msg)
    matrix: list[list[float]] = []
    for i, row in enumerate(rows):
        if not isinstance(row, list) or len(cast("list[object]", row)) != n:
            msg = f"matrix debe ser cuadrada: fila {i} tiene largo distinto de {n}"
            raise ValueError(msg)
        entries: list[float] = []
        for j, value in enumerate(cast("list[object]", row)):
            if isinstance(value, bool) or not isinstance(value, int | float):
                msg = f"matrix[{i}][{j}] no es numérico: {value!r}"
                raise ValueError(msg)
            entries.append(float(value))
        matrix.append(entries)
    for i in range(n):
        for j in range(i + 1, n):
            if matrix[i][j] != matrix[j][i]:
                msg = (
                    f"matrix no es simétrica: [{i}][{j}]={matrix[i][j]} != "
                    f"[{j}][{i}]={matrix[j][i]} (convención Q simétrica §1.2)"
                )
                raise ValueError(msg)
    return matrix


def _energy(matrix: list[list[float]], assignment: list[int]) -> float:
    n = len(assignment)
    return sum(
        matrix[i][j] * assignment[i] * assignment[j] for i in range(n) for j in range(n)
    )


def _decode_bitstring(bitstring: str, matrix: list[list[float]]) -> list[int]:
    """Bitstrings de qiskit son little-endian (qubit 0 a la derecha)."""
    return [int(bitstring[-1 - i]) for i in range(len(matrix))]


def _decode_best(
    counts: dict[str, int], matrix: list[list[float]]
) -> tuple[list[int], float]:
    """Best-of-samples: la partición muestreada de mayor energía entre shots."""
    best_assignment: list[int] | None = None
    best_energy = float("-inf")
    for bitstring in counts:
        assignment = _decode_bitstring(bitstring, matrix)
        energy = _energy(matrix, assignment)
        if energy > best_energy:
            best_assignment, best_energy = assignment, energy
    if best_assignment is None:  # pragma: no cover — Aer siempre devuelve counts
        msg = "el muestreo no devolvió ningún bitstring"
        raise RuntimeError(msg)
    return best_assignment, best_energy


def _sampled_mean_energy(counts: dict[str, int], matrix: list[list[float]]) -> float:
    """Estimador muestral de ⟨C⟩: media de `_energy` ponderada por counts."""
    total_shots = sum(counts.values())
    weighted_sum = sum(
        _energy(matrix, _decode_bitstring(bitstring, matrix)) * count
        for bitstring, count in counts.items()
    )
    return weighted_sum / total_shots


def solve_qaoa(
    raw_matrix: Any,
    *,
    layers: int = 2,
    seed: int = 1,
    reference_optimum: float | None = None,
) -> dict[str, Any]:
    """Corre QAOA y devuelve la mejor partición muestreada (con su energía)."""
    import numpy as np
    from qiskit import transpile
    from qiskit.circuit.library import QAOAAnsatz
    from qiskit.quantum_info import Statevector
    from qiskit_aer import AerSimulator
    from qiskit_optimization import QuadraticProgram
    from qiskit_optimization.translators import to_ising
    from scipy.optimize import minimize

    matrix = _validate_matrix(raw_matrix)
    if isinstance(layers, bool) or layers < 1:
        msg = f"layers debe ser un entero >= 1, no {layers!r}"
        raise ValueError(msg)

    program = QuadraticProgram()
    for i in range(len(matrix)):
        program.binary_var(f"x{i}")
    # Convención §1.2: se MAXIMIZA xᵀQx ⇒ el Ising minimiza −Q
    program.minimize(quadratic=(-np.array(matrix)))
    hamiltonian, offset = to_ising(program)

    ansatz = QAOAAnsatz(cost_operator=hamiltonian, reps=layers)
    # Sintetizar los PauliEvolution UNA vez (exponenciales scipy caras);
    # después solo se ligan parámetros sobre gates básicos.
    synthesized = transpile(
        ansatz, basis_gates=["rz", "ry", "rx", "h", "cx"], seed_transpiler=seed
    )

    def bind(theta: Any) -> Any:
        bound = synthesized.assign_parameters(theta)
        if bound is None:  # pragma: no cover — solo ocurre con inplace=True
            msg = "assign_parameters devolvió None sobre el circuito sintetizado"
            raise RuntimeError(msg)
        return bound

    def expectation(theta: Any) -> float:
        state = Statevector(bind(theta))
        return float(np.real(state.expectation_value(hamiltonian)))

    initial = np.full(ansatz.num_parameters, _INITIAL_ANGLE)
    optimized = minimize(
        expectation,
        initial,
        method="COBYLA",
        options={"maxiter": _COBYLA_MAX_ITER},
    )

    final_circuit = bind(optimized.x)
    final_circuit.measure_all()
    simulator = AerSimulator(seed_simulator=seed)
    compiled = transpile(final_circuit, simulator, seed_transpiler=seed)
    counts_raw = simulator.run(compiled, shots=_SHOTS).result().get_counts()
    counts = cast("dict[str, int]", counts_raw)

    assignment, energy = _decode_best(counts, matrix)

    # Convención de signo (verificada empíricamente — ver task4b-brief.md):
    # `to_ising` produce H tal que offset + ⟨H⟩ == -(xᵀQx) para cada bitstring
    # x (H es diagonal en base computacional, solo términos Z ⇒ ⟨H⟩ en un
    # estado mixto es la combinación convexa de esos valores por bitstring).
    # COBYLA minimiza ⟨H⟩ = minimiza -corte; el valor esperado del CORTE bajo
    # la distribución variacional en los ángulos óptimos es, por tanto, el
    # positivo -offset - ⟨H⟩_óptimo (comparable a `energy`, NO su negación).
    expected_energy = -float(offset) - float(optimized.fun)
    sampled_mean_energy = _sampled_mean_energy(counts, matrix)

    result: dict[str, Any] = {
        "assignment": assignment,
        "energy": energy,
        "layers": layers,
        "seed": seed,
        "shots": _SHOTS,
        "expected_energy": expected_energy,
        "sampled_mean_energy": sampled_mean_energy,
    }
    if reference_optimum is not None:
        if reference_optimum <= 0:
            msg = f"reference_optimum debe ser > 0, no {reference_optimum!r}"
            raise ValueError(msg)
        result["approximation_ratio"] = energy / float(reference_optimum)
        result["expected_ratio"] = expected_energy / float(reference_optimum)
    return result
