"""Preparacion tabular anti-fuga para clasificacion binaria por kernel
(recipe knowledge/quantum/02-recetario-formulacion-por-reto.md SS2.1).

Orden del pipeline (el orden ES el contrato anti-fuga):

    asignacion de folds estratificados (SOLO labels + seed)
    -> por fold: imputar mediana (fit train) -> seleccionar top-k features por
       importancia de RandomForest (fit train) -> escalar a [0, pi] (fit train)
    -> transform aplicado a train Y test

**Por que la asignacion de folds va PRIMERO y depende SOLO de labels+seed:**
es lo que hace que el sello por compromiso previo (docs/specs/generalidad-
retos.md SS4, Dwork et al. 2015) sea significativo — si el fold dependiera de
los VALORES de las features, el `folds_digest` comprometido en el plan ANTES
de entrenar no significaria nada (alguien podria recomputar folds distintos
con datos distintos y decir que es "el mismo split"). `StratifiedKFold` de
scikit-learn en efecto solo mira `y` (y el largo de `X` para validar formas)
— nunca los VALORES de `X` — por eso basta pasarle un array dummy del largo
correcto como `X`.

**Por que se escala a [0, pi] y no a [0, 2*pi]:** con angle embedding,
RY(x)|0> tiene <Z> = cos(x), y cos es inyectiva SOLO en [0, pi]. Escalar a
[0, 2*pi] haria que x y 2*pi - x produzcan el MISMO <Z> — dos valores de
feature genuinamente distintos colisionando en el mismo estado cuantico.
[0, pi] es el intervalo mas grande donde el encoding sigue siendo una
biyeccion (recipe SS2.1).
"""

from __future__ import annotations

from typing import Any

# sklearn no publica stubs completos bajo strict — se silencian SOLO los
# reportes de tipos desconocidos de terceros; las firmas propias de este
# modulo siguen bajo strict.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false

_DEFAULT_N_FOLDS = 5
_DEFAULT_SEED = 1
_DEFAULT_N_FEATURES = 4
_MIN_FOLDS = 2


def _is_number(value: Any) -> bool:
    """True si `value` es int/float real — rechaza bool (subclase de int)."""
    return not isinstance(value, bool) and isinstance(value, int | float)


def _validate_rows(raw: Any) -> list[list[float]]:
    if not isinstance(raw, list) or not raw:
        msg = "TabularPrep: 'rows' (lista no vacia) es requerido"
        raise ValueError(msg)
    width: int | None = None
    validated: list[list[float]] = []
    for idx, row in enumerate(raw):
        if not isinstance(row, list) or not row:
            msg = f"TabularPrep: rows[{idx}] debe ser una lista no vacia, no {row!r}"
            raise ValueError(msg)
        if width is None:
            width = len(row)
        elif len(row) != width:
            msg = (
                f"TabularPrep: rows[{idx}] tiene longitud {len(row)}, "
                f"esperada {width} (todas las filas deben coincidir)"
            )
            raise ValueError(msg)
        parsed: list[float] = []
        for col, value in enumerate(row):
            if value is None:
                parsed.append(float("nan"))
                continue
            if not _is_number(value):
                msg = (
                    f"TabularPrep: rows[{idx}][{col}] debe ser numerico o "
                    f"null, no {value!r}"
                )
                raise ValueError(msg)
            parsed.append(float(value))
        validated.append(parsed)
    return validated


def _validate_labels(raw: Any, n_rows: int) -> list[int]:
    if not isinstance(raw, list) or len(raw) != n_rows:
        msg = (
            f"TabularPrep: 'labels' debe ser una lista de longitud {n_rows}, no {raw!r}"
        )
        raise ValueError(msg)
    validated: list[int] = []
    for idx, value in enumerate(raw):
        if isinstance(value, bool) or value not in (0, 1):
            msg = f"TabularPrep: labels[{idx}] debe ser 0 o 1, no {value!r}"
            raise ValueError(msg)
        validated.append(int(value))
    return validated


def _validate_int_at_least(raw: Any, name: str, minimum: int) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < minimum:
        msg = f"TabularPrep: {name} debe ser entero >= {minimum}, no {raw!r}"
        raise ValueError(msg)
    return raw


def tabular_prep(inputs: dict[str, Any]) -> dict[str, Any]:
    """Corre el pipeline anti-fuga completo y devuelve, por fold, las
    matrices de features preparadas (imputadas, top-k seleccionadas y
    escaladas a [0, pi]) junto con la asignacion de folds (ver docstring del
    modulo para el porque de cada paso y su orden)."""
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import StratifiedKFold
    from sklearn.preprocessing import MinMaxScaler

    from blite_cap_ml._shared import impute_median_fit_train

    rows = _validate_rows(inputs.get("rows"))
    n_rows = len(rows)
    labels = _validate_labels(inputs.get("labels"), n_rows)
    n_folds = _validate_int_at_least(
        inputs.get("n_folds", _DEFAULT_N_FOLDS), "n_folds", _MIN_FOLDS
    )
    seed = _validate_int_at_least(inputs.get("seed", _DEFAULT_SEED), "seed", 0)
    n_raw_features = len(rows[0])
    n_features = _validate_int_at_least(
        inputs.get("n_features", _DEFAULT_N_FEATURES), "n_features", 1
    )
    if n_features > n_raw_features:
        msg = (
            f"TabularPrep: n_features={n_features} excede el numero de "
            f"columnas crudas ({n_raw_features})"
        )
        raise ValueError(msg)

    labels_arr = np.array(labels, dtype=int)
    features_arr = np.array(rows, dtype=float)

    # La asignacion de folds depende SOLO de labels+seed (ver docstring del
    # modulo) — el `X` que se le pasa a `.split` es un dummy, nunca las
    # features reales.
    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=seed)
    dummy_x = np.zeros((n_rows, 1))
    splits = list(skf.split(dummy_x, labels_arr))

    folds = np.empty(n_rows, dtype=int)
    for fold_idx, (_train_idx, test_idx) in enumerate(splits):
        folds[test_idx] = fold_idx

    feature_indices: list[list[int]] = []
    prepared: list[dict[str, Any]] = []
    fold_sizes: list[dict[str, int]] = []

    for train_idx, test_idx in splits:
        train_raw = features_arr[train_idx]
        test_raw = features_arr[test_idx]

        # 1. imputar mediana — fit SOLO en train
        train_imputed, test_imputed = impute_median_fit_train(train_raw, test_raw)

        # 2. seleccionar top-n_features por importancia de RandomForest —
        #    fit SOLO en train
        forest = RandomForestClassifier(random_state=seed)
        forest.fit(train_imputed, labels_arr[train_idx])
        ranked = np.argsort(forest.feature_importances_)[::-1][:n_features]
        selected = sorted(int(i) for i in ranked)
        feature_indices.append(selected)

        train_selected = train_imputed[:, selected]
        test_selected = test_imputed[:, selected]

        # 3. escalar a [0, pi] — fit SOLO en train (ver docstring del modulo)
        scaler = MinMaxScaler(feature_range=(0.0, float(np.pi)))
        train_scaled = scaler.fit_transform(train_selected)
        test_scaled = (
            scaler.transform(test_selected) if test_selected.shape[0] else test_selected
        )

        prepared.append(
            {
                "train": {
                    "features": train_scaled.tolist(),
                    "labels": labels_arr[train_idx].tolist(),
                },
                "test": {
                    "features": test_scaled.tolist(),
                    "labels": labels_arr[test_idx].tolist(),
                },
            }
        )
        fold_sizes.append({"train": int(len(train_idx)), "test": int(len(test_idx))})

    return {
        "folds": folds.tolist(),
        "n_folds": n_folds,
        "seed": seed,
        "feature_indices": feature_indices,
        "prepared": prepared,
        "fold_sizes": fold_sizes,
    }
