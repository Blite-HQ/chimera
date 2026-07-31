"""SEED · ciencia (Sebas) — el vector de la falla sembrada como test (EC-2).

Convergencia §10-4: bus 1 de ieee14-flujo, r = 0.5712, corte 32 597 / óptimo
57 070; prohibidos [7] (flujo) y [0, 1, 11] (uniforme). Dos fuentes
independientes eligieron el mismo bus — este seed lo fija como regresión.
VERDE (dominio capabilities 2026-07-23): `capabilities_sim_api` expone el
recompute; xfail volteado a aserción real (docs/specs/README.md).
"""

from __future__ import annotations

import pytest

from capabilities_sim_api import recompute_seeded_failure

pytestmark = [pytest.mark.seed]


def test_bus_1_flip_reproduces_the_seeded_failure_numbers() -> None:
    # Arrange / Act — la API concreta la fija Sebas; este seed fija los NÚMEROS
    result = recompute_seeded_failure(instance="ieee14-flujo", bus=1)

    # Assert — los valores validados por ambos tracks (convergencia EC-2)
    assert result.cut_value == 32_597
    assert result.optimum == 57_070
    assert round(result.r, 4) == 0.5712
    assert result.forbidden_flow == [7]
    assert result.forbidden_uniform == [0, 1, 11]
