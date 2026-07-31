"""Seed de la supersede ADITIVA de GatewayContext (C-5/#106 — S-B).

Contrato: freeze §8, marca [MEJORADO C-5/#106]: el contexto gana
`run_id`/`step_id`/`domain_id` OPCIONALES (el cruce por invocación de
capability queda correlacionable con el run/step que lo causó). La
construcción actual (sin los campos) sigue válida — aditivo puro.
Implementación = ítem C2/M2 (Fase 1).

Directiva pyright per-file: los campos objetivo no existen por diseño hasta
Fase 1; la directiva se retira junto con el xfail.
"""

# pyright: reportCallIssue=false, reportAttributeAccessIssue=false
# pyright: reportUnknownMemberType=false

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.seed,
    pytest.mark.xfail(
        strict=False,
        reason=(
            "Fase 1 C2/M2: GatewayContext aún no porta run_id/step_id/domain_id "
            "— freeze §8 marca [MEJORADO C-5/#106]"
        ),
    ),
]


def _identity():  # noqa: ANN202 — tipo del engine, import diferido
    from blite.identity.identity import Identity

    return Identity(
        id="user:dylan",
        kind="human",
        domain_id="domain-default",
        permissions=frozenset({"capability:invoke"}),
    )


def test_campos_nuevos_opcionales_con_default_none() -> None:
    """Compat total: construir SIN los campos nuevos sigue siendo válido."""
    from blite.gateway.context import GatewayContext

    ctx = GatewayContext(
        identity=_identity(),
        capability_id="blite.solvers.qubo",
        inputs={},
    )
    assert ctx.run_id is None
    assert ctx.step_id is None
    assert ctx.domain_id is None


def test_cruce_correlacionado_porta_run_y_step() -> None:
    """Un cruce por invocación de capability viaja con su run/step (§13)."""
    from blite.gateway.context import GatewayContext

    ctx = GatewayContext(
        identity=_identity(),
        capability_id="blite.solvers.qubo",
        inputs={},
        run_id="run-1",
        step_id="step-1",
        domain_id="domain-default",
    )
    assert (ctx.run_id, ctx.step_id, ctx.domain_id) == (
        "run-1",
        "step-1",
        "domain-default",
    )
