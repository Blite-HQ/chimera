"""Reparación M.3 (REGRID-QAOA, `knowledge/quantum/05-regrid-qaoa-extraccion.md`
§1.5) — descenso greedy con feasibility-feedback de conectividad.

Portado DESDE las ecuaciones del paper (Algorithm 3): no publica repositorio
de código (nota 05 §3), así que no hay implementación de referencia contra la
cual diffear — la única red son los tests de este módulo.

**Convención de signo** (misma que `blite_cap_quantum.qaoa` /
`blite_cap_graphs.maxcut`): la matriz QUBO es simétrica y este repo MAXIMIZA
C(x) = xᵀQx. El paper MINIMIZA su Q(z) (Eq. 39-40) — la condición del
pseudocódigo "Δ_j(z) < 0" (una mejora, en su convención de minimizar) se
traduce acá a `gain_j(z) > 0` (una mejora, en la convención de maximizar de
este repo). Mismo criterio, signo espejado.

**DFS de conectividad**: portado (no importado) desde
`engine/src/blite/verification/execution.py:_is_connected` — ADR-008
prohíbe que una capability importe `blite` (`pyproject.toml`, contrato
"capabilities never import engine internals"). El algoritmo (BFS sobre las
aristas internas de cada clase de la asignación) es cómputo de grafo puro sin
dependencias; se re-implementa acá sobre vocabulario genérico ("clase de la
asignación"), nunca "isla" (ADR-029).

El grafo para el chequeo de conectividad se reconstruye de la MISMA matriz
QUBO recibida: existe arista (i,j) sii `matrix[i][j] != 0` — el mismo grafo
que ve el objetivo (misma convención que `blite_cap_graphs.maxcut._edge_weights`,
W_uv = -Q[u][v]; acá solo importa la EXISTENCIA de la arista, no su peso).

**M.4 (relajación de penalización λ^(r)) NO se porta esta sesión**: M.4
relaja pesos de penalización λ de restricciones codificadas en la QUBO
(tamaño/generadores/cargas — Eqs. 25-27 del paper, encoding one-hot+slacks).
Esa formulación fue **descartada** para este repo (nota 05 §2: "Formulación
K-way one-hot + slacks — descartar (demo)"); la QUBO de este repo es Max-Cut
puro por bisección, sin términos de penalización λ de ningún tipo. No hay
λ que relajar — M.4 no tiene análogo aplicable hasta que exista esa
formulación (Fase 2, si aparece K≥3 islas).
"""

from __future__ import annotations

from collections import deque
from typing import Any, cast

M3_METHOD = "M.3"
"""Único método portado esta sesión (ver nota del módulo sobre M.4)."""

_MIN_BUDGET = 32
_BUDGET_PER_NODE = 8


def _validate_matrix(raw: Any) -> list[list[float]]:
    if not isinstance(raw, list) or not raw:
        msg = "repair_connectivity: 'matrix' (lista de listas, no vacía) es requerida"
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


def _validate_assignment(raw: Any, n: int) -> list[int]:
    if not isinstance(raw, list) or len(cast("list[object]", raw)) != n:
        msg = f"repair_connectivity: 'assignment' debe ser una lista de {n} bits"
        raise ValueError(msg)
    assignment: list[int] = []
    for i, value in enumerate(cast("list[object]", raw)):
        if isinstance(value, bool) or value not in (0, 1):
            msg = f"assignment[{i}] debe ser 0 o 1, no {value!r}"
            raise ValueError(msg)
        assignment.append(int(value))
    return assignment


def energy(matrix: list[list[float]], assignment: list[int]) -> float:
    n = len(assignment)
    return sum(
        matrix[i][j] * assignment[i] * assignment[j] for i in range(n) for j in range(n)
    )


def _flip(assignment: list[int], index: int) -> list[int]:
    """Copia con el bit `index` invertido — nunca muta la entrada."""
    flipped = list(assignment)
    flipped[index] = 1 - flipped[index]
    return flipped


def _graph_edges(matrix: list[list[float]]) -> list[tuple[int, int]]:
    """Arista (i,j) sii `matrix[i][j] != 0` — el mismo grafo que ve C(x)."""
    n = len(matrix)
    return [(i, j) for i in range(n) for j in range(i + 1, n) if matrix[i][j] != 0]


def _class_components(nodes: set[int], edges: list[tuple[int, int]]) -> int:
    """BFS sobre el subgrafo inducido por `nodes` — cuenta sus componentes
    conexas. Porteado de `_is_connected` (execution.py:242), generalizado a
    CONTAR componentes en vez de solo responder sí/no: C(z) necesita el
    número de componentes de más, no un booleano."""
    if len(nodes) <= 1:
        return len(nodes)
    adjacency: dict[int, list[int]] = {node: [] for node in nodes}
    for u, v in edges:
        if u in adjacency and v in adjacency:
            adjacency[u].append(v)
            adjacency[v].append(u)
    seen: set[int] = set()
    components = 0
    for start in nodes:
        if start in seen:
            continue
        components += 1
        queue = deque([start])
        seen.add(start)
        while queue:
            node = queue.popleft()
            for neighbor in adjacency[node]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
    return components


def connectivity_violations(matrix: list[list[float]], assignment: list[int]) -> int:
    """C(z) = Σ_clase (componentes − 1) — 0 sii cada clase de la asignación
    induce un subgrafo conexo (nota 05 §1.5, definición previa a Eq. 45)."""
    edges = _graph_edges(matrix)
    classes: dict[int, set[int]] = {}
    for node, cls in enumerate(assignment):
        classes.setdefault(cls, set()).add(node)
    return sum(_class_components(nodes, edges) - 1 for nodes in classes.values())


def gain(matrix: list[list[float]], assignment: list[int], index: int) -> float:
    """gain_j(z) := C(z⊕e_j) − C(z), convención de MAXIMIZAR de este repo
    (−Δ_j(z) del paper — ver docstring del módulo)."""
    return energy(matrix, _flip(assignment, index)) - energy(matrix, assignment)


def violation_delta(
    matrix: list[list[float]], assignment: list[int], index: int
) -> int:
    """Δ_jC(z) := violaciones(z⊕e_j) − violaciones(z)."""
    after = connectivity_violations(matrix, _flip(assignment, index))
    before = connectivity_violations(matrix, assignment)
    return after - before


def _ascend_to_local_optimum(
    matrix: list[list[float]], assignment: list[int], *, budget: int
) -> tuple[list[int], int]:
    """Etapa 1 (Algorithm 3): descenso QUBO puro — acá, ascenso, por la
    convención de maximizar de este repo. Flipea el bit de mayor ganancia
    mientras exista ganancia ESTRICTAMENTE positiva. UNRESTRICTED por
    diseño del paper: no mira conectividad — eso entra recién en la etapa 2."""
    current = assignment
    flips = 0
    n = len(current)
    for _ in range(budget):
        best_index, best_gain = max(
            ((j, gain(matrix, current, j)) for j in range(n)),
            key=lambda item: item[1],
        )
        if best_gain <= 0:
            return current, flips
        current = _flip(current, best_index)
        flips += 1
    msg = "M.3: la etapa de ascenso QUBO no convergió en el presupuesto de rondas"
    raise RuntimeError(msg)


def restricted_repair_step(
    matrix: list[list[float]], assignment: list[int]
) -> tuple[list[int], bool]:
    """Etapa 2 — feasibility-feedback restringida a conectividad: entre los
    flips que ESTRICTAMENTE reducen violaciones (J(z) del paper), aplica el
    de mejor ganancia — pero SOLO si esa ganancia también es positiva. Un
    candidato que empeoraría o no mejoraría conectividad nunca entra a
    J(z), así que nunca se considera, sin importar cuánta ganancia ofrezca
    (feasibility-feedback real: la tentación del objetivo no compra un flip
    que rompe conectividad). Devuelve (nueva_asignación, aceptado)."""
    n = len(assignment)
    candidates = [
        (j, gain(matrix, assignment, j))
        for j in range(n)
        if violation_delta(matrix, assignment, j) < 0
    ]
    if not candidates:
        return assignment, False
    best_index, best_gain = max(candidates, key=lambda item: item[1])
    if best_gain <= 0:
        return assignment, False
    return _flip(assignment, best_index), True


def repair_connectivity(
    raw_matrix: Any, raw_assignment: Any, *, method: str = M3_METHOD
) -> dict[str, Any]:
    """M.3 completo (Algorithm 3, nota 05 §1.5): descenso QUBO + reparación
    restringida a conectividad, en loop, hasta factibilidad o hasta
    atascarse. Espejo fail-loud: si no hay flip que ayude, la salida es la
    entrada tal cual — `repair.pre_value == repair.post_value`, nunca una
    mejora fabricada.

    `connectivity_violations` en la salida es C(z) del bitstring CRUDO (la
    `raw_assignment` de entrada, antes de reparar) — freeze §11.
    """
    if method != M3_METHOD:
        msg = f"repair_connectivity: method {method!r} no soportado — use {M3_METHOD!r}"
        raise ValueError(msg)
    matrix = _validate_matrix(raw_matrix)
    assignment = _validate_assignment(raw_assignment, len(matrix))

    pre_value = energy(matrix, assignment)
    pre_violations = connectivity_violations(matrix, assignment)

    budget = max(_MIN_BUDGET, _BUDGET_PER_NODE * len(assignment))
    current = assignment
    total_flips = 0
    for _round in range(budget):
        current, ascent_flips = _ascend_to_local_optimum(matrix, current, budget=budget)
        total_flips += ascent_flips
        if connectivity_violations(matrix, current) == 0:
            break
        repaired, accepted = restricted_repair_step(matrix, current)
        if not accepted:
            break
        current = repaired
        total_flips += 1
    else:  # pragma: no cover — cota defensiva; cada ronda aceptada sube la
        # energía estrictamente, así que el loop termina mucho antes en la
        # práctica (espacio de estados finito, sin ciclos posibles)
        msg = "M.3: la reparación no convergió en el presupuesto de rondas"
        raise RuntimeError(msg)

    post_value = energy(matrix, current)
    return {
        "assignment": current,
        "repair": {
            "method": method,
            "flips": total_flips,
            "pre_value": pre_value,
            "post_value": post_value,
        },
        "connectivity_violations": pre_violations,
    }
