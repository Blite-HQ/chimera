"""El runner: determinismo del log y la frontera error-de-proceso ≠ veredicto.

Dos propiedades que la forma de Inspect NO da gratis (trust/17 §1.1: su
`EvalSpec` captura `revision` y `packages` pero «sin un solo campo de digest de
config»), y una doctrina que es de esta casa: un fallo del PROCESO no es un
resultado del sujeto evaluado.
"""

from __future__ import annotations

import json

import pytest

from chimera_eval.dataset import Dataset, Sample
from chimera_eval.runner import run_task
from chimera_eval.score import JSONValue, Score
from chimera_eval.task import Task


def _dataset() -> Dataset:
    return Dataset(
        name="fixture",
        samples=(
            Sample(id="s1", input={"n": 1}, target={"ok": True}),
            Sample(id="s2", input={"n": 2}, target={"ok": False}),
        ),
    )


def _echo_solver(sample: Sample) -> JSONValue:
    return {"echo": sample.input}


def _fixture_scorer(sample: Sample, output: JSONValue) -> Score:
    return Score(
        value="C" if sample.id == "s1" else "N",
        answer=json.dumps(output, sort_keys=True),
        explanation="fixture",
    )


def _task(**overrides: object) -> Task:
    base: dict[str, object] = {
        "name": "fixture-task",
        "version": "1",
        "dataset": _dataset(),
        "solver": _echo_solver,
        "solver_id": "echo-v1",
        "scorer": _fixture_scorer,
        "scorer_id": "fixture-scorer-v1",
    }
    base.update(overrides)
    return Task(**base)  # type: ignore[arg-type]


class TestDeterminismoDelLog:
    def test_dos_corridas_del_mismo_task_dan_logs_byte_identicos(self) -> None:
        """La propiedad que hace comparable una ablación.

        Si el log llevara reloj, dos corridas idénticas producirían bytes
        distintos y «comparar dos variantes» se volvería lectura a ojo. El
        tiempo NO entra al log: la identidad de una evaluación es su
        `config_digest`, no cuándo se corrió.
        """
        assert run_task(_task()).to_json() == run_task(_task()).to_json()

    def test_cambiar_un_parametro_cambia_el_config_digest(self) -> None:
        base = run_task(_task()).config_digest
        assert run_task(_task(params={"ablation": "off"})).config_digest != base

    def test_cambiar_el_corpus_cambia_el_config_digest(self) -> None:
        otro = Dataset(name="fixture", samples=(Sample(id="s1", input={}, target={}),))
        assert (
            run_task(_task(dataset=otro)).config_digest
            != run_task(_task()).config_digest
        )

    def test_el_digest_del_dataset_no_depende_del_orden_de_las_llaves(self) -> None:
        a = Dataset(
            name="d", samples=(Sample(id="x", input={"a": 1, "b": 2}, target={}),)
        )
        b = Dataset(
            name="d", samples=(Sample(id="x", input={"b": 2, "a": 1}, target={}),)
        )
        assert a.digest() == b.digest()

    def test_el_orden_de_las_muestras_si_cuenta(self) -> None:
        """Un corpus reordenado es otro corpus: el orden es parte de la identidad."""
        s1 = Sample(id="1", input={}, target={})
        s2 = Sample(id="2", input={}, target={})
        assert (
            Dataset(name="d", samples=(s1, s2)).digest()
            != Dataset(name="d", samples=(s2, s1)).digest()
        )


class TestErrorDeProcesoNoEsVeredicto:
    """Misma doctrina que `VerificationProcessError` en el engine.

    Si el solver o el scorer explotan, el sujeto evaluado no «falló»: la
    medición no se pudo hacer. Contarlo como `I` inventaría un error del
    sistema, y contarlo como `N` inventaría una abstención que nadie tomó —
    las dos mentiras corrompen justo el KPI que este runner existe para medir.
    """

    def test_un_solver_que_explota_no_produce_score(self) -> None:
        def boom(sample: Sample) -> JSONValue:
            raise RuntimeError("el adapter se cayó")

        log = run_task(_task(solver=boom))

        assert [r.error for r in log.results] == [
            "RuntimeError: el adapter se cayó",
            "RuntimeError: el adapter se cayó",
        ]
        assert all(r.score is None for r in log.results)

    def test_los_errores_de_proceso_salen_de_las_tasas_y_se_reportan_aparte(
        self,
    ) -> None:
        def boom_en_s2(sample: Sample) -> JSONValue:
            if sample.id == "s2":
                raise RuntimeError("caída parcial")
            return {}

        log = run_task(_task(solver=boom_en_s2))

        assert log.metrics["process_errors"] == 1.0
        assert log.metrics["scored"] == 1.0
        # s1 puntuó C; la tasa se calcula sobre lo MEDIDO, no sobre el corpus.
        assert log.metrics["accuracy"] == 1.0
        assert log.metrics["over_refusal_rate"] == 0.0

    def test_un_corpus_entero_en_error_no_reporta_exactitud_perfecta_ni_cero(
        self,
    ) -> None:
        """El caso que un `try/except` descuidado convierte en mentira."""

        def boom(sample: Sample) -> JSONValue:
            raise RuntimeError("todo mal")

        log = run_task(_task(solver=boom))

        assert log.metrics["scored"] == 0.0
        assert log.metrics["process_errors"] == 2.0
        assert log.metrics["accuracy"] == 0.0
        assert log.metrics["over_refusal_rate"] == 0.0


class TestFormaDelLog:
    def test_el_log_declara_su_procedencia_completa(self) -> None:
        log = run_task(_task())
        payload = json.loads(log.to_json())

        for field in (
            "task",
            "task_version",
            "dataset_name",
            "dataset_digest",
            "solver_id",
            "scorer_id",
            "config_digest",
            "params",
            "packages",
            "results",
            "metrics",
        ):
            assert field in payload, f"el log no declara `{field}`"

    def test_cada_resultado_cita_su_muestra(self) -> None:
        log = run_task(_task())
        assert [r.sample_id for r in log.results] == ["s1", "s2"]

    def test_el_task_exige_version_no_vacia(self) -> None:
        """Sin versión, dos logs del «mismo» task no son comparables."""
        with pytest.raises(ValueError, match="version"):
            _task(version="")
