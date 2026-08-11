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


class TestSimulatedAnnealingBackend:
    """G5: baseline heurístico de Simulated Annealing (dwave.samplers,
    SimulatedAnnealingSampler) — mismo rol PROPOSER que CP-SAT pero SIN
    garantía de optimalidad. Convención §1.2 sin cambios: Q simétrica, se
    MAXIMIZA xᵀQx. Reusa G6 (triángulo, óptimo hand-checked = 5) para
    verificar el adapter de signo: dimod MINIMIZA, así que un adapter con
    el signo invertido convergería a 0 (el MÍNIMO real de G6, ver
    knowledge/quantum/02 §1.2), no a 5."""

    def test_sa_reaches_hand_checked_optimum_not_the_minimum(self) -> None:
        # Act
        result = QuboSolver().invoke({"matrix": _G6, "backend": "sa"})

        # Assert — 5 es el MAX de xᵀQx en G6; 0 (asignación [0,0,0]/[1,1,1])
        # es el MIN — si el adapter de signo estuviera invertido, SA
        # convergería ahí en vez de acá
        assert result["energy"] == 5
        assert _energy(_G6, result["assignment"]) == 5

    def test_sa_is_deterministic_across_runs(self) -> None:
        # Determinismo reproducible (mismo principio CP-SAT, trust/10 §1.4):
        # seed fija + num_reads fijo
        first = QuboSolver().invoke({"matrix": _G6, "backend": "sa"})
        second = QuboSolver().invoke({"matrix": _G6, "backend": "sa"})

        assert first["assignment"] == second["assignment"]
        assert first["energy"] == second["energy"]

    def test_sa_never_claims_proven_optimal(self) -> None:
        # Honestidad (trust/10): SA es heurístico, jamás prueba optimalidad
        # — el vocabulario 'OPTIMAL'/'FEASIBLE' queda reservado a CP-SAT
        result = QuboSolver().invoke({"matrix": _G6, "backend": "sa"})

        assert result["status"] not in ("OPTIMAL", "FEASIBLE")
        assert result["status"] == "HEURISTIC"


class TestManifestSinDriftDeBackend:
    """Hallazgo 12 del handoff S3: el manifest anunciaba un backend que
    `invoke` rechazaba. El planner ELIGE sobre el manifest, así que un enum
    que promete lo que la implementación niega es una mentira de contrato.
    El enum y el guard salen ahora de la misma tupla — este test lo fija."""

    def test_todo_valor_del_enum_es_aceptado_por_invoke(self) -> None:
        enum = QuboSolver().manifest.input_schema["properties"]["backend"]["enum"]

        assert enum, "el manifest declara el eje backend sin valores"
        for backend in enum:
            resultado = QuboSolver().invoke({"matrix": _G6, "backend": backend})
            assert len(resultado["assignment"]) == 3

    def test_el_default_del_enum_esta_en_el_enum(self) -> None:
        esquema = QuboSolver().manifest.input_schema["properties"]["backend"]

        assert esquema["default"] in esquema["enum"]

    def test_backend_fuera_del_enum_falla_fuerte(self) -> None:
        with pytest.raises(ValueError, match="no implementado"):
            QuboSolver().invoke({"matrix": _G6, "backend": "gurobi"})


class TestGenericitySelfCheck:
    """ADR-029: el gate del repo (tests/invariants/test_capability_genericity.py)
    lee entry points INSTALADOS — en este worktree resuelve por PYTHONPATH,
    así que en la práctica sí ve este manifest, pero esta aserción local
    (plantilla: capabilities/quantum/tests/test_zne.py:432) es la que queda
    ejercitada sin depender de ese detalle de entorno."""

    def test_manifest_has_no_scenario_vocabulary(self) -> None:
        import dataclasses
        from pathlib import Path

        denylist_path = (
            Path(__file__).resolve().parents[3]
            / "tests"
            / "invariants"
            / "scenario_denylist.txt"
        )
        denylist = [
            line.strip().lower()
            for line in denylist_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]

        manifest = QuboSolver().manifest
        text = json.dumps(dataclasses.asdict(manifest), default=str).lower()

        violations = [term for term in denylist if term in text]
        assert not violations, (
            f"manifest contiene vocabulario de escenario: {violations}"
        )
