#!/usr/bin/env python3
"""Importa las 19 corridas Nexus/Quantinuum del espejo `reto1-vanilla` — B3.

`docs/specs/evidencia-externa.md` (R3, dueño Sebas): tres capas por corrida,
mismo patrón que `scripts/gen-fixtures-ingesta.py`/`scripts/gen_corpus_ice.py`:

  1. blob crudo -> digest sobre bytes exactos (`ExternalSourceProvenance`,
     `capability-ingesta.md` — cero tipo nuevo).
  2. `NormalizedCounts` (esquema propio de counts) + su `DerivationProvenance`
     (`blite.verification.external_evidence`).
  3. `ExternalImportStatement` (in-toto Statement v1 / predicado SLSA propio)
     — custodia de LA IMPORTACIÓN, nunca sustituye el veredicto científico.

Lee el espejo SOLO-LECTURA (`reto1-vanilla/runs/nexus/*.json`, default
`<padre de este repo>/reto1-vanilla` — hermano bajo el mismo directorio
Quantathon; override con `--mirror-dir` o `BLITE_NEXUS_MIRROR`). Escribe
en `knowledge/nexus/` (statements/, normalized/, `index.json`,
`consensus.json`) — NUNCA en el espejo.

## `bit_order` EMPÍRICO (no adivinado)

Para cada corrida, decodifica TODOS los bitstrings muestreados bajo
`msb-left`/`msb-right`, recomputa el corte contra el grafo del corpus
(`knowledge/islanding/corpus/<instance>.json`) y compara el máximo corte
alcanzado contra `stats.best_cut` — el test G6
(`knowledge/quantum/08` §5, "la muestra dominante decodifica a corte 5")
generalizado a "el mejor corte muestreado decodifica al `best_cut`
reportado". En grafos chicos con cobertura casi completa de 2^n
(cr6/cr8, ~1024 shots sobre ≤256 estados) AMBOS órdenes pueden ser
consistentes con una corrida aislada — eso es señal real de la estructura
del grafo, no un error; el empate se rompe con el consenso de las corridas
donde SÍ hay señal inequívoca (documentado por corrida en `index.json`,
campo `bit_order_resolution`). Si NINGÚN orden reproduce `best_cut`, el
importador falla-fuerte (no inventa un valor).

## Honestidad de digests (freeze §11)

`circuit_digest`/`transpiled_circuit_digest` cubren la misma fuente
disponible (`instance`/`p`/`betas`/`gammas` — la definición determinista
del circuito QAOA lógico); la corrida cacheada NO trae los bytes del
circuito ya rebaseado al gate set nativo (QASM post-`AutoRebase`/HUGR), así
que `transpiled_circuit_digest` es la MEJOR representación disponible, no
una promesa de bytes que no existen — declarado en `DIGEST_COVERAGE_NOTES`
y en la assertion `digest_coverage_declared` de cada `DerivationProvenance`.
`noise_config_digest` cubre `{backend, noisy_simulation, error_params}`:
`error_params` es `None` para `H2-1LE` (emulador SIN ruido, ver
`reto1-vanilla/README.md`/`scripts/run_h2_emulator.py`) y un descriptor
declarativo (sin parámetros numéricos — la API cacheada no los expone) para
`H2-Emulator` (aplica el modelo de ruido H2 default de Quantinuum).

Correr desde la raíz del repo:  uv run python scripts/import_nexus_runs.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from blite.certificate.canonical import canonicalize
from blite.runtime.content_store import InMemoryContentStore
from blite.verification.evidence import ConsensusLeg, ConsensusReplicationPredicate
from blite.verification.external_evidence import (
    BitOrder,
    ExternalImportStatement,
    NormalizedCounts,
    normalize_counts,
)
from blite.verification.provenance import DerivationProvenance, ExternalSourceProvenance

REPO = Path(__file__).resolve().parent.parent
DEFAULT_MIRROR_DIR = REPO.parent / "reto1-vanilla" / "runs" / "nexus"
CORPUS_DIR = REPO / "knowledge" / "islanding" / "corpus"
OUT_DIR = REPO / "knowledge" / "nexus"
DOMAIN_ID = "nexus-import"
IMPORTED_BY = "scripts/import_nexus_runs.py"
CAPABILITY_ID = "blite.evidencia.nexus.normalize_counts"
CAPABILITY_VERSION = "0.1.0"
NOISELESS_DEVICE = "H2-1LE"
# Constante fija, NO wall-clock: "Determinista (re-correr = byte-idéntico)"
# (spec §Salida) exige que `retrieved_at`/`imported_at` no varíen entre
# corridas del importador — se ancla al día de la importación de este lote.
IMPORT_BATCH_AT = datetime(2026, 7, 24, tzinfo=UTC)

DIGEST_COVERAGE_NOTES: dict[str, str] = {
    "circuit_digest": (
        "canonicalize({kind, instance, p, betas, gammas}) — cubre la "
        "definición determinista del circuito QAOA lógico (ansatz + "
        "ángulos); NO son bytes de circuito."
    ),
    "transpiled_circuit_digest": (
        "misma fuente que circuit_digest (instance/p/betas/gammas), "
        "namespace distinto ('kind') — la corrida cacheada NO trae los "
        "bytes del circuito post-AutoRebase/QASM nativo ni el HUGR "
        "compilado; esta es la MEJOR representación disponible, declarada "
        "como tal (freeze §11, patrón 'ingerido≠ancla')."
    ),
    "noise_config_digest": (
        "canonicalize({kind, backend, noisy_simulation, error_params}) — "
        "error_params=None para H2-1LE (emulador sin ruido, documentado en "
        "reto1-vanilla/README.md); descriptor declarativo sin parámetros "
        "numéricos para H2-Emulator (modelo de ruido H2 default de "
        "Quantinuum, no expuesto por la respuesta cacheada de qnexus)."
    ),
}


def _cut(aristas: Sequence[Sequence[int]], assignment: Sequence[int]) -> int:
    return sum(w for i, j, w in aristas if assignment[i] != assignment[j])


def _decode_bitstring(bitstring: str, order: BitOrder) -> list[int]:
    chars = bitstring if order == "msb-left" else bitstring[::-1]
    return [int(ch) for ch in chars]


def _max_cut_over_samples(
    counts: dict[str, int], aristas: Sequence[Sequence[int]], order: BitOrder
) -> int:
    return max(_cut(aristas, _decode_bitstring(bs, order)) for bs in counts)


def _dominant_bitstring(counts: dict[str, int]) -> str:
    # Empate de conteo desambiguado por la clave (determinismo).
    return max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]


def candidate_bit_orders(
    run: dict[str, Any], aristas: Sequence[Sequence[int]]
) -> tuple[BitOrder, ...]:
    """Órdenes consistentes con `stats.best_cut` recomputado: el máximo
    corte alcanzado por CUALQUIER bitstring muestreado, decodificado bajo
    ese orden, debe igualar `best_cut` (test G6 generalizado)."""
    counts = run["counts"]
    best_cut = run["stats"]["best_cut"]
    orders: tuple[BitOrder, ...] = ("msb-left", "msb-right")
    return tuple(
        o for o in orders if _max_cut_over_samples(counts, aristas, o) == best_cut
    )


def dominant_bit_orders(
    run: dict[str, Any], aristas: Sequence[Sequence[int]]
) -> tuple[BitOrder, ...]:
    """Señal más fuerte: la muestra DOMINANTE (mayor conteo) también debe
    decodificar a `best_cut` — el vector G6 original tal cual."""
    counts = run["counts"]
    best_cut = run["stats"]["best_cut"]
    dominant = _dominant_bitstring(counts)
    orders: tuple[BitOrder, ...] = ("msb-left", "msb-right")
    return tuple(
        o for o in orders if _cut(aristas, _decode_bitstring(dominant, o)) == best_cut
    )


@dataclass(frozen=True, slots=True)
class BitOrderResolution:
    bit_order: BitOrder
    reason: Literal["unambiguous", "tie_broken_by_corpus_consensus"]
    consistent_orders: tuple[BitOrder, ...]
    narrowed_orders: tuple[BitOrder, ...]


def _tally_votes(
    narrowed_by_job: dict[str, tuple[BitOrder, ...]],
) -> dict[BitOrder, int]:
    votes: dict[BitOrder, int] = {"msb-left": 0, "msb-right": 0}
    for narrowed in narrowed_by_job.values():
        if len(narrowed) == 1:
            votes[narrowed[0]] += 1
    return votes


def resolve_bit_orders(
    records: Sequence[tuple[str, dict[str, Any], list[list[int]]]],
) -> dict[str, BitOrderResolution]:
    """`bit_order` por corrida, empírico. Dos pasadas: (1) resuelve cada
    corrida contra SU PROPIA evidencia (`candidate_bit_orders` +
    `dominant_bit_orders`); (2) las corridas que quedan empatadas (posible
    en grafos chicos con cobertura casi completa del espacio de estados) se
    desempatan por el consenso de las corridas YA resueltas sin ambigüedad
    — nunca por una constante fija sin evidencia. Falla-fuerte si una
    corrida no tiene NINGÚN orden consistente, o si el consenso global no
    es compatible localmente."""
    consistent_by_job: dict[str, tuple[BitOrder, ...]] = {}
    narrowed_by_job: dict[str, tuple[BitOrder, ...]] = {}
    for job_id, run, aristas in records:
        consistent = candidate_bit_orders(run, aristas)
        if not consistent:
            msg = (
                f"{job_id}: ningún bit_order reproduce stats.best_cut="
                f"{run['stats']['best_cut']} contra el corpus — falla-fuerte, "
                "no se adivina (docs/specs/evidencia-externa.md §Capa 2)"
            )
            raise ValueError(msg)
        dominant = dominant_bit_orders(run, aristas)
        narrowed: tuple[BitOrder, ...] = (
            tuple(o for o in consistent if o in dominant) or consistent
        )
        consistent_by_job[job_id] = consistent
        narrowed_by_job[job_id] = narrowed

    votes = _tally_votes(narrowed_by_job)
    resolutions: dict[str, BitOrderResolution] = {}
    for job_id, narrowed in narrowed_by_job.items():
        consistent = consistent_by_job[job_id]
        if len(narrowed) == 1:
            resolutions[job_id] = BitOrderResolution(
                narrowed[0], "unambiguous", consistent, narrowed
            )
            continue
        if votes["msb-left"] == votes["msb-right"]:
            msg = f"{job_id}: empate {narrowed} sin consenso global (votos {votes})"
            raise ValueError(msg)
        winner: BitOrder = max(votes, key=lambda o: votes[o])
        if winner not in narrowed:
            msg = f"{job_id}: consenso global {winner!r} incompatible con {narrowed}"
            raise ValueError(msg)
        resolutions[job_id] = BitOrderResolution(
            winner, "tie_broken_by_corpus_consensus", consistent, narrowed
        )
    return resolutions


def _digest_of(
    store: InMemoryContentStore, value: dict[str, Any], media_type: str
) -> str:
    ctx = {"domain_id": DOMAIN_ID}
    return store.put(canonicalize(value), media_type, ctx).digest


def _load_run(path: Path) -> tuple[bytes, dict[str, Any]]:
    raw_bytes = path.read_bytes()
    run: dict[str, Any] = json.loads(raw_bytes)
    return raw_bytes, run


def _load_corpus(corpus_dir: Path, instance: str) -> dict[str, Any]:
    path = corpus_dir / f"{instance}.json"
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _parse_timestamp(raw: str) -> datetime:
    return datetime.strptime(raw, "%Y%m%d-%H%M%S").replace(tzinfo=UTC)


def _build_source_provenance(
    run: dict[str, Any], retrieved_at: datetime
) -> ExternalSourceProvenance:
    """Capa 1 (spec §Capa 1) — el ancla es el blob (digest sobre bytes
    exactos, calculado aparte vía `ContentStore.put()` en `_process_run`),
    esta `Provenance` es el acompañante que documenta la procedencia. NO
    conocemos el instante real en que Nexus sirvió esta respuesta (leemos
    un espejo estático, no la API en vivo) — `retrieved_at` reutiliza
    honestamente el `timestamp` que la propia corrida declara (documentado
    aquí, no una hora de pared inventada)."""
    return ExternalSourceProvenance(
        uri=f"nexus://{run['project']}/{run['job_id']}",
        retrieved_at=retrieved_at,
        content_type="application/json",
    )


def _error_params_for(device: str, noisy: bool) -> dict[str, Any] | None:
    if not noisy:
        return None
    return {
        "model": "quantinuum-h2-default-noise-model",
        "source": "device_default",
        "device": device,
        "detail": (
            "parametros numericos (p1/p2/p_init/p_meas/...) no expuestos por "
            "la respuesta qnexus cacheada; el dispositivo aplica el modelo de "
            "ruido H2 default de Quantinuum del lado del servidor"
        ),
    }


def _circuit_digests(
    run: dict[str, Any],
    noisy: bool,
    error_params: dict[str, Any] | None,
    store: InMemoryContentStore,
) -> tuple[str, str, str]:
    """(circuit_digest, transpiled_circuit_digest, noise_config_digest) —
    honestidad documentada en `DIGEST_COVERAGE_NOTES`."""
    circuit_note = {
        "kind": "circuit_digest",
        "instance": run["instance"],
        "p": run["p"],
        "betas": run["betas"],
        "gammas": run["gammas"],
    }
    transpiled_note = {**circuit_note, "kind": "transpiled_circuit_digest"}
    noise_note = {
        "kind": "noise_config_digest",
        "backend": run["device"],
        "noisy_simulation": noisy,
        "error_params": error_params,
    }
    return (
        _digest_of(store, circuit_note, "application/json"),
        _digest_of(store, transpiled_note, "application/json"),
        _digest_of(store, noise_note, "application/json"),
    )


def _build_derivation_provenance(
    run: dict[str, Any],
    raw_digest: str,
    resolution: BitOrderResolution,
    noisy: bool,
    error_params: dict[str, Any] | None,
    store: InMemoryContentStore,
) -> DerivationProvenance:
    params = {
        "bit_order": resolution.bit_order,
        "noisy_simulation": noisy,
        "error_params": error_params,
    }
    params_digest = _digest_of(store, params, "application/json")
    return DerivationProvenance(
        inputs=({"ref": "nexus-response", "digest": raw_digest},),
        recipe={
            "capability": CAPABILITY_ID,
            "version": CAPABILITY_VERSION,
            "params_digest": "sha256:" + params_digest,
            "code_ref": "git:HEAD",
        },
        run_id=run["job_id"],
        assertions=(
            {
                "name": "bit_order_declared",
                "passed": True,
                "detail": {
                    "bit_order": resolution.bit_order,
                    "reason": resolution.reason,
                    "consistent_orders": list(resolution.consistent_orders),
                    "narrowed_orders": list(resolution.narrowed_orders),
                },
            },
            {
                "name": "bit_order_matches_recomputed_best_cut",
                "passed": True,
                "detail": {
                    "instance": run["instance"],
                    "best_cut": run["stats"]["best_cut"],
                },
            },
            {
                "name": "digest_coverage_declared",
                "passed": True,
                "detail": dict(DIGEST_COVERAGE_NOTES),
            },
        ),
    )


def _build_statement(
    run: dict[str, Any],
    normalized_digest: str,
    circuit_digest: str,
    transpiled_digest: str,
    noise_digest: str,
    finished_on: datetime,
) -> ExternalImportStatement:
    return ExternalImportStatement(
        subject_name=f"nexus-job:{run['job_id']}",
        subject_digest=normalized_digest,
        external_parameters={
            "circuit_digest": "sha256:" + circuit_digest,
            "shots_requested": run["stats"]["shots"],
        },
        resolved_dependencies=(
            {"name": "transpiled_circuit", "digest": {"sha256": transpiled_digest}},
            {"name": "noise_model", "digest": {"sha256": noise_digest}},
        ),
        builder_id=f"nexus://quantinuum/{run['device']}",
        invocation_id=run["job_id"],
        finished_on=finished_on,
    )


@dataclass(frozen=True, slots=True)
class RunImportResult:
    job_id: str
    instance: str
    p: int
    seed: int
    device: str
    bit_order: BitOrder
    bit_order_resolution: BitOrderResolution
    raw_blob_digest: str
    normalized_digest: str
    statement_digest: str
    circuit_digest: str
    transpiled_circuit_digest: str
    noise_config_digest: str
    betas: tuple[float, ...]
    gammas: tuple[float, ...]
    best_cut: int
    source_provenance: ExternalSourceProvenance
    normalized_counts: NormalizedCounts
    provenance: DerivationProvenance
    statement: ExternalImportStatement
    event: dict[str, Any] = field(repr=False)


def _process_run(
    path: Path,
    corpus_dir: Path,
    store: InMemoryContentStore,
    resolution: BitOrderResolution,
) -> RunImportResult:
    raw_bytes, run = _load_run(path)
    raw_digest = store.put(
        raw_bytes, "application/json", {"domain_id": DOMAIN_ID}
    ).digest
    finished_on = _parse_timestamp(run["timestamp"])
    source_provenance = _build_source_provenance(run, finished_on)

    device = str(run["device"])
    noisy = device != NOISELESS_DEVICE
    error_params = _error_params_for(device, noisy)

    normalized = normalize_counts(
        run,
        bit_order=resolution.bit_order,
        noisy_simulation=noisy,
        error_params=error_params,
    )
    normalized_digest = _digest_of(
        store, normalized.model_dump(mode="json"), "application/json"
    )
    provenance = _build_derivation_provenance(
        run, raw_digest, resolution, noisy, error_params, store
    )

    circuit_digest, transpiled_digest, noise_digest = _circuit_digests(
        run, noisy, error_params, store
    )
    statement = _build_statement(
        run,
        normalized_digest,
        circuit_digest,
        transpiled_digest,
        noise_digest,
        finished_on,
    )
    statement_digest = _digest_of(
        store, statement.to_intoto(), "application/vnd.in-toto+json"
    )

    event = {
        "job_id": run["job_id"],
        "backend_id": device,
        "statement_digest": statement_digest,
        "raw_blob_digest": raw_digest,
        "normalized_digest": normalized_digest,
        "imported_by": IMPORTED_BY,
        "imported_at": IMPORT_BATCH_AT.isoformat(),
    }
    return RunImportResult(
        job_id=run["job_id"],
        instance=run["instance"],
        p=int(run["p"]),
        seed=int(run["seed"]),
        device=device,
        bit_order=resolution.bit_order,
        bit_order_resolution=resolution,
        raw_blob_digest=raw_digest,
        normalized_digest=normalized_digest,
        statement_digest=statement_digest,
        circuit_digest=circuit_digest,
        transpiled_circuit_digest=transpiled_digest,
        noise_config_digest=noise_digest,
        # Copia FIEL de los ángulos que la corrida usó — no se re-derivan ni
        # se redondean: ya son la fuente de `circuit_digest`, y un ángulo
        # ingerido distinto del que se corrió rompería esa correspondencia.
        betas=tuple(float(a) for a in run["betas"]),
        gammas=tuple(float(a) for a in run["gammas"]),
        best_cut=int(run["stats"]["best_cut"]),
        source_provenance=source_provenance,
        normalized_counts=normalized,
        provenance=provenance,
        statement=statement,
        event=event,
    )


def _pair_key(result: RunImportResult) -> tuple[str, int]:
    return (result.instance, result.p)


def build_consensus_predicates(
    results: Sequence[RunImportResult],
) -> tuple[dict[str, Any], ...]:
    """`ConsensusReplicationPredicate` con `legs` — una por (instance, p)
    corrida en ≥2 backends independientes (spec §`ConsensusReplicationPredicate`).
    `agreement` = los backends concuerdan en `best_cut`."""
    grouped: dict[tuple[str, int], list[RunImportResult]] = {}
    for result in results:
        grouped.setdefault(_pair_key(result), []).append(result)

    predicates: list[dict[str, Any]] = []
    for (instance, p), group in sorted(grouped.items()):
        if len(group) < 2:
            continue
        ordered = sorted(group, key=lambda r: r.device)
        legs = tuple(
            ConsensusLeg(
                seed=r.seed,
                backend_id=r.device,
                transpiled_circuit_digest=r.transpiled_circuit_digest,
                noise_config_digest=r.noise_config_digest,
            )
            for r in ordered
        )
        agreement = len({r.best_cut for r in ordered}) == 1
        predicate = ConsensusReplicationPredicate(
            replicas=len(legs),
            seeds=tuple(leg.seed for leg in legs),
            agreement=agreement,
            legs=legs,
        )
        predicates.append(
            {
                "instance": instance,
                "p": p,
                "job_ids": [r.job_id for r in ordered],
                "predicate": predicate.model_dump(mode="json"),
            }
        )
    return tuple(predicates)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


@dataclass(frozen=True, slots=True)
class ImportSummary:
    results: tuple[RunImportResult, ...]
    consensus: tuple[dict[str, Any], ...]


def run_import(mirror_dir: Path, corpus_dir: Path, out_dir: Path) -> ImportSummary:
    """Orquesta las tres capas para las corridas en `mirror_dir` y escribe
    `out_dir/{statements,normalized}/*.json` + `index.json` +
    `consensus.json`. Determinista: mismos 19 archivos de entrada -> mismos
    bytes de salida (ningún wall-clock, `IMPORT_BATCH_AT` es constante)."""
    paths = sorted(mirror_dir.glob("*.json"))
    if not paths:
        msg = f"sin corridas en {mirror_dir} — ¿espejo reto1-vanilla montado?"
        raise FileNotFoundError(msg)

    raw_by_path = {path: _load_run(path) for path in paths}
    aristas_by_instance = {
        run["instance"]: _load_corpus(corpus_dir, run["instance"])["aristas"]
        for _, run in raw_by_path.values()
    }
    records = [
        (run["job_id"], run, aristas_by_instance[run["instance"]])
        for _, run in raw_by_path.values()
    ]
    resolutions = resolve_bit_orders(records)

    store = InMemoryContentStore()
    results: list[RunImportResult] = []
    for path in paths:
        _, run = raw_by_path[path]
        results.append(
            _process_run(path, corpus_dir, store, resolutions[run["job_id"]])
        )

    for result in results:
        stem = f"{result.instance}-p{result.p}-s{result.seed}-{result.device}"
        _write_json(
            out_dir / "normalized" / f"{stem}.json",
            {
                "source_provenance": result.source_provenance.model_dump(mode="json"),
                "normalized_counts": result.normalized_counts.model_dump(mode="json"),
                "provenance": result.provenance.model_dump(mode="json"),
            },
        )
        _write_json(
            out_dir / "statements" / f"{stem}.json", result.statement.to_intoto()
        )

    consensus = build_consensus_predicates(results)
    _write_json(out_dir / "consensus.json", list(consensus))
    _write_json(
        out_dir / "index.json",
        {
            "digest_coverage_notes": DIGEST_COVERAGE_NOTES,
            "imports": [
                {
                    "job_id": r.job_id,
                    "instance": r.instance,
                    "p": r.p,
                    "seed": r.seed,
                    "backend_id": r.device,
                    "bit_order": r.bit_order,
                    "bit_order_resolution": {
                        "reason": r.bit_order_resolution.reason,
                        "consistent_orders": list(
                            r.bit_order_resolution.consistent_orders
                        ),
                        "narrowed_orders": list(r.bit_order_resolution.narrowed_orders),
                    },
                    "raw_blob_digest": r.raw_blob_digest,
                    "normalized_digest": r.normalized_digest,
                    "statement_digest": r.statement_digest,
                    "circuit_digest": r.circuit_digest,
                    "transpiled_circuit_digest": r.transpiled_circuit_digest,
                    "noise_config_digest": r.noise_config_digest,
                    # V3/M20 — los ángulos que Quantinuum corrió, legibles sin
                    # salir del repo. Ya eran la FUENTE de `circuit_digest`, así
                    # que persistirlos no agrega procedencia nueva ni mueve
                    # ningún digest; los saca del espejo solo-lectura para que
                    # ⟨C⟩ se pueda evaluar en ELLOS y no en ángulos propios.
                    "betas": list(r.betas),
                    "gammas": list(r.gammas),
                    "event": r.event,
                }
                for r in results
            ],
        },
    )
    return ImportSummary(results=tuple(results), consensus=consensus)


def _resolve_mirror_dir(cli_value: str | None) -> Path:
    if cli_value:
        return Path(cli_value)
    env_value = os.environ.get("BLITE_NEXUS_MIRROR")
    if env_value:
        return Path(env_value) / "runs" / "nexus"
    return DEFAULT_MIRROR_DIR


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mirror-dir",
        default=None,
        help=f"runs/nexus del espejo reto1-vanilla (default: {DEFAULT_MIRROR_DIR})",
    )
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    args = parser.parse_args(argv)

    mirror_dir = _resolve_mirror_dir(args.mirror_dir)
    summary = run_import(mirror_dir, CORPUS_DIR, Path(args.out_dir))

    print(f"{len(summary.results)} corridas importadas desde {mirror_dir}")
    votes: dict[BitOrder, int] = {"msb-left": 0, "msb-right": 0}
    for r in summary.results:
        votes[r.bit_order] += 1
    print(f"bit_order: {dict(votes)}")
    print(f"consensus_replication con legs: {len(summary.consensus)}")
    for entry in summary.consensus:
        print(f"  {entry['instance']} p={entry['p']} job_ids={entry['job_ids']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
