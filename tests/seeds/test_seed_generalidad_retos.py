"""Seed de la costura de generalidad (S-C, decisión #126).

Contrato: docs/specs/generalidad-retos.md. Cada test fijó una pieza que
G1/G2/G3 (Fase 1) implementaron; el xfail se retiró **pieza por pieza** (no
a nivel de módulo) según el contrato §Tests semilla. VERDE completo: C-14
(`Differential.status`/`relative_tolerance`, G1), los tres adapters
(`exact_diagonalization`/`ground_truth`/`property_rule`, G1/G2) y
`CLAIM_TYPE_VERIFIERS` (G3, `api/src/chimera_api/instance_verifiers.py`) —
sin xfail pendiente en este archivo.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.seed


def test_differential_acepta_exact_diagonalization_con_tolerancia() -> None:
    """§Contrato-2 (C-14): status nuevo aditivo + relative_tolerance ≤5%.

    VERDE (G1): `docs/specs/generalidad-retos.md` §Contrato-2 implementado en
    `engine/src/blite/verification/evidence.py`.
    """
    from blite.verification.evidence import Differential

    differential = Differential(
        status="EXACT_DIAGONALIZATION",
        objective=0.482,
        reference_objective=0.471,
        relative_tolerance=0.05,
    )
    assert differential.relative_tolerance == 0.05


def test_relative_tolerance_none_para_cpsat() -> None:
    """§Contrato-2: CP-SAT sigue exacto — el campo nuevo default None.

    VERDE (G1): mismo alcance que el test anterior.
    """
    from blite.verification.evidence import Differential

    differential = Differential(
        status="OPTIMAL", objective=57070.0, reference_objective=57070.0
    )
    assert differential.relative_tolerance is None


def test_modulos_de_verificadores_nuevos() -> None:
    """§Contrato-3: los tres adapters viven en sus homes declarados.

    VERDE (G1/G2): `exact_diagonalization`/`ground_truth` implementados en
    G1; `property_rule` implementado en G2 — los tres homes existen.
    """
    from blite.verification import exact_diagonalization, ground_truth, property_rule

    assert hasattr(exact_diagonalization, "ExactDiagonalizationVerifier")
    assert hasattr(ground_truth, "GroundTruthVerifier")
    assert hasattr(property_rule, "PropertyRuleVerifier")


def test_registro_de_dispatch_por_clase() -> None:
    """§Contrato-6 (G3): el registro declarativo reemplaza el Reto-1-only.

    VERDE (G3): `docs/specs/generalidad-retos.md` §Contrato-6 implementado en
    `api/src/chimera_api/instance_verifiers.py::CLAIM_TYPE_VERIFIERS`.
    """
    from chimera_api.instance_verifiers import CLAIM_TYPE_VERIFIERS

    assert {"simulation_result", "statistical"} <= set(CLAIM_TYPE_VERIFIERS)
