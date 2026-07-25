#!/usr/bin/env python3
"""Artefacto de extrapolación HONESTA — B4 (`docs/planeado/04-consolidacion.md`
§3, base §15.3): ieee30→70 nodos clásico, **barrera 26 qubits**.

La idea central (`knowledge/quantum/08-ruta-quantinuum-guppy.md` §2,
actualización oficial 2026-07-18): el emulador H2 hace tratamiento **EXACTO**
hasta **26 qubits**. Con la codificación Max-Cut congelada (1 nodo = 1 qubit,
`knowledge/quantum/02-recetario-formulacion-por-reto.md` §1), cualquier
instancia con n≤26 es elegible para evidencia cuántica; n>26 es SOLO
clásica. Esto NO es una brecha que no se intentó — es una barrera física del
emulador, confirmada por el enunciado oficial, y este artefacto la declara
explícitamente en cada fila (`regime` + `barrier_qubits`), nunca la esconde
detrás de un campo vacío.

Segunda idea central: QAOA **NO** supera a Goemans-Williamson en ninguna
instancia de este corpus (garantía teórica p=1 ≈0.6924 < GW ≈0.878,
`docs/retos/reto1-consigna.md` + `knowledge/quantum/01-fundamentos-
matematicos.md` §... — los equipos DEBEN reportar esta brecha). El bloque
`honest_limitations` lo declara con los números observados, no solo la cota
teórica.

Fuentes de datos (todas ya committeadas — cero red, determinista):
  - `knowledge/islanding/corpus/*.json` — óptimo/aristas por instancia
    (`optimo=None` en ICE, n=68 — ver `scripts/gen_corpus_ice.py`).
  - `knowledge/nexus/` (B3) — las 19 corridas QAOA reales importadas de
    Quantinuum/Nexus (`index.json` + `normalized/*.json`); el r cuántico de
    este artefacto se RECOMPUTA aquí desde los counts crudos (nunca se
    confía en un número reportado — mismo principio que
    `engine/src/blite/verification/exact_solver.py`), usando el
    `bit_order` empírico que `scripts/import_nexus_runs.py` ya resolvió por
    corrida.
  - `capabilities/graphs/src/blite_cap_graphs/maxcut.py::solve_maxcut` —
    baseline clásico REUTILIZABLE (GW + greedy), corre a cualquier n (n=68
    es trivial para la SDP). `sdp_upper_bound` (B4): el valor de la
    relajación SDP sin redondear es una cota superior rigurosa del corte
    máximo real — se expone gratis del mismo solve.

Determinismo: GW usa una semilla fija (`_GW_SEED`); las corridas QAOA NO se
re-ejecutan en vivo (se usa el r ya congelado en `knowledge/nexus/`); el
digest del artefacto es `sha256(json canónico sin el campo "digest")`
—misma fórmula que `scripts/gen_corpus_islanding.py::con_digest`. Re-correr
este script produce bytes idénticos.

Uso (correr desde la raíz del repo):
    uv run python scripts/gen_extrapolation.py

Salida:
  (a) `results/extrapolation/extrapolation.json` — la tabla completa +
      `honest_limitations` + `provenance` + `digest`.
  (b) `results/extrapolation/extrapolation.md` — la misma información en
      narrativa legible.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

BARRIER_QUBITS = 26
BARRIER_SOURCE = (
    "knowledge/quantum/08-ruta-quantinuum-guppy.md §2 "
    "(actualización oficial 2026-07-18: 'tope de 26 qubits confirma la "
    "escalera de instancias: cr8/ieee9/ieee14 en emulador; ieee30 solo "
    "clásico')"
)
BARRIER_REASON = "excede la barrera de 26 qubits del emulador H2"
ICE_NO_GROUND_TRUTH_SOURCE = "scripts/gen_corpus_ice.py"

_QAOA_P1_GUARANTEE = 0.6924
_GW_GUARANTEE = 0.878
_GUARANTEE_SOURCE = (
    "docs/retos/reto1-consigna.md (enunciado oficial: 'QAOA no supera a GW "
    "para Max-Cut en ninguna instancia... los equipos DEBEN reportar esta "
    "brecha') + knowledge/quantum/01-fundamentos-matematicos.md §... "
    "(Farhi et al. 2014, p=1 en grafos 3-regulares; Goemans-Williamson 1995)"
)

_GW_SEED = 1

# La escalera declarada en el insumo B4: cada entrada es un archivo real de
# `knowledge/islanding/corpus/`. Quantum-eligible (n<=26) solo si trae
# corridas Nexus reales (B3) -- nunca un `None` ambiguo entre "no corrimos"
# y "barrera física"; classical-only siempre por la barrera de 26 qubits.
INSTANCES: tuple[str, ...] = (
    "cr6-uniforme",
    "cr8-uniforme",
    "cr8-voltaje",
    "ieee9-uniforme",
    "ieee14-flujo",
    "ieee30-uniforme",
    "ice-uniforme",
    "ice-voltaje",
)


def _repo_root() -> Path:
    """Walk-up desde este archivo — mismo patrón que scripts/exp_r_vs_p.py."""
    for base in (Path(__file__).resolve(), *Path(__file__).resolve().parents):
        candidate = base / "knowledge" / "islanding" / "corpus"
        if candidate.is_dir():
            return base
    msg = "raíz del repo no encontrada (falta knowledge/islanding/corpus)"
    raise FileNotFoundError(msg)


def _default_output_dir() -> Path:
    # Misma convención que scripts/exp_r_vs_p.py: correr desde la raíz.
    return Path.cwd() / "results" / "extrapolation"


def con_digest(registro: dict[str, Any]) -> dict[str, Any]:
    """digest = SHA-256 del JSON canónico (claves ordenadas, sin espacios,
    ensure_ascii) SIN el campo digest — misma fórmula que
    `scripts/gen_corpus_islanding.py::con_digest`."""
    canonico = json.dumps(
        registro, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return {**registro, "digest": hashlib.sha256(canonico.encode("utf-8")).hexdigest()}


def _sha256_hex(value: dict[str, Any]) -> str:
    canonico = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def regime_for(n_nodos: int) -> str:
    """`"quantum-eligible"` si n<=26 (barrera del emulador H2), si no
    `"classical-only"` — la regla central de este artefacto (§2)."""
    return "quantum-eligible" if n_nodos <= BARRIER_QUBITS else "classical-only"


def load_corpus_instance(name: str) -> dict[str, Any]:
    path = _repo_root() / "knowledge" / "islanding" / "corpus" / f"{name}.json"
    record: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return record


def build_matrix(aristas: list[list[int]], n: int) -> list[list[int]]:
    """QUBO simétrica del transform canónico (context.md § Grafo↔QUBO) —
    misma fórmula que `scripts/exp_r_vs_p.py::load_instance`."""
    matrix = [[0] * n for _ in range(n)]
    for u, v, w in aristas:
        matrix[u][u] += w
        matrix[v][v] += w
        matrix[u][v] -= w
        matrix[v][u] -= w
    return matrix


def decode_bitstring(bitstring: str, order: str) -> list[int]:
    """Misma convención que `scripts/import_nexus_runs.py::_decode_bitstring`."""
    chars = bitstring if order == "msb-left" else bitstring[::-1]
    return [int(ch) for ch in chars]


def cut_value(aristas: list[list[int]], assignment: list[int]) -> int:
    return sum(w for u, v, w in aristas if assignment[u] != assignment[v])


def nexus_run_stats(
    counts: dict[str, int], order: str, aristas: list[list[int]], optimo: int
) -> dict[str, Any]:
    """ratio_mean/ratio_best/best_cut/shots RECOMPUTADOS desde los counts
    crudos — nunca se confía en un número reportado (misma disciplina que
    `ExactSolverVerifier`, `engine/src/blite/verification/exact_solver.py`)."""
    shots = sum(counts.values())
    cuts = {bs: cut_value(aristas, decode_bitstring(bs, order)) for bs in counts}
    best_cut = max(cuts.values())
    mean_cut = sum(cuts[bs] * n for bs, n in counts.items()) / shots
    return {
        "shots": shots,
        "best_cut": best_cut,
        "ratio_best": best_cut / optimo,
        "ratio_mean": mean_cut / optimo,
    }


def load_nexus_index() -> dict[str, Any]:
    path = _repo_root() / "knowledge" / "nexus" / "index.json"
    index: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return index


def load_normalized_counts(stem: str) -> dict[str, int]:
    path = _repo_root() / "knowledge" / "nexus" / "normalized" / f"{stem}.json"
    normalized: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    counts: dict[str, int] = normalized["normalized_counts"]["counts"]
    return counts


def nexus_runs_for_instance(
    instance: str,
    index: dict[str, Any],
    aristas: list[list[int]],
    optimo: int,
) -> list[dict[str, Any]]:
    """Una entrada por (p, backend) — r cuántico REAL con su `job_id`
    citado (B4: "cita los job_id"), ordenadas para salida determinista."""
    runs: list[dict[str, Any]] = []
    for imp in index["imports"]:
        if imp["instance"] != instance:
            continue
        stem = f"{instance}-p{imp['p']}-s{imp['seed']}-{imp['backend_id']}"
        counts = load_normalized_counts(stem)
        stats = nexus_run_stats(counts, imp["bit_order"], aristas, optimo)
        runs.append(
            {
                "p": imp["p"],
                "backend_id": imp["backend_id"],
                "seed": imp["seed"],
                "job_id": imp["job_id"],
                "bit_order": imp["bit_order"],
                "normalized_digest": imp["normalized_digest"],
                "statement_digest": imp["statement_digest"],
                **stats,
            }
        )
    return sorted(runs, key=lambda r: (r["p"], r["backend_id"]))


def classical_baselines(matrix: list[list[int]]) -> dict[str, Any]:
    """GW + greedy vía `blite_cap_graphs.maxcut.solve_maxcut` (baseline
    reutilizable, B4) — semilla GW fija para determinismo."""
    from blite_cap_graphs.maxcut import solve_maxcut

    greedy = solve_maxcut(matrix, method="greedy")
    gw = solve_maxcut(matrix, method="gw", seed=_GW_SEED)
    return {
        "greedy_cut": greedy["energy"],
        "gw_cut": gw["energy"],
        "sdp_upper_bound": gw["sdp_upper_bound"],
    }


def _quantum_fields(
    name: str,
    regime: str,
    index: dict[str, Any],
    aristas: list[list[int]],
    n_nodos: int,
    optimo: int | None,
) -> tuple[list[dict[str, Any]] | None, str | None]:
    """(`quantum`, `reason`) — nunca ambos `None`/vacíos "por descuido": una
    instancia classical-only siempre trae la razón de la barrera; una
    quantum-eligible siempre trae corridas Nexus reales (o falla-fuerte)."""
    if regime == "classical-only":
        return None, BARRIER_REASON
    if optimo is None:  # pragma: no cover — curaduría INSTANCES lo evita
        msg = f"{name}: quantum-eligible sin óptimo — no se puede computar r"
        raise ValueError(msg)
    runs = nexus_runs_for_instance(name, index, aristas, optimo)
    if not runs:  # pragma: no cover — curaduría INSTANCES lo evita
        msg = (
            f"{name}: quantum-eligible (n={n_nodos}) sin corridas Nexus en "
            "el índice — curaduría de INSTANCES desalineada con B3"
        )
        raise ValueError(msg)
    return runs, None


def _ratio_or_band_fields(
    classical: dict[str, Any], n_nodos: int, optimo: int | None
) -> dict[str, Any]:
    """Con `optimo` conocido: r_gw/r_greedy. Sin él (ICE): banda honesta
    `[greedy_cut, gw_cut, sdp_upper_bound]` — NUNCA un r inventado."""
    if optimo is not None:
        return {
            "r_gw": classical["gw_cut"] / optimo,
            "r_greedy": classical["greedy_cut"] / optimo,
            "band": None,
            "band_note": None,
        }
    return {
        "r_gw": None,
        "r_greedy": None,
        "band": [
            classical["greedy_cut"],
            classical["gw_cut"],
            classical["sdp_upper_bound"],
        ],
        "band_note": (
            f"sin óptimo probado a n={n_nodos} (excede FUERZA_BRUTA_MAX_N=14 "
            "de la doble ancla; esta generación no corrió CP-SAT sobre la "
            f"red completa — {ICE_NO_GROUND_TRUTH_SOURCE}); banda honesta "
            "[greedy_cut, gw_cut, sdp_upper_bound], GW heurístico + cota "
            "SDP, NUNCA un r inventado"
        ),
    }


def build_row(name: str, index: dict[str, Any]) -> dict[str, Any]:
    """Un escalón de la escalera: régimen + baseline clásico SIEMPRE + r
    cuántico real (quantum-eligible) o barrera declarada (classical-only)."""
    record = load_corpus_instance(name)
    n_nodos = int(record["n_nodos"])
    optimo: int | None = record["optimo"]
    aristas: list[list[int]] = record["aristas"]
    matrix = build_matrix(aristas, n_nodos)
    regime = regime_for(n_nodos)
    classical = classical_baselines(matrix)
    quantum, reason = _quantum_fields(name, regime, index, aristas, n_nodos, optimo)

    return {
        "instance": name,
        "convencion": record["convencion"],
        "n_nodos": n_nodos,
        "optimo": optimo,
        "regime": regime,
        "barrier_qubits": BARRIER_QUBITS,
        "corpus_source": f"knowledge/islanding/corpus/{name}.json",
        "corpus_digest": record["digest"],
        "classical": classical,
        "quantum": quantum,
        "reason": reason,
        **_ratio_or_band_fields(classical, n_nodos, optimo),
    }


def _qaoa_vs_gw_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    quantum_rows = [r for r in rows if r["quantum"] is not None]
    all_runs = [run for r in quantum_rows for run in r["quantum"]]
    beats_gw = [
        {"instance": r["instance"], "p": run["p"], "backend_id": run["backend_id"]}
        for r in quantum_rows
        for run in r["quantum"]
        if run["ratio_best"] > r["r_gw"]
    ]
    return {
        "qaoa_p1_theoretical_guarantee": _QAOA_P1_GUARANTEE,
        "gw_theoretical_guarantee": _GW_GUARANTEE,
        "guarantee_source": _GUARANTEE_SOURCE,
        "max_ratio_best_observed": max(
            (run["ratio_best"] for run in all_runs), default=None
        ),
        "max_ratio_mean_observed": max(
            (run["ratio_mean"] for run in all_runs), default=None
        ),
        "instances_where_qaoa_beat_gw": beats_gw,
        "statement": (
            "QAOA no superó a GW en ninguna corrida Nexus de este artefacto "
            "('instances_where_qaoa_beat_gw' vacío ⇒ verificado, no supuesto): "
            "en las instancias con evidencia cuántica (n<=14) GW ya alcanza "
            "el óptimo exacto (r_gw=1.0); el ratio_best de QAOA solo lo "
            "empata por muestreo en espacios de estados chicos (best-of-"
            "~1024 shots sobre <=2^14 estados) — artefacto de muestreo "
            "documentado en scripts/exp_r_vs_p.py (Fix 4b), no ventaja "
            "cuántica; el ratio_mean muestral (la métrica honesta) se queda "
            "sistemáticamente por debajo de 1.0. Coherente con la garantía "
            "teórica: QAOA p=1 (0.6924) < GW (0.878)."
        ),
    }


def _barrier_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    classical_only = [r["instance"] for r in rows if r["regime"] == "classical-only"]
    quantum_eligible = [
        r["instance"] for r in rows if r["regime"] == "quantum-eligible"
    ]
    return {
        "value": BARRIER_QUBITS,
        "source": BARRIER_SOURCE,
        "quantum_eligible_instances": quantum_eligible,
        "classical_only_instances": classical_only,
        "statement": (
            "El emulador H2 hace tratamiento EXACTO hasta 26 qubits (1 nodo "
            "= 1 qubit en la codificación Max-Cut congelada) — NO es una "
            "brecha que no intentamos, es una barrera física del emulador "
            "confirmada por el enunciado oficial (2026-07-18). "
            f"{classical_only} exceden la barrera y son SOLO clásicas; "
            f"{quantum_eligible} tienen evidencia cuántica real."
        ),
    }


def _ice_ground_truth_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    no_optimum = [r["instance"] for r in rows if r["optimo"] is None]
    return {
        "instances": no_optimum,
        "source": ICE_NO_GROUND_TRUTH_SOURCE,
        "statement": (
            "A n=68 no hay verdad de terreno: el óptimo no fue probado "
            "(excede FUERZA_BRUTA_MAX_N=14 de la doble ancla y esta "
            f"generación no corrió CP-SAT sobre la red completa — "
            f"{ICE_NO_GROUND_TRUTH_SOURCE}) — solo se reporta la banda "
            "[greedy_cut, gw_cut, sdp_upper_bound] por instancia, nunca un "
            "r inventado."
        ),
    }


def build_honest_limitations(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "qaoa_vs_gw": _qaoa_vs_gw_summary(rows),
        "barrier_26_qubits": _barrier_summary(rows),
        "ice_no_ground_truth": _ice_ground_truth_summary(rows),
    }


def build_provenance(
    rows: list[dict[str, Any]], nexus_index_digest: str
) -> dict[str, Any]:
    inputs = [
        {"ref": row["corpus_source"], "digest": row["corpus_digest"]} for row in rows
    ]
    inputs.append({"ref": "knowledge/nexus/index.json", "digest": nexus_index_digest})
    params_digest = _sha256_hex(
        {
            "instances": list(INSTANCES),
            "barrier_qubits": BARRIER_QUBITS,
            "gw_seed": _GW_SEED,
        }
    )
    return {
        "inputs": inputs,
        "recipe": {
            "capability": "blite.evidencia.extrapolacion.gen_extrapolation",
            "version": "0.1.0",
            "params_digest": "sha256:" + params_digest,
            "code_ref": "git:HEAD",
        },
    }


def build_artifact() -> dict[str, Any]:
    """Ensambla la escalera completa + honest_limitations + provenance, y
    la sella con su propio digest (misma fórmula que el corpus). Re-correr
    produce bytes idénticos: GW con semilla fija, QAOA nunca se re-ejecuta
    (se usa el r ya congelado en knowledge/nexus/)."""
    index = load_nexus_index()
    rows = [build_row(name, index) for name in INSTANCES]
    nexus_index_path = _repo_root() / "knowledge" / "nexus" / "index.json"
    nexus_index_digest = hashlib.sha256(nexus_index_path.read_bytes()).hexdigest()

    artifact = {
        "barrier_qubits": BARRIER_QUBITS,
        "barrier_source": BARRIER_SOURCE,
        "instances": rows,
        "honest_limitations": build_honest_limitations(rows),
        "provenance": build_provenance(rows, nexus_index_digest),
    }
    return con_digest(artifact)


def _format_quantum_cell(row: dict[str, Any]) -> str:
    if row["quantum"] is None:
        return f"barrera ({row['reason']})"
    ratios_mean = [run["ratio_mean"] for run in row["quantum"]]
    return (
        f"ratio_mean {min(ratios_mean):.4f}–{max(ratios_mean):.4f} "
        f"({len(row['quantum'])} corridas Nexus)"
    )


def _format_r_cell(row: dict[str, Any]) -> str:
    if row["r_gw"] is not None:
        return f"r_gw={row['r_gw']:.4f} · r_greedy={row['r_greedy']:.4f}"
    greedy_cut, gw_cut, sdp_bound = row["band"]
    return f"banda [{greedy_cut:.2f}, {gw_cut:.2f}, {sdp_bound:.2f}]"


def render_markdown(artifact: dict[str, Any]) -> str:
    """Narrativa honesta — misma información que el JSON, legible. Sin
    reloj de pared: el contenido es una función pura del artefacto."""
    lines = [
        "# Extrapolación honesta — ieee30→70 nodos clásico, barrera 26 qubits",
        "",
        f"Barrera del emulador H2: **{artifact['barrier_qubits']} qubits** "
        f"(fuente: {artifact['barrier_source']}).",
        "",
        "| instancia | n | régimen | r cuántico (real) | gw_cut | greedy_cut "
        "| cota SDP | r_gw/r_greedy o banda |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in artifact["instances"]:
        classical = row["classical"]
        lines.append(
            f"| {row['instance']} | {row['n_nodos']} | {row['regime']} | "
            f"{_format_quantum_cell(row)} | {classical['gw_cut']} | "
            f"{classical['greedy_cut']} | {classical['sdp_upper_bound']:.2f} | "
            f"{_format_r_cell(row)} |"
        )

    lines += ["", "## Limitaciones honestas", ""]
    limitations = artifact["honest_limitations"]
    for key in ("qaoa_vs_gw", "barrier_26_qubits", "ice_no_ground_truth"):
        lines.append(f"- **{key}**: {limitations[key]['statement']}")

    lines += ["", f"Digest del artefacto: `{artifact['digest']}`", ""]
    return "\n".join(lines)


def main() -> int:
    artifact = build_artifact()

    output_dir = _default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "extrapolation.json"
    json_path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    md_path = output_dir / "extrapolation.md"
    md_path.write_text(render_markdown(artifact), encoding="utf-8")

    print(f"artefacto JSON escrito en {json_path}")
    print(f"narrativa Markdown escrita en {md_path}")
    print(f"digest: {artifact['digest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
