"""capabilities_sim_api — recompute clásico del vector de la falla sembrada.

Superficie demo/seed del paquete sim (freeze §15.5, seed
`tests/seeds/test_seed_ciencia_falla_sembrada.py`): dado un `<familia>-<convencion>`
del corpus de islanding y un bus, recomputa el corte de la asignación canónica
con ese bus movido de isla, el ratio contra el óptimo congelado y las "minas"
(buses cuyo flip degrada CERO) de ambas convenciones de la familia.

El corpus JSON congelado es la fuente de verdad (knowledge/islanding/01 §1.6):
cada carga verifica el digest canónico y la consistencia corte(canónica)==óptimo
— cualquier discrepancia es `CorpusIntegrityError`, jamás un resultado.

ADR-029: el manifest de la capability sigue genérico; este módulo es la
superficie del seed, no entra en ningún CapabilityManifest.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "CorpusIntegrityError",
    "SeededFailureRecompute",
    "recompute_seeded_failure",
]

_CONVENTIONS = ("flujo", "uniforme")
_CORPUS_RELATIVE = Path("knowledge") / "islanding" / "corpus"

Edges = tuple[tuple[int, int, int], ...]


class CorpusIntegrityError(ValueError):
    """El JSON del corpus no pasa sus chequeos de integridad — fail-loud."""


@dataclass(frozen=True)
class SeededFailureRecompute:
    """Resultado del recompute: números del flip + minas por convención."""

    instance: str
    bus: int
    cut_value: int
    optimum: int
    r: float
    forbidden_flow: list[int]
    forbidden_uniform: list[int]


@dataclass(frozen=True)
class _Instance:
    n_nodes: int
    edges: Edges
    optimum: int
    canonical: tuple[int, ...]


def _cut_value(assignment: tuple[int, ...], edges: Edges) -> int:
    """Valor del corte: suma de pesos de aristas con extremos en islas distintas."""
    return sum(w for u, v, w in edges if assignment[u] != assignment[v])


def _flip(assignment: tuple[int, ...], bus: int) -> tuple[int, ...]:
    return tuple(1 - x if i == bus else x for i, x in enumerate(assignment))


def _verify_digest(raw: dict[str, Any], path: Path) -> None:
    """Receta §1.6: SHA-256 del JSON canónico SIN el campo `digest`."""
    record = {k: v for k, v in raw.items() if k != "digest"}
    canonical_json = json.dumps(
        record, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    recomputed = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    if recomputed != raw.get("digest"):
        msg = (
            f"{path.name}: el digest embebido no reproduce — el archivo "
            "congelado manda; una copia que no reproduce se reporta, no se usa"
        )
        raise CorpusIntegrityError(msg)


def _parse_instance(raw: dict[str, Any], path: Path) -> _Instance:
    try:
        n_nodes = int(raw["n_nodos"])
        edges: Edges = tuple(
            (int(u), int(v), int(w)) for u, v, w in raw["aristas"]
        )
        optimum = int(raw["optimo"])
        canonical = tuple(int(x) for x in raw["asignacion_canonica"])
    except (KeyError, TypeError, ValueError) as exc:
        msg = f"{path.name}: campo del corpus ausente o malformado: {exc}"
        raise CorpusIntegrityError(msg) from exc

    if len(canonical) != n_nodes:
        msg = (
            f"{path.name}: asignacion_canonica de largo {len(canonical)} "
            f"para {n_nodes} nodos"
        )
        raise CorpusIntegrityError(msg)
    if _cut_value(canonical, edges) != optimum:
        msg = (
            f"{path.name}: la asignacion_canonica no reproduce el optimo "
            f"({_cut_value(canonical, edges)} != {optimum}) — el digest es "
            "auto-referencial; esta consistencia es el chequeo independiente"
        )
        raise CorpusIntegrityError(msg)
    return _Instance(
        n_nodes=n_nodes, edges=edges, optimum=optimum, canonical=canonical
    )


def _load_instance(corpus_dir: Path, family: str, convention: str) -> _Instance:
    path = corpus_dir / f"{family}-{convention}.json"
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    _verify_digest(raw, path)
    return _parse_instance(raw, path)


def _zero_degradation_buses(inst: _Instance) -> list[int]:
    """Las minas del guion (§15.5): flips que dejan el corte EN el óptimo."""
    return [
        bus
        for bus in range(inst.n_nodes)
        if _cut_value(_flip(inst.canonical, bus), inst.edges) == inst.optimum
    ]


def _default_corpus_dir() -> Path:
    for base in (Path.cwd(), *Path.cwd().parents):
        candidate = base / _CORPUS_RELATIVE
        if candidate.is_dir():
            return candidate
    msg = (
        f"no se encontró {_CORPUS_RELATIVE} subiendo desde {Path.cwd()}; "
        "pase corpus_dir explícito"
    )
    raise FileNotFoundError(msg)


def _parse_instance_name(instance: str) -> tuple[str, str]:
    family, sep, convention = instance.rpartition("-")
    if not sep or not family:
        msg = (
            f"instance {instance!r} malformado: se espera "
            "'<familia>-<convencion>' (p. ej. 'ieee14-flujo')"
        )
        raise ValueError(msg)
    if convention not in _CONVENTIONS:
        msg = f"convencion {convention!r} desconocida: se espera una de {_CONVENTIONS}"
        raise ValueError(msg)
    return family, convention


def recompute_seeded_failure(
    *, instance: str, bus: int, corpus_dir: Path | None = None
) -> SeededFailureRecompute:
    """Recomputa el flip de `bus` sobre la asignación canónica de `instance`.

    Devuelve el corte degradado, el óptimo congelado, el ratio r y las minas
    (flips de degradación cero) de ambas convenciones de la familia.
    """
    family, convention = _parse_instance_name(instance)
    corpus = corpus_dir if corpus_dir is not None else _default_corpus_dir()

    requested = _load_instance(corpus, family, convention)
    if not 0 <= bus < requested.n_nodes:
        msg = f"bus {bus} fuera de rango [0, {requested.n_nodes})"
        raise ValueError(msg)

    by_convention = {
        conv: requested if conv == convention else _load_instance(corpus, family, conv)
        for conv in _CONVENTIONS
    }
    cut = _cut_value(_flip(requested.canonical, bus), requested.edges)
    return SeededFailureRecompute(
        instance=instance,
        bus=bus,
        cut_value=cut,
        optimum=requested.optimum,
        r=cut / requested.optimum,
        forbidden_flow=_zero_degradation_buses(by_convention["flujo"]),
        forbidden_uniform=_zero_degradation_buses(by_convention["uniforme"]),
    )
