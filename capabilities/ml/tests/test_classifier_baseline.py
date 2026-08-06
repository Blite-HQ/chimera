"""Unit tests de `ClassifierBaseline._invoke_impl` (SVM-RBF bajo CV-5
estratificado — protocolo OFICIAL, recipe knowledge/quantum/02 SS3) y del
helper de McNemar (knowledge/quantum/04-estadistica-evidencia.md SS6)."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("sklearn", reason="extra opcional: uv sync --extra sklearn")
pytest.importorskip("scipy", reason="McNemar exacto via scipy.stats.binomtest")

from blite_cap_ml import ClassifierBaseline  # noqa: E402

_SEED = 1


def _separable_rows_and_labels(
    n: int = 60,
) -> tuple[list[list[float | None]], list[int]]:
    import numpy as np

    rng = np.random.default_rng(_SEED)
    half = n // 2
    class0 = rng.normal(loc=-2.0, scale=0.5, size=(half, 3))
    class1 = rng.normal(loc=2.0, scale=0.5, size=(n - half, 3))
    rows = np.vstack([class0, class1]).tolist()
    labels = [0] * half + [1] * (n - half)
    return rows, labels


class TestCrossValidation:
    def test_well_separated_classes_reach_high_accuracy(self) -> None:
        rows, labels = _separable_rows_and_labels()
        result = ClassifierBaseline().invoke(
            {"rows": rows, "labels": labels, "n_folds": 5, "seed": _SEED}
        )

        assert result["aggregate"]["accuracy"] >= 0.85

    def test_predictions_are_out_of_fold_and_full_length(self) -> None:
        rows, labels = _separable_rows_and_labels()
        result = ClassifierBaseline().invoke(
            {"rows": rows, "labels": labels, "n_folds": 5, "seed": _SEED}
        )

        assert len(result["predictions"]) == len(rows)
        assert all(p in (0, 1) for p in result["predictions"])

    def test_fold_metrics_length_matches_n_folds(self) -> None:
        rows, labels = _separable_rows_and_labels()
        result = ClassifierBaseline().invoke(
            {"rows": rows, "labels": labels, "n_folds": 4, "seed": _SEED}
        )

        assert len(result["fold_metrics"]) == 4
        for fold_metric in result["fold_metrics"]:
            for key in ("accuracy", "precision", "recall", "f1", "confusion_matrix"):
                assert key in fold_metric

    def test_missing_values_are_imputed_per_fold(self) -> None:
        rows, labels = _separable_rows_and_labels()
        rows[0][0] = None
        rows[5][1] = None

        result = ClassifierBaseline().invoke(
            {"rows": rows, "labels": labels, "n_folds": 5, "seed": _SEED}
        )

        assert len(result["predictions"]) == len(rows)


class TestMcNemar:
    def test_identical_predictions_yield_zero_discordant_pairs(self) -> None:
        rows, labels = _separable_rows_and_labels()
        baseline = ClassifierBaseline().invoke(
            {"rows": rows, "labels": labels, "n_folds": 5, "seed": _SEED}
        )

        result = ClassifierBaseline().invoke(
            {
                "rows": rows,
                "labels": labels,
                "n_folds": 5,
                "seed": _SEED,
                "compare_predictions": baseline["predictions"],
            }
        )

        assert result["mcnemar"] == {"b": 0, "c": 0, "p_value": 1.0}

    def test_mcnemar_absent_without_compare_predictions(self) -> None:
        rows, labels = _separable_rows_and_labels()
        result = ClassifierBaseline().invoke(
            {"rows": rows, "labels": labels, "n_folds": 5, "seed": _SEED}
        )

        assert "mcnemar" not in result

    def test_mcnemar_reports_discordant_pairs_and_p_value(self) -> None:
        rows, labels = _separable_rows_and_labels()
        baseline = ClassifierBaseline().invoke(
            {"rows": rows, "labels": labels, "n_folds": 5, "seed": _SEED}
        )
        # un comparador que SIEMPRE predice la clase mayoritaria (0) —
        # discordante en cada fila donde la etiqueta real es 1 y el baseline
        # acierta.
        always_zero = [0] * len(rows)

        result = ClassifierBaseline().invoke(
            {
                "rows": rows,
                "labels": labels,
                "n_folds": 5,
                "seed": _SEED,
                "compare_predictions": always_zero,
            }
        )

        mcnemar = result["mcnemar"]
        assert mcnemar["b"] + mcnemar["c"] > 0
        assert 0.0 <= mcnemar["p_value"] <= 1.0
        assert baseline["predictions"] == result["predictions"]


class TestDeterminism:
    def test_identical_invocations_return_identical_dicts(self) -> None:
        rows, labels = _separable_rows_and_labels()
        payload = {"rows": rows, "labels": labels, "n_folds": 4, "seed": _SEED}

        first = ClassifierBaseline().invoke(payload)
        second = ClassifierBaseline().invoke(payload)

        assert first == second


class TestInputValidation:
    def test_missing_rows_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="rows"):
            ClassifierBaseline().invoke({"labels": [0, 1]})

    def test_labels_length_mismatch_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="labels"):
            ClassifierBaseline().invoke({"rows": [[1.0], [2.0]], "labels": [0]})

    def test_n_folds_below_two_raises_value_error(self) -> None:
        rows, labels = _separable_rows_and_labels()
        with pytest.raises(ValueError, match="n_folds"):
            ClassifierBaseline().invoke({"rows": rows, "labels": labels, "n_folds": 1})

    def test_boolean_seed_raises_value_error(self) -> None:
        rows, labels = _separable_rows_and_labels()
        with pytest.raises(ValueError, match="seed"):
            ClassifierBaseline().invoke({"rows": rows, "labels": labels, "seed": True})

    def test_non_positive_c_raises_value_error(self) -> None:
        rows, labels = _separable_rows_and_labels()
        with pytest.raises(ValueError, match="c debe"):
            ClassifierBaseline().invoke({"rows": rows, "labels": labels, "c": -1.0})

    def test_invalid_gamma_string_raises_value_error(self) -> None:
        rows, labels = _separable_rows_and_labels()
        with pytest.raises(ValueError, match="gamma"):
            ClassifierBaseline().invoke(
                {"rows": rows, "labels": labels, "gamma": "bogus"}
            )

    def test_negative_gamma_number_raises_value_error(self) -> None:
        rows, labels = _separable_rows_and_labels()
        with pytest.raises(ValueError, match="gamma"):
            ClassifierBaseline().invoke({"rows": rows, "labels": labels, "gamma": -0.5})

    def test_compare_predictions_length_mismatch_raises_value_error(self) -> None:
        rows, labels = _separable_rows_and_labels()
        with pytest.raises(ValueError, match="compare_predictions"):
            ClassifierBaseline().invoke(
                {"rows": rows, "labels": labels, "compare_predictions": [0, 1]}
            )


def _prepared_folds_fixture() -> tuple[
    list[list[float]], list[int], list[dict[str, dict[str, list[Any]]]], list[int]
]:
    """8 filas, 2 folds. `rows` (features CRUDAS) llevan CERO informacion
    sobre `labels` (el valor 1.0/2.0 aparece con ambas etiquetas por igual)
    -- un SVM entrenado sobre `rows` no puede superar el azar (~0.5). Las
    features de `prepared_folds`, en cambio, codifican la etiqueta
    exactamente (0.0/1.0) -- perfectamente separables (accuracy 1.0). Si
    `ClassifierBaseline` alguna vez ignorase `prepared_folds` y recalculase
    desde `rows` en silencio, la accuracy agregada caeria a ~0.5 en vez de
    1.0 -- la propiedad que `TestPreparedFoldsSharedPipeline` fija."""
    rows: list[list[float]] = [[1.0], [1.0], [2.0], [2.0], [1.0], [1.0], [2.0], [2.0]]
    labels = [0, 1, 0, 1, 0, 1, 0, 1]
    folds = [0, 0, 0, 0, 1, 1, 1, 1]

    fold0_train = {"features": [[0.0], [1.0], [0.0], [1.0]], "labels": [0, 1, 0, 1]}
    fold0_test = {"features": [[0.0], [1.0], [0.0], [1.0]], "labels": [0, 1, 0, 1]}
    fold1_train = {"features": [[0.0], [1.0], [0.0], [1.0]], "labels": [0, 1, 0, 1]}
    fold1_test = {"features": [[0.0], [1.0], [0.0], [1.0]], "labels": [0, 1, 0, 1]}
    prepared_folds = [
        {"train": fold0_train, "test": fold0_test},
        {"train": fold1_train, "test": fold1_test},
    ]
    return rows, labels, prepared_folds, folds


class TestPreparedFoldsSharedPipeline:
    """Regresion de sesgo mismo-pipeline: cuando el caller trae
    `prepared_folds` (mismo shape que `blite.ml.tabular_prep`), el SVM-RBF
    DEBE ajustar exactamente sobre esas matrices -- nunca recalcular su
    propio split/imputacion sobre `rows` en silencio. Sin esto, comparar el
    brazo que SI usa el pipeline preparado (kernel cuantico) contra este
    baseline seria un McNemar entre dos PIPELINES distintos, no entre dos
    modelos sobre los mismos datos."""

    def test_svm_ve_exactamente_las_matrices_de_prepared_folds(self) -> None:
        rows, labels, prepared_folds, folds = _prepared_folds_fixture()

        result = ClassifierBaseline().invoke(
            {
                "rows": rows,
                "labels": labels,
                "n_folds": 2,
                "seed": _SEED,
                "prepared_folds": prepared_folds,
                "folds": folds,
            }
        )

        # Si el capability hubiera ignorado `prepared_folds` y recalculado
        # desde `rows` (sin señal alguna sobre el label), la accuracy
        # agregada rondaria el azar (~0.5), jamas 1.0.
        assert result["aggregate"]["accuracy"] == 1.0
        assert len(result["predictions"]) == len(rows)
        assert len(result["fold_metrics"]) == 2

    def test_mcnemar_funciona_junto_con_prepared_folds(self) -> None:
        rows, labels, prepared_folds, folds = _prepared_folds_fixture()
        always_wrong = [1 - label for label in labels]

        result = ClassifierBaseline().invoke(
            {
                "rows": rows,
                "labels": labels,
                "n_folds": 2,
                "seed": _SEED,
                "prepared_folds": prepared_folds,
                "folds": folds,
                "compare_predictions": always_wrong,
            }
        )

        # El propio modelo acierta las 8 (fixture perfectamente separable);
        # el comparador falla las 8 -> b=8, c=0.
        assert result["mcnemar"]["b"] == 8
        assert result["mcnemar"]["c"] == 0

    def test_prepared_folds_sin_folds_raises_value_error(self) -> None:
        rows, labels, prepared_folds, _folds = _prepared_folds_fixture()

        with pytest.raises(
            ValueError, match="prepared_folds.*folds|folds.*prepared_folds"
        ):
            ClassifierBaseline().invoke(
                {
                    "rows": rows,
                    "labels": labels,
                    "n_folds": 2,
                    "prepared_folds": prepared_folds,
                }
            )

    def test_folds_sin_prepared_folds_raises_value_error(self) -> None:
        rows, labels, _prepared_folds, folds = _prepared_folds_fixture()

        with pytest.raises(
            ValueError, match="prepared_folds.*folds|folds.*prepared_folds"
        ):
            ClassifierBaseline().invoke(
                {"rows": rows, "labels": labels, "n_folds": 2, "folds": folds}
            )

    def test_prepared_folds_longitud_incorrecta_raises_value_error(self) -> None:
        rows, labels, prepared_folds, folds = _prepared_folds_fixture()

        with pytest.raises(ValueError, match="prepared_folds"):
            ClassifierBaseline().invoke(
                {
                    "rows": rows,
                    "labels": labels,
                    "n_folds": 2,
                    "prepared_folds": prepared_folds[:1],
                    "folds": folds,
                }
            )

    def test_folds_fuera_de_rango_raises_value_error(self) -> None:
        rows, labels, prepared_folds, folds = _prepared_folds_fixture()
        folds_malos = [*folds[:-1], 99]

        with pytest.raises(ValueError, match="folds"):
            ClassifierBaseline().invoke(
                {
                    "rows": rows,
                    "labels": labels,
                    "n_folds": 2,
                    "prepared_folds": prepared_folds,
                    "folds": folds_malos,
                }
            )

    def test_labels_desincronizadas_entre_folds_y_prepared_folds_raises_value_error(
        self,
    ) -> None:
        rows, labels, prepared_folds, folds = _prepared_folds_fixture()
        # Tamperar las labels declaradas del test de fold 0 -- ya NO
        # coinciden con `labels[]` en las filas que `folds` asigna a fold 0.
        tampered = [dict(entry) for entry in prepared_folds]
        tampered[0] = {
            "train": tampered[0]["train"],
            "test": {
                "features": tampered[0]["test"]["features"],
                "labels": [1, 1, 1, 1],
            },
        }

        with pytest.raises(ValueError, match="desincronizados"):
            ClassifierBaseline().invoke(
                {
                    "rows": rows,
                    "labels": labels,
                    "n_folds": 2,
                    "prepared_folds": tampered,
                    "folds": folds,
                }
            )


class TestGenericitySelfCheck:
    """ADR-029: el gate del repo lee entry points INSTALADOS y no verá esta
    capability hasta un reinstall — esta aserción local es la que cubre en
    vivo (ver tests/invariants/test_capability_genericity.py)."""

    def test_manifest_has_no_scenario_vocabulary(self) -> None:
        denylist_path = (
            Path(__file__).resolve().parents[3]
            / "tests"
            / "invariants"
            / "scenario_denylist.txt"
        )
        denylist = [
            line.strip().lower()
            for line in denylist_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]

        manifest = ClassifierBaseline().manifest
        text = json.dumps(dataclasses.asdict(manifest), default=str).lower()

        violations = [term for term in denylist if term in text]
        assert not violations, (
            f"manifest contiene vocabulario de escenario: {violations}"
        )
