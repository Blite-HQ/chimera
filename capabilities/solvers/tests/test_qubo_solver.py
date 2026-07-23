"""Unit tests de `QuboSolver._invoke_impl` (CP-SAT real, lado proposer).

Convención congelada (knowledge/quantum/02 §1.2): Q simétrica, MAXIMIZACIÓN
de C(x) = xᵀQx. El caso G6 (triángulo w₀₁=1, w₁₂=2, w₀₂=3, óptimo 5) está
chequeado a mano en esa nota. El Verifier CP-SAT del engine es otro adapter
(blite/verification/exact_solver.py) — esto es el proposer, no lo duplica.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from blite_cap_solvers import QuboSolver

# G6 de knowledge/quantum/02 §1.2 — óptimo 5 en [0,0,1] (o su complemento)
_G6 = [[4, -1, -3], [-1, 3, -2], [-3, -2, 5]]


def _energy(matrix: list[list[int]], assignment: list[int]) -> int:
    n = len(assignment)
    return sum(
        matrix[i][j] * assignment[i] * assignment[j] for i in range(n) for j in range(n)
    )


class TestSolve:
    def test_g6_triangle_reaches_hand_checked_optimum(self) -> None:
        # Act
        result = QuboSolver().invoke({"matrix": _G6})

        # Assert — energía óptima 5, asignación consistente con su energía
        assert result["energy"] == 5
        assert result["status"] == "OPTIMAL"
        assert _energy(_G6, result["assignment"]) == 5

    def test_diagonal_matrix_picks_only_positive_terms(self) -> None:
        # Arrange — maximización: activa Q_ii=2, deja fuera Q_ii=-3
        result = QuboSolver().invoke({"matrix": [[2, 0], [0, -3]]})

        assert result["assignment"] == [1, 0]
        assert result["energy"] == 2

    def test_same_input_yields_identical_assignment(self) -> None:
        # Determinismo congelado: workers=1 + seed fija (trust/10 §1.4)
        first = QuboSolver().invoke({"matrix": _G6})
        second = QuboSolver().invoke({"matrix": _G6})

        assert first["assignment"] == second["assignment"]


class TestCorpusGoldenPath:
    def test_ieee14_flujo_qubo_reproduces_frozen_optimum(self) -> None:
        # Arrange — Q por la regla §1.2 desde el corpus congelado
        corpus = self._find_corpus() / "ieee14-flujo.json"
        record: dict[str, Any] = json.loads(corpus.read_text(encoding="utf-8"))
        edges = [(int(u), int(v), int(w)) for u, v, w in record["aristas"]]
        n = int(record["n_nodos"])
        matrix = [[0] * n for _ in range(n)]
        for u, v, w in edges:
            matrix[u][u] += w
            matrix[v][v] += w
            matrix[u][v] -= w
            matrix[v][u] -= w

        # Act
        result = QuboSolver().invoke({"matrix": matrix})

        # Assert — energía QUBO == corte == óptimo congelado (doble vía)
        assert result["energy"] == record["optimo"] == 57_070
        cut = sum(
            w for u, v, w in edges if result["assignment"][u] != result["assignment"][v]
        )
        assert cut == 57_070

    @staticmethod
    def _find_corpus() -> Path:
        for base in (Path(__file__).resolve(), *Path(__file__).resolve().parents):
            candidate = base / "knowledge" / "islanding" / "corpus"
            if candidate.is_dir():
                return candidate
        msg = "corpus de islanding no encontrado sobre este archivo"
        raise FileNotFoundError(msg)


class TestInputValidation:
    def test_missing_matrix_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="matrix"):
            QuboSolver().invoke({})

    def test_non_square_matrix_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="cuadrada"):
            QuboSolver().invoke({"matrix": [[1, 2]]})

    def test_asymmetric_matrix_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="sim"):
            QuboSolver().invoke({"matrix": [[1, 2], [3, 1]]})

    def test_non_integral_entries_raise_value_error(self) -> None:
        # El caso exacto es entero (trust/10 §1.5); el escalado float es del
        # llamador — jamás redondeo silencioso del solver
        with pytest.raises(ValueError, match="enter"):
            QuboSolver().invoke({"matrix": [[0.5, 0], [0, 1]]})

    def test_integral_floats_are_accepted(self) -> None:
        result = QuboSolver().invoke({"matrix": [[2.0, 0.0], [0.0, -3.0]]})

        assert result["energy"] == 2
