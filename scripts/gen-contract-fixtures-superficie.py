#!/usr/bin/env python3
"""Genera los fixtures de contrato de la superficie visual (spec
`docs/specs/superficie-visual.md` §8; decisión #125; convención
`docs/specs/README.md` §"Fixtures de costura — un solo origen").

ORIGEN ÚNICO = `TopologyResponse` (`chimera_api.reads`, modelo YA existente).
El caso ejercita el shape §4 completo — `verification` POR isla (freeze §9,
sin excepción) — y AMBAS formas de la convención de branch-ids C-8 (§8):
`edge_id_property` de GIS (FID numérico) y el id canónico `L{min}-{max}[-k]`.
Espejo byte-idéntico al Studio; el par [fixture + `topologySnapshotSchema` a
mano] es el contrato. Los casos de `run-metrics-recorded` (V2) y rvsp (V3)
quedan DECLARADOS — sus modelos origen son Fase 1 (regla del README: donde el
modelo aún no existe, el fixture verde lo entrega el dueño).

Falla-fuerte por construcción: mismo patrón anti-drift que
`gen-contract-fixtures-harness.py` (el test exige byte-identidad con lo que
este script produce hoy).
"""

from __future__ import annotations

import json
from pathlib import Path

from chimera_api.reads import TopologyResponse

REPO = Path(__file__).resolve().parent.parent
CANONICAL_DIR = REPO / "tests" / "fixtures" / "contract" / "superficie"
STUDIO_DIR = REPO / "apps" / "studio" / "src" / "fixtures" / "contract" / "superficie"


def _island(k: int, name: str, bus_ids: tuple[str, ...]) -> dict[str, object]:
    """Isla del shape §4 — id estable `island-{k}` (base de C4/M4)."""
    return {
        "id": f"island-{k}",
        "name": name,
        "bus_ids": list(bus_ids),
        "verification": {
            "verdict": "pass",
            "verifier_class": "execution",
            "level": "AL3",
            "anchor_kind": "execution",
            "method": "pandapower newton-raphson",
            "summary": f"isla {k}: conexa, con fuente, flujo converge",
        },
    }


def _cases() -> dict[str, object]:
    return {
        "topology-snapshot": TopologyResponse(
            topology_ref="ieee14-topology@v1",
            islands=(
                _island(1, "Norte", ("0", "1", "2", "3", "4", "5")),
                _island(2, "Sur", ("6", "7", "8", "9", "10", "11", "12", "13")),
            ),
            # AMBAS formas de branch-id (C-8): canónica determinista con y sin
            # paralela, y un edge_id_property de GIS (FID numérico como string).
            cut_branch_ids=("L3-6", "L4-8-2", "70143"),
            cut_cost=57070.0,
        ),
    }


def serialize(payload: object) -> str:
    """Forma canónica del fixture (snake_case de wire, claves ordenadas,
    optativos None omitidos → compat con `.optional()` de Zod)."""
    data = payload.model_dump(exclude_none=True)  # type: ignore[attr-defined]
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> int:
    CANONICAL_DIR.mkdir(parents=True, exist_ok=True)
    STUDIO_DIR.mkdir(parents=True, exist_ok=True)
    for case, payload in _cases().items():
        text = serialize(payload)
        (CANONICAL_DIR / f"{case}.json").write_text(text, encoding="utf-8")
        (STUDIO_DIR / f"{case}.json").write_text(text, encoding="utf-8")
        print(f"  {case}.json -> tests/ + apps/studio/ (byte-idéntico)")
    print(f"{len(_cases())} fixtures de contrato de superficie emitidos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
