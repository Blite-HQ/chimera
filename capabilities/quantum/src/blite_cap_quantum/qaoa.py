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

V5 (aditivo — sin argumentos nuevos el comportamiento es idéntico): los
ángulos usados SIEMPRE se reportan (`angles`), se puede fijar de dónde
arranca el optimizador (`initial_angles`) o evaluar en un calendario ajeno
sin re-optimizar (`optimize=False`), y se puede subir la escalera p=1…layers
con warm start INTERP (`init_strategy="interp"`, ver `warm_start.py`).
"""

from __future__ import annotations

# Qiskit/scipy no publican stubs completos — se silencian SOLO los reportes de
# tipos desconocidos de terceros; las firmas propias siguen bajo strict.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
from dataclasses import dataclass
from typing import Any, cast

from blite_cap_quantum.warm_start import interp_angles

_MAX_QUBITS = 20
_SHOTS = 2048
_COBYLA_MAX_ITER = 200
_INITIAL_ANGLE = 0.1
_BASIS_GATES = ["rz", "ry", "rx", "h", "cx"]

CONSTANT_INIT = "constant"
"""Arranque histórico: todos los ángulos en `_INITIAL_ANGLE`."""
INTERP_INIT = "interp"
"""Escalera p=1…layers, cada nivel arrancando del anterior interpolado."""
GIVEN_INIT = "given"
"""Los ángulos vinieron de afuera — NO es una estrategia pedible, es lo que
se reporta cuando el llamante pasó `initial_angles`."""

_INIT_STRATEGIES = (CONSTANT_INIT, INTERP_INIT)
_ANGLE_FAMILIES = ("betas", "gammas")
_BETA = "β"
_GAMMA = "γ"


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


def _validate_initial_angles(raw: Any, layers: int) -> tuple[float, ...]:
    """Valida `{'betas': [...], 'gammas': [...]}` y lo aplana a betas+gammas.

    El calendario entra y sale con la MISMA forma, así que la salida de una
    corrida se puede re-inyectar tal cual en otra — que es exactamente lo que
    hace comparables dos corridas sobre los mismos ángulos.
    """
    if not isinstance(raw, dict):
        msg = "initial_angles debe ser un objeto {'betas': [...], 'gammas': [...]}"
        raise ValueError(msg)
    angles = cast("dict[str, object]", raw)
    desconocidas = sorted(set(angles) - set(_ANGLE_FAMILIES))
    if desconocidas:
        msg = f"initial_angles solo admite betas/gammas; sobra: {desconocidas}"
        raise ValueError(msg)

    plano: list[float] = []
    for familia in _ANGLE_FAMILIES:
        valores = angles.get(familia)
        if not isinstance(valores, list):
            msg = (
                f"initial_angles.{familia} debe ser una lista de números (una por capa)"
            )
            raise ValueError(msg)
        items = cast("list[object]", valores)
        if len(items) != layers:
            msg = (
                f"initial_angles.{familia} trae {len(items)} ángulos y el "
                f"circuito tiene {layers} capas — un calendario incompleto no "
                "describe el circuito que se dice haber corrido"
            )
            raise ValueError(msg)
        for value in items:
            if isinstance(value, bool) or not isinstance(value, int | float):
                msg = f"initial_angles.{familia} no es numérico: {value!r}"
                raise ValueError(msg)
            plano.append(float(value))
    return tuple(plano)


def _angle_parameters(circuit: Any, layers: int) -> list[Any]:
    """Parámetros del ansatz en orden canónico β₀…β_{p−1}, γ₀…γ_{p−1}.

    Resueltos por NOMBRE, no por posición: el orden de `circuit.parameters`
    es un detalle de Qiskit, y confundir β con γ no produce un error — produce
    una energía plausible de un circuito distinto del que se reporta. Por
    nombre, un cambio de ansatz revienta ruidosamente acá.
    """
    familias: dict[str, list[Any]] = {f: [None] * layers for f in (_BETA, _GAMMA)}
    for parameter in circuit.parameters:
        nombre = str(parameter)
        familia, _, resto = nombre.partition("[")
        destino = familias.get(familia)
        if destino is None or not resto.endswith("]"):
            msg = f"parámetro inesperado en el ansatz QAOA: {nombre!r}"
            raise RuntimeError(msg)
        destino[int(resto[:-1])] = parameter
    ordenados = familias[_BETA] + familias[_GAMMA]
    if any(parameter is None for parameter in ordenados):
        msg = f"el ansatz de {layers} capas no expuso una β y una γ por capa"
        raise RuntimeError(msg)
    return ordenados


@dataclass(frozen=True)
class _LevelResult:
    """Lo que deja un nivel: sus ángulos, su ⟨H⟩ y el circuito ligado en ellos."""

    angles: tuple[float, ...]
    expectation: float
    circuit: Any


def _solve_level(
    hamiltonian: Any,
    *,
    layers: int,
    seed: int,
    start: tuple[float, ...],
    optimize: bool,
) -> _LevelResult:
    """Sintetiza el ansatz de `layers` capas y devuelve los ángulos finales.

    ⟨H⟩ se recomputa SIEMPRE sobre los ángulos finales en vez de leerse del
    `fun` de COBYLA: así el valor reportado es el del circuito que se ligó y
    se muestreó, y re-evaluar esos mismos ángulos con `optimize=False`
    devuelve el mismo número por construcción, no por suerte.
    """
    import numpy as np
    from qiskit import transpile
    from qiskit.circuit.library import QAOAAnsatz
    from qiskit.quantum_info import Statevector
    from scipy.optimize import minimize

    ansatz = QAOAAnsatz(cost_operator=hamiltonian, reps=layers)
    # Sintetizar los PauliEvolution UNA vez (exponenciales scipy caras);
    # después solo se ligan parámetros sobre gates básicos.
    synthesized = transpile(ansatz, basis_gates=_BASIS_GATES, seed_transpiler=seed)
    orden = _angle_parameters(synthesized, layers)

    def bind(theta: Any) -> Any:
        bound = synthesized.assign_parameters(dict(zip(orden, theta, strict=True)))
        if bound is None:  # pragma: no cover — solo ocurre con inplace=True
            msg = "assign_parameters devolvió None sobre el circuito sintetizado"
            raise RuntimeError(msg)
        return bound

    def expectation(theta: Any) -> float:
        state = Statevector(bind(theta))
        return float(np.real(state.expectation_value(hamiltonian)))

    final = start
    if optimize:
        optimized = minimize(
            expectation,
            np.array(start),
            method="COBYLA",
            options={"maxiter": _COBYLA_MAX_ITER},
        )
        final = tuple(float(angle) for angle in optimized.x)
    return _LevelResult(
        angles=final, expectation=expectation(final), circuit=bind(final)
    )


def _schedule(angles: tuple[float, ...], layers: int) -> dict[str, list[float]]:
    """Aplana ↔ familias: la forma en que los ángulos entran y salen."""
    return {"betas": list(angles[:layers]), "gammas": list(angles[layers:])}


def _climb_interp(
    hamiltonian: Any, *, layers: int, seed: int, offset: float
) -> tuple[_LevelResult, list[dict[str, Any]]]:
    """Sube la escalera p=1…layers con warm start INTERP.

    Cada peldaño queda registrado con su ⟨C⟩ y sus ángulos: la curva r vs p
    de una corrida INTERP se lee del resultado en vez de re-correr el barrido
    (y esos peldaños son los que INTERP realmente usó, no una re-medición).
    """
    arranque: tuple[float, ...] = (_INITIAL_ANGLE, _INITIAL_ANGLE)
    nivel = _solve_level(
        hamiltonian, layers=1, seed=seed, start=arranque, optimize=True
    )
    escalera: list[dict[str, Any]] = []
    for p in range(1, layers + 1):
        if p > 1:
            nivel = _solve_level(
                hamiltonian, layers=p, seed=seed, start=arranque, optimize=True
            )
        calendario = _schedule(nivel.angles, p)
        escalera.append(
            {"p": p, **calendario, "expected_energy": -offset - nivel.expectation}
        )
        arranque = interp_angles(calendario["betas"]) + interp_angles(
            calendario["gammas"]
        )
    return nivel, escalera


def _resolve_init(
    initial_angles: Any, *, layers: int, optimize: bool, init_strategy: str
) -> tuple[str, tuple[float, ...] | None]:
    """Decide (estrategia reportada, arranque) o explota. Nunca elige en silencio."""
    if init_strategy not in _INIT_STRATEGIES:
        msg = (
            f"init_strategy debe ser uno de {list(_INIT_STRATEGIES)}, "
            f"no {init_strategy!r}"
        )
        raise ValueError(msg)
    if initial_angles is None:
        if not optimize:
            msg = (
                "optimize=False exige initial_angles: sin ellos se evaluaría en "
                "el arranque constante arbitrario y se reportaría como resultado"
            )
            raise ValueError(msg)
        return init_strategy, None
    if init_strategy == INTERP_INIT:
        msg = (
            "initial_angles e init_strategy='interp' son excluyentes: son dos "
            "respuestas distintas a de dónde arranca el optimizador"
        )
        raise ValueError(msg)
    return GIVEN_INIT, _validate_initial_angles(initial_angles, layers)


def solve_qaoa(  # noqa: PLR0913 — la superficie del proposer es su contrato con el experimento
    raw_matrix: Any,
    *,
    layers: int = 2,
    seed: int = 1,
    reference_optimum: float | None = None,
    initial_angles: Any = None,
    optimize: bool = True,
    init_strategy: str = CONSTANT_INIT,
) -> dict[str, Any]:
    """Corre QAOA y devuelve la mejor partición muestreada (con su energía)."""
    import numpy as np
    from qiskit import transpile
    from qiskit_aer import AerSimulator
    from qiskit_optimization import QuadraticProgram
    from qiskit_optimization.translators import to_ising

    matrix = _validate_matrix(raw_matrix)
    if isinstance(layers, bool) or layers < 1:
        msg = f"layers debe ser un entero >= 1, no {layers!r}"
        raise ValueError(msg)
    estrategia, arranque = _resolve_init(
        initial_angles, layers=layers, optimize=optimize, init_strategy=init_strategy
    )

    program = QuadraticProgram()
    for i in range(len(matrix)):
        program.binary_var(f"x{i}")
    # Convención §1.2: se MAXIMIZA xᵀQx ⇒ el Ising minimiza −Q
    program.minimize(quadratic=(-np.array(matrix)))
    hamiltonian, offset = to_ising(program)

    escalera: list[dict[str, Any]] | None = None
    if estrategia == INTERP_INIT:
        nivel, escalera = _climb_interp(
            hamiltonian, layers=layers, seed=seed, offset=float(offset)
        )
    else:
        nivel = _solve_level(
            hamiltonian,
            layers=layers,
            seed=seed,
            start=(_INITIAL_ANGLE,) * (2 * layers) if arranque is None else arranque,
            optimize=optimize,
        )

    final_circuit = nivel.circuit
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
    expected_energy = -float(offset) - nivel.expectation
    sampled_mean_energy = _sampled_mean_energy(counts, matrix)

    result: dict[str, Any] = {
        "assignment": assignment,
        "energy": energy,
        "layers": layers,
        "seed": seed,
        "shots": _SHOTS,
        "expected_energy": expected_energy,
        "sampled_mean_energy": sampled_mean_energy,
        "angles": _schedule(nivel.angles, layers),
        "init_strategy": estrategia,
        "optimized": optimize,
    }
    if escalera is not None:
        result["warm_start_levels"] = escalera
    if reference_optimum is not None:
        if reference_optimum <= 0:
            msg = f"reference_optimum debe ser > 0, no {reference_optimum!r}"
            raise ValueError(msg)
        result["approximation_ratio"] = energy / float(reference_optimum)
        result["expected_ratio"] = expected_energy / float(reference_optimum)
    return result
