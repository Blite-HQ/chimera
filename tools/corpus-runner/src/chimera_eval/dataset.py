"""`Sample` y `Dataset` — la mitad de datos de la forma Dataset→Task→Solver→Scorer.

Una divergencia deliberada con Inspect (trust/17 §1.2, «lo que no calza»): allí
`Target` es estrictamente `str | list[str]`, así que una partición de grafo o una
serie numérica hay que JSON-encodearla peleando contra el tipo. Acá `target` es
un valor JSON estructurado desde el principio — el corpus de esta casa tiene
óptimos y series, no respuestas de texto.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from chimera_eval.score import JSONValue, empty_metadata

_DIGEST_DOMAIN = "chimera/eval-dataset/v1"
"""Prefijo de dominio versionado (misma disciplina que el anexo de
canonicalización y que S-F): cambiar cómo se digesta = bump del prefijo, jamás
un digest nuevo con el mismo nombre.

Esto NO es el canonicalizador de certificados: un `EvalLog` no es evidencia
firmada y no debe acoplarse a un contrato congelado. Por eso lleva su propio
prefijo y su propia serialización.
"""


def canonical_json(value: JSONValue) -> str:
    """JSON estable: llaves ordenadas, sin espacios, UTF-8 literal."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_of(value: JSONValue, domain: str) -> str:
    return hashlib.sha256(f"{domain}\n{canonical_json(value)}".encode()).hexdigest()


@dataclass(frozen=True)
class Sample:
    """Una unidad de evaluación: qué se le da al solver y qué se espera."""

    id: str
    input: JSONValue
    target: JSONValue
    metadata: Mapping[str, JSONValue] = field(default_factory=empty_metadata)

    def as_json(self) -> dict[str, JSONValue]:
        return {
            "id": self.id,
            "input": self.input,
            "target": self.target,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class Dataset:
    """Un corpus ordenado de muestras, con identidad propia."""

    name: str
    samples: tuple[Sample, ...]

    def digest(self) -> str:
        """Identidad del corpus: nombre + muestras EN ORDEN.

        El orden cuenta a propósito — un corpus reordenado es otro corpus, y
        dos ablaciones solo son comparables si corrieron sobre el mismo.
        """
        return digest_of(
            {"name": self.name, "samples": [s.as_json() for s in self.samples]},
            _DIGEST_DOMAIN,
        )

    def __len__(self) -> int:
        return len(self.samples)


def json_dataset(path: Path, name: str | None = None) -> Dataset:
    """Carga un corpus desde un JSON `{"samples": [{id, input, target, metadata?}]}`."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    samples = tuple(
        Sample(
            id=str(item["id"]),
            input=item.get("input"),
            target=item.get("target"),
            metadata=item.get("metadata", {}),
        )
        for item in raw["samples"]
    )
    return Dataset(name=name or path.stem, samples=samples)
