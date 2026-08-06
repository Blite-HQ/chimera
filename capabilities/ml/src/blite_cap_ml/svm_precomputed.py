"""SVM binario sobre un kernel PRECOMPUTADO (recipe knowledge/quantum/02
SS2.3): el caller entrega la matriz de Gram (por ejemplo desde
`blite.quantum.fidelity_kernel`); esta capability solo corre el dual del SVM
y reporta metricas — accuracy sola esta documentada como insuficiente dado el
desbalance 61/39 (recipe SS2.3 / knowledge/quantum/04 SS6): por eso siempre
se reportan tambien precision/recall/f1/matriz de confusion.
"""

from __future__ import annotations

from typing import Any

# sklearn no publica stubs completos bajo strict — se silencian SOLO los
# reportes de tipos desconocidos de terceros; las firmas propias de este
# modulo siguen bajo strict.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false

_DEFAULT_SEED = 1
_DEFAULT_C = 1.0


def _is_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int | float)


def _validate_matrix(
    raw: Any, name: str, expected_cols: int | None
) -> list[list[float]]:
    if not isinstance(raw, list) or not raw:
        msg = f"SvmPrecomputed: '{name}' (lista no vacia) es requerido"
        raise ValueError(msg)
    width = expected_cols
    validated: list[list[float]] = []
    for i, row in enumerate(raw):
        if not isinstance(row, list) or not row:
            msg = f"SvmPrecomputed: {name}[{i}] debe ser una lista no vacia, no {row!r}"
            raise ValueError(msg)
        if width is None:
            width = len(row)
        elif len(row) != width:
            msg = (
                f"SvmPrecomputed: {name}[{i}] tiene longitud {len(row)}, "
                f"esperada {width}"
            )
            raise ValueError(msg)
        parsed: list[float] = []
        for j, value in enumerate(row):
            if not _is_number(value):
                msg = (
                    f"SvmPrecomputed: {name}[{i}][{j}] debe ser numerico, no {value!r}"
                )
                raise ValueError(msg)
            parsed.append(float(value))
        validated.append(parsed)
    return validated


def _validate_labels(raw: Any, name: str, n_rows: int) -> list[int]:
    if not isinstance(raw, list) or len(raw) != n_rows:
        msg = (
            f"SvmPrecomputed: '{name}' debe ser una lista de longitud "
            f"{n_rows}, no {raw!r}"
        )
        raise ValueError(msg)
    validated: list[int] = []
    for idx, value in enumerate(raw):
        if isinstance(value, bool) or value not in (0, 1):
            msg = f"SvmPrecomputed: {name}[{idx}] debe ser 0 o 1, no {value!r}"
            raise ValueError(msg)
        validated.append(int(value))
    return validated


def _validate_seed(raw: Any) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int):
        msg = f"SvmPrecomputed: seed debe ser entero, no {raw!r}"
        raise ValueError(msg)
    return raw


def _validate_c(raw: Any) -> float:
    if not _is_number(raw) or raw <= 0:
        msg = f"SvmPrecomputed: c debe ser numerico > 0, no {raw!r}"
        raise ValueError(msg)
    return float(raw)


def svm_precomputed(inputs: dict[str, Any]) -> dict[str, Any]:
    """Ajusta `SVC(kernel="precomputed", class_weight="balanced")` sobre
    `kernel_train`/`labels_train` y predice sobre `kernel_test` (la matriz de
    kernel test-vs-train, forma k x m — MISMO orden de columnas que
    `kernel_train`, exigido por la API de scikit-learn para kernels
    precomputados)."""
    import numpy as np
    from sklearn.svm import SVC

    from blite_cap_ml._shared import binary_classification_metrics

    kernel_train = _validate_matrix(inputs.get("kernel_train"), "kernel_train", None)
    m_train = len(kernel_train)
    if any(len(row) != m_train for row in kernel_train):
        msg = "SvmPrecomputed: 'kernel_train' debe ser cuadrada (m x m)"
        raise ValueError(msg)
    labels_train = _validate_labels(inputs.get("labels_train"), "labels_train", m_train)

    kernel_test = _validate_matrix(inputs.get("kernel_test"), "kernel_test", m_train)
    m_test = len(kernel_test)
    labels_test = _validate_labels(inputs.get("labels_test"), "labels_test", m_test)

    seed = _validate_seed(inputs.get("seed", _DEFAULT_SEED))
    c = _validate_c(inputs.get("c", _DEFAULT_C))

    model = SVC(kernel="precomputed", class_weight="balanced", C=c, random_state=seed)
    model.fit(np.array(kernel_train), np.array(labels_train))
    predictions = model.predict(np.array(kernel_test))

    metrics = binary_classification_metrics(labels_test, predictions)
    # dual_coef_/intercept_ are dense for a fitted (non-sparse-input) SVC —
    # the stub's type is a dense/sparse union, np.asarray narrows it back.
    dual_coef = np.asarray(model.dual_coef_)
    intercept = np.asarray(model.intercept_)

    return {
        "predictions": [int(p) for p in predictions],
        "dual_coef": dual_coef.tolist(),
        "intercept": intercept.tolist(),
        "support_indices": [int(i) for i in model.support_],
        **metrics,
    }
