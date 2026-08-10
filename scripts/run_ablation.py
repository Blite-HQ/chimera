#!/usr/bin/env python3
"""Corre la ablación real de una instancia como sub-runs — V2/M19 (C-4, §13).

El último cable de M19: `blite.runtime.ablation` existe desde el commit del
mecanismo y NADIE lo llamaba, así que el panel de 4 barras del Studio no tenía
de dónde sacar filas. Esto es quien lo llama.

## Qué hace, y por qué así

Crea un run RAÍZ y cuelga de él un sub-run por brazo (§13: califican como
sub-run porque producen claims propios que un certificado citará). Cada brazo
emite SU `run.metrics.recorded` en SU stream con su variante, su `wall_ms`
MEDIDO y su costo de corte LEÍDO de su propia salida. `GET /runs/{raiz}/ablation`
los agrega para el panel.

El raíz existe porque sin él «cuántico vs clásico» son dos corridas sin
relación declarada y el panel tendría que adivinar cuáles comparar.

## Contra qué store

Contra el MISMO que el API: con `CHIMERA_DATABASE_URL` en el entorno,
`create_event_store()` devuelve el Postgres durable y los brazos quedan
visibles para el Studio en vivo. Sin la variable corre en memoria y los
resultados viven solo en el JSON — útil para mirar los números, inútil para
la demo. El script lo DICE en su salida en vez de dejar que se descubra
mirando un panel vacío.

## Los cuatro brazos

`quantum` (QAOA) · `classical` (CP-SAT exacto) · `zne` (mitigación con su
control negativo) son reales hoy. `mitigated` (corrector aprendido) es V9 y
NO se declara: un brazo declarado sin productor sería una barra vacía con
nombre, que es peor que una barra ausente.

Correr desde la raíz del repo:
    uv run python scripts/run_ablation.py --instance cr8-uniforme
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from uuid import uuid4

from blite.events import create_event_store
from blite.runtime.ablation import AblationArm, ArmOutcome, run_ablation_arms
from blite.runtime.content_store import InMemoryContentStore
from blite.runtime.dispatch import ProfileDispatcher
from blite.runtime.registry import EntryPointRegistry

REPO = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO / "knowledge" / "islanding" / "corpus"
OUT_DIR = REPO / "results" / "ablation"

DOMAIN_ID = "domain-default"
ACTOR_ID = "user:dylan"
_DEFAULT_INSTANCE = "cr8-uniforme"
_DEFAULT_LAYERS = 2
_DEFAULT_SEED = 1


def load_matrix(name: str) -> tuple[list[list[int]], int | None]:
    """QUBO simétrica del corpus (transform canónico) + su óptimo congelado."""
    record: dict[str, Any] = json.loads(
        (CORPUS_DIR / f"{name}.json").read_text(encoding="utf-8")
    )
    n = int(record["n_nodos"])
    matrix = [[0] * n for _ in range(n)]
    for u, v, w in ((int(a), int(b), int(c)) for a, b, c in record["aristas"]):
        matrix[u][u] += w
        matrix[v][v] += w
        matrix[u][v] -= w
        matrix[v][u] -= w
    optimo = record.get("optimo")
    return matrix, None if optimo is None else int(optimo)


def expected_energy_of(salida: Mapping[str, Any]) -> float | None:
    """⟨C⟩ del brazo cuántico — el valor ESPERADO, no el best-of-samples.

    Las tres barras tienen que ser la misma CLASE de número o el panel
    compara peras con manzanas: `energy` es el mejor de 2048 muestras (en
    instancias chicas alcanza el óptimo casi siempre — artefacto de muestreo,
    fix 4b) y `mitigated_energy` es un valor esperado. Poner los dos en el
    mismo eje haría ver a la mitigación peor de lo que es por una razón que
    no tiene nada que ver con mitigar.
    """
    valor = salida.get("expected_energy")
    return None if valor is None else float(valor)


def exact_energy_of(salida: Mapping[str, Any]) -> float | None:
    """El corte del solver exacto — la barra de referencia del panel.

    CP-SAT no muestrea ni estima: su `energy` ES el óptimo, así que es
    directamente comparable contra los ⟨C⟩ de los otros brazos (que son
    esperanzas del MISMO observable).
    """
    valor = salida.get("energy")
    return None if valor is None else float(valor)


def mitigated_energy_of(salida: Mapping[str, Any]) -> float | None:
    """Costo de corte del brazo ZNE — el valor MITIGADO, no el crudo.

    Si la mejora no sobrevivió al control negativo, el brazo NO aporta costo:
    publicar un número que el propio control desautoriza sería exactamente lo
    que arXiv:2607.09360 advierte (ver `blite_cap_quantum.zne`).
    """
    if not salida.get("improvement_survives_control", False):
        return None
    valor = salida.get("mitigated_energy")
    return None if valor is None else float(valor)


def build_arms(matrix: list[list[int]], *, layers: int, seed: int) -> list[AblationArm]:
    """Los brazos con productor REAL. `mitigated` es V9 y no se declara."""
    return [
        AblationArm(
            variant="quantum",
            capability_id="blite.quantum.qaoa",
            inputs={"matrix": matrix, "layers": layers, "seed": seed},
            cut_cost_from=expected_energy_of,
        ),
        AblationArm(
            variant="classical",
            capability_id="blite.solvers.qubo",
            inputs={"matrix": matrix},
            cut_cost_from=exact_energy_of,
        ),
        AblationArm(
            variant="zne",
            capability_id="blite.quantum.zne",
            inputs={"matrix": matrix, "layers": layers, "seed": seed},
            cut_cost_from=mitigated_energy_of,
        ),
    ]


def _registry() -> EntryPointRegistry:
    """Registry EXPLÍCITO con las tres capabilities que este experimento
    compara.

    Deliberadamente NO `load_registry()`: la comparación quedaría a merced del
    estado de instalación del venv, y un brazo que desaparece porque falta un
    reinstall no es un resultado — es un artefacto de entorno disfrazado de
    dato. El script declara qué compara; si una de las tres no importa, revienta
    acá y se ve, en vez de producir un panel con una barra menos.
    """
    from blite_cap_quantum import QaoaSolver, ZeroNoiseExtrapolation
    from blite_cap_solvers import QuboSolver

    return EntryPointRegistry(
        {
            "blite.quantum.qaoa": QaoaSolver(),
            "blite.solvers.qubo": QuboSolver(),
            "blite.quantum.zne": ZeroNoiseExtrapolation(),
        }
    )


def _row(outcome: ArmOutcome, optimo: int | None) -> dict[str, Any]:
    metricas = outcome.metrics
    cut_cost = None if metricas is None else metricas.cut_cost
    return {
        "variant": outcome.variant,
        "sub_run_id": outcome.sub_run_id,
        "status": outcome.status,
        "cut_cost": cut_cost,
        "wall_ms": None if metricas is None else metricas.wall_ms,
        "verification_latency_ms": (
            None if metricas is None else metricas.verification_latency_ms
        ),
        # r solo cuando hay ambos: sin óptimo congelado no hay denominador, y
        # sin costo no hay numerador. Ninguno se rellena.
        "r": (
            cut_cost / optimo
            if cut_cost is not None and optimo is not None and optimo > 0
            else None
        ),
        "sub_run_provenance_hash": outcome.sub_run_provenance_hash,
    }


def run(
    instance: str, *, layers: int, seed: int, dsn: str | None = None
) -> dict[str, Any]:
    """Crea el raíz, corre los brazos y devuelve el reporte."""
    matrix, optimo = load_matrix(instance)
    store = create_event_store(dsn)
    root_run_id = f"run-{uuid4().hex}"
    policy_digest = hashlib.sha256(f"ablation:{instance}".encode()).hexdigest()

    store.append(
        stream_id=root_run_id,
        type="run.created",
        actor_id=ACTOR_ID,
        domain_id=DOMAIN_ID,
        payload={
            "run_id": root_run_id,
            "actor_id": ACTOR_ID,
            "domain_id": DOMAIN_ID,
            "max_steps": 8,
            "policy_digest": policy_digest,
        },
    )

    outcomes = run_ablation_arms(
        store,
        _registry(),
        ProfileDispatcher(),
        InMemoryContentStore(),
        root_run_id=root_run_id,
        root_policy_digest=policy_digest,
        actor_id=ACTOR_ID,
        domain_id=DOMAIN_ID,
        arms=build_arms(matrix, layers=layers, seed=seed),
    )

    return {
        "instance": instance,
        "optimo": optimo,
        "root_run_id": root_run_id,
        "config": {"layers": layers, "seed": seed},
        "arms": [_row(outcome, optimo) for outcome in outcomes],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", default=_DEFAULT_INSTANCE)
    parser.add_argument("--layers", type=int, default=_DEFAULT_LAYERS)
    parser.add_argument("--seed", type=int, default=_DEFAULT_SEED)
    parser.add_argument("--output-dir", default=str(OUT_DIR))
    args = parser.parse_args(argv)

    dsn = os.environ.get("CHIMERA_DATABASE_URL")
    if dsn:
        print("store: Postgres durable — los brazos quedan visibles en el Studio")
    else:
        print(
            "store: EN MEMORIA (sin CHIMERA_DATABASE_URL) — los brazos NO van a "
            "aparecer en el Studio; solo queda el JSON"
        )

    report = run(args.instance, layers=args.layers, seed=args.seed)

    print(f"\nraíz: {report['root_run_id']}   óptimo: {report['optimo']}")
    print(f"{'variante':>10}  {'estado':>10}  {'corte':>10}  {'r':>8}  {'ms':>8}")
    for fila in report["arms"]:
        corte = "—" if fila["cut_cost"] is None else f"{fila['cut_cost']:.2f}"
        razon = "—" if fila["r"] is None else f"{fila['r']:.4f}"
        ms = "—" if fila["wall_ms"] is None else f"{fila['wall_ms']:.0f}"
        print(
            f"{fila['variant']:>10}  {fila['status']:>10}  {corte:>10}  "
            f"{razon:>8}  {ms:>8}"
        )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{args.instance}.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    print(f"\nartefacto JSON escrito en {path}")
    if dsn:
        print(f"panel: GET /runs/{report['root_run_id']}/ablation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
