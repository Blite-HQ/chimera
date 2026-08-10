#!/usr/bin/env python3
"""Proyecta el mapa índice→nodo de una instancia ESTAMPADA del corpus al
Studio, para que el overlay de partición pueda reconciliar los buses del
payload con las features del GeoJSON (V1/M18).

Correr desde la raíz del repo:  uv run python scripts/gen-studio-ice-instance.py
Salida: apps/studio/src/fixtures/ice/instancia.json

Por qué existe: el payload de partición (`superficie-visual.md` §4) cita
`bus_ids` — índices de la instancia derivada, no nombres de subestación. El
mapa pinta features geográficas nombradas. El puente entre ambos es el mapa
`nodos` que la instancia YA estampó con su digest; copiarlo a mano al Studio
sería una segunda fuente de verdad que se desincronizaría en silencio.

Qué NO hace: no re-deriva nada ni recalcula digests. Copia el `nodos` y el
`digest` del registro estampado tal cual — el digest viaja para que el
consumidor pueda decir CUÁL instancia está reconciliando, y para que el test
anti-drift falle si el corpus cambia y esta proyección no.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CORPUS = REPO / "knowledge" / "islanding" / "corpus"
OUT = REPO / "apps" / "studio" / "src" / "fixtures" / "ice" / "instancia.json"

INSTANCE_SLUG = "ice-uniforme"


def build(slug: str = INSTANCE_SLUG) -> dict[str, object]:
    record = json.loads((CORPUS / f"{slug}.json").read_text(encoding="utf-8"))
    return {
        "slug": slug,
        "instancia": record["instancia"],
        "convencion": record["convencion"],
        "digest": record["digest"],
        "n_nodos": record["n_nodos"],
        "nodos": record["nodos"],
    }


def serialize(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(serialize(build()), encoding="utf-8")
    print(f"instancia {INSTANCE_SLUG} proyectada -> {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
