"""Resolución exacta de QUBO con CP-SAT — lado PROPOSER (baseline clásico).

Convención congelada (knowledge/quantum/02 §1.2): Q simétrica y se MAXIMIZA
C(x) = xᵀQx sobre x binario. Caso exacto entero (trust/10 §1.5): las entradas
deben ser enteras (o floats integrales) — el escalado de un QUBO float es
decisión del llamador, jamás redondeo silencioso del solver.

Determinismo reproducible (trust/10 §1.4): workers=1, seed fija, presupuesto
en tiempo DETERMINISTA. El Verifier diferencial del engine
(blite/verification/exact_solver.py) es un adapter distinto — esto propone,
aquello refuta; no comparten código por diseño (doble ancla).

G5 — baseline heurístico (Simulated Annealing, `dwave.samplers`): mismo rol
PROPOSER, misma convención Q simétrica/MAXIMIZA xᵀQx, seed fija para el
mismo determinismo reproducible — pero SIN prueba de optimalidad. Honestidad
(trust/10): su `status` se reporta 'HEURISTIC', nunca 'OPTIMAL'/'FEASIBLE'
(vocabulario reservado al solver que sí lo prueba, `solve_qubo`).
"""

from __future__ import annotations

from typing import Any, cast

_RANDOM_SEED = 1
_MAX_DETERMINISTIC_TIME = 60.0
_SA_NUM_READS = 50


def _validate_matrix(raw: Any) -> list[list[int]]:
    if not isinstance(raw, list) or not raw:
        msg = "QuboSolver: input 'matrix' (lista de listas, no vacía) es requerida"
        raise ValueError(msg)
    rows = cast("list[object]", raw)
    n = len(rows)
    matrix: list[list[int]] = []
    for i, row in enumerate(rows):
        if not isinstance(row, list) or len(cast("list[object]", row)) != n:
            msg = f"matrix debe ser cuadrada: fila {i} tiene largo distinto de {n}"
            raise ValueError(msg)
        entries: list[int] = []
        for j, value in enumerate(cast("list[object]", row)):
            if isinstance(value, bool) or not isinstance(value, int | float):
                msg = f"matrix[{i}][{j}] no es numérico: {value!r}"
                raise ValueError(msg)
            if float(value) != int(value):
                msg = (
                    f"matrix[{i}][{j}]={value!r} no es entera: el caso exacto "
                    "es entero; escale y redondee ANTES de llamar al solver"
                )
                raise ValueError(msg)
            entries.append(int(value))
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


def _energy(matrix: list[list[int]], assignment: list[int]) -> int:
    n = len(assignment)
    return sum(
        matrix[i][j] * assignment[i] * assignment[j] for i in range(n) for j in range(n)
    )


def solve_qubo(raw_matrix: Any) -> dict[str, Any]:
    """Maximiza xᵀQx con CP-SAT (linealización AND de los productos x_i·x_j)."""
    from ortools.sat.python import cp_model

    matrix = _validate_matrix(raw_matrix)
    n = len(matrix)

    model = cp_model.CpModel()
    x = [model.new_bool_var(f"x{i}") for i in range(n)]
    objective_terms: list[Any] = [
        matrix[i][i] * x[i] for i in range(n) if matrix[i][i] != 0
    ]
    for i in range(n):
        for j in range(i + 1, n):
            if matrix[i][j] == 0:
                continue
            y = model.new_bool_var(f"y_{i}_{j}")
            model.add(y <= x[i])
            model.add(y <= x[j])
            model.add(y >= x[i] + x[j] - 1)
            objective_terms.append(2 * matrix[i][j] * y)
    model.maximize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = _RANDOM_SEED
    solver.parameters.max_deterministic_time = _MAX_DETERMINISTIC_TIME
    status = solver.status_name(solver.solve(model))

    if status == "UNKNOWN":
        msg = (
            f"CP-SAT agotó el presupuesto determinista ({_MAX_DETERMINISTIC_TIME}) "
            "sin incumbente — instancia demasiado grande para este adapter"
        )
        raise RuntimeError(msg)
    if status not in ("OPTIMAL", "FEASIBLE"):
        msg = f"CP-SAT devolvió {status} en un QUBO sin restricciones — bug de modelado"
        raise RuntimeError(msg)
    assignment = [int(solver.value(var)) for var in x]
    energy = int(round(solver.objective_value))
    recomputed = _energy(matrix, assignment)
    if recomputed != energy:
        msg = f"CP-SAT inconsistente: objetivo {energy} != recompute {recomputed}"
        raise RuntimeError(msg)
    return {"assignment": assignment, "energy": energy, "status": status}


def _qubo_dict_from_matrix(matrix: list[list[int]]) -> dict[tuple[int, int], int]:
    """Adapter de signo dimod-vs-convención (§1.2): dimod MINIMIZA, acá se
    MAXIMIZA xᵀQx — así que Q_dimod = -Q. La diagonal se incluye SIEMPRE,
    incluso en cero: dimod solo registra una variable en el sample si
    aparece como key del dict, así que omitir una diagonal cero la dejaría
    fuera de la asignación devuelta. El off-diagonal usa el factor 2
    (Q_dimod[i][j] = -2*matrix[i][j] para i<j) porque `matrix` es simétrica
    y xᵀQx cuenta Q[i][j] + Q[j][i] — dimod espera esa suma ya colapsada en
    el triángulo superior. Verificado contra un óptimo conocido (triángulo
    G6) en tests/test_qubo_solver.py::TestSimulatedAnnealingBackend."""
    n = len(matrix)
    q: dict[tuple[int, int], int] = {}
    for i in range(n):
        q[(i, i)] = -matrix[i][i]
        for j in range(i + 1, n):
            if matrix[i][j] != 0:
                q[(i, j)] = -2 * matrix[i][j]
    return q


def solve_qubo_sa(raw_matrix: Any) -> dict[str, Any]:
    """Maximiza xᵀQx heurísticamente con Simulated Annealing (G5, baseline
    clásico — `dwave.samplers.SimulatedAnnealingSampler`, no `neal`: ese
    paquete no está instalado en este entorno, `dwave.samplers` sí).

    Determinismo reproducible (mismo principio que `solve_qubo`, trust/10
    §1.4): seed fija + num_reads fijo, sin presupuesto de tiempo (SA no lo
    necesita — corre un número fijo de reads, no busca hasta un límite).

    SIN garantía de optimalidad — a diferencia de CP-SAT, SA no prueba que
    su mejor `assignment` sea el máximo real. El `status` se reporta
    'HEURISTIC', nunca 'OPTIMAL'/'FEASIBLE' (honestidad, trust/10)."""
    from dwave.samplers import SimulatedAnnealingSampler

    matrix = _validate_matrix(raw_matrix)
    n = len(matrix)
    qubo_dict = _qubo_dict_from_matrix(matrix)

    # cast(Any, ...) — mismo patrón que blite_cap_graphs.maxcut para cvxpy:
    # dwave-samplers tiene py.typed pero `sample_qubo(self, Q, **parameters)`
    # deja **parameters sin anotar, lo que bajo pyright strict propaga
    # "Unknown" a SampleSet/SampleView completos. No es un hueco nuestro:
    # es la superficie pública de la librería.
    sampler = cast(Any, SimulatedAnnealingSampler)()
    sampleset = sampler.sample_qubo(
        qubo_dict, seed=_RANDOM_SEED, num_reads=_SA_NUM_READS
    )
    best_sample = sampleset.first.sample
    assignment = [int(best_sample[i]) for i in range(n)]
    energy = _energy(matrix, assignment)
    return {"assignment": assignment, "energy": energy, "status": "HEURISTIC"}
