"""ZNE digital propio — folding unitario + extrapolación a ruido cero (V4/M6).

`knowledge/quantum/09` §1.2/§2: Temme–Bravyi–Gambetta (PRL 119, 180509) y
Li–Benjamin (PRX 7, 021050); la versión DIGITAL por unitary folding
(arXiv:2005.10921) no exige control de pulsos — se corre el circuito a
factores de ruido amplificado y se extrapola a λ=0.

**Por qué implementación propia y no Mitiq:** Mitiq es GPL-3.0 y este repo se
distribuye MIT (nota 09 §3). Mitiq entra como dependencia OPCIONAL del harness
de benchmarks para validar este código contra una referencia; jamás como
dependencia del engine ni vendorizada.

## El folding no puede cambiar el resultado ideal

`C (C†C)^k` es la MISMA unitaria que `C` — matemáticamente idéntica, con
(2k+1) veces las compuertas. Eso es lo que hace legítima la extrapolación: los
puntos λ=1,3,5 miden EL MISMO observable bajo cada vez más ruido, no tres
circuitos distintos. Si el plegado alterara el ideal, el valor extrapolado no
describiría nada.

## La advertencia que este módulo toma en serio

arXiv:2607.09360 (Köster & Mauerer, 2026-07-10) demuestra que ZNE-Richardson
produce **mejoras artefactuales**: cuando la amplificación supera la señal
útil, la extrapolación colapsa a un reescalado fijo de una medición ruidosa y
"mejora" sin física detrás — su control negativo de garbage-folding, sobre
circuitos SIN señal alguna, mostró mejoras aparentes MAYORES que los métodos
legítimos. Por eso `apparent_improvement` está acá y no en un test: la mejora
de una corrida solo significa algo comparada contra la del control negativo al
MISMO presupuesto (ver `mitigate_expectation`).
"""

from __future__ import annotations

# Qiskit no publica stubs completos — se silencian SOLO los reportes de tipos
# desconocidos de terceros; las firmas propias siguen bajo strict.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
import hashlib
import json
from collections.abc import Sequence
from typing import Any

MITIGATION_METHOD = "zne-digital"
"""Valor de `mitigation.method` (freeze §11). El enum del contrato es
{`ml-rf`, `ml-gbm`, `ml-mlp`, `zne-digital`, `none`} — este módulo es el
baseline NO-ML, el que el corrector aprendido (V9) tiene que batir en costo."""

BASELINE_UNMITIGATED = "unmitigated-lambda-1"
"""`mitigation.baseline`: contra qué se comparó. La medición cruda a λ=1 es el
único baseline que se mide en la MISMA corrida, con el mismo ruido y el mismo
presupuesto de shots — comparar contra otra corrida sería comparar dos ruidos."""

EXTRAPOLATOR_LINEAR = "linear"
"""Ajuste de mínimos cuadrados de grado 1 evaluado en λ=0 — robusto al ruido
de muestreo, sesgado si la dependencia en λ tiene curvatura real."""
EXTRAPOLATOR_RICHARDSON = "richardson"
"""Interpolación polinómica EXACTA por los n puntos, evaluada en λ=0 — sin
sesgo de método si el ruido es polinómico de grado n−1, pero amplifica el
ruido de muestreo (es justo el régimen donde 2607.09360 ve artefactos)."""

EXTRAPOLATORS = (EXTRAPOLATOR_LINEAR, EXTRAPOLATOR_RICHARDSON)

DEFAULT_SCALE_FACTORS = (1, 3, 5)
"""Impares por construcción: el folding global sube la profundidad de a 2k+1."""

FOLDING_GLOBAL = "global"
"""`C (C†C)^k` — el circuito entero. Folding local (por compuerta) permite
factores no enteros; no está acá porque no hace falta para λ ∈ {1,3,5} y una
opción sin uso es superficie sin dueño."""


def _validated_scales(scale_factors: Sequence[int]) -> tuple[int, ...]:
    if len(scale_factors) < 2:
        msg = (
            "la extrapolación necesita al menos dos factores de escala: con un "
            "punto no hay pendiente que estimar, y devolver la medición cruda "
            "llamándola mitigada sería solo renombrarla"
        )
        raise ValueError(msg)
    if len(set(scale_factors)) != len(scale_factors):
        msg = f"los factores de escala deben ser distintos: {list(scale_factors)}"
        raise ValueError(msg)
    return tuple(int(s) for s in scale_factors)


def _linear_weights(scales: tuple[int, ...]) -> tuple[float, ...]:
    """Pesos del ajuste de grado 1 evaluado en λ=0 (mínimos cuadrados).

    a = ȳ − b·λ̄ con b la pendiente OLS ⇒ a = Σ wᵢ yᵢ con
    wᵢ = 1/n − λ̄(λᵢ − λ̄)/Σ(λⱼ − λ̄)².
    """
    n = len(scales)
    media = sum(scales) / n
    varianza = sum((s - media) ** 2 for s in scales)
    if varianza == 0.0:  # pragma: no cover — `_validated_scales` ya exige distintos
        msg = "todos los factores de escala son iguales: no hay pendiente"
        raise ValueError(msg)
    return tuple(1.0 / n - media * (s - media) / varianza for s in scales)


def _richardson_weights(scales: tuple[int, ...]) -> tuple[float, ...]:
    """Pesos de Lagrange evaluados en λ=0: wᵢ = Π_{j≠i} λⱼ/(λⱼ − λᵢ)."""
    pesos: list[float] = []
    for i, escala_i in enumerate(scales):
        peso = 1.0
        for j, escala_j in enumerate(scales):
            if i != j:
                peso *= escala_j / (escala_j - escala_i)
        pesos.append(peso)
    return tuple(pesos)


def extrapolation_weights(
    scale_factors: Sequence[int], *, method: str
) -> tuple[float, ...]:
    """Los coeficientes con que se combinan las mediciones para llegar a λ=0.

    Se exponen (y no solo el resultado) porque SON el método: publicarlos deja
    que un tercero recompute el valor mitigado desde las mediciones crudas sin
    volver a correr nada.
    """
    scales = _validated_scales(scale_factors)
    if method == EXTRAPOLATOR_LINEAR:
        return _linear_weights(scales)
    if method == EXTRAPOLATOR_RICHARDSON:
        return _richardson_weights(scales)
    msg = f"extrapolator debe ser uno de {list(EXTRAPOLATORS)}, no {method!r}"
    raise ValueError(msg)


def extrapolate(
    scale_factors: Sequence[int], values: Sequence[float], *, method: str
) -> float:
    """Valor del observable extrapolado a ruido cero."""
    pesos = extrapolation_weights(scale_factors, method=method)
    if len(values) != len(pesos):
        msg = (
            f"llegaron {len(values)} mediciones para {len(pesos)} factores de "
            "escala — una medición faltante no se rellena, se reporta"
        )
        raise ValueError(msg)
    return sum(peso * float(valor) for peso, valor in zip(pesos, values, strict=True))


def apparent_improvement(
    *, ideal: float, unmitigated: float, mitigated: float
) -> float:
    """Fracción del error contra el ideal que la mitigación eliminó.

    NEGATIVA cuando la mitigación aleja del ideal — recortarla a cero
    escondería justo el caso que más interesa reportar. Se llama APARENTE
    porque, sola, no significa nada: 2607.09360 muestra mejoras aparentes
    grandes sobre circuitos sin señal. Solo tiene sentido comparada contra el
    control negativo al mismo presupuesto.
    """
    error_crudo = abs(ideal - unmitigated)
    if error_crudo == 0.0:
        # 0/0: el valor crudo YA era el ideal. La respuesta honesta es "no hay
        # mejora que reclamar", no una mejora infinita.
        return 0.0
    return (error_crudo - abs(ideal - mitigated)) / error_crudo


def fold_global(circuit: Any, scale_factor: int) -> Any:
    """`C (C†C)^k` con `scale_factor = 2k+1` — misma unitaria, (2k+1)× compuertas.

    El circuito NO puede traer mediciones: `inverse()` no está definido sobre
    una operación no unitaria, y plegar después de medir sería plegar otra
    cosa. El llamante mide DESPUÉS de plegar.
    """
    if isinstance(scale_factor, bool) or scale_factor < 1 or scale_factor % 2 == 0:
        msg = (
            f"scale_factor debe ser un entero impar >= 1, no {scale_factor!r}: el "
            "folding global sube la profundidad de a 2k+1 y un factor par no "
            "corresponde a ningún plegado"
        )
        raise ValueError(msg)
    repeticiones = (scale_factor - 1) // 2
    if repeticiones == 0:
        return circuit.copy()
    inverso = circuit.inverse()
    plegado = circuit.copy()
    for _ in range(repeticiones):
        plegado = plegado.compose(inverso).compose(circuit)
    return plegado


def fold_garbage(circuit: Any, scale_factor: int, *, seed: int) -> Any:
    """Control negativo: infla el circuito con `(G†G)^k`, G ALEATORIO.

    Igual que `fold_global` en las dos cosas que importan para que la
    comparación sea justa —la unitaria ideal no cambia (G†G = I) y el costo en
    compuertas sube en la misma proporción— y distinto en la única que
    importa para el control: las compuertas insertadas no tienen NINGUNA
    relación con la estructura del circuito, así que la dependencia en λ que
    produce no es la del propio error del circuito.

    Si la "mejora" que ZNE reporta sobre esto es comparable a la que reporta
    sobre el plegado legítimo, entonces la mejora es una propiedad de la
    EXTRAPOLACIÓN y no de la mitigación (arXiv:2607.09360). Este es el control
    de costo igual que la nota 09 §1.4 exige antes de publicar un delta.
    """
    from qiskit.circuit.random import random_circuit

    if isinstance(scale_factor, bool) or scale_factor < 1 or scale_factor % 2 == 0:
        msg = f"scale_factor debe ser un entero impar >= 1, no {scale_factor!r}"
        raise ValueError(msg)
    repeticiones = (scale_factor - 1) // 2
    if repeticiones == 0:
        return circuit.copy()
    plegado = circuit.copy()
    for indice in range(repeticiones):
        # Semilla por repetición: dos inserciones idénticas se cancelarían
        # entre sí como patrón y el control dejaría de ser basura variada.
        basura = random_circuit(
            circuit.num_qubits,
            max(1, circuit.depth()),
            seed=seed + indice,
        )
        plegado = plegado.compose(basura.inverse()).compose(basura)
    return plegado


def noise_spec(*, one_qubit: float, two_qubit: float) -> dict[str, Any]:
    """Descriptor DECLARATIVO del ruido — lo que se digierte, no el objeto.

    El digest tiene que cubrir los parámetros, no la instancia de `NoiseModel`
    (cuya serialización cambia con la versión de Aer sin que el ruido cambie).
    Dos corridas mitigadas bajo ruidos distintos no son comparables, y este
    descriptor es lo que lo hace comprobable.
    """
    if not 0.0 <= one_qubit < 1.0 or not 0.0 <= two_qubit < 1.0:
        msg = (
            "las probabilidades de despolarización viven en [0,1): llegaron "
            f"{one_qubit!r} y {two_qubit!r}"
        )
        raise ValueError(msg)
    return {
        "kind": "depolarizing",
        "one_qubit": float(one_qubit),
        "two_qubit": float(two_qubit),
        "source": "aer-local-declarado",
    }


def _digest(payload: dict[str, Any]) -> str:
    """SHA-256 sobre JSON canónico plano — misma regla que el corpus."""
    return hashlib.sha256(
        json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode()
    ).hexdigest()


def build_noise_model(spec: dict[str, Any]) -> Any:
    """`NoiseModel` de Aer desde el descriptor. Ruido LOCAL declarado: el modo
    demostración honesto de la nota 09 §1.4 («mitigamos ruido simulado con
    este modelo declarado, no el del evento» — dicho así, sin maquillaje)."""
    from qiskit_aer.noise import NoiseModel, depolarizing_error

    modelo = NoiseModel()
    if spec["one_qubit"] > 0.0:
        modelo.add_all_qubit_quantum_error(
            depolarizing_error(spec["one_qubit"], 1), ["rz", "ry", "rx", "h", "sx", "x"]
        )
    if spec["two_qubit"] > 0.0:
        modelo.add_all_qubit_quantum_error(
            depolarizing_error(spec["two_qubit"], 2), ["cx", "cz"]
        )
    return modelo


def mitigation_block(
    *,
    scale_factors: Sequence[int],
    extrapolator: str,
    noise: dict[str, Any],
) -> dict[str, Any]:
    """El bloque `mitigation.*` del freeze §11, para el método ZNE.

    `training_digest` viaja EXPLÍCITAMENTE en `None`: ZNE no entrena nada, y
    rellenar el campo con un digest cualquiera fabricaría procedencia. El
    corrector aprendido (V9) sí lo llena — el mismo bloque distingue los dos
    métodos sin cambiar de forma.

    `model_digest` acá cubre la RECETA determinista que produjo el número
    (método + factores + extrapolador + folding): para ZNE eso ES el modelo, y
    con él un tercero recomputa el valor mitigado desde las mediciones crudas.
    """
    receta = {
        "method": MITIGATION_METHOD,
        "folding": FOLDING_GLOBAL,
        "extrapolator": extrapolator,
        "scale_factors": list(scale_factors),
    }
    return {
        "method": MITIGATION_METHOD,
        "model_digest": _digest(receta),
        "training_digest": None,
        "noise_model_digest": _digest(noise),
        "baseline": BASELINE_UNMITIGATED,
    }


def measured_curve(
    circuit: Any,
    matrix: list[list[float]],
    *,
    scales: tuple[int, ...],
    fold: Any,
    seed: int,
    shots: int,
    noise_model: Any,
    optimization_level: int | None = None,
) -> list[float]:
    """⟨C⟩ medido a cada factor de escala, con el plegado que se le pase.

    Pública (V9) a propósito: `blite_cap_quantum.corrector` mide la MISMA
    curva (legítima y garbage) que este módulo usa para Richardson/lineal —
    el corrector aprendido parte de la misma medición, nunca de una
    reimplementación paralela que podría driftear de esta.

    `optimization_level` (V9, aditivo — pasa tal cual a
    `qaoa.sample_counts`; `None` no cambia el comportamiento de
    `mitigate_expectation`, que no lo pasa).
    """
    from blite_cap_quantum.qaoa import sample_counts, sampled_mean_cut

    energias: list[float] = []
    for escala in scales:
        plegado = fold(circuit, escala)
        counts = sample_counts(
            plegado,
            seed=seed,
            shots=shots,
            noise_model=noise_model,
            optimization_level=optimization_level,
        )
        energias.append(sampled_mean_cut(counts, matrix))
    return energias


def mitigate_expectation(  # noqa: PLR0913 — el experimento ES la suma de estos parámetros
    raw_matrix: Any,
    *,
    layers: int = 1,
    seed: int = 1,
    initial_angles: Any = None,
    optimize: bool = True,
    scale_factors: Sequence[int] = DEFAULT_SCALE_FACTORS,
    extrapolator: str = EXTRAPOLATOR_RICHARDSON,
    one_qubit_noise: float = 0.002,
    two_qubit_noise: float = 0.02,
    shots: int = 2048,
) -> dict[str, Any]:
    """ZNE sobre ⟨C⟩ de un circuito QAOA, CON su control negativo.

    Las cuatro cantidades que salen son las cuatro barras del panel de
    ablación (nota 09 §1.4): ideal (statevector exacto, sin ruido) · crudo
    (λ=1 bajo ruido) · mitigado (extrapolado) · y el control negativo que
    decide si la diferencia entre los dos últimos significa algo.

    El control corre al MISMO presupuesto de shots y comparte su punto λ=1
    con la corrida legítima (plegar por 1 es la identidad en ambos casos), así
    que la comparación no está sesgada por presupuesto ni por baseline.

    **Reproducibilidad, medida y no prometida:** la rama legítima sí es
    bit-estable con la seed pinneada; la del CONTROL no siempre lo es entre
    corridas del mismo proceso (los circuitos de basura son mucho más
    profundos y Aer no garantiza el mismo reparto de shots a esa profundidad).
    El VEREDICTO sí es estable — verificado sobre 5 semillas, con dos órdenes
    de magnitud de margen. Se dice así en vez de prometer un determinismo que
    no se cumple.
    """
    from blite_cap_quantum.qaoa import prepare_circuit

    scales = _validated_scales(scale_factors)
    if scales[0] != 1:
        msg = (
            f"el primer factor de escala debe ser 1 (la medición cruda): {list(scales)} "
            "— sin ella no hay baseline medido en la misma corrida"
        )
        raise ValueError(msg)

    preparation = prepare_circuit(
        raw_matrix,
        layers=layers,
        seed=seed,
        initial_angles=initial_angles,
        optimize=optimize,
    )
    noise = noise_spec(one_qubit=one_qubit_noise, two_qubit=two_qubit_noise)
    noise_model = build_noise_model(noise)

    def _legitimo(circuito: Any, escala: int) -> Any:
        return fold_global(circuito, escala)

    def _basura(circuito: Any, escala: int) -> Any:
        return fold_garbage(circuito, escala, seed=seed)

    medidas = measured_curve(
        preparation.circuit,
        preparation.matrix,
        scales=scales,
        fold=_legitimo,
        seed=seed,
        shots=shots,
        noise_model=noise_model,
    )
    control = measured_curve(
        preparation.circuit,
        preparation.matrix,
        scales=scales,
        fold=_basura,
        seed=seed,
        shots=shots,
        noise_model=noise_model,
    )

    ideal = preparation.expected_energy
    crudo = medidas[0]
    mitigado = extrapolate(scales, medidas, method=extrapolator)
    mitigado_control = extrapolate(scales, control, method=extrapolator)

    mejora = apparent_improvement(ideal=ideal, unmitigated=crudo, mitigated=mitigado)
    mejora_control = apparent_improvement(
        ideal=ideal, unmitigated=control[0], mitigated=mitigado_control
    )

    return {
        "ideal_energy": ideal,
        "unmitigated_energy": crudo,
        "mitigated_energy": mitigado,
        "scaled_energies": [
            {"scale_factor": escala, "energy": energia}
            for escala, energia in zip(scales, medidas, strict=True)
        ],
        "extrapolation_weights": list(
            extrapolation_weights(scales, method=extrapolator)
        ),
        "improvement": mejora,
        "negative_control": {
            "kind": "garbage-folding",
            "reference": "arXiv:2607.09360",
            "unmitigated_energy": control[0],
            "mitigated_energy": mitigado_control,
            "improvement": mejora_control,
        },
        # La regla de publicación de la nota 09 §1.4: sin superar al control,
        # un delta positivo NO se publica. Se emite el booleano en vez de
        # ocultar el resultado, porque "no superó el control" es un hallazgo.
        "improvement_survives_control": mejora > mejora_control,
        "mitigation": mitigation_block(
            scale_factors=scales, extrapolator=extrapolator, noise=noise
        ),
        "noise": noise,
        "angles": preparation.angles,
        "layers": layers,
        "seed": seed,
        "shots": shots,
    }
