"""KPI de over-refusal: por qué `N` no puede vivir dentro de la exactitud.

`C/I/P/N` es la convención portada de Inspect (trust/17 §1.2 — «portar»,
cero dependencia). La razón de portarla es que `N` (NOANSWER / abstención) es
un resultado DISTINTO de `I` (INCORRECT), y esa distinción se pierde en
cualquier métrica escalar de acierto.
"""

from __future__ import annotations

import pytest

from chimera_eval.score import (
    NUMERIC_VALUE,
    Score,
    ScoreValue,
    accuracy,
    decisive_error_rate,
    over_refusal_rate,
)


def _scores(*values: ScoreValue) -> tuple[Score, ...]:
    return tuple(Score(value=v, answer="", explanation="") for v in values)


class TestVocabularioCIPN:
    def test_los_cuatro_valores_tienen_peso_numerico(self) -> None:
        assert NUMERIC_VALUE == {"C": 1.0, "P": 0.5, "I": 0.0, "N": 0.0}

    def test_un_valor_fuera_del_vocabulario_no_se_construye(self) -> None:
        with pytest.raises(ValueError, match="C/I/P/N"):
            Score(value="WRONG", answer="", explanation="")  # type: ignore[arg-type]


class TestPorQueOverRefusalEsKPIAparte:
    def test_incorrecto_y_abstencion_valen_igual_en_exactitud(self) -> None:
        """La observación que justifica el KPI: `I` y `N` pesan 0.0 los dos."""
        assert accuracy(_scores("C", "I")) == accuracy(_scores("C", "N")) == 0.5

    def test_pero_over_refusal_los_separa(self) -> None:
        """Un sistema que se abstiene y uno que se equivoca NO son el mismo sistema.

        Es la diferencia entre «verificación demasiado estricta» (cuesta
        utilidad, trust/05 §1.3) y «verificación equivocada» (cuesta confianza).
        """
        assert over_refusal_rate(_scores("C", "N")) == 0.5
        assert over_refusal_rate(_scores("C", "I")) == 0.0
        assert decisive_error_rate(_scores("C", "I")) == 0.5
        assert decisive_error_rate(_scores("C", "N")) == 0.0

    def test_sin_muestras_las_tasas_son_cero_no_division_por_cero(self) -> None:
        assert over_refusal_rate(()) == 0.0
        assert accuracy(()) == 0.0
        assert decisive_error_rate(()) == 0.0

    def test_parcial_cuenta_medio_y_no_es_ni_abstencion_ni_error(self) -> None:
        scores = _scores("P", "P")
        assert accuracy(scores) == 0.5
        assert over_refusal_rate(scores) == 0.0
        assert decisive_error_rate(scores) == 0.0
