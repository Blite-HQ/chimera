#!/usr/bin/env python3
"""verify-bundle — el checklist del freeze §7 (+ punto 8, harness-agentico
§Contrato-5), offline. [track Dylan #1]

EL beat anti-ceremonia: "auditable sin confiar en nosotros" (D20) — corre en
una segunda máquina, sin red, contra el Bundle exacto. La lógica vive en
`blite.certificate.bundle_check` (testeada adversarialmente); este CLI solo
reporta. Exit 0 SOLO con TODOS los puntos OK — un punto no verificable FALLA
(fail-closed), degradar el checklist a "firma válida" es exactamente lo que
T11 prohíbe. El denominador se deriva de `check_bundle` (nunca hardcodeado):
así el CLI no queda desincronizado si el checklist gana un punto nuevo.

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
    total = len(results)
    for r in results:
        if r.ok:
            print(f"[{r.number}/{total}] OK — {r.name}")
        else:
            print(f"[{r.number}/{total}] FALLA — {r.name}:")
            for failure in r.failures:
                print(f"        · {failure}")
    ok = sum(1 for r in results if r.ok)
    print(f"{ok}/{total} puntos verificados")
    return 0 if ok == total else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
