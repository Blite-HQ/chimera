#!/usr/bin/env python3
"""Corre el corpus runner (tercer plano) contra el plano de verificación REAL.

    uv run python scripts/run_eval_corpus.py [--out results/eval]

Construye el dataset desde un corpus versionado con verdad conocida y mide, por
instancia, DOS muestras de polaridad opuesta:

- **fiel**: el claim reproduce la serie congelada del corpus ⇒ debe `pass`.
- **perturbada**: la misma serie escalada por encima de la tolerancia ⇒ debe `fail`.

Sin las dos polaridades el número no dice nada: un verificador que dijera `pass`
a todo sacaría 100 % con solo las fieles, y uno que dijera `fail` a todo sacaría
100 % con solo las perturbadas.

El conocimiento de reto vive ACÁ (script + `knowledge/`), jamás en el runner: el
paquete `chimera_eval` no sabe qué es una cadena de espines (ADR-029).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from chimera_eval.dataset import Dataset
from chimera_eval.runner import EvalLog, run_task
from chimera_eval.tasks.verification_plane import (
    build_task,
    perturb_series,
    sample_from_claim,
)

_REPO_ROOT = Path(__file__).parents[1]
_CORPUS_DIR = _REPO_ROOT / "knowledge" / "tfim" / "corpus"
_CLAIM_TYPE = "simulation_result"

_PERTURBATION_FACTOR = 1.5
"""50 % de error relativo — muy por encima de la tolerancia del corpus (5 %).
Una perturbación al filo mediría la calibración de la tolerancia, no si el
sistema distingue verdad de mentira; eso es otro experimento."""


def _claim_payload(record: dict[str, Any], series: list[float]) -> dict[str, Any]:
    observables = [*record["observables_z"], *record["observables_zz"]]
    return {
        "n_sites": record["n_sitios"],
        "terms": record["terminos"],
        "time": record["tiempo"],
        "initial_bitstring": record["estado_inicial"],
        "observables": observables,
        "series": series,
        "canonical_statement": (
            f"La serie declarada reproduce la evolución de {record['instancia']}"
        ),
        "scope": {"instancia": record["instancia"]},
    }


def build_dataset(corpus_dir: Path = _CORPUS_DIR) -> Dataset:
    """Dos muestras por instancia del corpus: una fiel y una perturbada."""
    samples = []
    for path in sorted(corpus_dir.glob("*.json")):
        record: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        instance = str(record["instancia"])
        faithful = [*record["serie_z"], *record["serie_zz"]]

        samples.append(
            sample_from_claim(
                sample_id=f"{instance}:faithful",
                claim_type=_CLAIM_TYPE,
                instance_id=instance,
                payload=_claim_payload(record, faithful),
                expected_verdict="pass",
                metadata={"polarity": "faithful", "corpus_digest": record["digest"]},
            )
        )
        samples.append(
            sample_from_claim(
                sample_id=f"{instance}:perturbed",
                claim_type=_CLAIM_TYPE,
                instance_id=instance,
                payload=_claim_payload(
                    record, perturb_series(faithful, _PERTURBATION_FACTOR)
                ),
                expected_verdict="fail",
                metadata={"polarity": "perturbed", "corpus_digest": record["digest"]},
            )
        )
    return Dataset(name=corpus_dir.name, samples=tuple(samples))


def _revision() -> str | None:
    """Commit + flag de sucio, o `None` fuera de un repo.

    Se resuelve `git` por ruta absoluta (`shutil.which`) — un ejecutable
    buscado por nombre lo elige el `PATH` de quien corra el script. Los dos
    argumentos son literales del módulo: no hay entrada de usuario en la
    línea de comando (por eso el `noqa: S603` es honesto y no un silencio).
    """
    git = shutil.which("git")
    if git is None:
        return None
    try:
        sha = subprocess.run(  # noqa: S603 — argv literal, ejecutable resuelto
            [git, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=_REPO_ROOT,
        ).stdout.strip()
        dirty = subprocess.run(  # noqa: S603 — argv literal, ejecutable resuelto
            [git, "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
            cwd=_REPO_ROOT,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return f"{sha}{'-dirty' if dirty else ''}"


def _report(log: EvalLog) -> None:
    print(f"task           {log.task}@{log.task_version}")
    print(f"dataset        {log.dataset_name} ({log.dataset_digest[:12]}…)")
    print(f"config_digest  {log.config_digest}")
    print(f"revision       {log.revision}")
    print("\nresultados por muestra:")
    for result in log.results:
        mark = result.score.value if result.score else "!"
        detail = result.error or (result.score.answer if result.score else "")
        print(f"  [{mark}] {result.sample_id:<28} {detail}")
    print("\nKPIs:")
    for key in (
        "scored",
        "process_errors",
        "accuracy",
        "over_refusal_rate",
        "decisive_error_rate",
    ):
        print(f"  {key:<22} {log.metrics[key]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=_REPO_ROOT / "results" / "eval")
    parser.add_argument("--corpus", type=Path, default=_CORPUS_DIR)
    args = parser.parse_args()

    log = run_task(build_task(dataset=build_dataset(args.corpus)), revision=_revision())
    _report(log)

    args.out.mkdir(parents=True, exist_ok=True)
    destination = args.out / f"{log.task}-{log.config_digest[:12]}.json"
    destination.write_text(log.to_json(), encoding="utf-8")
    print(f"\nlog: {destination.relative_to(_REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
