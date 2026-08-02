"""Baseline OFICIAL del reto: SVM-RBF bajo validacion cruzada estratificada
de 5 particiones (recipe knowledge/quantum/02 SS3, nota de drift: CV-5 es el
protocolo OFICIAL de comparacion, a diferencia del split unico usado por el
brazo cuantico via `blite.ml.tabular_prep`).

Las predicciones que devuelve son OUT-OF-FOLD (cada fila se predice con un
modelo que NUNCA la vio en train) — precisamente para que sean comparables
PUNTO A PUNTO contra las predicciones de cualquier otro brazo sobre las
MISMAS filas (docs/mejorado/03-research.md R1, capability #4).

**Modo `prepared_folds` (mismo pipeline que el brazo cuantico):** por
default esta capability corre su PROPIO split + imputacion sobre `rows`
crudas ("standalone", protocolo oficial CV-5 sin mas contrato que ese). Pero
comparar un brazo que corre sobre features seleccionadas+escaladas (el
kernel cuantico, via `blite.ml.tabular_prep`) contra un brazo que corre
sobre features CRUDAS sin escalar confunde "que kernel es mejor" con "que
preprocesamiento es mejor" (un RBF con `gamma="scale"` normaliza por la
varianza GLOBAL, no por feature — una sola columna con escala mucho mayor
domina la distancia). El input OPCIONAL `prepared_folds` (mismo shape que
el campo `prepared` que devuelve `tabular_prep`) + `folds` (la asignacion
fila->fold, mismo shape que su campo `folds`) hacen que el SVM-RBF ajuste
EXACTAMENTE sobre esas matrices ya preparadas — el unico grado de libertad
que queda entre los dos brazos es el KERNEL (fidelidad cuantica vs
gaussiano), no el preprocesamiento. Ausentes ambos ⇒ camino standalone
INTACTO (compat total); solo uno de los dos ⇒ error de validacion (deben
viajar juntos, `folds` es lo que permite reensamblar las predicciones
out-of-fold en el orden GLOBAL de `rows`/`labels`).

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


def _validate_prepared_folds(
    raw: Any, n_folds: int
) -> list[dict[str, dict[str, Any]]] | None:
    """Valida el `prepared_folds` OPCIONAL (modo mismo-pipeline, ver
    docstring del modulo): mismo shape que el campo `prepared` de
    `blite.ml.tabular_prep` — una entrada por fold, cada una
    `{"train": {"features", "labels"}, "test": {"features", "labels"}}`.
    Ausente ⇒ `None` (camino standalone intacto)."""
    if raw is None:
        return None
    if not isinstance(raw, list) or len(raw) != n_folds:
        msg = (
            f"ClassifierBaseline: 'prepared_folds' debe ser una lista de "
            f"longitud {n_folds} (uno por fold), no {raw!r}"
        )
        raise ValueError(msg)
    validated: list[dict[str, dict[str, Any]]] = []
    for fold_idx, entry in enumerate(raw):
        if not isinstance(entry, dict) or "train" not in entry or "test" not in entry:
            msg = (
                f"ClassifierBaseline: prepared_folds[{fold_idx}] debe ser "
                "{'train': {...}, 'test': {...}}"
            )
            raise ValueError(msg)
        split: dict[str, dict[str, Any]] = {}
        for part in ("train", "test"):
            block = entry[part]
            if not isinstance(block, dict):
                msg = (
                    f"ClassifierBaseline: prepared_folds[{fold_idx}]['{part}'] "
                    "debe ser un dict con 'features'/'labels'"
                )
                raise ValueError(msg)
            features = _validate_rows(block.get("features"))
            labels = _validate_binary_list(
                block.get("labels"),
                f"prepared_folds[{fold_idx}].{part}.labels",
                len(features),
            )
            split[part] = {"features": features, "labels": labels}
        validated.append(split)
    return validated


def _validate_fold_assignment(raw: Any, n_rows: int, n_folds: int) -> list[int]:
    """Valida `folds` (fila -> indice de fold, mismo shape que el campo
    `folds` de `blite.ml.tabular_prep`) — el mapeo que reensambla las
    predicciones de `prepared_folds` en el orden GLOBAL de `rows`/`labels`."""
    if not isinstance(raw, list) or len(raw) != n_rows:
        msg = f"ClassifierBaseline: 'folds' debe ser una lista de longitud {n_rows}, no {raw!r}"
        raise ValueError(msg)
    validated: list[int] = []
    for idx, value in enumerate(raw):
        if isinstance(value, bool) or not isinstance(value, int) or not (0 <= value < n_folds):
            msg = (
                f"ClassifierBaseline: folds[{idx}] debe ser entero en "
                f"[0, {n_folds}), no {value!r}"
            )
            raise ValueError(msg)
        validated.append(value)
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


def _fit_predict_rbf(
    train_features: Any, train_labels: Any, test_features: Any, *, c: float, gamma: str | float, seed: int
) -> Any:
    """Un SVM-RBF ajustado sobre `(train_features, train_labels)` y
    evaluado sobre `test_features` — el ÚNICO lugar donde este modulo
    construye un `SVC`, compartido por los dos caminos (standalone y
    `prepared_folds`) para que jamas diverjan en hiperparametros."""
    from sklearn.svm import SVC

    # SVC.gamma accepts 'scale'/'auto' OR a positive float at runtime; the
    # installed stub infers `str` from the default value only.
    model = SVC(
        kernel="rbf",
        class_weight="balanced",
        C=c,
        gamma=gamma,  # pyright: ignore[reportArgumentType]
        random_state=seed,
    )
    model.fit(train_features, train_labels)
    return model.predict(test_features)


def _cv_standalone(
    features_arr: Any, labels_arr: Any, *, n_folds: int, seed: int, c: float, gamma: str | float
) -> tuple[Any, list[dict[str, Any]]]:
    """Camino OFICIAL sin contrato adicional (compat total): su PROPIO
    split estratificado + imputacion de mediana EN-FOLD sobre `rows`
    crudas — protocolo CV-5 standalone, intacto."""
    import numpy as np
    from sklearn.model_selection import StratifiedKFold

    from blite_cap_ml._shared import (
        binary_classification_metrics,
        impute_median_fit_train,
    )

    n_rows = features_arr.shape[0]
    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=seed)
    oof_predictions = np.empty(n_rows, dtype=int)
    fold_metrics: list[dict[str, Any]] = []

    for fold_idx, (train_idx, test_idx) in enumerate(skf.split(features_arr, labels_arr)):
        train_raw = features_arr[train_idx]
        test_raw = features_arr[test_idx]
        train_imputed, test_imputed = impute_median_fit_train(train_raw, test_raw)

        fold_predictions = _fit_predict_rbf(
            train_imputed, labels_arr[train_idx], test_imputed, c=c, gamma=gamma, seed=seed
        )
        oof_predictions[test_idx] = fold_predictions

        fold_labels = labels_arr[test_idx]
        fold_metrics.append(
            {"fold": fold_idx, **binary_classification_metrics(fold_labels, fold_predictions)}
        )
    return oof_predictions, fold_metrics


def _cv_over_prepared_folds(
    prepared_folds: list[dict[str, dict[str, Any]]],
    folds: list[int],
    labels_arr: Any,
    *,
    n_rows: int,
    c: float,
    gamma: str | float,
    seed: int,
) -> tuple[Any, list[dict[str, Any]]]:
    """Camino mismo-pipeline (ver docstring del modulo): ajusta el SVM-RBF
    EXACTAMENTE sobre las matrices de `prepared_folds` -- nunca recalcula
    imputacion/split desde `rows`. `folds` reensambla las predicciones en el
    orden GLOBAL de `rows`/`labels`; un desacuerdo entre las labels que
    `prepared_folds` trae y las labels GLOBALES en esas mismas posiciones es
    un error de sincronizacion entre los dos argumentos (fail-loud, nunca
    una metrica silenciosamente mal calculada)."""
    import numpy as np

    from blite_cap_ml._shared import binary_classification_metrics

    oof_predictions = np.empty(n_rows, dtype=int)
    fold_metrics: list[dict[str, Any]] = []

    test_indices_by_fold: dict[int, list[int]] = {}
    for row_idx, fold_idx in enumerate(folds):
        test_indices_by_fold.setdefault(fold_idx, []).append(row_idx)

    for fold_idx, split in enumerate(prepared_folds):
        train_features = np.array(split["train"]["features"], dtype=float)
        train_labels = np.array(split["train"]["labels"], dtype=int)
        test_features = np.array(split["test"]["features"], dtype=float)
        test_labels_declared = split["test"]["labels"]

        test_indices = test_indices_by_fold.get(fold_idx, [])
        expected_test_labels = [int(labels_arr[i]) for i in test_indices]
        if [int(v) for v in test_labels_declared] != expected_test_labels:
            msg = (
                f"ClassifierBaseline: fold {fold_idx} -- prepared_folds"
                "[fold]['test']['labels'] no coincide con labels[] en las "
                "posiciones que 'folds' declara para este fold ('folds' y "
                "'prepared_folds' desincronizados)"
            )
            raise ValueError(msg)

        fold_predictions = _fit_predict_rbf(
            train_features, train_labels, test_features, c=c, gamma=gamma, seed=seed
        )
        if len(test_indices) != len(fold_predictions):
            msg = (
                f"ClassifierBaseline: fold {fold_idx} -- 'folds' declara "
                f"{len(test_indices)} filas de test pero prepared_folds trae "
                f"{len(fold_predictions)}"
            )
            raise ValueError(msg)
        for row_idx, prediction in zip(test_indices, fold_predictions, strict=True):
            oof_predictions[row_idx] = prediction

        fold_metrics.append(
            {
                "fold": fold_idx,
                **binary_classification_metrics(
                    np.array(expected_test_labels, dtype=int), fold_predictions
                ),
            }
        )
    return oof_predictions, fold_metrics


def classifier_baseline(inputs: dict[str, Any]) -> dict[str, Any]:
    """CV-5 estratificado de `SVC(kernel="rbf", class_weight="balanced")`.
    Por default corre su PROPIO split + imputacion de mediana EN-FOLD sobre
    `rows` crudas (protocolo OFICIAL standalone, misma disciplina anti-fuga
    que `blite.ml.tabular_prep`). Si el caller trae `prepared_folds` +
    `folds`, ajusta en cambio sobre esas matrices ya preparadas (modo
    mismo-pipeline — ver docstring del modulo). En ambos casos devuelve
    metricas por fold, metricas agregadas (sobre las predicciones OOF
    concatenadas) y las propias predicciones OOF."""
    import numpy as np

    from blite_cap_ml._shared import binary_classification_metrics

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

    prepared_folds = _validate_prepared_folds(inputs.get("prepared_folds"), n_folds)
    folds_raw = inputs.get("folds")
    if (prepared_folds is None) != (folds_raw is None):
        msg = (
            "ClassifierBaseline: 'prepared_folds' y 'folds' deben venir "
            "JUNTOS (o ninguno) -- 'folds' es lo que reensambla las "
            "predicciones out-of-fold en el orden global (ver docstring "
            "del modulo)"
        )
        raise ValueError(msg)
    folds = (
        _validate_fold_assignment(folds_raw, n_rows, n_folds)
        if folds_raw is not None
        else None
    )

    labels_arr = np.array(labels, dtype=int)
    features_arr = np.array(rows, dtype=float)

    if prepared_folds is not None and folds is not None:
        oof_predictions, fold_metrics = _cv_over_prepared_folds(
            prepared_folds, folds, labels_arr, n_rows=n_rows, c=c, gamma=gamma, seed=seed
        )
    else:
        oof_predictions, fold_metrics = _cv_standalone(
            features_arr, labels_arr, n_folds=n_folds, seed=seed, c=c, gamma=gamma
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
