"""Registro de adapters de guardrail — ítem C12 (trust/16 §1.3-1.4).

Los detectores llegaban a `GuardrailsStage` como callables anónimos: nada
decía QUÉ corrió ni con qué versión, y dos corridas con detectores distintos
dejaban rastros indistinguibles. El registro los vuelve citables por digest —
la misma regla que ya vale para verificadores, anclas y policies.

Lo que estos tests protegen además: que un detector NO pueda decidir egreso
(Inv-E), y que el score viaje siempre aunque el umbral no marque nada.
"""

from __future__ import annotations

import pytest

from blite.guardrails.registry import (
    ALIGNSCORE_DETECTOR_ID,
    HALLUCINATION_KIND,
    HHEM_DETECTOR_ID,
    Detector,
    DetectorRegistry,
    ScoreDetector,
)
from blite.guardrails.signal import Signal


def _detector(score: float, detector_id: str = HHEM_DETECTOR_ID) -> ScoreDetector:
    return ScoreDetector(
        detector_id=detector_id,
        kind=HALLUCINATION_KIND,
        score_fn=lambda target, content: score,  # noqa: ARG005 — doble determinista
    )


def test_el_score_detector_satisface_el_puerto() -> None:
    assert isinstance(_detector(0.1), Detector)


def test_la_senal_lleva_la_convencion_etapa_mecanismo() -> None:
    señal = _detector(0.9).detect("claim:abc", "contenido")

    assert isinstance(señal, Signal)
    assert señal.kind == "egress.hallucination"
    assert señal.detector == HHEM_DETECTOR_ID


def test_el_score_viaja_aunque_no_marque() -> None:
    """Esconder el número detrás del umbral haría que ajustar el umbral
    pareciera un cambio de detector."""
    señal = _detector(0.2).detect("claim:abc", "contenido")

    assert señal.flagged is False
    assert señal.score == pytest.approx(0.2)
    assert señal.detail["threshold"] == pytest.approx(0.5)


def test_una_senal_jamas_decide_egreso() -> None:
    """Inv-E/D18 como hecho de tipo: `non_decisional` no tiene valor False y
    el registro no tiene forma de expresar «bloquear»."""
    señal = _detector(0.99).detect("claim:abc", "contenido")

    assert señal.non_decisional is True
    assert not hasattr(señal, "block")


def test_el_digest_pinnea_que_detectores_corrieron() -> None:
    uno = DetectorRegistry().with_detector(_detector(0.1))
    dos = uno.with_detector(_detector(0.1, ALIGNSCORE_DETECTOR_ID))

    assert uno.digest != dos.digest
    assert dos.declared == (
        {"detector_id": HHEM_DETECTOR_ID, "kind": HALLUCINATION_KIND},
        {"detector_id": ALIGNSCORE_DETECTOR_ID, "kind": HALLUCINATION_KIND},
    )


def test_el_mismo_digest_para_el_mismo_registro() -> None:
    a = DetectorRegistry().with_detector(_detector(0.1))
    b = DetectorRegistry().with_detector(_detector(0.9))  # mismo id, otro umbral

    assert a.digest == b.digest  # el digest cita QUIÉN corrió, no su umbral


def test_dos_detectores_con_el_mismo_id_no_se_registran() -> None:
    """Dos versiones bajo el mismo id harían el digest ambiguo — y el digest
    existe justo para que «corrió esto» sea una afirmación exacta."""
    registro = DetectorRegistry().with_detector(_detector(0.1))

    with pytest.raises(ValueError, match="ya está registrado"):
        registro.with_detector(_detector(0.2))


def test_un_kind_sin_la_convencion_no_es_representable() -> None:
    malo = ScoreDetector(
        detector_id="x@1",
        kind="sinpunto",
        score_fn=lambda target, content: 0.0,  # noqa: ARG005
    )

    with pytest.raises(ValueError, match="convención"):
        malo.detect("claim:abc", "contenido")
