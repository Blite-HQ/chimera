#!/usr/bin/env python3
"""Experimento r vs p — QAOA (p∈{1,2,3} × ≥5 semillas) vs GW/greedy/CP-SAT.

Task 4 (`.superpowers/sdd/task4-brief.md`, D6 en docs/mvp/decisiones.md).
Rúbrica del reto: implementación cuántica 30% + comparación/escalamiento 20%.

Convención QUBO congelada (context.md § Grafo↔QUBO, misma que
`blite_cap_solvers.qubo` / `blite_cap_quantum.qaoa` / `blite_cap_graphs.maxcut`):
Q simétrica, se MAXIMIZA C(x) = xᵀQx sobre x binario; para Max-Cut el óptimo
de C(x) coincide con el valor del corte.

r = corte/óptimo, donde óptimo es el `optimo` CONGELADO del corpus
(`knowledge/islanding/corpus/<instancia>.json`) — verdad de terreno anclada
por CP-SAT (+fuerza bruta cuando n≤14, ver `scripts/gen_corpus_islanding.py`).

Fix 4b (`.superpowers/sdd/task4b-brief.md`): `solve_qaoa` devuelve
best-of-2048-shots, que en instancias chicas (p.ej. 6 qubits = 64 estados)
encuentra el óptimo casi siempre — un artefacto de MUESTREO, no la
performance real de QAOA (r(p)=1.0000±0.0000 trivial en todo p). La curva
r vs p reportada aquí usa en cambio el valor esperado EXACTO ⟨C⟩ de la
distribución variacional (`expected_energy`, statevector) como r_esperado
(curva primaria) y su estimador muestral (`sampled_mean_energy`) como
r_muestral (media±std sobre semillas, honesto sobre el ruido de muestreo).
El best-of-samples se reporta aparte como `success_rate` (secundario).

QAOA (Qiskit 2.x + Aer, `blite_cap_quantum.qaoa.solve_qaoa`) NO es
bit-determinista entre versiones de librería (misma lección que Task 1) —
por eso los números que este script produce son una INSTANTÁNEA
ilustrativa/entregable (JSON en `results/exp_r_vs_p/`), no un oráculo de
test. Los tests (`tests/unit/experiment/test_exp_r_vs_p.py`) asertan
invariantes (r_esperado∈[0,1], r_muestral∈[0,1], cpsat.r==1.0, determinismo
dentro de una corrida), nunca valores QAOA exactos.

Uso (correr desde la raíz del repo):
    uv run python scripts/exp_r_vs_p.py --instance ieee6-flujo
    uv run python scripts/exp_r_vs_p.py --instance ieee9-flujo --p-values 1 2 --seeds 1 2 3

Salida:
  (a) tabla de texto a stdout;
  (b) `results/exp_r_vs_p/<instancia>.json` — SIEMPRE (fuente reproducible);
  (c) `results/exp_r_vs_p/<instancia>_r_vs_p.png` — SOLO si matplotlib está
      instalado (import perezoso; si falta, se imprime un aviso y se sigue).
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

_DEFAULT_INSTANCE = "ieee6-flujo"
_DEFAULT_P_VALUES = (1, 2, 3)
_DEFAULT_SEEDS = (1, 2, 3, 4, 5)
_GW_SEED = 1


def compute_ratio(energy: float, optimo: float) -> float:
    """r = energy/optimo. `optimo` es el óptimo congelado del corpus (>0)."""
    return energy / optimo


def summarize(ratios: list[float]) -> dict[str, float | int]:
    """mean/std/n/min/max de una lista de razones.

    std = desviación estándar POBLACIONAL (`statistics.pstdev`, ddof=0):
    caracteriza la dispersión observada en las semillas efectivamente
    corridas (la muestra completa que se reporta), no una inferencia sobre
    semillas no vistas — y sigue definida en n=1 (barridos con una sola
    semilla), a diferencia de la muestral (ddof=1, indefinida en n=1).
    """
    if not ratios:
        msg = "summarize: ratios no puede ser una lista vacía"
        raise ValueError(msg)
    return {
        "mean": statistics.fmean(ratios),
        "std": statistics.pstdev(ratios),
        "n": len(ratios),
        "min": min(ratios),
        "max": max(ratios),
    }


def _find_corpus() -> Path:
    """Walk-up desde este archivo — mismo patrón que solvers/tests y
    tests/unit/verification/test_corpus_ieee6.py (independiente del cwd)."""
    for base in (Path(__file__).resolve(), *Path(__file__).resolve().parents):
        candidate = base / "knowledge" / "islanding" / "corpus"
        if candidate.is_dir():
            return candidate
    msg = "corpus de islanding no encontrado sobre este archivo"
    raise FileNotFoundError(msg)


def load_instance(name: str) -> tuple[list[list[int]], int, dict[str, Any]]:
    """Carga `<name>.json` del corpus y construye la QUBO (transform canónico).

    Devuelve (matrix, optimo, meta) — meta es el registro completo del
    corpus (incluye digest, asignacion_canonica, metodos, etc.).
    """
    path = _find_corpus() / f"{name}.json"
    record: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    edges = [(int(u), int(v), int(w)) for u, v, w in record["aristas"]]
    n = int(record["n_nodos"])
    matrix = [[0] * n for _ in range(n)]
    for u, v, w in edges:
        matrix[u][u] += w
        matrix[v][v] += w
        matrix[u][v] -= w
        matrix[v][u] -= w
    optimo = int(record["optimo"])
    return matrix, optimo, record


def run_baselines(matrix: list[list[int]], optimo: int) -> dict[str, dict[str, Any]]:
    """GW / greedy (`blite_cap_graphs.maxcut`) + CP-SAT exacto (`blite_cap_solvers.qubo`).

    Determinista: greedy no tiene aleatoriedad, GW usa una semilla fija
    (`_GW_SEED`) para el redondeo por hiperplano, CP-SAT ya es determinista
    (workers=1, seed fija — ver qubo.py).
    """
    from blite_cap_graphs.maxcut import solve_maxcut
    from blite_cap_solvers.qubo import solve_qubo

    cpsat = solve_qubo(matrix)
    greedy = solve_maxcut(matrix, method="greedy")
    gw = solve_maxcut(matrix, method="gw", seed=_GW_SEED)
    return {
        "cpsat": {
            "energy": cpsat["energy"],
            "r": compute_ratio(cpsat["energy"], optimo),
        },
        "greedy": {
            "energy": greedy["energy"],
            "r": compute_ratio(greedy["energy"], optimo),
        },
        "gw": {"energy": gw["energy"], "r": compute_ratio(gw["energy"], optimo)},
    }


def run_qaoa_sweep(
    matrix: list[list[int]],
    optimo: int,
    p_values: list[int],
    seeds: list[int],
) -> dict[int, dict[str, Any]]:
    """Barre QAOA (`blite_cap_quantum.qaoa.solve_qaoa`) sobre p_values × seeds.

    Fix 4b (task4b-brief.md): best-of-samples (`energy`) trivializa r en
    instancias chicas (best-of-2048-shots ≈ óptimo en un espacio de 64
    estados) — es un artefacto de muestreo, no la performance de QAOA. Se
    reportan en cambio dos curvas honestas:
      - `r_esperado` — stats (`summarize`) del ratio del valor esperado
        EXACTO ⟨C⟩ (`expected_energy`, statevector) sobre las semillas.
        Curva PRIMARIA (approx ratio en esperanza); casi determinista en p
        (`expected_energy` no depende del muestreo) — si `std≈0` se reporta
        tal cual, honestamente.
      - `r_muestral` — stats del ratio muestral (`sampled_mean_energy`,
        media de `_energy` ponderada por counts) sobre las semillas — SÍ
        varía con `seed` vía `seed_simulator`, cumple "media±std de ≥5
        corridas".
    `success_rate` = fracción de semillas cuyo best-of-samples alcanza el
    óptimo — dato secundario honesto, NO la curva r.
    """
    from blite_cap_quantum.qaoa import solve_qaoa

    sweep: dict[int, dict[str, Any]] = {}
    for p in p_values:
        best_energies: list[float] = []
        expected_energies: list[float] = []
        sampled_mean_energies: list[float] = []
        for seed in seeds:
            result = solve_qaoa(matrix, layers=p, seed=seed, reference_optimum=optimo)
            best_energies.append(result["energy"])
            expected_energies.append(result["expected_energy"])
            sampled_mean_energies.append(result["sampled_mean_energy"])

        best_ratios = [compute_ratio(e, optimo) for e in best_energies]
        expected_ratios = [compute_ratio(e, optimo) for e in expected_energies]
        sampled_ratios = [compute_ratio(e, optimo) for e in sampled_mean_energies]
        success_rate = sum(1 for r in best_ratios if r >= 1.0) / len(best_ratios)

        sweep[p] = {
            "best_energies": best_energies,
            "expected_energies": expected_energies,
            "sampled_mean_energies": sampled_mean_energies,
            "best_ratios": best_ratios,
            "r_esperado": summarize(expected_ratios),
            "r_muestral": summarize(sampled_ratios),
            "success_rate": success_rate,
        }
    return sweep


def build_report(
    instance: str,
    optimo: int,
    config: dict[str, Any],
    qaoa: dict[int, dict[str, Any]],
    baselines: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Ensambla el artefacto JSON: {instance, optimo, config, qaoa, baselines}."""
    return {
        "instance": instance,
        "optimo": optimo,
        "config": config,
        "qaoa": qaoa,
        "baselines": baselines,
    }


def _print_table(report: dict[str, Any]) -> None:
    print(f"instancia: {report['instance']}   optimo congelado: {report['optimo']}")
    print()
    print(
        f"{'p':>3}  {'r_esperado':>10}  {'r_muestral':>10}  {'std_muestral':>12}  "
        f"{'n':>3}  {'exito':>8}"
    )
    for p, entry in sorted(report["qaoa"].items()):
        esperado = entry["r_esperado"]
        muestral = entry["r_muestral"]
        print(
            f"{p:>3}  {esperado['mean']:>10.4f}  {muestral['mean']:>10.4f}  "
            f"{muestral['std']:>12.4f}  {muestral['n']:>3}  "
            f"{entry['success_rate']:>8.2%}"
        )
    print()
    print(f"{'baseline':>10}  {'energy':>12}  {'r':>10}")
    for name in ("cpsat", "gw", "greedy"):
        entry = report["baselines"][name]
        print(f"{name:>10}  {entry['energy']:>12.2f}  {entry['r']:>10.4f}")


def _maybe_plot(report: dict[str, Any], png_path: Path) -> None:
    """Figura r vs p — línea de r_esperado + barras de error de r_muestral
    (media±std), más líneas horizontales de baselines. SOLO si matplotlib
    está instalado (import perezoso)."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print(
            "matplotlib no está instalado — se omite la figura "
            "(el JSON es la fuente reproducible, no depende de esto)"
        )
        return

    p_values = sorted(report["qaoa"].keys())
    esperado_means = [report["qaoa"][p]["r_esperado"]["mean"] for p in p_values]
    muestral_means = [report["qaoa"][p]["r_muestral"]["mean"] for p in p_values]
    muestral_stds = [report["qaoa"][p]["r_muestral"]["std"] for p in p_values]

    fig, ax = plt.subplots()
    ax.plot(p_values, esperado_means, marker="o", label="r_esperado (⟨C⟩ exacto)")
    ax.errorbar(
        p_values,
        muestral_means,
        yerr=muestral_stds,
        marker="s",
        linestyle="--",
        capsize=4,
        label="r_muestral (media±std, shots)",
    )
    for name in ("cpsat", "gw", "greedy"):
        ax.axhline(report["baselines"][name]["r"], linestyle=":", label=name)
    ax.set_xlabel("p (capas QAOA)")
    ax.set_ylabel("r = corte / óptimo")
    ax.set_title(f"r vs p — {report['instance']}")
    ax.set_xticks(p_values)
    ax.legend()
    fig.savefig(png_path)
    plt.close(fig)
    print(f"figura escrita en {png_path}")


def _default_output_dir() -> Path:
    # Misma convención que scripts/gen_corpus_islanding.py: correr desde la
    # raíz del repo (documentado en el docstring del módulo).
    return Path.cwd() / "results" / "exp_r_vs_p"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", default=_DEFAULT_INSTANCE)
    parser.add_argument(
        "--p-values", type=int, nargs="+", default=list(_DEFAULT_P_VALUES)
    )
    parser.add_argument("--seeds", type=int, nargs="+", default=list(_DEFAULT_SEEDS))
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args(argv)

    matrix, optimo, _meta = load_instance(args.instance)
    baselines = run_baselines(matrix, optimo)
    qaoa = run_qaoa_sweep(matrix, optimo, args.p_values, args.seeds)
    config = {"p_values": args.p_values, "seeds": args.seeds}
    report = build_report(args.instance, optimo, config, qaoa, baselines)

    _print_table(report)

    output_dir = Path(args.output_dir) if args.output_dir else _default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{args.instance}.json"
    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    print()
    print(f"artefacto JSON escrito en {json_path}")

    _maybe_plot(report, output_dir / f"{args.instance}_r_vs_p.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
