"""Integracion Reto 2 de punta a punta sobre una porcion CHICA del corpus
sintetico sellado (knowledge/tabular/corpus/synthetic-binary.csv — Deliverable
1): `blite.ml.tabular_prep` -> `blite.quantum.fidelity_kernel` ->
`blite.ml.svm_precomputed` (brazo cuantico) y `blite.ml.classifier_baseline`
(brazo clasico oficial, CV-5 SVM-RBF) sobre la MISMA porcion — ambos arman
predicciones out-of-fold (`fold_sizes`/`folds` de `tabular_prep` y las
predicciones de `classifier_baseline` comparten la MISMA asignacion de fold
por compromiso previo: StratifiedKFold solo depende de labels+seed, no de
las features — ver `test_tabular_prep.py::TestAntiLeakageFoldCommitment`),
asi que son comparables PUNTO A PUNTO para McNemar
(knowledge/quantum/04-estadistica-evidencia.md SS6).

Se mantiene chica (120 filas, 2 folds, 4 qubits) para correr en <10s.
"""

from __future__ import annotations

import csv
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("sklearn", reason="extra opcional: uv sync --extra sklearn")
pytest.importorskip(
    "qiskit", reason="extra opcional: uv sync --all-packages --extra qaoa"
)
pytest.importorskip("scipy", reason="McNemar exacto via scipy.stats.binomtest")

from blite_cap_ml import ClassifierBaseline, SvmPrecomputed, TabularPrep  # noqa: E402
from blite_cap_quantum import FidelityKernel  # noqa: E402

_SEED = 1
_N_FOLDS = 2
_N_FEATURES = 4
_SLICE_SIZE = 120


def _find_corpus_csv() -> Path:
    for base in (Path(__file__).resolve(), *Path(__file__).resolve().parents):
        candidate = base / "knowledge" / "tabular" / "corpus" / "synthetic-binary.csv"
        if candidate.is_file():
            return candidate
    msg = "corpus tabular no encontrado sobre este archivo"
    raise FileNotFoundError(msg)


def _load_corpus_slice(n_rows: int) -> tuple[list[list[float | None]], list[int]]:
    with _find_corpus_csv().open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        next(reader)  # encabezado
        raw_rows = [next(reader) for _ in range(n_rows)]

    rows: list[list[float | None]] = []
    labels: list[int] = []
    for raw in raw_rows:
        *feature_cells, label_cell = raw
        rows.append([None if cell == "" else float(cell) for cell in feature_cells])
        labels.append(int(label_cell))
    return rows, labels


@dataclass
class _FoldResult:
    fold: int
    kernel_train_shape: tuple[int, int]
    kernel_cross_shape: tuple[int, int]
    lambda_min: float | None
    svm_result: dict[str, Any]


def _quantum_oof_predictions(
    rows: list[list[float | None]], labels: list[int], n_folds: int, seed: int
) -> tuple[list[int], list[_FoldResult]]:
    """Corre tabular_prep -> fidelity_kernel -> svm_precomputed en CADA fold
    y arma predicciones out-of-fold del brazo cuantico (misma logica que
    `classifier_baseline`, para ser comparable punto a punto)."""
    prep = TabularPrep().invoke(
        {
            "rows": rows,
            "labels": labels,
            "n_folds": n_folds,
            "seed": seed,
            "n_features": _N_FEATURES,
        }
    )

    n_rows = len(rows)
    oof_predictions: list[int | None] = [None] * n_rows
    per_fold_results: list[_FoldResult] = []

    test_indices_by_fold: dict[int, list[int]] = {}
    for row_idx, fold_idx in enumerate(prep["folds"]):
        test_indices_by_fold.setdefault(fold_idx, []).append(row_idx)

    for fold_idx, fold_data in enumerate(prep["prepared"]):
        train_features = fold_data["train"]["features"]
        test_features = fold_data["test"]["features"]
        train_labels = fold_data["train"]["labels"]
        test_labels = fold_data["test"]["labels"]

        kernel_train = FidelityKernel().invoke({"x": train_features})
        kernel_cross = FidelityKernel().invoke({"x": test_features, "y": train_features})

        svm_result = SvmPrecomputed().invoke(
            {
                "kernel_train": kernel_train["kernel"],
                "kernel_test": kernel_cross["kernel"],
                "labels_train": train_labels,
                "labels_test": test_labels,
                "seed": seed,
            }
        )

        test_indices = test_indices_by_fold[fold_idx]
        assert len(test_indices) == len(svm_result["predictions"])
        for row_idx, prediction in zip(test_indices, svm_result["predictions"], strict=True):
            oof_predictions[row_idx] = prediction

        per_fold_results.append(
            _FoldResult(
                fold=fold_idx,
                kernel_train_shape=(len(kernel_train["kernel"]), len(kernel_train["kernel"][0])),
                kernel_cross_shape=(len(kernel_cross["kernel"]), len(kernel_cross["kernel"][0])),
                lambda_min=kernel_train["lambda_min"],
                svm_result=svm_result,
            )
        )

    assert all(p is not None for p in oof_predictions), "toda fila debe caer en exactamente un fold"
    return [int(p) for p in oof_predictions], per_fold_results  # type: ignore[arg-type]


class TestFullChainOnCorpusSlice:
    def test_both_arms_produce_metrics_with_aligned_shapes(self) -> None:
        rows, labels = _load_corpus_slice(_SLICE_SIZE)
        started = time.monotonic()

        quantum_predictions, per_fold = _quantum_oof_predictions(
            rows, labels, _N_FOLDS, _SEED
        )

        classical = ClassifierBaseline().invoke(
            {
                "rows": rows,
                "labels": labels,
                "n_folds": _N_FOLDS,
                "seed": _SEED,
                "compare_predictions": quantum_predictions,
            }
        )

        elapsed = time.monotonic() - started
        assert elapsed < 10.0, f"la integracion debe correr en <10s, tomo {elapsed:.2f}s"

        # shapes: cada fold produce un kernel_train cuadrado (m_train) y un
        # kernel_cross (m_test x m_train) — y svm_precomputed predice
        # exactamente m_test filas.
        for fold_result in per_fold:
            train_m, train_m2 = fold_result.kernel_train_shape
            cross_k, cross_m = fold_result.kernel_cross_shape
            assert train_m == train_m2
            assert cross_m == train_m
            assert len(fold_result.svm_result["predictions"]) == cross_k

        # ambos brazos producen predicciones OOF completas y comparables
        assert len(quantum_predictions) == _SLICE_SIZE
        assert len(classical["predictions"]) == _SLICE_SIZE

        # ambos brazos exponen metricas completas (accuracy sola es
        # insuficiente bajo el desbalance 61/39 — recipe SS2.3)
        for key in ("accuracy", "precision", "recall", "f1", "confusion_matrix"):
            assert key in classical["aggregate"]
        for fold_result in per_fold:
            for key in ("accuracy", "precision", "recall", "f1", "confusion_matrix"):
                assert key in fold_result.svm_result

        # McNemar entre brazos (mismos folds por compromiso previo)
        mcnemar = classical["mcnemar"]
        assert set(mcnemar) == {"b", "c", "p_value"}
        assert 0.0 <= mcnemar["p_value"] <= 1.0

        # lambda_min se reporta SIEMPRE para el self-Gram de train (nunca se
        # repara en silencio)
        for fold_result in per_fold:
            assert fold_result.lambda_min is not None


class TestLeakageControl:
    """Detector anti-fuga operacional (recipe/nota 04 SS5): con las
    ETIQUETAS barajadas, un pipeline que "siga funcionando" esta fugando
    informacion. Con el 61/39 de este corpus, la clase mayoritaria por si
    sola ya da ~0.61 de accuracy — el umbral 0.60 deja margen bajo esa cota
    sin ser tan laxo como para no cazar una fuga real."""

    def test_quantum_arm_accuracy_collapses_with_shuffled_labels(self) -> None:
        import numpy as np

        rows, labels = _load_corpus_slice(_SLICE_SIZE)
        rng = np.random.default_rng(_SEED)
        shuffled_labels = [int(v) for v in rng.permutation(labels)]

        quantum_predictions, _per_fold = _quantum_oof_predictions(
            rows, shuffled_labels, _N_FOLDS, _SEED
        )

        correct = sum(
            1 for pred, true in zip(quantum_predictions, shuffled_labels, strict=True)
            if pred == true
        )
        accuracy = correct / len(shuffled_labels)

        assert accuracy < 0.60, (
            f"accuracy={accuracy:.3f} con etiquetas barajadas — deberia "
            "colapsar cerca del azar; un valor alto indicaria fuga de datos "
            "en el pipeline (recipe/nota 04 SS5)"
        )
