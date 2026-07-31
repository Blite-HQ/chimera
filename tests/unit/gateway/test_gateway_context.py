"""GatewayContext aditivo — supersede C-5/#106 (freeze §8, misma ceremonia).

El ctx congelado 2026-07-22 gana `run_id`/`step_id`/`domain_id` OPCIONALES:
las construcciones existentes siguen validando (aditivo puro) y el cruce por
step puede portar su procedencia. La granularidad quedó registrada como
interpretación de §13: UN cruce por invocación de capability (resolve es
parte de mediation).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from blite.gateway.context import GatewayContext
from blite.identity.identity import Identity

_IDENTITY = Identity(
    id="user:test",
    kind="human",
    domain_id="domain-a",
    permissions=frozenset({"capability:invoke"}),
)


def _ctx(**overrides: object) -> GatewayContext:
    base: dict[str, object] = {
        "identity": _IDENTITY,
        "capability_id": "cap.echo",
        "inputs": {"x": 1},
    }
    base.update(overrides)
    return GatewayContext.model_validate(base)


def test_construccion_previa_a_c5_sigue_validando() -> None:
    """Aditivo puro: el ctx sin los campos nuevos valida — nada existente rompe."""
    ctx = _ctx()
    assert ctx.run_id is None
    assert ctx.step_id is None
    assert ctx.domain_id is None


def test_el_cruce_porta_run_step_y_domain() -> None:
    """C-5: el cruce por invocación porta la procedencia del step."""
    ctx = _ctx(run_id="run-1", step_id="step-2", domain_id="domain-a")
    assert ctx.run_id == "run-1"
    assert ctx.step_id == "step-2"
    assert ctx.domain_id == "domain-a"


def test_el_ctx_sigue_congelado_y_cerrado() -> None:
    """La ceremonia no relaja el freeze: frozen=True y extra=forbid intactos."""
    ctx = _ctx(run_id="run-1")
    with pytest.raises(ValidationError):
        ctx.run_id = "run-2"
    with pytest.raises(ValidationError):
        _ctx(invented_field="x")
