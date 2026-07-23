"""Unit tests de `QaoaSolver._invoke_impl` (Qiskit QAOA + Aer con seed).

Misma convención Q que el proposer clásico (quantum/02 §1.2: simétrica,
maximización). Determinismo del demo (freeze §15.4): Aer + seed pinneada —
mismo input ⇒ misma partición. El decode es el estándar best-of-samples:
cada bitstring medido se evalúa clásicamente contra Q.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip(
    "qiskit", reason="extra opcional: uv sync --all-packages --extra qaoa"
)

from blite_cap_quantum import QaoaSolver  # noqa: E402

# G6 de knowledge/quantum/02 §1.2 — óptimo 5 en [0,0,1] (o su complemento)
_G6 = [[4, -1, -3], [-1, 3, -2], [-3, -2, 5]]


def _energy(matrix: Sequence[Sequence[float]], assignment: list[int]) -> float:
    n = len(assignment)
    return sum(
        matrix[i][j] * assignment[i] * assignment[j] for i in range(n) for j in range(n)
    )


class TestSolve:
    def test_g6_triangle_reaches_hand_checked_optimum(self) -> None:
        # Act
        result = QaoaSolver().invoke({"matrix": _G6, "layers": 2, "seed": 1})

        # Assert — n=3: el best-of-samples alcanza el óptimo a mano (5) y la
        # energía reportada es la de la asignación devuelta
        assert result["energy"] == 5
        assert _energy(_G6, result["assignment"]) == result["energy"]

    def test_same_seed_yields_identical_partition(self) -> None:
        first = QaoaSolver().invoke({"matrix": _G6, "seed": 7})
        second = QaoaSolver().invoke({"matrix": _G6, "seed": 7})

        assert first["assignment"] == second["assignment"]
        assert first["energy"] == second["energy"]

    def test_reference_optimum_reports_approximation_ratio(self) -> None:
        result = QaoaSolver().invoke({"matrix": _G6, "seed": 1, "reference_optimum": 5})

        assert result["approximation_ratio"] == result["energy"] / 5


class TestCorpusGoldenPath:
    def test_ieee9_uniform_partition_is_good_and_consistent(self) -> None:
        # Arrange — ieee9-uniforme: n=9, óptimo 9 (bipartito, corta todo)
        corpus = _find_corpus() / "ieee9-uniforme.json"
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
        result = QaoaSolver().invoke(
            {"matrix": matrix, "layers": 2, "seed": 1, "reference_optimum": 9}
        )

        # Assert — partición buena (criterio r ≥ 0.6 del enunciado) y energía
        # QUBO == corte recomputado sobre las aristas (doble vía)
        assert result["approximation_ratio"] >= 0.6
        cut = sum(
            w for u, v, w in edges if result["assignment"][u] != result["assignment"][v]
        )
        assert cut == result["energy"]


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
            QaoaSolver().invoke({})

    def test_asymmetric_matrix_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="sim"):
            QaoaSolver().invoke({"matrix": [[1, 2], [3, 1]]})

    def test_layers_below_one_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="layers"):
            QaoaSolver().invoke({"matrix": _G6, "layers": 0})

    def test_boolean_layers_raises_value_error(self) -> None:
        # bool es subclase de int: True se colaría como layers=1
        with pytest.raises(ValueError, match="layers"):
            QaoaSolver().invoke({"matrix": _G6, "layers": True})

    def test_non_integer_seed_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="seed"):
            QaoaSolver().invoke({"matrix": _G6, "seed": "1"})

    def test_non_numeric_reference_optimum_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="reference_optimum"):
            QaoaSolver().invoke({"matrix": _G6, "reference_optimum": "5"})

    def test_unimplemented_backend_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="backend"):
            QaoaSolver().invoke({"matrix": _G6, "backend": "runtime"})
