#!/usr/bin/env python3
"""verify-bundle — el checklist de 7 puntos del freeze §7, offline. [track Dylan #1]

EL beat anti-ceremonia: "auditable sin confiar en nosotros" (D20) — corre en
una segunda máquina, sin red, contra el Bundle exacto. La lógica vive en
`blite.certificate.bundle_check` (testeada adversarialmente); este CLI solo
reporta. Exit 0 SOLO con 7/7 OK — un punto no verificable FALLA (fail-closed),
degradar el checklist a "firma válida" es exactamente lo que T11 prohíbe.

Uso: verify-bundle.py <bundle.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from blite.certificate.bundle_check import check_bundle


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    bundle_path = Path(argv[1])
    if not bundle_path.exists():
        print(f"FALLA: bundle {bundle_path} no existe")
        return 1
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    results = check_bundle(bundle)
    for r in results:
        if r.ok:
            print(f"[{r.number}/7] OK — {r.name}")
        else:
            print(f"[{r.number}/7] FALLA — {r.name}:")
            for failure in r.failures:
                print(f"        · {failure}")
    ok = sum(1 for r in results if r.ok)
    print(f"{ok}/7 puntos verificados")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
