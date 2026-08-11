"""Corrector AI-QEM aprendido (V9 — freeze §11, bloque `mitigation.*`).

Lo que se prueba, en orden de importancia para la tarea:

1. El corpus de entrenamiento es REAL (Aer, no fabricado) y train/holdout no
   comparten ninguna instancia.
2. Determinismo bit-a-bit: la MISMA semilla da el MISMO `training_digest`, el
   MISMO `model_digest` y el MISMO `mitigated_energy` entre corridas — incluso
   entre corridas que no comparten caché (`_trained.cache_clear()`).
3. `training_digest` nunca es `None` para un método aprendido (a diferencia
   de `zne.mitigation_block`, que lo deja `None` a propósito).
4. El control negativo es el MISMO mecanismo de costo igual que V4 estableció
   (garbage-folding, `apparent_improvement`) — aplicado al modelo entrenado,
   nunca a un modelo aparte ajustado sobre el control.
5. `mitigation.method` sale del enum congelado; un método desconocido explota.
"""

from __future__ import annotations

import pytest

pytest.importorskip("sklearn")

from blite_cap_quantum import corrector as c  # noqa: E402
from blite_cap_quantum.zne import apparent_improvement  # noqa: E402


class TestCorpusHonesto:
    def test_holdout_no_comparte_ninguna_matriz_con_train(self) -> None:
        """Ninguna fila de evaluación puede provenir de una instancia que el
        modelo ya vio — si no, "mejora en holdout" no significaría nada."""
        train = {tuple(tuple(fila) for fila in m) for m in c.TRAIN_MATRICES}
        holdout = {tuple(tuple(fila) for fila in m) for m in c.HOLDOUT_MATRICES}

        assert train.isdisjoint(holdout)

    def test_el_corpus_no_esta_vacio(self) -> None:
        assert len(c.TRAIN_MATRICES) >= 2
        assert len(c.HOLDOUT_MATRICES) >= 2


class TestDeterminismo:
    def test_el_training_digest_es_estable_entre_corridas_sin_cache(self) -> None:
        """Dos ajustes independientes (caché limpiada entre medio, como dos
        procesos distintos) tienen que dar el MISMO digest — la seed pinneada
        es la única fuente de aleatoriedad y está fija."""
        c._trained.cache_clear()  # pyright: ignore[reportPrivateUsage] — white-box: prueba el mecanismo interno de V9 a propósito
        _, digest1, _ = c._trained("ml-rf")  # pyright: ignore[reportPrivateUsage] — white-box: prueba el mecanismo interno de V9 a propósito
        c._trained.cache_clear()  # pyright: ignore[reportPrivateUsage] — white-box: prueba el mecanismo interno de V9 a propósito
        _, digest2, _ = c._trained("ml-rf")  # pyright: ignore[reportPrivateUsage] — white-box: prueba el mecanismo interno de V9 a propósito

        assert digest1 == digest2
        # SHA-256 hex real, no un placeholder de otra forma.
        assert len(digest1) == 64
        int(digest1, 16)

    def test_el_model_digest_es_estable_entre_corridas_sin_cache(self) -> None:
        c._trained.cache_clear()  # pyright: ignore[reportPrivateUsage] — white-box: prueba el mecanismo interno de V9 a propósito
        _, _, model_digest1 = c._trained("ml-rf")  # pyright: ignore[reportPrivateUsage] — white-box: prueba el mecanismo interno de V9 a propósito
        c._trained.cache_clear()  # pyright: ignore[reportPrivateUsage] — white-box: prueba el mecanismo interno de V9 a propósito
        _, _, model_digest2 = c._trained("ml-rf")  # pyright: ignore[reportPrivateUsage] — white-box: prueba el mecanismo interno de V9 a propósito

        assert model_digest1 == model_digest2

    def test_correct_expectation_da_el_mismo_resultado_dos_veces(self) -> None:
        matrix = c.HOLDOUT_MATRICES[0]

        r1 = c.correct_expectation(matrix, method="ml-rf", layers=1, seed=1, shots=256)
        r2 = c.correct_expectation(matrix, method="ml-rf", layers=1, seed=1, shots=256)

        assert r1["mitigated_energy"] == r2["mitigated_energy"]
        assert r1["unmitigated_energy"] == r2["unmitigated_energy"]
        assert (
            r1["mitigation"]["training_digest"] == r2["mitigation"]["training_digest"]
        )
        assert r1["mitigation"]["model_digest"] == r2["mitigation"]["model_digest"]


class TestTrainingDigestReal:
    def test_nunca_es_none_para_un_metodo_aprendido(self) -> None:
        """A diferencia de `zne.mitigation_block` (`training_digest: None`
        explícito — ZNE no entrena nada), acá es donde ese `None` deja de
        aplicar: el corrector SÍ entrena, y el digest lo prueba."""
        resultado = c.correct_expectation(
            c.HOLDOUT_MATRICES[0], method="ml-rf", layers=1, seed=1, shots=256
        )

        assert resultado["mitigation"]["training_digest"] is not None
        assert len(resultado["mitigation"]["training_digest"]) == 64

    def test_cambia_si_cambia_el_corpus(self) -> None:
        """El digest depende de VERDAD de los datos — no es una constante
        disfrazada de digest."""
        dataset_a = c._build_dataset(c.TRAIN_MATRICES)  # pyright: ignore[reportPrivateUsage] — white-box: prueba el mecanismo interno de V9 a propósito
        dataset_b = c._build_dataset(c.HOLDOUT_MATRICES)  # pyright: ignore[reportPrivateUsage] — white-box: prueba el mecanismo interno de V9 a propósito

        assert c.training_digest_of(dataset_a) != c.training_digest_of(dataset_b)


class TestControlNegativoDeCostoIgual:
    """La disciplina es la de V4 (`zne.apparent_improvement` + garbage
    folding al mismo presupuesto de shots) — este módulo no inventa un
    control aparte, aplica el MODELO YA ENTRENADO (nunca ajustado sobre
    datos de control) a la curva garbage-folded."""

    def test_el_resultado_trae_el_mismo_bloque_negative_control_que_zne(self) -> None:
        resultado = c.correct_expectation(
            c.HOLDOUT_MATRICES[0], method="ml-rf", layers=1, seed=1, shots=256
        )

        control = resultado["negative_control"]
        assert control["kind"] == "garbage-folding"
        assert control["reference"] == "arXiv:2607.09360"
        assert isinstance(control["improvement"], float)
        assert isinstance(resultado["improvement_survives_control"], bool)

    def test_el_modelo_nunca_se_ajusta_sobre_datos_de_control(self) -> None:
        """`_fit`/`_trained` solo tocan `dataset.features`/`.targets` (la
        rama LEGÍTIMA) — `garbage_features` existe en `_Dataset` para
        EVALUAR, nunca para entrenar."""
        import inspect

        fuente = inspect.getsource(c._fit)  # pyright: ignore[reportPrivateUsage] — white-box: prueba el mecanismo interno de V9 a propósito

        assert "garbage" not in fuente


class TestHonestidadDeLaMejora:
    """El corrector tiene que batir el baseline de verdad (ZNE, el que V4
    estableció) y sobrevivir a SU control — si no lo bate, se reporta que no
    lo bate. Este test corre el holdout completo y deja el número, sin
    inflarlo ni esconderlo."""

    def test_reporte_de_mejora_en_holdout(self) -> None:
        import statistics as st

        from blite_cap_quantum.zne import EXTRAPOLATOR_RICHARDSON, extrapolate

        model, _, _ = c._trained("ml-rf")  # pyright: ignore[reportPrivateUsage] — white-box: prueba el mecanismo interno de V9 a propósito
        holdout = c._build_dataset(c.HOLDOUT_MATRICES)  # pyright: ignore[reportPrivateUsage] — white-box: prueba el mecanismo interno de V9 a propósito

        mejoras_ml: list[float] = []
        mejoras_control: list[float] = []
        mejoras_zne: list[float] = []
        for features, target, garbage_features, garbage_unmit, unmit in zip(
            holdout.features,
            holdout.targets,
            holdout.garbage_features,
            holdout.garbage_unmitigated,
            holdout.unmitigated,
            strict=True,
        ):
            predicho = features[c._RICHARDSON_INDEX] + float(  # pyright: ignore[reportPrivateUsage] — white-box: prueba el mecanismo interno de V9 a propósito
                model.predict([list(features)])[0]
            )
            predicho_control = garbage_features[c._RICHARDSON_INDEX] + float(  # pyright: ignore[reportPrivateUsage] — white-box: prueba el mecanismo interno de V9 a propósito
                model.predict([list(garbage_features)])[0]
            )
            mejoras_ml.append(
                apparent_improvement(
                    ideal=target, unmitigated=unmit, mitigated=predicho
                )
            )
            mejoras_control.append(
                apparent_improvement(
                    ideal=target, unmitigated=garbage_unmit, mitigated=predicho_control
                )
            )
            mejoras_zne.append(
                apparent_improvement(
                    ideal=target,
                    unmitigated=unmit,
                    mitigated=extrapolate(
                        c._SCALES,  # pyright: ignore[reportPrivateUsage] — white-box: prueba el mecanismo interno de V9 a propósito
                        list(features[0:3]),
                        method=EXTRAPOLATOR_RICHARDSON,
                    ),
                )
            )

        media_ml = st.mean(mejoras_ml)
        media_control = st.mean(mejoras_control)
        media_zne = st.mean(mejoras_zne)

        # El hallazgo real de esta tarea (documentado en el reporte de V9):
        # el corrector sobrevive su propio control por un margen enorme —
        # `apparent_improvement` de un dígito contra uno de varios dígitos
        # negativos — y con ESTE corpus queda más cerca de cero que el
        # baseline ZNE-Richardson que V4 estableció, aunque ninguno de los
        # dos mejora la medición cruda en promedio (corpus chico, declarado
        # como prueba de concepto en el docstring del módulo).
        assert media_ml > media_control
        assert media_control < -1.0  # el control es un piso, no un empate
        assert media_ml > media_zne


class TestMetodoDesconocido:
    def test_explota(self) -> None:
        with pytest.raises(ValueError, match="method"):
            c.correct_expectation(c.HOLDOUT_MATRICES[0], method="bogus")

    def test_producer_available_distingue_metodo(self) -> None:
        assert c.producer_available("ml-rf") is True


class TestMetodoGbm:
    def test_tambien_produce_un_resultado_valido(self) -> None:
        pytest.importorskip("xgboost")

        resultado = c.correct_expectation(
            c.HOLDOUT_MATRICES[0], method="ml-gbm", layers=1, seed=1, shots=256
        )

        assert resultado["mitigation"]["method"] == "ml-gbm"
        assert resultado["mitigation"]["training_digest"] is not None
