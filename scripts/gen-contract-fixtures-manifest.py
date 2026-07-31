#!/usr/bin/env python3
"""Genera el fixture de contrato del manifest v2 (spec
`docs/specs/manifest-v2-sdk.md` §"Tests de contrato"; decisión #127;
convención `docs/specs/README.md` §"Fixtures de costura — un solo origen").

ORIGEN ÚNICO = el dataclass `CapabilityManifest` del SDK (v2 desde C1):
dataclass → `asdict` (la letra de S-E) — el wire serializa TODO, incluido
`execution_profile` con su default in-process explícito.

Falla-fuerte por construcción: mismo patrón anti-drift que los otros
generadores de contrato (byte-identidad exigida por el test).
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from blite_capability.manifest import CapabilityManifest

REPO = Path(__file__).resolve().parent.parent
CANONICAL_DIR = REPO / "tests" / "fixtures" / "contract" / "manifest"
STUDIO_DIR = REPO / "apps" / "studio" / "src" / "fixtures" / "contract" / "manifest"


def _cases() -> dict[str, CapabilityManifest]:
    return {
        "capability-manifest-v2": CapabilityManifest(
            id="blite.example.echo",
            description="Generic echo capability (contract fixture)",
            input_schema={
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
            output_schema={
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
            side_effects="pure",
            required_permission="capability:invoke",
            interaction="request_response",
            version="0.1.0",
            tags=("example",),
        ),
    }


def serialize(manifest: CapabilityManifest) -> str:
    """Forma canónica del fixture (asdict, claves ordenadas, tuple→list)."""
    data = dataclasses.asdict(manifest)
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> int:
    CANONICAL_DIR.mkdir(parents=True, exist_ok=True)
    STUDIO_DIR.mkdir(parents=True, exist_ok=True)
    for case, manifest in _cases().items():
        text = serialize(manifest)
        (CANONICAL_DIR / f"{case}.json").write_text(text, encoding="utf-8")
        (STUDIO_DIR / f"{case}.json").write_text(text, encoding="utf-8")
        print(f"  {case}.json -> tests/ + apps/studio/ (byte-idéntico)")
    print(f"{len(_cases())} fixtures de contrato del manifest emitidos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
