"""Unit tests de `MaxCutBaseline._invoke_impl` — baselines clásicos de Max-Cut
(Goemans-Williamson + greedy), lado PROPOSER (context.md, patrón `capabilities/solvers`).

Convención QUBO congelada (context.md — misma que blite_cap_solvers.qubo):
Q simétrica, se MAXIMIZA C(x) = xᵀQx sobre x binario; para Max-Cut el óptimo
de C(x) coincide con el valor del corte. Los pesos del grafo se reconstruyen
como W_uv = -Q[u][v] (u≠v) — inversa exacta del transform del generador del
corpus (scripts/gen_corpus_islanding.py).

GW (Goemans & Williamson 1995): relajación SDP + redondeo por hiperplano
aleatorio (K intentos, mejor corte); cota de aproximación ≈0.878·óptimo.
greedy: recorrido secuencial determinista; garantía clásica corte ≥ óptimo/2
(vale para cualquier grafo, cualquier orden de recorrido).
"""

from __future__ import annotations

import json
import math
from importlib.util import find_spec
from pathlib import Path
from typing import Any

import pytest

from blite_cap_graphs import MaxCutBaseline

_INSTANCES = [
    "ieee9-uniforme",
    "ieee9-flujo",
    "ieee14-uniforme",
    "ieee14-flujo",
    "ieee30-uniforme",
    "ieee30-flujo",
]

# Candado de regresión determinista: energy OBSERVADOS tras implementar
# (greedy determinista puro; gw con seed=1, K=100 hiperplanos — ver maxcut.py).
# No son valores derivados analíticamente, son la salida real del solver.
_GREEDY_GOLDEN = {
    "ieee9-uniforme": 9,
    "ieee9-flujo": 63769,
    "ieee14-uniforme": 15,
    "ieee14-flujo": 57070,
    "ieee30-uniforme": 34,
    "ieee30-flujo": 30997,
}
_requires_cvxpy = pytest.mark.skipif(
    find_spec("cvxpy") is None,
    reason="extra opcional: uv sync --all-packages --extra gw",
)


def _find_corpus() -> Path:
    for base in (Path(__file__).resolve(), *Path(__file__).resolve().parents):
        candidate = base / "knowledge" / "islanding" / "corpus"
        if candidate.is_dir():
            return candidate
    msg = "corpus de islanding no encontrado sobre este archivo"
    raise FileNotFoundError(msg)


def _load_instance(
    name: str,
) -> tuple[list[list[int]], list[tuple[int, int, int]], int]:
    record: dict[str, Any] = json.loads(
        (_find_corpus() / f"{name}.json").read_text(encoding="utf-8")
    )
    edges = [(int(u), int(v), int(w)) for u, v, w in record["aristas"]]
    n = int(record["n_nodos"])
    matrix = [[0] * n for _ in range(n)]
    for u, v, w in edges:
        matrix[u][u] += w
        matrix[v][v] += w
        matrix[u][v] -= w
        matrix[v][u] -= w
    return matrix, edges, int(record["optimo"])


def _cut_value(assignment: list[int], edges: list[tuple[int, int, int]]) -> int:
    return sum(w for u, v, w in edges if assignment[u] != assignment[v])


class TestGreedyCorpusGoldenPath:
    @pytest.mark.parametrize("name", _INSTANCES)
    def test_meets_half_optimum_guarantee(self, name: str) -> None:
        # Arrange
        matrix, edges, optimo = _load_instance(name)

        # Act
        result = MaxCutBaseline().invoke({"matrix": matrix, "method": "greedy"})

        # Assert — consistencia interna + cota clásica greedy: corte >= W/2 >= óptimo/2
        assert result["energy"] == _cut_value(result["assignment"], edges)
        assert 0 <= result["energy"] <= optimo
        assert result["energy"] >= optimo // 2
        assert result["assignment"][0] == 0

    @pytest.mark.parametrize("name", _INSTANCES)
    def test_reproduces_observed_golden_energy(self, name: str) -> None:
        # Arrange
        matrix, _edges, _optimo = _load_instance(name)

        # Act
        result = MaxCutBaseline().invoke({"matrix": matrix, "method": "greedy"})

        # Assert
        assert result["energy"] == _GREEDY_GOLDEN[name]

    def test_is_deterministic(self) -> None:
        # Arrange
        matrix, _edges, _optimo = _load_instance("ieee14-flujo")

        # Act
        first = MaxCutBaseline().invoke({"matrix": matrix, "method": "greedy"})
        second = MaxCutBaseline().invoke({"matrix": matrix, "method": "greedy"})

        # Assert
        assert first["assignment"] == second["assignment"]


@_requires_cvxpy
class TestGwCorpusGoldenPath:
    @pytest.mark.parametrize("name", _INSTANCES)
    def test_meets_approximation_guarantee_and_is_deterministic(
        self, name: str
    ) -> None:
        # Arrange
        matrix, edges, optimo = _load_instance(name)

        # Act — dos corridas con el mismo seed
        first = MaxCutBaseline().invoke({"matrix": matrix, "method": "gw", "seed": 1})
        second = MaxCutBaseline().invoke({"matrix": matrix, "method": "gw", "seed": 1})

        # Assert — consistencia interna, cota GW (K redondeos), determinismo
        assert first["energy"] == _cut_value(first["assignment"], edges)
        assert 0 <= first["energy"] <= optimo
        assert first["energy"] >= math.ceil(0.878 * optimo)
        assert first["assignment"] == second["assignment"]


class TestInputValidation:
    def test_invalid_method_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="method"):
            MaxCutBaseline().invoke({"matrix": [[0, -1], [-1, 0]], "method": "bogus"})
