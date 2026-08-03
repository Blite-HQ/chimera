"""Differential — C-14 (docs/specs/generalidad-retos.md §Contrato-2).

freeze §3 (resolución C-14, #106, forma #126): `EXACT_DIAGONALIZATION` es un
status aditivo a la unión CpSat — NO es de proceso, mapea a verdict por
comparación (como `OPTIMAL`). `relative_tolerance` es el criterio de
aceptación oficial de C3 (≤5% ⇒ 0.05); `None` para CP-SAT, que sigue exacto
(`abs_tol: 0`). La letra fail-closed del contrato: un status por tolerancia
sin su criterio es inauditable, y CP-SAT con tolerancia rompe la doctrina de
exactitud — ambos casos deben levantar, no pasar en silencio.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from blite.verification.evidence import Differential, FormalExactPredicate


class TestExactDiagonalizationStatus:
    def test_acepta_exact_diagonalization_con_tolerancia(self) -> None:
        differential = Differential(
            status="EXACT_DIAGONALIZATION",
            objective=0.482,
            reference_objective=0.471,
            relative_tolerance=0.05,
        )

        assert differential.status == "EXACT_DIAGONALIZATION"
        assert differential.relative_tolerance == 0.05

    def test_round_trip_por_model_dump_y_validate(self) -> None:
        differential = Differential(
            status="EXACT_DIAGONALIZATION",
            objective=0.482,
            reference_objective=0.471,
            relative_tolerance=0.05,
        )

        dumped = differential.model_dump(mode="json")
        rebuilt = Differential.model_validate(dumped)

        assert rebuilt == differential


class TestRegresionCpSat:
    """El status CP-SAT (unión original) no cambia de comportamiento."""

    def test_optimal_sigue_construyendo_con_tolerancia_none(self) -> None:
        differential = Differential(
            status="OPTIMAL", objective=57070.0, reference_objective=57070.0
        )

        assert differential.relative_tolerance is None

    def test_infeasible_sigue_levantando(self) -> None:
        with pytest.raises(ValidationError):
            Differential(status="INFEASIBLE", objective=0.0, reference_objective=0.0)

    def test_model_invalid_sigue_levantando(self) -> None:
        with pytest.raises(ValidationError):
            Differential(status="MODEL_INVALID", objective=0.0, reference_objective=0.0)


class TestToleranciaFailClosed:
    """§Contrato-2: la letra exacta — None para CP-SAT, obligatoria para ED."""

    def test_exact_diagonalization_sin_tolerancia_levanta(self) -> None:
        with pytest.raises(ValidationError):
            Differential(
                status="EXACT_DIAGONALIZATION",
                objective=0.482,
                reference_objective=0.471,
            )

    def test_cpsat_con_tolerancia_levanta(self) -> None:
        with pytest.raises(ValidationError):
            Differential(
                status="OPTIMAL",
                objective=57070.0,
                reference_objective=57070.0,
                relative_tolerance=0.05,
            )

    @pytest.mark.parametrize("tolerance", [0.0, -0.01, 1.01])
    def test_tolerancia_fuera_de_rango_levanta(self, tolerance: float) -> None:
        with pytest.raises(ValidationError):
            Differential(
                status="EXACT_DIAGONALIZATION",
                objective=0.482,
                reference_objective=0.471,
                relative_tolerance=tolerance,
            )

    def test_tolerancia_limite_superior_uno_es_valida(self) -> None:
        differential = Differential(
            status="EXACT_DIAGONALIZATION",
            objective=0.482,
            reference_objective=0.471,
            relative_tolerance=1.0,
        )

        assert differential.relative_tolerance == 1.0


class TestFormalExactPredicateRoundTrip:
    """El predicate que porta el Differential también round-tripea (§4-iii)."""

    def test_predicate_con_exact_diagonalization_round_trip_json(self) -> None:
        predicate = FormalExactPredicate(
            differential=Differential(
                status="EXACT_DIAGONALIZATION",
                objective=0.482,
                reference_objective=0.471,
                relative_tolerance=0.05,
            )
        )

        dumped = predicate.model_dump(mode="json")
        rebuilt = FormalExactPredicate.model_validate(dumped)

        assert rebuilt == predicate
