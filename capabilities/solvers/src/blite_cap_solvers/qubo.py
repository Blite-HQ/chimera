"""Resolución exacta de QUBO con CP-SAT — lado PROPOSER (baseline clásico).

Convención congelada (knowledge/quantum/02 §1.2): Q simétrica y se MAXIMIZA
C(x) = xᵀQx sobre x binario. Caso exacto entero (trust/10 §1.5): las entradas
deben ser enteras (o floats integrales) — el escalado de un QUBO float es
decisión del llamador, jamás redondeo silencioso del solver.

Determinismo reproducible (trust/10 §1.4): workers=1, seed fija, presupuesto
en tiempo DETERMINISTA. El Verifier diferencial del engine
(blite/verification/exact_solver.py) es un adapter distinto — esto propone,
aquello refuta; no comparten código por diseño (doble ancla).
"""

from __future__ import annotations

from typing import Any, cast

_RANDOM_SEED = 1
_MAX_DETERMINISTIC_TIME = 60.0


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
        matrix[i][j] * assignment[i] * assignment[j]
        for i in range(n)
        for j in range(n)
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
