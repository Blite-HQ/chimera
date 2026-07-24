"""Baselines clásicos de Max-Cut: Goemans-Williamson (SDP) y greedy — lado
PROPOSER (context.md, mismo rol que `blite_cap_solvers.qubo` / `qaoa.py`).

Convención QUBO congelada (context.md — misma que blite_cap_solvers.qubo):
Q simétrica, se MAXIMIZA C(x) = xᵀQx sobre x binario. Para Max-Cut el óptimo
de C(x) coincide con el valor del corte. Los pesos del grafo se reconstruyen
como W_uv = -Q[u][v] (u≠v) — inversa exacta del transform del generador del
corpus (scripts/gen_corpus_islanding.py).

GW (Goemans & Williamson 1995): relajación SDP
  maximize (1/4) Σ_{u<v} W_uv (1 - Y_uv)   s.a. Y⪰0, diag(Y)=1
seguida de redondeo por hiperplano aleatorio (K intentos, mejor corte se
queda). Cota de aproximación ≈0.878·óptimo (asintótica sobre el ensamble de
hiperplanos, no garantía dura por instancia).

greedy: recorrido secuencial de nodos, cada uno al lado que maximiza el
corte parcial con los ya colocados. Determinista (sin aleatoriedad),
garantía clásica corte ≥ W/2 ≥ óptimo/2 para cualquier grafo y cualquier
orden de recorrido. x[0] queda fijo en 0 (rompe la simetría de complemento).
"""

from __future__ import annotations

from typing import Any, cast

_GW_HYPERPLANES = 100


def _validate_matrix(raw: Any) -> list[list[float]]:
    if not isinstance(raw, list) or not raw:
        msg = "MaxCutBaseline: input 'matrix' (lista de listas, no vacía) es requerida"
        raise ValueError(msg)
    rows = cast("list[object]", raw)
    n = len(rows)
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


def _edge_weights(matrix: list[list[float]]) -> list[list[float]]:
    """W_uv = -Q[u][v] (u≠v); diagonal en 0 (no aporta al corte)."""
    n = len(matrix)
    return [[0.0 if i == j else -matrix[i][j] for j in range(n)] for i in range(n)]


def _energy(matrix: list[list[float]], assignment: list[int]) -> float:
    n = len(assignment)
    return sum(
        matrix[i][j] * assignment[i] * assignment[j] for i in range(n) for j in range(n)
    )


def _greedy(matrix: list[list[float]]) -> list[int]:
    n = len(matrix)
    weights = _edge_weights(matrix)
    assignment = [0] * n
    for i in range(1, n):
        gain_zero = sum(weights[i][j] for j in range(i) if assignment[j] == 1)
        gain_one = sum(weights[i][j] for j in range(i) if assignment[j] == 0)
        assignment[i] = 1 if gain_one > gain_zero else 0
    return assignment


def _gw(matrix: list[list[float]], seed: int) -> list[int]:
    import cvxpy as cp
    import numpy as np

    n = len(matrix)
    weights = _edge_weights(matrix)
    w = cast(Any, np).array(weights)

    y = cast(Any, cp).Variable((n, n), symmetric=True)
    constraints = [y >> 0] + [y[i, i] == 1 for i in range(n)]
    terms = [w[i, j] * (1 - y[i, j]) for i in range(n) for j in range(i + 1, n)]
    objective = cast(Any, cp).Maximize(0.25 * cast(Any, cp).sum(terms))
    problem = cast(Any, cp).Problem(objective, constraints)
    problem.solve()
    if problem.status not in ("optimal", "optimal_inaccurate"):
        msg = f"GW: el solver SDP no convergió (status={problem.status!r})"
        raise RuntimeError(msg)

    y_value = cast(Any, np).asarray(y.value, dtype=float)
    y_sym = (y_value + y_value.T) / 2.0
    eigvals, eigvecs = cast(Any, np).linalg.eigh(y_sym)
    eigvals = cast(Any, np).clip(eigvals, 0.0, None)
    vectors = eigvecs * cast(Any, np).sqrt(eigvals)

    rng = cast(Any, np).random.default_rng(seed)
    best_assignment: list[int] | None = None
    best_energy = float("-inf")
    for _ in range(_GW_HYPERPLANES):
        hyperplane = rng.standard_normal(n)
        projection = vectors @ hyperplane
        candidate = [1 if p >= 0 else 0 for p in projection]
        candidate_energy = _energy(matrix, candidate)
        if candidate_energy > best_energy:
            best_assignment, best_energy = candidate, candidate_energy
    if best_assignment is None:  # pragma: no cover — K>=1 siempre produce una candidata
        msg = "GW: el redondeo por hiperplano no produjo ninguna asignación"
        raise RuntimeError(msg)
    return best_assignment


def solve_maxcut(
    raw_matrix: Any, *, method: str = "greedy", seed: int = 1
) -> dict[str, Any]:
    """Aproxima el Max-Cut de una QUBO simétrica con el método elegido."""
    if method not in ("gw", "greedy"):
        msg = f"MaxCutBaseline: method {method!r} no soportado — use 'gw' o 'greedy'"
        raise ValueError(msg)
    matrix = _validate_matrix(raw_matrix)
    assignment = _greedy(matrix) if method == "greedy" else _gw(matrix, seed)
    energy = _energy(matrix, assignment)
    return {"assignment": assignment, "energy": energy, "method": method, "seed": seed}
