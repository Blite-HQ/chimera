"""Unit tests de `FidelityKernel._invoke_impl` (kernel de fidelidad por
overlap de statevectors, un solo producto matricial — recipe
knowledge/quantum/02 SS2.2/SS2.3, docs/mejorado/03-research.md R1)."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

pytest.importorskip(
    "qiskit", reason="extra opcional: uv sync --all-packages --extra qaoa"
)

from blite_cap_quantum import FidelityKernel  # noqa: E402

_X = [
    [0.1, 0.5, 1.0],
    [0.4, 0.2, 2.5],
    [1.5, 3.0, 0.05],
    [2.9, 1.1, 1.7],
]
_Y = [
    [0.3, 0.3, 0.3],
    [1.0, 1.0, 1.0],
]


class TestSelfGram:
    def test_diagonal_is_one(self) -> None:
        result = FidelityKernel().invoke({"x": _X})

        for i in range(len(_X)):
            assert result["kernel"][i][i] == pytest.approx(1.0, abs=1e-9)

    def test_exact_symmetry(self) -> None:
        result = FidelityKernel().invoke({"x": _X})
        kernel = result["kernel"]

        for i in range(len(_X)):
            for j in range(len(_X)):
                assert kernel[i][j] == kernel[j][i]

    def test_lambda_min_is_reported(self) -> None:
        result = FidelityKernel().invoke({"x": _X})

        assert result["lambda_min"] is not None
        assert isinstance(result["lambda_min"], float)

    def test_n_qubits_matches_feature_count(self) -> None:
        result = FidelityKernel().invoke({"x": _X})

        assert result["n_qubits"] == len(_X[0])


class TestPsdRepair:
    def test_clip_makes_kernel_psd(self) -> None:
        import numpy as np

        result = FidelityKernel().invoke({"x": _X, "psd_repair": "clip"})

        eigenvalues = np.linalg.eigvalsh(np.array(result["kernel"]))
        assert eigenvalues.min() >= -1e-12
        assert result["psd_repair"] == "clip"
        assert result["repaired"] is True

    def test_none_leaves_kernel_untouched(self) -> None:
        clipped = FidelityKernel().invoke({"x": _X, "psd_repair": "clip"})
        untouched = FidelityKernel().invoke({"x": _X, "psd_repair": "none"})

        assert untouched["psd_repair"] == "none"
        assert untouched["repaired"] is False
        # el metodo "none" no reconstruye via eigendescomposicion — si el
        # kernel ya era (casi) PSD, difiere del clip solo por el
        # re-simetrizado explicito, no por la reconstruccion espectral.
        assert untouched["lambda_min"] == clipped["lambda_min"]

    def test_cross_gram_does_not_apply_psd_repair(self) -> None:
        result = FidelityKernel().invoke({"x": _X, "y": _Y, "psd_repair": "clip"})

        assert result["lambda_min"] is None
        assert result["repaired"] is False
        assert result["psd_repair"] == "none"


class TestCrossKernel:
    def test_cross_kernel_shape_is_x_rows_by_y_rows(self) -> None:
        result = FidelityKernel().invoke({"x": _X, "y": _Y})

        assert len(result["kernel"]) == len(_X)
        assert all(len(row) == len(_Y) for row in result["kernel"])

    def test_cross_kernel_values_are_bounded(self) -> None:
        result = FidelityKernel().invoke({"x": _X, "y": _Y})

        for row in result["kernel"]:
            for value in row:
                assert -1e-9 <= value <= 1.0 + 1e-9


class TestReps:
    def test_more_reps_changes_kernel_values(self) -> None:
        one_rep = FidelityKernel().invoke({"x": _X, "reps": 1})
        two_reps = FidelityKernel().invoke({"x": _X, "reps": 2})

        assert one_rep["kernel"] != two_reps["kernel"]


class TestDeterminism:
    def test_identical_invocations_return_identical_dicts(self) -> None:
        payload = {"x": _X, "y": _Y, "reps": 2, "psd_repair": "clip"}

        first = FidelityKernel().invoke(payload)
        second = FidelityKernel().invoke(payload)

        assert first == second


class TestInputValidation:
    def test_missing_x_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="x"):
            FidelityKernel().invoke({})

    def test_empty_x_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="x"):
            FidelityKernel().invoke({"x": []})

    def test_ragged_x_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="x"):
            FidelityKernel().invoke({"x": [[1.0, 2.0], [1.0]]})

    def test_non_numeric_x_entry_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="x"):
            FidelityKernel().invoke({"x": [[1.0, "z"]]})

    def test_y_width_mismatch_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="y"):
            FidelityKernel().invoke({"x": _X, "y": [[1.0, 2.0]]})

    def test_too_many_qubits_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="qubits"):
            FidelityKernel().invoke({"x": [[0.1] * 20]})

    def test_unsupported_feature_map_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="feature_map"):
            FidelityKernel().invoke({"x": _X, "feature_map": "zz"})

    def test_reps_below_one_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="reps"):
            FidelityKernel().invoke({"x": _X, "reps": 0})

    def test_boolean_reps_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="reps"):
            FidelityKernel().invoke({"x": _X, "reps": True})

    def test_unsupported_psd_repair_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="psd_repair"):
            FidelityKernel().invoke({"x": _X, "psd_repair": "flip"})


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

        manifest = FidelityKernel().manifest
        text = json.dumps(dataclasses.asdict(manifest), default=str).lower()

        violations = [term for term in denylist if term in text]
        assert not violations, f"manifest contiene vocabulario de escenario: {violations}"
