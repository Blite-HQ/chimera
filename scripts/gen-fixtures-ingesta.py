#!/usr/bin/env python3
"""Genera los fixtures de contrato de la costura B↔A (ingesta).

docs/specs/README.md §Fixtures de costura: "el fixture de costura tiene UN
solo origen y ambos lados lo parsean" — el origen es Python (los modelos
Pydantic del contrato, `blite.verification.provenance`). Este generador
construye UNA instancia de cada rama de `Provenance` a través del modelo
Pydantic (auto-validante: si `ExternalSourceProvenance(...)`/
`DerivationProvenance(...)` no explota, ya es válida contra el contrato;
además se re-parsea con `parse_provenance` antes de escribir, mismo espíritu
que el 7/7 de `gen-example-bundle.py`) y escribe DOS salidas desde la MISMA
fuente:

- `tests/fixtures/contract/ingesta/{snapshot,derivation}-example.json`
- `apps/studio/src/fixtures/contract/ingesta/{snapshot,derivation}-example.json`
  (espejo — Vite solo importa dentro de `src/`)

Son ejemplos de contrato SINTÉTICOS por diseño (docs/specs/capability-ingesta.md
§Tests de contrato) — no datos reales de ningún corpus.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from blite.verification.provenance import (
    DerivationProvenance,
    ExternalSourceProvenance,
    parse_provenance,
)

REPO = Path(__file__).resolve().parent.parent

_CONTRACT_DIRS = (
    REPO / "tests" / "fixtures" / "contract" / "ingesta",
    REPO / "apps" / "studio" / "src" / "fixtures" / "contract" / "ingesta",
)


def _write_mirrored(filename: str, data: dict[str, Any]) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    for directory in _CONTRACT_DIRS:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / filename
        path.write_text(text, encoding="utf-8")
        print(f"escrito: {path.relative_to(REPO)}")


def _require_roundtrip(data: dict[str, Any], expected_type: type) -> None:
    """Auto-validante (mismo espíritu que el 7/7 de `gen-example-bundle.py`):
    el generador jamás escribe un fixture que su propio modelo no re-parsee."""
    parsed = parse_provenance(data)
    if not isinstance(parsed, expected_type):
        msg = f"round-trip de {expected_type.__name__} produjo {type(parsed).__name__}"
        raise TypeError(msg)


def main() -> int:
    snapshot = ExternalSourceProvenance(
        uri="https://services.example.gov/FeatureServer/0/query",
        retrieved_at=datetime(2026, 7, 24, 12, 0, 0, tzinfo=UTC),
        content_type="application/geo+json",
        http_status=200,
    )
    _require_roundtrip(snapshot.model_dump(mode="json"), ExternalSourceProvenance)

    derivation = DerivationProvenance(
        inputs=({"ref": "snapshot:example-source", "digest": "sha256:" + "a" * 64},),
        recipe={
            "capability": "blite.ingesta.geojson.to_graph",
            "version": "0.1.0",
            "params_digest": "sha256:" + "b" * 64,
            "code_ref": "git:HEAD",
        },
        run_id="example-run-1",
        assertions=(
            {"name": "node_geojson_schema_valid", "passed": True, "detail": None},
            {"name": "edge_geojson_schema_valid", "passed": True, "detail": None},
            {"name": "tabular_schema_valid", "passed": True, "detail": None},
        ),
    )
    _require_roundtrip(derivation.model_dump(mode="json"), DerivationProvenance)

    _write_mirrored("snapshot-example.json", snapshot.model_dump(mode="json"))
    _write_mirrored("derivation-example.json", derivation.model_dump(mode="json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
