"""Baseline OFICIAL del reto: SVM-RBF bajo validacion cruzada estratificada
de 5 particiones (recipe knowledge/quantum/02 SS3, nota de drift: CV-5 es el
protocolo OFICIAL de comparacion, a diferencia del split unico usado por el
brazo cuantico via `blite.ml.tabular_prep`).

Las predicciones que devuelve son OUT-OF-FOLD (cada fila se predice con un
modelo que NUNCA la vio en train) — precisamente para que sean comparables
PUNTO A PUNTO contra las predicciones de cualquier otro brazo sobre las
MISMAS filas (docs/mejorado/03-research.md R1, capability #4).

McNemar (knowledge/quantum/04-estadistica-evidencia.md SS6): cuando se
suministra `compare_predictions` (predicciones de otro modelo, alineadas
fila a fila con `rows`/`labels`), el output agrega `mcnemar` con los pares
discordantes b/c y el p-valor EXACTO (`scipy.stats.binomtest`, dos colas).
Regla de lenguaje de conclusion (misma nota SS6, ratificada en
docs/specs/generalidad-retos.md SS1): sin significancia estadistica la unica
frase defendible es "el modelo cuantico es COMPETITIVO (delta-accuracy = ...,
McNemar p = ...)" — NUNCA "supera". Esta capability calcula los numeros; la
frase la arma quien consume el output (agente/informe), no este modulo.
"""

from __future__ import annotations

from typing import Any

# sklearn/scipy no publican stubs completos bajo strict — se silencian SOLO
# los reportes de tipos desconocidos de terceros; las firmas propias de este
# modulo siguen bajo strict.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false

_DEFAULT_N_FOLDS = 5
_DEFAULT_SEED = 1
_DEFAULT_C = 1.0
_DEFAULT_GAMMA = "scale"
_VALID_GAMMA_MODES = ("scale", "auto")
_MIN_FOLDS = 2


def _is_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int | float)


def _validate_rows(raw: Any) -> list[list[float]]:
    if not isinstance(raw, list) or not raw:
        msg = "ClassifierBaseline: 'rows' (lista no vacia) es requerido"
        raise ValueError(msg)
    width: int | None = None
    validated: list[list[float]] = []
    for idx, row in enumerate(raw):
        if not isinstance(row, list) or not row:
            msg = f"ClassifierBaseline: rows[{idx}] debe ser una lista no vacia, no {row!r}"
            raise ValueError(msg)
        if width is None:
            width = len(row)
        elif len(row) != width:
            msg = (
                f"ClassifierBaseline: rows[{idx}] tiene longitud {len(row)}, "
                f"esperada {width}"
            )
            raise ValueError(msg)
        parsed: list[float] = []
        for col, value in enumerate(row):
            if value is None:
                parsed.append(float("nan"))
                continue
            if not _is_number(value):
                msg = (
                    f"ClassifierBaseline: rows[{idx}][{col}] debe ser "
                    f"numerico o null, no {value!r}"
                )
                raise ValueError(msg)
            parsed.append(float(value))
        validated.append(parsed)
    return validated


def _validate_binary_list(raw: Any, name: str, n_rows: int) -> list[int]:
    if not isinstance(raw, list) or len(raw) != n_rows:
        msg = (
            f"ClassifierBaseline: '{name}' debe ser una lista de longitud "
            f"{n_rows}, no {raw!r}"
        )
        raise ValueError(msg)
    validated: list[int] = []
    for idx, value in enumerate(raw):
        if isinstance(value, bool) or value not in (0, 1):
            msg = f"ClassifierBaseline: {name}[{idx}] debe ser 0 o 1, no {value!r}"
            raise ValueError(msg)
        validated.append(int(value))
    return validated


def _validate_int_at_least(raw: Any, name: str, minimum: int) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < minimum:
        msg = f"ClassifierBaseline: {name} debe ser entero >= {minimum}, no {raw!r}"
        raise ValueError(msg)
    return raw


def _validate_c(raw: Any) -> float:
    if not _is_number(raw) or raw <= 0:
        msg = f"ClassifierBaseline: c debe ser numerico > 0, no {raw!r}"
        raise ValueError(msg)
    return float(raw)


def _validate_gamma(raw: Any) -> str | float:
    if isinstance(raw, str):
        if raw not in _VALID_GAMMA_MODES:
            msg = (
                f"ClassifierBaseline: gamma string debe ser uno de "
                f"{_VALID_GAMMA_MODES}, no {raw!r}"
            )
            raise ValueError(msg)
        return raw
    if _is_number(raw) and raw > 0:
        return float(raw)
    msg = (
        f"ClassifierBaseline: gamma debe ser 'scale'/'auto' o numerico > 0, "
        f"no {raw!r}"
    )
    raise ValueError(msg)


def _mcnemar(
    predictions: list[int], compare_predictions: list[int], labels: list[int]
) -> dict[str, Any]:
    """b = filas donde ESTE modelo acierta y el otro falla; c = al reves
    (knowledge/quantum/04 SS6). p-valor EXACTO via binomial de dos colas
    sobre min(b, c) ~ Bin(b+c, 1/2) (`scipy.stats.binomtest`) — evita la
    aproximacion chi-cuadrado (invalida cuando b+c es chico, el caso tipico
    de un test set de ablacion)."""
    from scipy.stats import binomtest

    b = 0
    c = 0
    for pred, other, label in zip(predictions, compare_predictions, labels, strict=True):
        own_correct = pred == label
        other_correct = other == label
        if own_correct and not other_correct:
            b += 1
        elif not own_correct and other_correct:
            c += 1

    n = b + c
    p_value = 1.0 if n == 0 else binomtest(min(b, c), n, 0.5, alternative="two-sided").pvalue
    return {"b": b, "c": c, "p_value": float(p_value)}


def classifier_baseline(inputs: dict[str, Any]) -> dict[str, Any]:
    """CV-5 estratificado de `SVC(kernel="rbf", class_weight="balanced")`
    sobre `rows`/`labels` (imputacion de mediana EN-FOLD, fit solo en train
    — misma disciplina anti-fuga que `blite.ml.tabular_prep`). Devuelve
    metricas por fold, metricas agregadas (sobre las predicciones OOF
    concatenadas) y las propias predicciones OOF."""
    import numpy as np
    from sklearn.model_selection import StratifiedKFold
    from sklearn.svm import SVC

    from blite_cap_ml._shared import (
        binary_classification_metrics,
        impute_median_fit_train,
    )

    rows = _validate_rows(inputs.get("rows"))
    n_rows = len(rows)
    labels = _validate_binary_list(inputs.get("labels"), "labels", n_rows)
    n_folds = _validate_int_at_least(
        inputs.get("n_folds", _DEFAULT_N_FOLDS), "n_folds", _MIN_FOLDS
    )
    seed = _validate_int_at_least(inputs.get("seed", _DEFAULT_SEED), "seed", 0)
    c = _validate_c(inputs.get("c", _DEFAULT_C))
    gamma = _validate_gamma(inputs.get("gamma", _DEFAULT_GAMMA))

    compare_raw = inputs.get("compare_predictions")
    compare_predictions = (
        _validate_binary_list(compare_raw, "compare_predictions", n_rows)
        if compare_raw is not None
        else None
    )

    labels_arr = np.array(labels, dtype=int)
    features_arr = np.array(rows, dtype=float)

    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=seed)
    oof_predictions = np.empty(n_rows, dtype=int)
    fold_metrics: list[dict[str, Any]] = []

    for fold_idx, (train_idx, test_idx) in enumerate(skf.split(features_arr, labels_arr)):
        train_raw = features_arr[train_idx]
        test_raw = features_arr[test_idx]
        train_imputed, test_imputed = impute_median_fit_train(train_raw, test_raw)

        # SVC.gamma accepts 'scale'/'auto' OR a positive float at runtime;
        # the installed stub infers `str` from the default value only.
        model = SVC(
            kernel="rbf",
            class_weight="balanced",
            C=c,
            gamma=gamma,  # pyright: ignore[reportArgumentType]
            random_state=seed,
        )
        model.fit(train_imputed, labels_arr[train_idx])
        fold_predictions = model.predict(test_imputed)
        oof_predictions[test_idx] = fold_predictions

        fold_labels = labels_arr[test_idx]
        fold_metrics.append(
            {"fold": fold_idx, **binary_classification_metrics(fold_labels, fold_predictions)}
        )

    aggregate = binary_classification_metrics(labels_arr, oof_predictions)

    result: dict[str, Any] = {
        "n_folds": n_folds,
        "seed": seed,
        "predictions": [int(p) for p in oof_predictions],
        "fold_metrics": fold_metrics,
        "aggregate": aggregate,
    }
    if compare_predictions is not None:
        result["mcnemar"] = _mcnemar(result["predictions"], compare_predictions, labels)
    return result
