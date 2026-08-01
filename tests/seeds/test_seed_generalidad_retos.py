"""Seed de la costura de generalidad (S-C, decisión #126).

Contrato: docs/specs/generalidad-retos.md. Cada test fija una pieza que
G1/G2/G3 (Fase 1) implementan; el xfail se retira **pieza por pieza** (no a
nivel de módulo) según el contrato §Tests semilla — las piezas de C-14 ya
las cubre G1 (`Differential.status`/`relative_tolerance`, extendido en
`engine/src/blite/verification/evidence.py`) y `CLAIM_TYPE_VERIFIERS` (G3,
`api/src/chimera_api/instance_verifiers.py`) quedan verdes sin xfail;
`property_rule` (G2, `PropertyRuleVerifier`) sigue pendiente.

Directiva pyright per-file: los módulos/campos objetivo de las piezas
pendientes no existen por diseño hasta Fase 1; la directiva se retira junto
con su xfail.
"""

# pyright: reportMissingImports=false, reportUnknownVariableType=false
# pyright: reportUnknownMemberType=false, reportAttributeAccessIssue=false
# pyright: reportArgumentType=false, reportCallIssue=false
# pyright: reportUnknownArgumentType=false

from __future__ import annotations

import pytest

pytestmark = pytest.mark.seed

_XFAIL_REASON_G2_G3 = (
    "Fase 1 G2/G3: los verificadores nuevos y el registro de dispatch no "
    "existen todavía — docs/specs/generalidad-retos.md (#126)"
)


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


@pytest.mark.xfail(strict=False, reason=_XFAIL_REASON_G2_G3)
def test_modulos_de_verificadores_nuevos() -> None:
    """§Contrato-3: los tres adapters viven en sus homes declarados."""
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
