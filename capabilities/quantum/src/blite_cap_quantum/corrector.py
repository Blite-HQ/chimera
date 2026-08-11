"""Corrector AI-QEM aprendido (V9 — freeze §11, bloque `mitigation.*`).

## Por qué esto y no una capability nueva

El gate de agnosticismo enumera `entry_points(group="blite.capabilities")`,
que lee metadata INSTALADA — una capability nueva no aparece en el registry
sin reinstalar el paquete, y el API en compose resuelve por ese registry. Este
módulo NO agrega un entry point: extiende `blite.quantum.zne` (ya registrado,
`tool.py::ZeroNoiseExtrapolation`) con un `method` alterno. La misma
capability, dos productores del bloque `mitigation.*`:

- `zne-digital` (`blite_cap_quantum.zne`) — extrapolación, no entrena nada;
  `training_digest` viaja en `None` a propósito.
- `ml-rf` / `ml-gbm` (este módulo) — un corrector APRENDIDO; `training_digest`
  es el SHA-256 real de los datos con que se ajustó.

## Honestidad del corpus

El corpus de entrenamiento se genera ACÁ, con una semilla propia
(`TRAIN_SEED`) — nunca toca `knowledge/*/corpus` (congelado; ese corpus no se
re-propone para un uso distinto al sellado). Las matrices QUBO son sintéticas
y pequeñas, simuladas de VERDAD en Aer (mismo camino que `zne.py`, ruido
declarado, jamás inventado). `HOLDOUT_MATRICES` no comparte ninguna instancia
con `TRAIN_MATRICES` (semillas de generación disjuntas por construcción) —
las cifras de mejora que este módulo reporta en sus tests salen del holdout,
nunca de filas que el modelo ya vio.

## El control negativo es el de V4, no uno nuevo

La nota 09 §1.4 y `zne.apparent_improvement` ya establecieron la disciplina:
una mejora solo se publica si sobrevive el control de garbage-folding al
MISMO presupuesto de shots (arXiv:2607.09360). Este módulo no inventa un
control aparte para el corrector: aplica el modelo YA entrenado —nunca
ajustado sobre datos de control— a la curva garbage-folded del propio
holdout, igual que `mitigate_expectation` aplica la MISMA extrapolación a las
dos curvas. Si el corrector "mejora" también sobre ruido sin estructura, la
mejora es un artefacto del método, no de la física.

## Determinismo

Toda la generación de corpus y el ajuste del modelo cuelgan de `TRAIN_SEED`.
La rama LEGÍTIMA es bit-estable (mismo supuesto que documenta `zne.py`), así
que dos corridas producen las mismas matrices, las mismas curvas de
entrenamiento, el mismo `training_digest` y el mismo modelo (mismos
hiperparámetros + `random_state` fijo + misma versión de sklearn/xgboost,
pinneada por el lock del workspace).

## Tamaño del corpus — declarado, no escondido

`TRAIN_MATRICES`/`HOLDOUT_MATRICES` son deliberadamente chicos (circuitos de
`_N_QUBITS` qubits, un puñado de instancias): esto es una prueba de concepto
de que el mecanismo AI-QEM funciona de punta a punta con separación honesta,
NO una afirmación de que generaliza a instancias grandes — un corpus de este
tamaño no lo permite, y decirlo es preferible a un número inflado.
"""

from __future__ import annotations

# sklearn/xgboost no publican stubs completos — se silencian SOLO los
# reportes de tipos desconocidos de terceros (mismo criterio puntual que
# `zne.py`/`qaoa.py` usan para Qiskit); las firmas propias siguen bajo strict.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
import hashlib
import importlib.util
import json
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from typing import Any

from blite_cap_quantum.qaoa import prepare_circuit
from blite_cap_quantum.zne import (
    BASELINE_UNMITIGATED,
    EXTRAPOLATOR_RICHARDSON,
    apparent_improvement,
    build_noise_model,
    extrapolate,
    fold_garbage,
    fold_global,
    measured_curve,
    noise_spec,
)

ML_METHOD_RF = "ml-rf"
ML_METHOD_GBM = "ml-gbm"
ML_METHODS = (ML_METHOD_RF, ML_METHOD_GBM)
"""Los dos métodos con productor en este módulo, del enum congelado (freeze
§11: `{ml-rf, ml-gbm, ml-mlp, zne-digital, none}`). `ml-mlp` queda SIN
productor — no hay corpus para justificar una tercera dependencia pesada
(torch/keras) cuando bagging (`ml-rf`) y boosting (`ml-gbm`) ya cubren dos
regímenes distintos con lo que el repo ya tiene instalado."""

PRIMARY_METHOD = ML_METHOD_RF
"""El método que `blite.runtime.ablation.build_arms` declara para el brazo
`mitigated`. Con ~30 muestras de entrenamiento un bosque aleatorio generaliza
mejor que boosting (que sobreajusta más rápido con tan poco corpus) — ver el
reporte de la tarea V9 para la comparación empírica en el holdout."""

TRAIN_SEED = 9001
"""Semilla única de TODO el pipeline: genera el corpus, arranca cada
`prepare_circuit` y fija el `random_state` del modelo. Determinismo total: la
misma semilla en cualquier máquina produce las mismas matrices, las mismas
curvas legítimas (bit-estables, igual que en `zne.py`) y el mismo modelo."""

_N_QUBITS = 3
_LAYERS = (1, 2)
_NOISE_CONFIGS: tuple[dict[str, float], ...] = (
    {"one_qubit": 0.002, "two_qubit": 0.02},
    {"one_qubit": 0.01, "two_qubit": 0.05},
)
_SAMPLE_SEEDS = (TRAIN_SEED + 1, TRAIN_SEED + 2)
_SCALES = (1, 3, 5)
_SHOTS = 256

_DETERMINISTIC_OPT_LEVEL = 0
"""`transpile()` por defecto (nivel 2, lo que usa `zne.mitigate_expectation`
vía `qaoa.sample_counts`) usa layout/routing estocástico (SABRE) que NO es
perfectamente reproducible entre llamadas con el MISMO `seed_transpiler` —
verificado en la exploración de esta tarea: hasta 2 circuitos compilados
distintos en 8 llamadas idénticas sobre el MISMO circuito plegado. El nivel 0
evita esas pasadas y es bit-estable (verificado: 1 circuito distinto en 8
llamadas). El corrector NO puede tolerar esa varianza — dos filas del corpus
medidas con el MISMO circuito/ruido/seed tienen que dar el MISMO número, o
`training_digest` no sería reproducible. `zne.py` no cambia: sigue sin pasar
este parámetro, así que el brazo `zne` mide exactamente como medía antes."""

FEATURE_NAMES = (
    "unmitigated_energy",
    "energy_scale_3",
    "energy_scale_5",
    "richardson_energy",
    "one_qubit_noise",
    "two_qubit_noise",
    "layers",
    "n_qubits",
)
"""El vector que ve el modelo: la curva cruda + lo que ZNE YA sabe
(Richardson) + el contexto del experimento. El corrector parte de la
extrapolación clásica como una feature más, no la descarta — con un corpus
de este tamaño, redescubrir desde cero lo que Richardson ya calcula exacto
sería tirar información a la basura."""

_RICHARDSON_INDEX = FEATURE_NAMES.index("richardson_energy")
"""El modelo NO predice el ⟨C⟩ ideal absoluto — predice el RESIDUO sobre
Richardson (`target − richardson_energy`) y `correct_expectation` lo suma de
vuelta. Probado en la exploración de esta tarea: predecir el valor absoluto
cruzando instancias (matrices QUBO con escalas de energía completamente
distintas) es un problema mucho más difícil que corregir el sesgo sistemático
de la extrapolación bajo más ruido — con ~30 muestras, la versión absoluta
sobreajustaba brutalmente (mejora aparente media en holdout de −4.1, la
versión residual la deja en −0.05 y hace que el corrector sobreviva su propio
control ~79 % de las veces en vez de 33 %). Ver el reporte de la tarea V9
para la comparación completa, incluida la cifra contra el baseline ZNE."""


def _synthetic_matrix(seed: int, n: int = _N_QUBITS) -> list[list[int]]:
    """QUBO simétrica entera pequeña, generada con una semilla propia.

    NUNCA `knowledge/*/corpus` (congelado, con digest embebido — ese corpus
    no se re-propone para un uso que no sea el sellado). El corrector
    necesita generar tantas instancias como haga falta para una separación
    train/holdout honesta, así que trae las suyas.
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        matrix[i][i] = int(rng.integers(0, 5))
        for j in range(i + 1, n):
            peso = int(rng.integers(-4, 5))
            matrix[i][j] = peso
            matrix[j][i] = peso
    return matrix


TRAIN_MATRICES: tuple[list[list[int]], ...] = tuple(
    _synthetic_matrix(TRAIN_SEED + i) for i in range(4)
)
HOLDOUT_MATRICES: tuple[list[list[int]], ...] = tuple(
    _synthetic_matrix(TRAIN_SEED + 100 + i) for i in range(3)
)
"""Separación honesta por CONSTRUCCIÓN: los rangos de semilla de generación
(`TRAIN_SEED+0..3` contra `TRAIN_SEED+100..102`) son disjuntos, así que
ninguna matriz de holdout puede coincidir con una de entrenamiento salvo una
colisión de generador — `test_corrector.py` lo comprueba en vivo, no lo da
por sentado."""


def producer_available(method: str = PRIMARY_METHOD) -> bool:
    """Sonda liviana (`find_spec`, NUNCA importa) de la dependencia óptima
    que `method` necesita. `blite.runtime.ablation.build_arms` no puede
    llamar a esta función (ADR-008: el engine no importa `blite_cap_*`) —
    replica la misma sonda localmente; este es el productor de verdad que
    esa réplica describe."""
    modulo = "sklearn" if method == ML_METHOD_RF else "xgboost"
    return importlib.util.find_spec(modulo) is not None


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(payload: Any) -> str:
    """SHA-256 sobre JSON canónico plano — misma regla que `zne._digest`."""
    return hashlib.sha256(_canonical(payload).encode()).hexdigest()


def _features(
    curve_values: Sequence[float],
    *,
    noise_cfg: dict[str, float],
    layers: int,
    n_qubits: int,
) -> list[float]:
    richardson = extrapolate(
        _SCALES, list(curve_values), method=EXTRAPOLATOR_RICHARDSON
    )
    return [
        float(curve_values[0]),
        float(curve_values[1]),
        float(curve_values[2]),
        float(richardson),
        float(noise_cfg["one_qubit"]),
        float(noise_cfg["two_qubit"]),
        float(layers),
        float(n_qubits),
    ]


@dataclass(frozen=True)
class _Curve:
    """Una medición: la curva legítima Y su control de costo igual, del
    MISMO circuito y el MISMO ruido — nunca dos experimentos distintos."""

    ideal: float
    legit: tuple[float, ...]
    garbage: tuple[float, ...]
    noise_cfg: dict[str, float]
    layers: int
    n_qubits: int


def _measure(
    matrix: list[list[int]],
    *,
    layers: int,
    noise_cfg: dict[str, float],
    sample_seed: int,
) -> _Curve:
    preparation = prepare_circuit(matrix, layers=layers, seed=TRAIN_SEED, optimize=True)
    noise = noise_spec(**noise_cfg)
    noise_model = build_noise_model(noise)

    def _garbage_fold(circuito: Any, escala: int) -> Any:
        return fold_garbage(circuito, escala, seed=sample_seed)

    legit = measured_curve(
        preparation.circuit,
        preparation.matrix,
        scales=_SCALES,
        fold=fold_global,
        seed=sample_seed,
        shots=_SHOTS,
        noise_model=noise_model,
        optimization_level=_DETERMINISTIC_OPT_LEVEL,
    )
    garbage = measured_curve(
        preparation.circuit,
        preparation.matrix,
        scales=_SCALES,
        fold=_garbage_fold,
        seed=sample_seed,
        shots=_SHOTS,
        noise_model=noise_model,
        optimization_level=_DETERMINISTIC_OPT_LEVEL,
    )
    return _Curve(
        ideal=preparation.expected_energy,
        legit=tuple(legit),
        garbage=tuple(garbage),
        noise_cfg=noise_cfg,
        layers=layers,
        n_qubits=len(matrix),
    )


@dataclass(frozen=True)
class _Dataset:
    features: tuple[tuple[float, ...], ...]
    targets: tuple[float, ...]
    """El ideal ⟨C⟩ exacto (statevector) de cada fila — target de
    entrenamiento y, para el holdout, la vara contra la que se mide la
    mejora."""
    garbage_features: tuple[tuple[float, ...], ...]
    garbage_unmitigated: tuple[float, ...]
    unmitigated: tuple[float, ...]


def _build_dataset(matrices: Sequence[list[list[int]]]) -> _Dataset:
    features: list[tuple[float, ...]] = []
    targets: list[float] = []
    garbage_features: list[tuple[float, ...]] = []
    garbage_unmitigated: list[float] = []
    unmitigated: list[float] = []
    for matrix in matrices:
        for layers in _LAYERS:
            for noise_cfg in _NOISE_CONFIGS:
                for sample_seed in _SAMPLE_SEEDS:
                    curve = _measure(
                        matrix,
                        layers=layers,
                        noise_cfg=noise_cfg,
                        sample_seed=sample_seed,
                    )
                    features.append(
                        tuple(
                            _features(
                                curve.legit,
                                noise_cfg=noise_cfg,
                                layers=layers,
                                n_qubits=curve.n_qubits,
                            )
                        )
                    )
                    targets.append(curve.ideal)
                    garbage_features.append(
                        tuple(
                            _features(
                                curve.garbage,
                                noise_cfg=noise_cfg,
                                layers=layers,
                                n_qubits=curve.n_qubits,
                            )
                        )
                    )
                    garbage_unmitigated.append(curve.garbage[0])
                    unmitigated.append(curve.legit[0])
    return _Dataset(
        features=tuple(features),
        targets=tuple(targets),
        garbage_features=tuple(garbage_features),
        garbage_unmitigated=tuple(garbage_unmitigated),
        unmitigated=tuple(unmitigated),
    )


def training_digest_of(dataset: _Dataset) -> str:
    """SHA-256 REAL de las features+targets con que se ajusta el modelo —
    nunca un placeholder. Estable entre corridas porque la rama legítima
    (la única que entra acá — el control jamás se entrena, ver el docstring
    del módulo) es bit-estable con `TRAIN_SEED` pinneada."""
    payload = {
        "feature_names": list(FEATURE_NAMES),
        "features": [list(row) for row in dataset.features],
        "targets": list(dataset.targets),
        "train_seed": TRAIN_SEED,
    }
    return _digest(payload)


def _hyperparams(method: str) -> dict[str, Any]:
    if method == ML_METHOD_RF:
        return {"n_estimators": 200, "max_depth": 4, "random_state": TRAIN_SEED}
    if method == ML_METHOD_GBM:
        return {
            "n_estimators": 200,
            "max_depth": 3,
            "learning_rate": 0.05,
            "random_state": TRAIN_SEED,
        }
    msg = f"method debe ser uno de {ML_METHODS}, no {method!r}"
    raise ValueError(msg)


def _residual_targets(dataset: _Dataset) -> list[float]:
    """`target − richardson_energy` por fila — lo que el modelo aprende de
    verdad (ver `_RICHARDSON_INDEX`)."""
    return [
        target - features[_RICHARDSON_INDEX]
        for target, features in zip(dataset.targets, dataset.features, strict=True)
    ]


def _fit(method: str, dataset: _Dataset) -> Any:
    hyperparams = _hyperparams(method)
    x = [list(row) for row in dataset.features]
    y = _residual_targets(dataset)
    if method == ML_METHOD_RF:
        from sklearn.ensemble import RandomForestRegressor

        model = RandomForestRegressor(**hyperparams)
    else:
        from xgboost import XGBRegressor

        model = XGBRegressor(**hyperparams)
    model.fit(x, y)
    return model


@cache
def _trained(method: str) -> tuple[Any, str, str]:
    """(modelo, training_digest, model_digest) — cacheado por PROCESO: dos
    invocaciones del mismo método en el mismo proceso reusan el ajuste; dos
    procesos distintos llegan al MISMO resultado igual (mismo `TRAIN_SEED`,
    mismo corpus, misma librería pinneada por el lock)."""
    if method not in ML_METHODS:
        msg = f"method debe ser uno de {ML_METHODS}, no {method!r}"
        raise ValueError(msg)
    dataset = _build_dataset(TRAIN_MATRICES)
    digest_entrenamiento = training_digest_of(dataset)
    model = _fit(method, dataset)
    receta = {
        "method": method,
        "hyperparams": _hyperparams(method),
        "training_digest": digest_entrenamiento,
    }
    return model, digest_entrenamiento, _digest(receta)


def _mitigation_block(
    *, method: str, training_digest: str, model_digest: str, noise: dict[str, Any]
) -> dict[str, Any]:
    """El bloque `mitigation.*` del freeze §11 para un corrector APRENDIDO —
    misma forma que `zne.mitigation_block`, `training_digest` REAL en vez de
    `None` (acá es donde ese `None` explícito de `zne.py` deja de aplicar)."""
    return {
        "method": method,
        "model_digest": model_digest,
        "training_digest": training_digest,
        "noise_model_digest": _digest(noise),
        "baseline": BASELINE_UNMITIGATED,
    }


def correct_expectation(  # noqa: PLR0913 — misma superficie que `zne.mitigate_expectation`, que espeja
    raw_matrix: Any,
    *,
    method: str = PRIMARY_METHOD,
    layers: int = 1,
    seed: int = 1,
    optimize: bool = True,
    one_qubit_noise: float = 0.002,
    two_qubit_noise: float = 0.02,
    shots: int = 2048,
) -> dict[str, Any]:
    """⟨C⟩ corregido por un modelo APRENDIDO, con el MISMO control negativo
    de costo igual que `zne.mitigate_expectation` — misma forma de salida
    (freeze §11), así que `blite.runtime.ablation.mitigated_energy_of` lee
    este resultado sin saber que no es ZNE.

    El modelo se entrena UNA vez por proceso (`_trained`, cacheado) sobre
    `TRAIN_MATRICES` — nunca sobre la instancia que este llamado está
    corrigiendo, así que ajustar y evaluar jamás comparten fila.
    """
    if method not in ML_METHODS:
        msg = f"method debe ser uno de {ML_METHODS}, no {method!r}"
        raise ValueError(msg)

    model, training_digest_value, model_digest = _trained(method)

    preparation = prepare_circuit(
        raw_matrix, layers=layers, seed=seed, optimize=optimize
    )
    noise_cfg = {
        "one_qubit": float(one_qubit_noise),
        "two_qubit": float(two_qubit_noise),
    }
    noise = noise_spec(**noise_cfg)
    noise_model = build_noise_model(noise)

    def _garbage_fold(circuito: Any, escala: int) -> Any:
        return fold_garbage(circuito, escala, seed=seed)

    legit = measured_curve(
        preparation.circuit,
        preparation.matrix,
        scales=_SCALES,
        fold=fold_global,
        seed=seed,
        shots=shots,
        noise_model=noise_model,
        optimization_level=_DETERMINISTIC_OPT_LEVEL,
    )
    garbage = measured_curve(
        preparation.circuit,
        preparation.matrix,
        scales=_SCALES,
        fold=_garbage_fold,
        seed=seed,
        shots=shots,
        noise_model=noise_model,
        optimization_level=_DETERMINISTIC_OPT_LEVEL,
    )

    n_qubits = len(preparation.matrix)
    legit_features = _features(
        legit, noise_cfg=noise_cfg, layers=layers, n_qubits=n_qubits
    )
    garbage_features = _features(
        garbage, noise_cfg=noise_cfg, layers=layers, n_qubits=n_qubits
    )

    # El modelo predice el RESIDUO sobre Richardson (`_RICHARDSON_INDEX`) —
    # se suma de vuelta acá, nunca dentro del modelo, para que el residuo
    # digerido en `training_digest_of` sea recomputable por un tercero desde
    # las features+targets publicados sin adivinar esta convención. `model`
    # es `Any` (viene de `_trained`, cuya firma no elige entre sklearn/
    # xgboost) — no hace falta `cast`, ya lo es.
    predicho = legit_features[_RICHARDSON_INDEX] + float(
        model.predict([legit_features])[0]
    )
    predicho_control = garbage_features[_RICHARDSON_INDEX] + float(
        model.predict([garbage_features])[0]
    )

    ideal = preparation.expected_energy
    crudo = legit[0]
    mejora = apparent_improvement(ideal=ideal, unmitigated=crudo, mitigated=predicho)
    mejora_control = apparent_improvement(
        ideal=ideal, unmitigated=garbage[0], mitigated=predicho_control
    )

    return {
        "ideal_energy": ideal,
        "unmitigated_energy": crudo,
        "mitigated_energy": predicho,
        "scaled_energies": [
            {"scale_factor": escala, "energy": energia}
            for escala, energia in zip(_SCALES, legit, strict=True)
        ],
        "improvement": mejora,
        "negative_control": {
            "kind": "garbage-folding",
            "reference": "arXiv:2607.09360",
            "unmitigated_energy": garbage[0],
            "mitigated_energy": predicho_control,
            "improvement": mejora_control,
        },
        "improvement_survives_control": mejora > mejora_control,
        "mitigation": _mitigation_block(
            method=method,
            training_digest=training_digest_value,
            model_digest=model_digest,
            noise=noise,
        ),
        "noise": noise,
        "angles": preparation.angles,
        "layers": layers,
        "seed": seed,
        "shots": shots,
    }
