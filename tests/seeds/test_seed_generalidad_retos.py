"""Seed de la costura de generalidad (S-C, decisión #126).

Contrato: docs/specs/generalidad-retos.md. Cada test fija una pieza que
G1/G2/G3 (Fase 1) implementan; el xfail se retira pieza por pieza.

Directiva pyright per-file: los módulos/campos objetivo no existen por diseño
hasta Fase 1; la directiva se retira junto con el xfail.
"""

# pyright: reportMissingImports=false, reportUnknownVariableType=false
# pyright: reportUnknownMemberType=false, reportAttributeAccessIssue=false
# pyright: reportArgumentType=false, reportCallIssue=false
# pyright: reportUnknownArgumentType=false

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.seed,
    pytest.mark.xfail(
        strict=False,
        reason=(
            "Fase 1 G1/G2/G3: C-14, los verificadores nuevos y el registro de "
            "dispatch no existen todavía — docs/specs/generalidad-retos.md (#126)"
        ),
    ),
]


def test_differential_acepta_exact_diagonalization_con_tolerancia() -> None:
    """§Contrato-2 (C-14): status nuevo aditivo + relative_tolerance ≤5%."""
    from blite.verification.evidence import Differential

    differential = Differential(
        status="EXACT_DIAGONALIZATION",
        objective=0.482,
        reference_objective=0.471,
        relative_tolerance=0.05,
    )
    assert differential.relative_tolerance == 0.05


def test_relative_tolerance_none_para_cpsat() -> None:
    """§Contrato-2: CP-SAT sigue exacto — el campo nuevo default None."""
    from blite.verification.evidence import Differential

    differential = Differential(
        status="OPTIMAL", objective=57070.0, reference_objective=57070.0
    )
    assert differential.relative_tolerance is None


def test_modulos_de_verificadores_nuevos() -> None:
    """§Contrato-3: los tres adapters viven en sus homes declarados."""
    from blite.verification import exact_diagonalization, ground_truth, property_rule

    assert hasattr(exact_diagonalization, "ExactDiagonalizationVerifier")
    assert hasattr(ground_truth, "GroundTruthVerifier")
    assert hasattr(property_rule, "PropertyRuleVerifier")


def test_registro_de_dispatch_por_clase() -> None:
    """§Contrato-6 (G3): el registro declarativo reemplaza el Reto-1-only."""
    from chimera_api.instance_verifiers import CLAIM_TYPE_VERIFIERS

    assert {"simulation_result", "statistical"} <= set(CLAIM_TYPE_VERIFIERS)
