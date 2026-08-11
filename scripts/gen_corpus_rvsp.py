#!/usr/bin/env python3
"""Congela la curva r-vs-p como corpus verificable — V3/M20 (C-9/#106 · #125).

Qué produce: `knowledge/rvsp/<instancia>.json`, el artefacto que
`GET /runs/{run_id}/rvsp` sirve. Mismo estatuto que el resto de
`knowledge/`: record con `digest` embebido que cierra sobre su propio
contenido (regla §15.3), cargado fail-closed. `results/exp_r_vs_p/` sigue
siendo lo que su docstring dice —una instantánea ilustrativa del
experimento—; esto es la versión INGERIDA, con identidad.

## Por qué los ángulos vienen de Nexus (`--angle-source nexus-import`)

El punto de la curva responde «¿qué tan bueno es QAOA a profundidad p?».
Con ángulos que optimizamos nosotros, la respuesta mide nuestro COBYLA
tanto como mide QAOA. Con los ángulos que Quantinuum realmente corrió
—ingeridos con su `circuit_digest` (`scripts/import_nexus_runs.py`)— la
respuesta es sobre el circuito que de verdad se ejecutó en hardware. `⟨C⟩`
se evalúa EN esos ángulos (`optimize=False`, V5): re-optimizarlos cambiaría
el circuito y la comparación dejaría de ser la misma corrida.

## Qué es exacto y qué es muestral (la ETIQUETA de la curva)

- `r_esperado_*` — ⟨C⟩ EXACTO por statevector en los ángulos dados. No
  depende de la semilla de muestreo; si su `std` sale 0 se reporta 0.
- `r_muestral_*` — media/std/min/max del estimador sobre shots de Aer, una
  corrida por semilla. Esta SÍ varía con la semilla: es la que cumple
  "media±std de ≥N corridas".
- `success_rate` — fracción de semillas cuyo best-of-samples alcanza el
  óptimo. Dato secundario honesto, NUNCA la curva r (en instancias chicas
  el best-of-2048-shots trivializa el ratio — fix 4b).

El bloque `metodo` del record deja escrito backend, shots, semillas, origen
de los ángulos y el digest del circuito por capa. Sin él, un punto medido en
hardware y uno medido en ángulos propios se ven idénticos en el wire, y son
afirmaciones distintas.

Correr desde la raíz del repo:
    uv run python scripts/gen_corpus_rvsp.py                    # las 5 con ángulos de Nexus
    uv run python scripts/gen_corpus_rvsp.py --instance ieee6-flujo --angle-source cobyla
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO / "knowledge" / "islanding" / "corpus"
NEXUS_INDEX = REPO / "knowledge" / "nexus" / "index.json"
OUT_DIR = REPO / "knowledge" / "rvsp"

NEXUS_ANGLES = "nexus-import"
"""Los ángulos los corrió Quantinuum; acá solo se evalúa ⟨C⟩ en ellos."""
COBYLA_ANGLES = "cobyla"
"""Los ángulos los optimizó este repo — la curva mide también al optimizador."""

ANGLE_SOURCES = (NEXUS_ANGLES, COBYLA_ANGLES)
BACKEND = "aer_simulator"
GENERATED_BY = "scripts/gen_corpus_rvsp.py"
_DEFAULT_SEEDS = (1, 2, 3, 4, 5)
_GW_SEED = 1


def record_digest(record_without_digest: dict[str, Any]) -> str:
    """Regla de identidad del corpus (§15.3): JSON canónico PLANO.

    Deliberadamente NO el JCS de `blite.certificate.canonical` — ese es el
    algoritmo de otro anexo, para digests de contenido de certificado. Misma
    función que `chimera_api.corpus_records.corpus_record_digest` valida del
    otro lado; si divergieran, el corpus no cargaría.
    """
    return hashlib.sha256(
        json.dumps(
            record_without_digest,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()
    ).hexdigest()


def load_instance(name: str) -> tuple[list[list[int]], int]:
    """(QUBO simétrica, óptimo congelado) de `<name>.json` del corpus.

    Transform canónico grafo→QUBO (context.md §Grafo↔QUBO), el MISMO que
    `scripts/exp_r_vs_p.py` y `chimera_api.runs._load_corpus_matrix`.
    """
    record: dict[str, Any] = json.loads(
        (CORPUS_DIR / f"{name}.json").read_text(encoding="utf-8")
    )
    optimo = record.get("optimo")
    if optimo is None:
        msg = (
            f"{name} no tiene optimo congelado — sin denominador no hay r, y "
            "una curva fabricada esta prohibida (letra C-9)"
        )
        raise ValueError(msg)
    n = int(record["n_nodos"])
    matrix = [[0] * n for _ in range(n)]
    for u, v, w in ((int(a), int(b), int(c)) for a, b, c in record["aristas"]):
        matrix[u][u] += w
        matrix[v][v] += w
        matrix[u][v] -= w
        matrix[v][u] -= w
    return matrix, int(optimo)


def nexus_angles_by_p(
    index: dict[str, Any], instance: str
) -> dict[int, dict[str, Any]]:
    """Ángulos ingeridos de Nexus por capa, con el digest que los cubre.

    Vacío honesto cuando la instancia no se corrió en hardware — decidir qué
    hacer con eso es de quien llama, no de esta función.
    """
    por_p: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)
    for entry in index["imports"]:
        if entry["instance"] == instance:
            por_p[int(entry["p"])].append(entry)

    angulos: dict[int, dict[str, Any]] = {}
    for p, entradas in por_p.items():
        distintos = {
            (tuple(e["betas"]), tuple(e["gammas"]), e["circuit_digest"])
            for e in entradas
        }
        if len(distintos) != 1:
            msg = (
                f"las corridas de {instance} p={p} discrepan en sus angulos: "
                "dos backends del MISMO circuito logico no pueden diferir, y "
                "elegir uno en silencio dejaria el punto sin corresponder a la "
                "mitad de la evidencia"
            )
            raise ValueError(msg)
        primera = entradas[0]
        angulos[p] = {
            "betas": list(primera["betas"]),
            "gammas": list(primera["gammas"]),
            "circuit_digest": primera["circuit_digest"],
        }
    return angulos


def _summarize(ratios: list[float]) -> dict[str, float]:
    """mean/std/min/max — `pstdev` (poblacional, ddof=0) por la misma razón
    que `scripts/exp_r_vs_p.summarize`: caracteriza la dispersión de las
    semillas efectivamente corridas y sigue definida en n=1."""
    return {
        "mean": statistics.fmean(ratios),
        "std": statistics.pstdev(ratios),
        "min": min(ratios),
        "max": max(ratios),
    }


def _baselines(matrix: list[list[int]], optimo: int) -> dict[str, dict[str, float]]:
    """CP-SAT exacto + GW + greedy, los 3 del contrato (cerrado, C-15).

    Deterministas los tres: greedy no tiene aleatoriedad, GW usa semilla fija,
    CP-SAT ya es determinista (workers=1, seed fija).
    """
    from blite_cap_graphs.maxcut import solve_maxcut
    from blite_cap_solvers.qubo import solve_qubo

    resultados = {
        "cpsat": solve_qubo(matrix),
        "greedy": solve_maxcut(matrix, method="greedy"),
        "gw": solve_maxcut(matrix, method="gw", seed=_GW_SEED),
    }
    return {
        nombre: {
            "energy": float(salida["energy"]),
            "r": float(salida["energy"]) / optimo,
        }
        for nombre, salida in resultados.items()
    }


def _point(
    matrix: list[list[int]],
    optimo: int,
    *,
    p: int,
    seeds: Sequence[int],
    angles: dict[str, Any] | None,
) -> dict[str, Any]:
    """Un punto de la curva: una corrida de Aer por semilla, en los MISMOS
    ángulos (si vienen dados) o re-optimizando en cada una (si no)."""
    from blite_cap_quantum.qaoa import solve_qaoa

    esperados: list[float] = []
    muestrales: list[float] = []
    exitos = 0
    for seed in seeds:
        resultado = solve_qaoa(
            matrix,
            layers=p,
            seed=seed,
            reference_optimum=optimo,
            initial_angles=(
                {"betas": angles["betas"], "gammas": angles["gammas"]}
                if angles
                else None
            ),
            optimize=angles is None,
        )
        esperados.append(resultado["expected_energy"] / optimo)
        muestrales.append(resultado["sampled_mean_energy"] / optimo)
        exitos += int(resultado["energy"] >= optimo)

    esperado = _summarize(esperados)
    muestral = _summarize(muestrales)
    return {
        "p": p,
        "r_esperado_mean": esperado["mean"],
        "r_muestral_mean": muestral["mean"],
        "r_muestral_std": muestral["std"],
        "r_muestral_min": muestral["min"],
        "r_muestral_max": muestral["max"],
        "success_rate": exitos / len(seeds),
    }


def build_record(  # noqa: PLR0913 — el record ES la suma de estos parámetros
    *,
    instance: str,
    matrix: list[list[int]],
    optimo: int,
    p_values: Sequence[int],
    seeds: Sequence[int],
    angle_source: str,
    angles_by_p: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """El record congelado: wire del contrato + el bloque `metodo` + digest."""
    if angle_source not in ANGLE_SOURCES:
        msg = f"angle_source debe ser uno de {list(ANGLE_SOURCES)}, no {angle_source!r}"
        raise ValueError(msg)
    dados = angles_by_p or {}
    if angle_source == NEXUS_ANGLES:
        faltantes = [p for p in p_values if p not in dados]
        if faltantes:
            msg = (
                f"{instance}: no hay angulos de Nexus ingeridos para p={faltantes} — "
                "la curva no se completa con angulos propios disfrazados de hardware"
            )
            raise ValueError(msg)

    puntos = [
        _point(matrix, optimo, p=p, seeds=seeds, angles=dados.get(p))
        for p in sorted(p_values)
    ]
    sin_digest: dict[str, Any] = {
        "instance": instance,
        "optimo": optimo,
        "baselines": _baselines(matrix, optimo),
        "points": puntos,
        "metodo": {
            "expectation": "statevector-exacto",
            "backend": BACKEND,
            "seeds": list(seeds),
            "angle_source": angle_source,
            "angle_digests": {
                str(p): dados[p]["circuit_digest"] for p in sorted(dados) if p in dados
            },
        },
        "generated_by": GENERATED_BY,
    }
    return {**sin_digest, "digest": record_digest(sin_digest)}


def _write(record: dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{record['instance']}.json"
    path.write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return path


def _instancias_con_angulos(index: dict[str, Any]) -> list[str]:
    return sorted({str(entry["instance"]) for entry in index["imports"]})


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--instance",
        action="append",
        default=None,
        help="instancia del corpus (repetible); default: todas las de Nexus",
    )
    parser.add_argument("--p-values", type=int, nargs="+", default=None)
    parser.add_argument("--seeds", type=int, nargs="+", default=list(_DEFAULT_SEEDS))
    parser.add_argument("--angle-source", choices=ANGLE_SOURCES, default=NEXUS_ANGLES)
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    args = parser.parse_args(argv)

    index: dict[str, Any] = json.loads(NEXUS_INDEX.read_text(encoding="utf-8"))
    instancias = args.instance or _instancias_con_angulos(index)

    for instancia in instancias:
        matrix, optimo = load_instance(instancia)
        angulos = (
            nexus_angles_by_p(index, instancia)
            if args.angle_source == NEXUS_ANGLES
            else {}
        )
        p_values = args.p_values or sorted(angulos) or [1, 2, 3]
        record = build_record(
            instance=instancia,
            matrix=matrix,
            optimo=optimo,
            p_values=p_values,
            seeds=tuple(args.seeds),
            angle_source=args.angle_source,
            angles_by_p=angulos,
        )
        path = _write(record, Path(args.out_dir))
        print(f"{instancia}: {len(record['points'])} puntos -> {path}")
        for punto in record["points"]:
            print(
                f"  p={punto['p']}  r_esperado={punto['r_esperado_mean']:.4f}  "
                f"r_muestral={punto['r_muestral_mean']:.4f}"
                f"±{punto['r_muestral_std']:.4f}  exito={punto['success_rate']:.0%}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
