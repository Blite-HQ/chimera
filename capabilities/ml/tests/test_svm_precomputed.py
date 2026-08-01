"""Unit tests de `SvmPrecomputed._invoke_impl` (SVM dual sobre un kernel YA
computado — recipe knowledge/quantum/02 SS2.3: accuracy sola es insuficiente
bajo desbalance, por eso siempre se reportan precision/recall/f1/matriz de
confusion)."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

pytest.importorskip("sklearn", reason="extra opcional: uv sync --extra sklearn")

from blite_cap_ml import SvmPrecomputed  # noqa: E402


def _linearly_separable_kernel() -> dict[str, object]:
    """Un kernel lineal (producto interno) sobre puntos 1D bien separados —
    el SVM dual deberia clasificar perfecto, sin ambiguedad de contrato."""
    train_points = [-3.0, -2.0, -1.0, 1.0, 2.0, 3.0]
    test_points = [-2.5, 2.5]
    kernel_train = [[a * b for b in train_points] for a in train_points]
    kernel_test = [[a * b for b in train_points] for a in test_points]
    labels_train = [0, 0, 0, 1, 1, 1]
    labels_test = [0, 1]
    return {
        "kernel_train": kernel_train,
        "kernel_test": kernel_test,
        "labels_train": labels_train,
        "labels_test": labels_test,
    }


class TestFitPredict:
    def test_perfectly_separable_kernel_reaches_full_accuracy(self) -> None:
        result = SvmPrecomputed().invoke({**_linearly_separable_kernel(), "seed": 1})

        assert result["predictions"] == [0, 1]
        assert result["accuracy"] == 1.0
        assert result["f1"] == 1.0

    def test_all_metrics_are_reported(self) -> None:
        result = SvmPrecomputed().invoke({**_linearly_separable_kernel(), "seed": 1})

        for key in ("accuracy", "precision", "recall", "f1", "confusion_matrix"):
            assert key in result

    def test_dual_and_support_shapes(self) -> None:
        result = SvmPrecomputed().invoke({**_linearly_separable_kernel(), "seed": 1})

        n_support = len(result["support_indices"])
        assert len(result["dual_coef"]) == 1  # binario: n_classes - 1
        assert len(result["dual_coef"][0]) == n_support
        assert len(result["intercept"]) == 1


class TestDeterminism:
    def test_identical_invocations_return_identical_dicts(self) -> None:
        payload = {**_linearly_separable_kernel(), "seed": 3}

        first = SvmPrecomputed().invoke(payload)
        second = SvmPrecomputed().invoke(payload)

        assert first == second


class TestInputValidation:
    def test_missing_kernel_train_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="kernel_train"):
            SvmPrecomputed().invoke({})

    def test_non_square_kernel_train_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="cuadrada"):
            SvmPrecomputed().invoke(
                {
                    "kernel_train": [[1.0, 2.0, 3.0], [2.0, 1.0, 3.0]],
                    "kernel_test": [[1.0, 2.0, 3.0]],
                    "labels_train": [0, 1],
                    "labels_test": [0],
                }
            )

    def test_kernel_test_wrong_width_raises_value_error(self) -> None:
        payload = _linearly_separable_kernel()
        payload["kernel_test"] = [[1.0, 2.0]]
        with pytest.raises(ValueError, match="kernel_test"):
            SvmPrecomputed().invoke(payload)

    def test_labels_train_length_mismatch_raises_value_error(self) -> None:
        payload = _linearly_separable_kernel()
        payload["labels_train"] = [0, 1]
        with pytest.raises(ValueError, match="labels_train"):
            SvmPrecomputed().invoke(payload)

    def test_non_binary_label_raises_value_error(self) -> None:
        payload = _linearly_separable_kernel()
        payload["labels_test"] = [0, 2]
        with pytest.raises(ValueError, match="labels_test"):
            SvmPrecomputed().invoke(payload)

    def test_boolean_seed_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="seed"):
            SvmPrecomputed().invoke({**_linearly_separable_kernel(), "seed": True})

    def test_non_positive_c_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="c debe"):
            SvmPrecomputed().invoke({**_linearly_separable_kernel(), "c": 0.0})


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

        manifest = SvmPrecomputed().manifest
        text = json.dumps(dataclasses.asdict(manifest), default=str).lower()

        violations = [term for term in denylist if term in text]
        assert not violations, f"manifest contiene vocabulario de escenario: {violations}"
