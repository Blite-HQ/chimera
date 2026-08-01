"""Helpers internos compartidos por los modulos de `blite_cap_ml` (NO es
superficie publica de la capability — ADR-029 rige manifests, no helpers
privados).

- `impute_median_fit_train`: `tabular_prep` y `classifier_baseline` necesitan
  EXACTAMENTE la misma disciplina anti-fuga (recipe KB2-02 SS2.1): imputar la
  mediana ajustada SOLO en train, nunca en test.
- `binary_classification_metrics`: `svm_precomputed` y `classifier_baseline`
  reportan el MISMO set de metricas (accuracy sola es insuficiente bajo el
  desbalance 61/39 — recipe SS2.3) con la misma convencion `zero_division=0`
  (un fold sin positivos predichos reporta 0, no un warning). `zero_division`
  acepta 0/1 en scikit-learn en tiempo de ejecucion, pero el stub instalado
  solo anota `str` — de ahi el `pyright: ignore` puntual, centralizado aqui
  en vez de repetido en cada call site.
"""

from __future__ import annotations

from typing import Any, cast

import numpy as np

# sklearn no publica stubs completos bajo strict — se silencian SOLO los
# reportes de tipos desconocidos de terceros; las firmas propias de este
# modulo siguen bajo strict.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false


def impute_median_fit_train(
    train: np.ndarray, test: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Imputa la mediana columna a columna; el estimador se ajusta SOLO con
    `train`. `test` solo recibe `transform` — jamas contribuye al estadistico
    (disciplina anti-fuga, recipe KB2-02 SS2.1: "todo fit ocurre dentro del
    fold de train").
    """
    from sklearn.impute import SimpleImputer

    # SimpleImputer's stub return type is a broad dense/sparse union (sparse
    # only happens on sparse INPUT, never the case here — `train`/`test` are
    # always dense `np.ndarray`) — cast narrows back to what actually comes
    # out at runtime for this capability's inputs.
    imputer = SimpleImputer(strategy="median")
    train_imputed = cast("np.ndarray", imputer.fit_transform(train))
    test_imputed = cast("np.ndarray", imputer.transform(test)) if test.shape[0] else test
    return train_imputed, test_imputed


def binary_classification_metrics(y_true: Any, y_pred: Any) -> dict[str, Any]:
    """accuracy/precision/recall/f1/confusion_matrix (labels fijos [0, 1])
    — el set completo que la recipe SS2.3 exige porque accuracy sola miente
    bajo desbalance de clases."""
    from sklearn.metrics import (
        accuracy_score,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
    )

    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(
            precision_score(y_true, y_pred, zero_division=0)  # pyright: ignore[reportArgumentType]
        ),
        "recall": float(
            recall_score(y_true, y_pred, zero_division=0)  # pyright: ignore[reportArgumentType]
        ),
        "f1": float(
            f1_score(y_true, y_pred, zero_division=0)  # pyright: ignore[reportArgumentType]
        ),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
    }
