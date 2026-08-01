"""Unit tests de `ClassifierBaseline._invoke_impl` (SVM-RBF bajo CV-5
estratificado — protocolo OFICIAL, recipe knowledge/quantum/02 SS3) y del
helper de McNemar (knowledge/quantum/04-estadistica-evidencia.md SS6)."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

pytest.importorskip("sklearn", reason="extra opcional: uv sync --extra sklearn")
pytest.importorskip("scipy", reason="McNemar exacto via scipy.stats.binomtest")

from blite_cap_ml import ClassifierBaseline  # noqa: E402

_SEED = 1


def _separable_rows_and_labels(n: int = 60) -> tuple[list[list[float | None]], list[int]]:
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
            ClassifierBaseline().invoke({"rows": rows, "labels": labels, "gamma": "bogus"})

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


class TestGenericitySelfCheck:
    """ADR-029: el gate del repo lee entry points INSTALADOS y no verá esta
    capability hasta un reinstall — esta aserción local es la que cubre en
    vivo (ver tests/invariants/test_capability_genericity.py)."""

    def test_manifest_has_no_scenario_vocabulary(self) -> None:
        denylist_path = (
            Path(__file__).resolve().parents[3] / "tests" / "invariants" / "scenario_denylist.txt"
        )
        denylist = [
            line.strip().lower()
            for line in denylist_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]

        manifest = ClassifierBaseline().manifest
        text = json.dumps(dataclasses.asdict(manifest), default=str).lower()

        violations = [term for term in denylist if term in text]
        assert not violations, f"manifest contiene vocabulario de escenario: {violations}"
