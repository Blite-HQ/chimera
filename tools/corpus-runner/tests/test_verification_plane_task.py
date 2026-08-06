"""La tarea que mide el plano de verificación, con patas falsas y con las reales.

Las falsas prueban la TRADUCCIÓN veredicto→`C/I/P/N` (la lógica que decide el
KPI); la real prueba que el cableado al plano existe y que la frontera se
respeta.
"""

from __future__ import annotations

from typing import Any

import pytest

from chimera_eval.dataset import Sample
from chimera_eval.score import JSONValue
from chimera_eval.tasks.verification_plane import (
    expected_verdict_scorer,
    perturb_series,
    sample_from_claim,
    verification_solver,
)


def _sample(expected: str = "pass") -> Sample:
    return sample_from_claim(
        sample_id="s",
        claim_type="simulation_result",
        instance_id="chain-n6-h10",
        payload={},
        expected_verdict=expected,
    )


def _legs(*specs: tuple[str, str, str | None]) -> JSONValue:
    return {
        "legs": [
            {
                "verifier_id": vid,
                "verdict": verdict,
                "independence_group": "g",
                "inconclusive_reason": reason,
            }
            for vid, verdict, reason in specs
        ]
    }


class TestTraduccionAVocabularioCIPN:
    def test_todas_las_patas_aciertan_puntua_correcto(self) -> None:
        score = expected_verdict_scorer(
            _sample("pass"), _legs(("a", "pass", None), ("b", "pass", None))
        )
        assert score.value == "C"

    def test_una_abstencion_manda_aunque_la_otra_pata_acierte(self) -> None:
        """La abstención MANDA sobre el acierto de la otra pata.

        Si una pata se abstiene, la corrida perdió una de sus dos patas
        independientes — el claim queda sostenido por una sola. Puntuarlo como
        `C` por «la otra acertó» escondería exactamente lo que el KPI mide.
        """
        score = expected_verdict_scorer(
            _sample("pass"),
            _legs(("a", "inconclusive", "budget_exhausted"), ("b", "pass", None)),
        )
        assert score.value == "N"
        assert "budget_exhausted" in score.explanation

    def test_veredicto_decisivo_equivocado_puntua_incorrecto(self) -> None:
        score = expected_verdict_scorer(
            _sample("pass"), _legs(("a", "fail", None), ("b", "fail", None))
        )
        assert score.value == "I"

    def test_patas_en_desacuerdo_puntua_parcial(self) -> None:
        score = expected_verdict_scorer(
            _sample("pass"), _legs(("a", "pass", None), ("b", "fail", None))
        )
        assert score.value == "P"

    def test_el_answer_cita_cada_pata_por_id(self) -> None:
        score = expected_verdict_scorer(
            _sample("pass"), _legs(("a", "pass", None), ("b", "fail", None))
        )
        assert score.answer == "a=pass,b=fail"


class TestPerturbacion:
    def test_es_multiplicativa_no_aditiva(self) -> None:
        """Un offset aditivo no mueve el error L∞-RELATIVO cerca de cero.

        Con perturbación aditiva la muestra «mentirosa» pasaría como verdad y
        la mitad del corpus no mediría nada.
        """
        assert perturb_series([0.0, 2.0], 1.5) == [0.0, 3.0]

    def test_el_factor_escala_todos_los_valores(self) -> None:
        assert perturb_series([1.0, -2.0, 0.5], 2.0) == [2.0, -4.0, 1.0]


class TestCableadoReal:
    """Contra el plano de verificación de verdad — sin mocks."""

    def test_una_instancia_desconocida_es_error_de_proceso_no_veredicto(self) -> None:
        sample = sample_from_claim(
            sample_id="x",
            claim_type="simulation_result",
            instance_id="instancia-que-no-existe",
            payload={},
            expected_verdict="pass",
        )
        with pytest.raises(LookupError, match="ningún verificador ampara"):
            verification_solver(sample)

    def test_un_claim_type_sin_registro_tambien(self) -> None:
        sample = sample_from_claim(
            sample_id="x",
            claim_type="tipo-inventado",
            instance_id="chain-n6-h10",
            payload={},
            expected_verdict="pass",
        )
        with pytest.raises(LookupError, match="claim_type sin registro"):
            verification_solver(sample)

    def test_evaluar_no_escribe_eventos(self) -> None:
        """La frontera del tercer plano (trust/17 §4.1).

        El runner produce `Attestation` para MEDIR. Si alguna vez terminaran en
        un stream, la evaluación agregada estaría contaminando el registro de
        runs individuales — y un KPI se habría convertido en evidencia.
        """
        import chimera_eval.tasks.verification_plane as module

        source = module.__file__
        assert source is not None
        text = open(source, encoding="utf-8").read()  # noqa: SIM115, PTH123

        for forbidden in ("append_event", "EventStore", "create_event_store", "emit"):
            assert forbidden not in text, (
                f"la tarea de evaluación menciona {forbidden!r}: el tercer plano "
                "mide, no escribe"
            )

    def test_el_contexto_de_evaluacion_es_constante_y_no_es_un_run(self) -> None:
        from chimera_eval.tasks.verification_plane import EVAL_CONTEXT

        assert EVAL_CONTEXT["run_id"].startswith("eval:")
        assert EVAL_CONTEXT["actor_id"].startswith("service:")


class TestFormaDeLaMuestra:
    def test_el_payload_se_copia_no_se_referencia(self) -> None:
        """Mutar el corpus después de construir la muestra no debe moverla.

        Un dataset cuya identidad (digest) cambie porque alguien tocó el dict
        de origen sería un corpus que no se puede citar.
        """
        payload: dict[str, Any] = {"series": [1.0]}
        sample = sample_from_claim(
            sample_id="s",
            claim_type="t",
            instance_id="i",
            payload=payload,
            expected_verdict="pass",
        )
        payload["series"].append(2.0)

        assert sample.input["payload"]["series"] == [1.0]  # type: ignore[index]
