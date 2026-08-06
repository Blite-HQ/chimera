#!/usr/bin/env python3
"""Guard de `knowledge/nexus/` — la cadena de digests de la evidencia externa.

    uv run python scripts/verify_nexus_digests.py

`knowledge/nexus/` es el ÚNICO directorio de datos estampados que no tenía
guard (censo 07 §8.5-4). Su README declara la línea roja —«NADA de este
directorio se re-digesta ni se regenera»— y hasta hoy eso vivía solo en prosa:
un archivo editado a mano, un import re-corrido con otro snapshot o un JSON
añadido sin registrar pasaban sin que nada los viera.

Qué verifica, por fila de `index.json`:

1. **normalized** — `sha256(canonicalize(archivo["normalized_counts"]))` es el
   `normalized_digest` de la fila.
2. **statement** — `sha256(canonicalize(archivo entero))` es el
   `statement_digest`.
3. **el eslabón in-toto** — el `subject[0].digest.sha256` del statement es el
   `normalized_digest`: es lo que hace que la attestation certifique ESTOS
   counts y no otros.
4. **coherencia interna** — los digests dentro de `event` coinciden con los de
   la fila que los contiene.
5. **cero huérfanos** — ningún archivo en `normalized/` o `statements/` fuera
   del índice, y ninguna fila sin archivo.
6. **consenso** — cada `job_id` de `consensus.json` existe en el índice.

Se recanonicaliza en vez de comparar bytes: el digest manda, no el formato
(misma doctrina que `verify_corpus_digests.py`). Y se usa el MISMO
`canonicalize` del anexo congelado que usó el importador — un guard con su
propia serialización estaría verificando otra cosa.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from blite.certificate.canonical import canonicalize

_REPO_ROOT = Path(__file__).parents[1]
_NEXUS_DIR = _REPO_ROOT / "knowledge" / "nexus"
_INDEX = _NEXUS_DIR / "index.json"
_CONSENSUS = _NEXUS_DIR / "consensus.json"


def _digest(value: Any) -> str:
    return hashlib.sha256(canonicalize(value)).hexdigest()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _stem(row: dict[str, Any]) -> str:
    """Mismo nombre que arma el importador (`import_nexus_runs.py:581`)."""
    return f"{row['instance']}-p{row['p']}-s{row['seed']}-{row['backend_id']}"


def _check_row(row: dict[str, Any], problems: list[str]) -> str | None:
    stem = _stem(row)
    normalized_path = _NEXUS_DIR / "normalized" / f"{stem}.json"
    statement_path = _NEXUS_DIR / "statements" / f"{stem}.json"

    if not normalized_path.is_file():
        problems.append(f"{stem}: falta normalized/{stem}.json")
        return None
    if not statement_path.is_file():
        problems.append(f"{stem}: falta statements/{stem}.json")
        return None

    normalized = _load(normalized_path)
    statement = _load(statement_path)

    got = _digest(normalized["normalized_counts"])
    if got != row["normalized_digest"]:
        problems.append(
            f"{stem}: normalized_digest no coincide\n"
            f"    índice:    {row['normalized_digest']}\n"
            f"    recomputado: {got}"
        )

    got_stmt = _digest(statement)
    if got_stmt != row["statement_digest"]:
        problems.append(
            f"{stem}: statement_digest no coincide\n"
            f"    índice:    {row['statement_digest']}\n"
            f"    recomputado: {got_stmt}"
        )

    subjects = statement.get("subject", [])
    subject_digest = subjects[0]["digest"]["sha256"] if subjects else None
    if subject_digest != row["normalized_digest"]:
        problems.append(
            f"{stem}: el statement certifica OTROS counts — subject[0] es "
            f"{subject_digest}, la fila dice {row['normalized_digest']}"
        )

    event = row.get("event", {})
    for field in ("raw_blob_digest", "normalized_digest", "statement_digest"):
        if event.get(field) != row.get(field):
            problems.append(
                f"{stem}: `event.{field}` ({event.get(field)}) discrepa de la "
                f"fila ({row.get(field)})"
            )
    return stem


def main() -> int:
    if not _INDEX.is_file():
        print(f"no existe {_INDEX.relative_to(_REPO_ROOT)}", file=sys.stderr)
        return 1

    index = _load(_INDEX)
    rows: list[dict[str, Any]] = index["imports"]
    problems: list[str] = []
    stems: set[str] = set()

    for row in rows:
        stem = _check_row(row, problems)
        if stem is not None:
            stems.add(stem)

    for subdir in ("normalized", "statements"):
        on_disk = {p.stem for p in (_NEXUS_DIR / subdir).glob("*.json")}
        for orphan in sorted(on_disk - stems):
            problems.append(
                f"{subdir}/{orphan}.json existe pero NO está en index.json — "
                "un archivo estampado sin registro no es evidencia"
            )

    indexed_jobs = {row["job_id"] for row in rows}
    for group in _load(_CONSENSUS):
        for job_id in group["job_ids"]:
            if job_id not in indexed_jobs:
                problems.append(
                    f"consensus.json cita el job {job_id}, que no está en el índice"
                )

    print(f"filas del índice: {len(rows)}   archivos verificados: {len(stems)}")
    if problems:
        print(f"\nVEREDICTO: {len(problems)} problema(s)\n")
        for problem in problems:
            print(f"  - {problem}")
        print(
            "\nRegla del README de knowledge/nexus: se REPORTA, jamás se "
            "sobreescribe.\nRestaurar con:  git restore knowledge/nexus"
        )
        return 1

    print("VEREDICTO: cadena de digests íntegra (normalized → statement → subject)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
