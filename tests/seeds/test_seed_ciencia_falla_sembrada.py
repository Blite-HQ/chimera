"""SEED · ciencia (Sebas) — el vector de la falla sembrada como test (EC-2).

Convergencia §10-4: bus 1 de ieee14-flujo, r = 0.5712, corte 32 597 / óptimo
57 070; prohibidos [7] (flujo) y [0, 1, 11] (uniforme). Dos fuentes
independientes eligieron el mismo bus — este seed lo fija como regresión.
Verde cuando la capability exponga el recomputo del flip.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.seed,
    pytest.mark.xfail(
        strict=False,
        reason="SEED S-G (Sebas): recompute del flip aún no expuesto por capabilities/sim",
    ),
]


def test_bus_1_flip_reproduces_the_seeded_failure_numbers() -> None:
    # Arrange / Act — la API concreta la fija Sebas; este seed fija los NÚMEROS
    from capabilities_sim_api import (
        recompute_seeded_failure,  # type: ignore[import-not-found]
    )

    result = recompute_seeded_failure(instance="ieee14-flujo", bus=1)

    # Assert — los valores validados por ambos tracks (convergencia EC-2)
    assert result.cut_value == 32_597
    assert result.optimum == 57_070
    assert round(result.r, 4) == 0.5712
    assert result.forbidden_flow == [7]
    assert result.forbidden_uniform == [0, 1, 11]
