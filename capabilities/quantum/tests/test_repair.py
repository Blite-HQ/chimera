"""Tests de `blite_cap_quantum.repair` — M.3 (REGRID-QAOA,
`knowledge/quantum/05-regrid-qaoa-extraccion.md` §1.5): descenso greedy con
feasibility-feedback de conectividad, portado desde el pseudocódigo del
paper (Algorithm 3). Sin repositorio de referencia público (nota 05 §3) —
estos tests son la única red.

Convención Q (misma que `blite_cap_quantum.qaoa` / `blite_cap_graphs.maxcut`):
simétrica, se MAXIMIZA C(x) = xᵀQx. Los fixtures numéricos de este archivo
son valores OBSERVADOS ejecutando el algoritmo sobre matrices de búsqueda
(mismo patrón que `capabilities/graphs/tests/test_maxcut.py` §"Candado de
regresión determinista": no se derivan a mano, se toman de una corrida real
y quedan fijos como candado de regresión).

Nota importante de diseño verificada empíricamente en esta sesión: para una
QUBO de Max-Cut PURO (sin los términos de penalización algebraica λ que el
paper sí codifica — Eqs. 25-27, descartados en este repo, nota 05 §2), la
etapa 1 (ascenso QUBO sin restricción) SIEMPRE converge a un óptimo local de
1-flip antes de que la etapa 2 pueda actuar — y en un óptimo local, NINGÚN
flip (por definición) mejora estrictamente el objetivo, así que la etapa 2
nunca puede aceptar un flip que la etapa 1 ya habría tomado. Por eso el test
de "feasibility-feedback real" (`TestFeasibilityFeedbackRestriction`) ejercita
`restricted_repair_step` directamente sobre una asignación construida a
mano, en vez de esperar que la etapa 2 dispare de punta a punta — la única
forma honesta de observar esa rama del algoritmo (ver reporte de la sesión
G8 para el argumento completo).
"""

from __future__ import annotations

import pytest

from blite_cap_quantum import repair as rep

# Triángulo completo (G6 de knowledge/quantum/02 §1.2): toda partición no
# trivial de 3 nodos con grafo completo queda conexa por construcción — caso
# base sin violaciones, útil para probar el no-op.
_G6 = [[4.0, -1.0, -3.0], [-1.0, 3.0, -2.0], [-3.0, -2.0, 5.0]]

# Grafo sin arista (0,3): [0,1] y [2] aislados en su propia clase, sin
# vecinos — hallado por búsqueda dirigida (matrix arbitraria, no derivada de
# un grafo físico) para que la ÚNICA arista existente (0-3, peso -3) quede
# SIEMPRE dentro de la misma clase o partida sin ganancia: ningún flip
# mejora ni la conectividad ni el objetivo simultáneamente — M.3 se atasca
# honestamente en la primera pasada (0 flips).
_STUCK_MATRIX = [
    [0.0, 0.0, 0.0, -3.0],
    [0.0, 0.0, 0.0, 0.0],
    [0.0, 0.0, 0.0, 0.0],
    [-3.0, 0.0, 0.0, 0.0],
]
_STUCK_START = [0, 0, 1, 0]

# Hallado por búsqueda aleatoria dirigida (ver reporte de sesión): la etapa 1
# (ascenso sin restricción) por sí sola camina desde una asignación con 1
# violación de conectividad hasta un óptimo local que además resulta conexo
# — 3 flips reales, energía observada 0.0 → 14.0.
_SUCCESS_MATRIX = [
    [0.0, 1.0, -4.0, 0.0, 2.0, -5.0],
    [1.0, 0.0, -3.0, 2.0, 1.0, 5.0],
    [-4.0, -3.0, 0.0, -1.0, 0.0, 0.0],
    [0.0, 2.0, -1.0, 0.0, -2.0, 0.0],
    [2.0, 1.0, 0.0, -2.0, 0.0, -3.0],
    [-5.0, 5.0, 0.0, 0.0, -3.0, 0.0],
]
_SUCCESS_START = [0, 1, 1, 0, 1, 1]

# Hallado por búsqueda: entre los 5 flips posibles, el de MAYOR ganancia
# (índice 2, +10) NO ayuda a la conectividad (Δviolaciones=0); el índice 4
# SÍ ayuda (Δviolaciones=-1) con ganancia menor (+4) — el candidato
# tentador-pero-inútil-para-conectividad debe quedar excluido.
_FEEDBACK_MATRIX = [
    [0.0, 0.0, 0.0, 0.0, -2.0],
    [0.0, 0.0, 1.0, -2.0, -2.0],
    [0.0, 1.0, 0.0, -6.0, 4.0],
    [0.0, -2.0, -6.0, 0.0, 0.0],
    [-2.0, -2.0, 4.0, 0.0, 0.0],
]
_FEEDBACK_START = [0, 1, 0, 0, 1]


class TestConnectivityViolations:
    """DFS portado de `execution.py:_is_connected` (nota 05, decisiones del
    reporte) — generalizado a CONTAR componentes, no solo responder sí/no."""

    def test_complete_graph_partition_is_always_connected(self) -> None:
        assert rep.connectivity_violations(_G6, [0, 1, 0]) == 0
        assert rep.connectivity_violations(_G6, [1, 1, 0]) == 0

    def test_isolated_pair_counts_as_one_violation_per_extra_component(self) -> None:
        # class0={0,1,3}: 0-3 tiene arista, 1 no tiene ninguna → 2
        # componentes → 1 violación. class1={2}: trivial → 0.
        assert rep.connectivity_violations(_STUCK_MATRIX, _STUCK_START) == 1

    def test_singleton_classes_are_trivially_connected(self) -> None:
        assert rep.connectivity_violations(_G6, [0, 0, 0]) == 0


class TestRepairConnectivitySuccess:
    def test_infeasible_assignment_gets_repaired_to_connected(self) -> None:
        # Arrange — precondición: el punto de partida SÍ viola conectividad
        assert rep.connectivity_violations(_SUCCESS_MATRIX, _SUCCESS_START) == 1

        # Act
        result = rep.repair_connectivity(_SUCCESS_MATRIX, _SUCCESS_START)

        # Assert — el resultado queda conexo, con flips reales aplicados
        assert rep.connectivity_violations(_SUCCESS_MATRIX, result["assignment"]) == 0
        assert result["repair"]["flips"] > 0
        assert result["repair"]["method"] == rep.M3_METHOD
        # connectivity_violations reportado es el del bitstring CRUDO
        # (freeze §11), no el del reparado
        assert result["connectivity_violations"] == 1

    def test_repaired_energy_matches_the_repaired_assignment(self) -> None:
        result = rep.repair_connectivity(_SUCCESS_MATRIX, _SUCCESS_START)

        assert result["repair"]["post_value"] == rep.energy(
            _SUCCESS_MATRIX, result["assignment"]
        )
        assert result["repair"]["pre_value"] == rep.energy(
            _SUCCESS_MATRIX, _SUCCESS_START
        )


class TestFeasibilityFeedbackRestriction:
    """Ejercita `restricted_repair_step` directamente — ver el docstring
    del módulo para por qué el pipeline público no puede observar esta rama
    de punta a punta con una QUBO de Max-Cut puro."""

    def test_tempting_flip_that_does_not_help_connectivity_is_excluded(self) -> None:
        # Arrange — confirmar la geometría del fixture antes de afirmar nada
        gains = {j: rep.gain(_FEEDBACK_MATRIX, _FEEDBACK_START, j) for j in range(5)}
        deltas = {
            j: rep.violation_delta(_FEEDBACK_MATRIX, _FEEDBACK_START, j)
            for j in range(5)
        }
        assert gains[2] == max(gains.values())  # el flip 2 es EL más tentador
        assert deltas[2] == 0  # ...pero no ayuda a la conectividad
        assert deltas[4] < 0  # el flip 4 sí ayuda (candidato legítimo)

        # Act
        repaired, accepted = rep.restricted_repair_step(
            _FEEDBACK_MATRIX, _FEEDBACK_START
        )

        # Assert — se acepta un flip, pero NUNCA el más tentador si no
        # ayuda a la conectividad
        assert accepted is True
        assert repaired[2] == _FEEDBACK_START[2]  # flip 2 NO se aplicó
        assert repaired[4] != _FEEDBACK_START[4]  # flip 4 sí se aplicó
        assert rep.connectivity_violations(_FEEDBACK_MATRIX, repaired) == 0

    def test_candidates_are_restricted_to_the_set_that_improves_connectivity(
        self,
    ) -> None:
        """J(z) del paper: ningún candidato con Δviolaciones >= 0 debe
        aparecer nunca como el flip elegido, sin importar su ganancia."""
        for _ in range(5):  # determinismo: mismo resultado en repetidas corridas
            repaired, accepted = rep.restricted_repair_step(
                _FEEDBACK_MATRIX, _FEEDBACK_START
            )
            assert accepted is True
            flipped_indices = [j for j in range(5) if repaired[j] != _FEEDBACK_START[j]]
            assert len(flipped_indices) == 1
            (index,) = flipped_indices
            assert rep.violation_delta(_FEEDBACK_MATRIX, _FEEDBACK_START, index) < 0


class TestHonestFailureReporting:
    """Espejo fail-loud: si no hay flip que ayude, la reparación NUNCA
    fabrica una mejora — se reporta la entrada tal cual."""

    def test_no_improving_flip_available_reports_pre_equals_post(self) -> None:
        # Arrange
        assert rep.connectivity_violations(_STUCK_MATRIX, _STUCK_START) == 1

        # Act
        result = rep.repair_connectivity(_STUCK_MATRIX, _STUCK_START)

        # Assert — cero flips, ningún valor fabricado, sigue infactible
        assert result["repair"]["flips"] == 0
        assert result["repair"]["pre_value"] == result["repair"]["post_value"]
        assert result["assignment"] == _STUCK_START
        assert rep.connectivity_violations(_STUCK_MATRIX, result["assignment"]) == 1


class TestDeterminism:
    def test_same_input_yields_identical_result(self) -> None:
        first = rep.repair_connectivity(_SUCCESS_MATRIX, _SUCCESS_START)
        second = rep.repair_connectivity(_SUCCESS_MATRIX, _SUCCESS_START)

        assert first == second

    def test_determinism_holds_on_the_stuck_case_too(self) -> None:
        first = rep.repair_connectivity(_STUCK_MATRIX, _STUCK_START)
        second = rep.repair_connectivity(_STUCK_MATRIX, _STUCK_START)

        assert first == second


class TestAlreadyFeasibleInputIsANoOp:
    def test_a_feasible_local_optimum_gets_zero_flips(self) -> None:
        # [1, 1, 0] es, además de conexo (G6 es completo), un óptimo local
        # de 1-flip para G6 (verificado: los 3 flips posibles degradan el
        # objetivo) — la única forma honesta de obtener flips=0, ya que la
        # etapa 1 corre SIEMPRE, sin mirar factibilidad primero (§1.5 del
        # paper: la conectividad se revisa recién DESPUÉS de la etapa 1).
        start = [1, 1, 0]
        assert rep.connectivity_violations(_G6, start) == 0

        result = rep.repair_connectivity(_G6, start)

        assert result["repair"]["flips"] == 0
        assert result["repair"]["pre_value"] == result["repair"]["post_value"]
        assert result["connectivity_violations"] == 0
        assert result["assignment"] == start


class TestInputValidation:
    def test_unsupported_method_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="method"):
            rep.repair_connectivity(_G6, [0, 1, 0], method="M.4")

    def test_non_square_matrix_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="cuadrada"):
            rep.repair_connectivity([[0.0, 1.0], [1.0, 0.0, 2.0]], [0, 1])

    def test_asymmetric_matrix_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="simétrica"):
            rep.repair_connectivity([[0.0, 1.0], [2.0, 0.0]], [0, 1])

    def test_assignment_length_mismatch_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="assignment"):
            rep.repair_connectivity(_G6, [0, 1])

    def test_non_binary_assignment_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="assignment"):
            rep.repair_connectivity(_G6, [0, 1, 2])


class TestGenericitySelfCheck:
    """ADR-029: el gate del repo lee entry points INSTALADOS y no verá el
    campo `repair` del manifest hasta un reinstall — esta aserción local es
    la que cubre en vivo (ver tests/invariants/test_capability_genericity.py),
    mismo patrón que `test_zne.py:432`."""

    def test_manifest_has_no_scenario_vocabulary(self) -> None:
        import dataclasses
        import json
        from pathlib import Path

        from blite_cap_quantum import QaoaSolver

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

        manifest = QaoaSolver().manifest
        text = json.dumps(dataclasses.asdict(manifest), default=str).lower()

        violations = [term for term in denylist if term in text]
        assert not violations, (
            f"manifest contiene vocabulario de escenario: {violations}"
        )
