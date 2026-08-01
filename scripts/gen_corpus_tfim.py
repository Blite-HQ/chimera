#!/usr/bin/env python3
"""Genera el corpus C3 (series de diagonalizacion exacta como referencia).

Correr desde la raiz del repo:  uv run python scripts/gen_corpus_tfim.py
Salida: knowledge/tfim/corpus/<instancia>.json  (9 puntos: 3 N x 3 h/J)

La receta congelada esta en knowledge/quantum/11-receta-c3-tfim-trotter.md:
convencion del operador (SS1.1), protocolo de quench (SS1.2), tiempo y malla
(SS2), identidad del corpus (SS5.1). Este script NO decide fisica — la aplica.

La referencia se computa llamando a la capability `blite.numeric.exact_evolve`
(la MISMA ancla que el verificador recomputa en vivo). Registrado y honesto:
las dos patas del reto 3 son «recompute vivo» y «serie congelada» — distintas
por INMUTABILIDAD, no por metodo. La diversidad metodologica real llega con el
stretch G6 (BdG analitico).

Digest EMBEBIDO self-consistente: SHA-256 del JSON canonico SIN el campo
`digest`, con el MISMO algoritmo que el corpus de islanding (el que
scripts/verify_corpus_digests.py aplica). Doctrina: se reporta, no se
sobreescribe.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from blite_cap_numeric import ExactEvolve

# Malla del enunciado (receta SS2).
N_SITIOS = (6, 8, 12)
RAZONES_H_J = (0.5, 1.0, 2.0)
ACOPLAMIENTO_J = 1.0
TIEMPO = 1.0
FRONTERA = "abierta"
TOLERANCIA_RELATIVA = 0.05  # criterio oficial <=5% (C-14)

CORPUS = "tfim-corpus"
VERSION_IDENTIDAD = 1
DIR_SALIDA = Path.cwd() / "knowledge" / "tfim" / "corpus"


def etiqueta_h(razon_h_j: float) -> str:
    """h/J -> sufijo de dos digitos: 0.5 -> h05, 1.0 -> h10, 2.0 -> h20.

    La forma `chain-n8-h10` la CONGELO el fixture de costura de Fase 0
    (tests/fixtures/contract/generalidad/predicate-ground-truth.json); este
    script la adopta, no la elige.
    """
    centesimas = round(razon_h_j * 10)
    return f"h{centesimas:02d}"


def nombre_instancia(n_sitios: int, razon_h_j: float) -> str:
    return f"chain-n{n_sitios}-{etiqueta_h(razon_h_j)}"


def dataset_id(n_sitios: int, razon_h_j: float) -> str:
    return f"{CORPUS}/{nombre_instancia(n_sitios, razon_h_j)}@v{VERSION_IDENTIDAD}"


def _pauli(n_sitios: int, sitios: dict[int, str]) -> str:
    """Cadena de Pauli con el indice i = sitio i (izquierda a derecha).

    Convencion del wire de las capabilities — deliberadamente NO es el orden
    little-endian de Qiskit; la conversion explicita vive del lado del circuito.
    """
    return "".join(sitios.get(i, "I") for i in range(n_sitios))


def terminos_del_operador(n_sitios: int, campo_h: float) -> list[dict[str, Any]]:
    """H = -J sum Z_i Z_{i+1} - h sum X_i (cadena abierta) — receta SS1.1."""
    terminos: list[dict[str, Any]] = [
        {"pauli": _pauli(n_sitios, {i: "Z", i + 1: "Z"}), "coefficient": -ACOPLAMIENTO_J}
        for i in range(n_sitios - 1)
    ]
    terminos += [
        {"pauli": _pauli(n_sitios, {i: "X"}), "coefficient": -campo_h}
        for i in range(n_sitios)
    ]
    return terminos


def observables_z(n_sitios: int) -> list[dict[str, str]]:
    return [
        {"label": f"Z{i}", "pauli": _pauli(n_sitios, {i: "Z"})} for i in range(n_sitios)
    ]


def observables_zz(n_sitios: int) -> list[dict[str, str]]:
    return [
        {"label": f"ZZ{i}", "pauli": _pauli(n_sitios, {i: "Z", i + 1: "Z"})}
        for i in range(n_sitios - 1)
    ]


def digest_embebido(registro: dict[str, Any]) -> str:
    """SHA-256 del JSON canonico sin el campo `digest` — mismo algoritmo que
    el corpus de islanding (scripts/verify_corpus_digests.py)."""
    sin_digest = {k: v for k, v in registro.items() if k != "digest"}
    canonico = json.dumps(
        sin_digest, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(canonico.encode()).hexdigest()


def construir_punto(n_sitios: int, razon_h_j: float) -> dict[str, Any]:
    campo_h = razon_h_j * ACOPLAMIENTO_J
    terminos = terminos_del_operador(n_sitios, campo_h)
    obs_z = observables_z(n_sitios)
    obs_zz = observables_zz(n_sitios)
    estado_inicial = "0" * n_sitios

    salida = ExactEvolve().invoke(
        {
            "n_sites": n_sitios,
            "terms": terminos,
            "time": TIEMPO,
            "initial_bitstring": estado_inicial,
            "observables": [*obs_z, *obs_zz],
        }
    )
    por_etiqueta = {e["label"]: float(e["value"]) for e in salida["expectations"]}

    norma = float(salida["norm"])
    if abs(norma - 1.0) > 1e-9:
        msg = f"{nombre_instancia(n_sitios, razon_h_j)}: norma {norma!r} != 1 — aborta"
        raise RuntimeError(msg)

    registro: dict[str, Any] = {
        "acoplamiento_j": ACOPLAMIENTO_J,
        "backend": salida["backend"],
        "campo_h": campo_h,
        "corpus": CORPUS,
        "dataset_id": dataset_id(n_sitios, razon_h_j),
        "estado_inicial": estado_inicial,
        "frontera": FRONTERA,
        "instancia": nombre_instancia(n_sitios, razon_h_j),
        "metodos": [salida["method"]],
        "n_sitios": n_sitios,
        "observables_z": obs_z,
        "observables_zz": obs_zz,
        "procedencia": "curated_internal",
        "razon_h_j": razon_h_j,
        "serie_z": [por_etiqueta[o["label"]] for o in obs_z],
        "serie_zz": [por_etiqueta[o["label"]] for o in obs_zz],
        "terminos": terminos,
        "tiempo": TIEMPO,
        "tolerancia_relativa": TOLERANCIA_RELATIVA,
    }
    registro["digest"] = digest_embebido(registro)
    return registro


def _chequeo_cono_de_luz(puntos: dict[str, dict[str, Any]]) -> None:
    """Receta SS5.3: a t=1 el cono de Lieb-Robinson no distingue N — el valor
    de borde debe coincidir entre N=6, 8 y 12 al mismo h/J. Si no coincide, el
    bug esta en el generador y NO se escribe nada."""
    for razon in RAZONES_H_J:
        bordes = {
            n: puntos[nombre_instancia(n, razon)]["serie_z"][0] for n in N_SITIOS
        }
        valores = list(bordes.values())
        if max(abs(v - valores[0]) for v in valores) > 1e-6:
            msg = (
                f"h/J={razon}: <Z0> depende de N ({bordes}) a t={TIEMPO} — "
                "viola el cono de luz (receta SS5.3): bug del generador"
            )
            raise RuntimeError(msg)


def main() -> int:
    puntos = {
        nombre_instancia(n, razon): construir_punto(n, razon)
        for n in N_SITIOS
        for razon in RAZONES_H_J
    }
    _chequeo_cono_de_luz(puntos)

    DIR_SALIDA.mkdir(parents=True, exist_ok=True)
    for nombre, registro in sorted(puntos.items()):
        destino = DIR_SALIDA / f"{nombre}.json"
        destino.write_text(
            json.dumps(registro, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        print(f"  {nombre}.json  digest={registro['digest'][:16]}...")

    print(f"{len(puntos)} puntos del corpus C3 escritos en {DIR_SALIDA}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
