#!/usr/bin/env python3
"""Genera el corpus C2 (clasificacion binaria tabular sintetica sellada).

Correr desde la raiz del repo:  uv run python scripts/gen_corpus_tabular.py
Salida: knowledge/tabular/corpus/synthetic-binary.csv + synthetic-binary.json

Contexto honesto (docs/mejorado/03-research.md R1, fila del dataset Kaggle
`water-potability`): el CSV CC0 real del reto no es obtenible en este entorno
(sin red). Este script NO lo mockea ni lo simula a escondidas: genera un
sustituto SINTETICO deterministico de la MISMA forma (3276 filas, 9 features
numericas + 1 etiqueta binaria, balance ~61/39, frontera no lineal, ruido de
etiqueta y faltantes) y lo declara como tal (`procedencia: "synthetic_generated"`,
NUNCA `curated_internal`) — el registro JSON lleva los caveats en español que
explican el techo de esta afirmacion. Si el CSV oficial se vuelve disponible,
su digest reemplaza a este; el pipeline no cambia porque el corpus es DATO
(docs/specs/generalidad-retos.md SS4).

Digest EMBEBIDO self-consistente: SHA-256 del JSON canonico SIN el campo
`digest`, MISMO algoritmo que knowledge/tfim (scripts/gen_corpus_tfim.py) y
knowledge/islanding — la identidad de corpus generalizada de la spec de
costura (SS4): "se reporta, no se sobreescribe".
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

# ── Parametros pinneados (todo lo que hace la corrida reproducible) ─────────
SEMILLA_GENERADOR = 1
N_FILAS = 3276
N_FEATURES = 9
FRACCION_MINORIA_OBJETIVO = 0.39  # balance final ~61/39 (mayoria=0, minoria=1)
FRACCION_RUIDO_ETIQUETA = 0.15  # ~15% de filas con la etiqueta volteada
FRACCION_FALTANTES = 0.05  # ~5% de faltantes en cada columna afectada
COLUMNAS_CON_FALTANTES = (1, 4, 7)  # exactamente 3, repartidas entre las 9

CORPUS = "tabular-corpus"
INSTANCIA = "synthetic-binary"
VERSION_IDENTIDAD = 1
DIR_SALIDA = Path.cwd() / "knowledge" / "tabular" / "corpus"

NOMBRES_FEATURES = [f"feature_{i}" for i in range(N_FEATURES)]
COLUMNA_ETIQUETA = "label"
NOMBRES_COLUMNAS = [*NOMBRES_FEATURES, COLUMNA_ETIQUETA]

CAVEATS = [
    (
        "Estos datos son SINTETICOS, generados deterministicamente con "
        "numpy.random.default_rng(semilla fija) — no provienen de ningun CSV "
        "real ni de la fuente de datos oficial del reto (no obtenible sin red "
        "en este entorno)."
    ),
    (
        "Cualquier claim de un clasificador entrenado sobre este corpus es una "
        "afirmacion sobre ESTE CSV sellado (identificado por su digest), jamas "
        "una prediccion sobre un fenomeno del mundo real — de ahi "
        "procedencia=\"synthetic_generated\" y el techo AL3/GROUND_TRUTH "
        "(docs/mejorado/03-research.md R1)."
    ),
    (
        "Si el CSV oficial CC0 del reto se vuelve disponible en este entorno, "
        "su digest SUPERSEDE a este (se reporta, no se sobreescribe); el "
        "pipeline (blite.ml.tabular_prep -> blite.quantum.fidelity_kernel -> "
        "blite.ml.svm_precomputed / blite.ml.classifier_baseline) no cambia, "
        "porque el corpus es DATO, no codigo (docs/specs/generalidad-retos.md "
        "SS4)."
    ),
]


def _generar_features(rng: np.random.Generator) -> np.ndarray:
    """9 columnas numericas heterogeneas (escalas y distribuciones distintas,
    como un dataset tabular real) — los nombres son genericos (ADR-029)."""
    columnas = [
        rng.uniform(0.0, 14.0, size=N_FILAS),
        rng.normal(196.0, 32.0, size=N_FILAS),
        rng.normal(21000.0, 8700.0, size=N_FILAS),
        rng.normal(7.1, 1.6, size=N_FILAS),
        rng.normal(333.0, 41.0, size=N_FILAS),
        rng.normal(426.0, 80.0, size=N_FILAS),
        rng.normal(14.3, 3.3, size=N_FILAS),
        rng.normal(66.4, 16.2, size=N_FILAS),
        rng.normal(3.97, 0.78, size=N_FILAS),
    ]
    return np.column_stack(columnas)


def _puntaje_no_lineal(features: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Frontera de decision NO lineal (cuadraticas + producto cruzado + seno/
    tanh sobre las features estandarizadas) mas un termino de ruido continuo
    — asi el problema no es trivialmente separable por un clasificador lineal
    y la comparacion cuantico-vs-clasico tiene algo que decir."""
    z = (features - features.mean(axis=0)) / features.std(axis=0)
    return (
        0.9 * z[:, 0] ** 2
        - 0.6 * z[:, 1]
        + 1.1 * np.sin(z[:, 2])
        + 0.8 * z[:, 3] * z[:, 4]
        - 0.5 * z[:, 5] ** 2
        + 0.7 * np.tanh(z[:, 6])
        - 0.4 * z[:, 7]
        + 0.3 * z[:, 8] ** 2
        + rng.normal(0.0, 0.5, size=N_FILAS)
    )


def _etiquetas_con_ruido(
    puntaje: np.ndarray, rng: np.random.Generator
) -> tuple[np.ndarray, int]:
    """Umbral por cuantil (balance PRE-ruido calculado para que el balance
    POST-ruido caiga en ~61/39) + volteo aleatorio uniforme de
    FRACCION_RUIDO_ETIQUETA de las filas (ruido de etiqueta, no de feature).

    Despeje: si m = fraccion minoria final, r = fraccion volteada (uniforme
    sobre TODAS las filas), minoria_pre*(1-2r) + N*r = m*N
      => minoria_pre = N*(m-r)/(1-2r)
    """
    r = FRACCION_RUIDO_ETIQUETA
    m = FRACCION_MINORIA_OBJETIVO
    minoria_pre = round(N_FILAS * (m - r) / (1 - 2 * r))

    orden_desc = np.argsort(puntaje)[::-1]
    etiquetas = np.zeros(N_FILAS, dtype=int)
    etiquetas[orden_desc[:minoria_pre]] = 1

    n_flip = round(N_FILAS * r)
    indices_flip = rng.choice(N_FILAS, size=n_flip, replace=False)
    etiquetas[indices_flip] = 1 - etiquetas[indices_flip]
    return etiquetas, int(n_flip)


def _insertar_faltantes(
    features: np.ndarray, rng: np.random.Generator
) -> dict[int, int]:
    """NaN en exactamente 3 columnas (COLUMNAS_CON_FALTANTES), ~5% cada una —
    para que la imputacion por mediana EN-FOLD (tabular_prep) se ejercite de
    verdad. Muta `features` in-place (arreglo de trabajo local al script)."""
    n_faltantes = round(N_FILAS * FRACCION_FALTANTES)
    conteo_por_columna: dict[int, int] = {}
    for columna in COLUMNAS_CON_FALTANTES:
        idx = rng.choice(N_FILAS, size=n_faltantes, replace=False)
        features[idx, columna] = np.nan
        conteo_por_columna[columna] = int(n_faltantes)
    return conteo_por_columna


def _formatear_valor(valor: float) -> str:
    """Formato fijo (6 decimales) y NaN -> celda vacia (convencion CSV
    estandar que pandas.read_csv reconoce como faltante)."""
    if math.isnan(valor):
        return ""
    return f"{valor:.6f}"


def _construir_csv(features: np.ndarray, etiquetas: np.ndarray) -> bytes:
    encabezado = ",".join(NOMBRES_COLUMNAS)
    filas = [encabezado]
    for i in range(N_FILAS):
        valores = [_formatear_valor(float(features[i, j])) for j in range(N_FEATURES)]
        valores.append(str(int(etiquetas[i])))
        filas.append(",".join(valores))
    contenido = "\n".join(filas) + "\n"
    return contenido.encode("utf-8")


def _digest_embebido(registro: dict[str, Any]) -> str:
    """SHA-256 del JSON canonico sin el campo `digest` — mismo algoritmo que
    knowledge/tfim/islanding (scripts/verify_corpus_digests.py)."""
    sin_digest = {k: v for k, v in registro.items() if k != "digest"}
    canonico = json.dumps(
        sin_digest, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(canonico.encode()).hexdigest()


def construir_corpus() -> tuple[bytes, dict[str, Any]]:
    rng = np.random.default_rng(SEMILLA_GENERADOR)

    features = _generar_features(rng)
    puntaje = _puntaje_no_lineal(features, rng)
    etiquetas, _n_flip = _etiquetas_con_ruido(puntaje, rng)
    faltantes_por_columna = _insertar_faltantes(features, rng)

    csv_bytes = _construir_csv(features, etiquetas)
    csv_digest = hashlib.sha256(csv_bytes).hexdigest()

    conteo_1 = int(etiquetas.sum())
    conteo_0 = N_FILAS - conteo_1
    total_faltantes = sum(faltantes_por_columna.values())

    registro: dict[str, Any] = {
        "balance": {
            "conteo_0": conteo_0,
            "conteo_1": conteo_1,
            "proporcion_0": conteo_0 / N_FILAS,
            "proporcion_1": conteo_1 / N_FILAS,
        },
        "caveats": CAVEATS,
        "celdas_faltantes": {
            "total": total_faltantes,
            "por_columna": {
                NOMBRES_FEATURES[col]: n for col, n in sorted(faltantes_por_columna.items())
            },
        },
        "columna_etiqueta": COLUMNA_ETIQUETA,
        "columnas": NOMBRES_COLUMNAS,
        "corpus": CORPUS,
        "csv_digest": csv_digest,
        "dataset_id": f"{CORPUS}/{INSTANCIA}@v{VERSION_IDENTIDAD}",
        "instancia": INSTANCIA,
        "n_columnas": len(NOMBRES_COLUMNAS),
        "n_filas": N_FILAS,
        "procedencia": "synthetic_generated",
        "semilla": SEMILLA_GENERADOR,
    }
    registro["digest"] = _digest_embebido(registro)
    return csv_bytes, registro


def main() -> int:
    csv_bytes, registro = construir_corpus()

    DIR_SALIDA.mkdir(parents=True, exist_ok=True)
    csv_destino = DIR_SALIDA / f"{INSTANCIA}.csv"
    json_destino = DIR_SALIDA / f"{INSTANCIA}.json"

    csv_destino.write_bytes(csv_bytes)
    json_destino.write_text(
        json.dumps(registro, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    print(f"  {csv_destino.name}  csv_digest={registro['csv_digest'][:16]}...")
    print(f"  {json_destino.name}  digest={registro['digest'][:16]}...")
    print(f"balance: {registro['balance']}")
    print(f"celdas_faltantes: {registro['celdas_faltantes']}")
    print(f"corpus C2 escrito en {DIR_SALIDA}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
