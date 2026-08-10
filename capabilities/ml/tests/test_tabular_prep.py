"""Unit tests de `TabularPrep._invoke_impl` (pipeline anti-fuga: folds
estratificados por compromiso previo -> imputar mediana -> seleccionar top-k
por RandomForest -> escalar a [0, pi], todo `fit` restringido al train de
cada fold — recipe knowledge/quantum/02 SS2.1).
"""

from __future__ import annotations

import dataclasses
import json
import math
from pathlib import Path

import pytest

pytest.importorskip("sklearn", reason="extra opcional: uv sync --extra sklearn")

from blite_cap_ml import TabularPrep  # noqa: E402

_SEED = 1


def _rows_and_labels(
    n: int = 40, n_features: int = 6
) -> tuple[list[list[float | None]], list[int]]:
    import numpy as np

    rng = np.random.default_rng(_SEED)
    rows: list[list[float | None]] = rng.normal(size=(n, n_features)).tolist()
    labels = [0] * (n // 2) + [1] * (n - n // 2)
    return rows, labels


class TestFoldAssignment:
    def test_folds_length_matches_rows(self) -> None:
        rows, labels = _rows_and_labels()
        result = TabularPrep().invoke(
            {"rows": rows, "labels": labels, "n_folds": 4, "seed": _SEED}
        )

        assert len(result["folds"]) == len(rows)
        assert set(result["folds"]) == {0, 1, 2, 3}

    def test_fold_sizes_sum_to_total_rows(self) -> None:
        rows, labels = _rows_and_labels()
        result = TabularPrep().invoke(
            {"rows": rows, "labels": labels, "n_folds": 5, "seed": _SEED}
        )

        for sizes in result["fold_sizes"]:
            assert sizes["train"] + sizes["test"] == len(rows)


class TestAntiLeakageFoldCommitment:
    """PROPERTY_RULE (recipe SS2.1, docs/specs/generalidad-retos.md SS4): la
    asignacion de folds es un COMPROMISO PREVIO — depende SOLO de labels+seed,
    jamas de los valores de las features. Se prueba operacionalmente: dos
    corridas con las MISMAS labels/seed pero features permutadas/corrompidas
    deben producir folds byte-identicos."""

    def test_folds_identical_when_feature_values_are_corrupted(self) -> None:
        rows, labels = _rows_and_labels()
        import numpy as np

        rng = np.random.default_rng(999)
        corrupted_rows = rng.uniform(
            -1000, 1000, size=(len(rows), len(rows[0]))
        ).tolist()

        first = TabularPrep().invoke(
            {"rows": rows, "labels": labels, "n_folds": 4, "seed": _SEED}
        )
        second = TabularPrep().invoke(
            {"rows": corrupted_rows, "labels": labels, "n_folds": 4, "seed": _SEED}
        )

        assert first["folds"] == second["folds"]

    def test_folds_identical_when_feature_columns_are_permuted(self) -> None:
        rows, labels = _rows_and_labels()
        permuted_rows = [list(reversed(row)) for row in rows]

        first = TabularPrep().invoke(
            {"rows": rows, "labels": labels, "n_folds": 4, "seed": _SEED}
        )
        second = TabularPrep().invoke(
            {"rows": permuted_rows, "labels": labels, "n_folds": 4, "seed": _SEED}
        )

        assert first["folds"] == second["folds"]


class TestScalingRange:
    def test_train_features_stay_within_zero_pi(self) -> None:
        """El scaler se ajusta (`fit`) SOLO sobre train — por construccion
        de `MinMaxScaler`, el propio train queda exactamente dentro de
        [0, pi] (min/max del propio fit)."""
        rows, labels = _rows_and_labels()
        result = TabularPrep().invoke(
            {
                "rows": rows,
                "labels": labels,
                "n_folds": 3,
                "seed": _SEED,
                "n_features": 3,
            }
        )

        for fold in result["prepared"]:
            for feature_row in fold["train"]["features"]:
                for value in feature_row:
                    assert -1e-9 <= value <= math.pi + 1e-9

    def test_test_features_are_finite(self) -> None:
        """El `test` split solo recibe `transform` (nunca `fit` — disciplina
        anti-fuga): si sus valores caen FUERA del rango observado en train,
        el `transform` los proyecta fuera de [0, pi] legitimamente (no es un
        bug: es el precio de no ajustar el scaler con datos de test). La
        unica garantia exigible aqui es que el pipeline no produzca NaN/Inf."""
        rows, labels = _rows_and_labels()
        result = TabularPrep().invoke(
            {
                "rows": rows,
                "labels": labels,
                "n_folds": 3,
                "seed": _SEED,
                "n_features": 3,
            }
        )

        for fold in result["prepared"]:
            for feature_row in fold["test"]["features"]:
                for value in feature_row:
                    assert math.isfinite(value)

    def test_selected_feature_count_matches_n_features(self) -> None:
        rows, labels = _rows_and_labels(n_features=6)
        result = TabularPrep().invoke(
            {
                "rows": rows,
                "labels": labels,
                "n_folds": 3,
                "seed": _SEED,
                "n_features": 3,
            }
        )

        for indices in result["feature_indices"]:
            assert len(indices) == 3
            assert len(set(indices)) == 3


class TestMissingValueImputation:
    def test_missing_values_do_not_propagate_to_prepared_output(self) -> None:
        rows, labels = _rows_and_labels()
        rows[0][0] = None
        rows[3][2] = None

        result = TabularPrep().invoke(
            {"rows": rows, "labels": labels, "n_folds": 4, "seed": _SEED}
        )

        for fold in result["prepared"]:
            for split in ("train", "test"):
                for feature_row in fold[split]["features"]:
                    assert all(not math.isnan(v) for v in feature_row)


class TestDeterminism:
    def test_identical_invocations_return_identical_dicts(self) -> None:
        rows, labels = _rows_and_labels()
        payload = {
            "rows": rows,
            "labels": labels,
            "n_folds": 4,
            "seed": _SEED,
            "n_features": 3,
        }

        first = TabularPrep().invoke(payload)
        second = TabularPrep().invoke(payload)

        assert first == second


class TestInputValidation:
    def test_missing_rows_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="rows"):
            TabularPrep().invoke({"labels": [0, 1]})

    def test_empty_rows_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="rows"):
            TabularPrep().invoke({"rows": [], "labels": []})

    def test_ragged_rows_raise_value_error(self) -> None:
        with pytest.raises(ValueError, match="rows"):
            TabularPrep().invoke({"rows": [[1.0, 2.0], [1.0]], "labels": [0, 1]})

    def test_non_numeric_cell_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="rows"):
            TabularPrep().invoke({"rows": [[1.0, "x"], [2.0, 3.0]], "labels": [0, 1]})

    def test_missing_labels_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="labels"):
            TabularPrep().invoke({"rows": [[1.0], [2.0]]})

    def test_labels_length_mismatch_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="labels"):
            TabularPrep().invoke({"rows": [[1.0], [2.0]], "labels": [0]})

    def test_non_binary_label_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="labels"):
            TabularPrep().invoke({"rows": [[1.0], [2.0]], "labels": [0, 2]})

    def test_boolean_label_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="labels"):
            TabularPrep().invoke({"rows": [[1.0], [2.0]], "labels": [0, True]})

    def test_n_folds_below_two_raises_value_error(self) -> None:
        rows, labels = _rows_and_labels()
        with pytest.raises(ValueError, match="n_folds"):
            TabularPrep().invoke({"rows": rows, "labels": labels, "n_folds": 1})

    def test_boolean_n_folds_raises_value_error(self) -> None:
        rows, labels = _rows_and_labels()
        with pytest.raises(ValueError, match="n_folds"):
            TabularPrep().invoke({"rows": rows, "labels": labels, "n_folds": True})

    def test_boolean_seed_raises_value_error(self) -> None:
        rows, labels = _rows_and_labels()
        with pytest.raises(ValueError, match="seed"):
            TabularPrep().invoke({"rows": rows, "labels": labels, "seed": True})

    def test_n_features_below_one_raises_value_error(self) -> None:
        rows, labels = _rows_and_labels()
        with pytest.raises(ValueError, match="n_features"):
            TabularPrep().invoke({"rows": rows, "labels": labels, "n_features": 0})

    def test_n_features_exceeding_raw_columns_raises_value_error(self) -> None:
        rows, labels = _rows_and_labels(n_features=4)
        with pytest.raises(ValueError, match="n_features"):
            TabularPrep().invoke({"rows": rows, "labels": labels, "n_features": 99})


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

        manifest = TabularPrep().manifest
        text = json.dumps(dataclasses.asdict(manifest), default=str).lower()

        violations = [term for term in denylist if term in text]
        assert not violations, (
            f"manifest contiene vocabulario de escenario: {violations}"
        )
