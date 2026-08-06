#!/usr/bin/env python3
"""verify-bundle — el checklist del freeze §7 (+ punto 8, harness-agentico
§Contrato-5; + puntos 9/10/11 de Mejorado C5-C7), offline. [track Dylan #1]

EL beat anti-ceremonia: "auditable sin confiar en nosotros" (D20) — corre en
una segunda máquina, sin red, contra el Bundle exacto. La lógica vive en
`blite.certificate.bundle_check` (testeada adversarialmente); este CLI solo
reporta. Exit 0 SOLO con TODOS los puntos OK — un punto no verificable FALLA
(fail-closed), degradar el checklist a "firma válida" es exactamente lo que
T11 prohíbe. El denominador se deriva de `check_bundle` (nunca hardcodeado):
así el CLI no queda desincronizado si el checklist gana un punto nuevo.

La StatusList (C7) es OPCIONAL y esa es la resolución del choque con el
air-gap: sin ella la verificación sigue completa y el punto 11 DICE que la
revocación no se comprobó — imprimir "verificado" callando eso sería la
ceremonia que este script existe para no hacer.

Uso: verify-bundle.py <bundle.json> [--status-list <lista.json>]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from blite.certificate.bundle_check import check_bundle


def _leer(path: Path, que: str) -> dict[str, object] | None:
    if not path.exists():
        print(f"FALLA: {que} {path} no existe")
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str]) -> int:
    args = argv[1:]
    status_list_path: Path | None = None
    if "--status-list" in args:
        idx = args.index("--status-list")
        if idx + 1 >= len(args):
            print(__doc__)
            return 2
        status_list_path = Path(args[idx + 1])
        args = args[:idx] + args[idx + 2 :]
    if len(args) != 1:
        print(__doc__)
        return 2

    bundle = _leer(Path(args[0]), "bundle")
    if bundle is None:
        return 1
    status_list = None
    if status_list_path is not None:
        status_list = _leer(status_list_path, "status-list")
        if status_list is None:
            return 1

    results = check_bundle(bundle, status_list=status_list)
    total = len(results)
    for r in results:
        if r.ok:
            print(f"[{r.number}/{total}] OK — {r.name}")
        else:
            print(f"[{r.number}/{total}] FALLA — {r.name}:")
            for failure in r.failures:
                print(f"        · {failure}")
        for note in r.notes:
            print(f"        ⓘ {note}")
    ok = sum(1 for r in results if r.ok)
    print(f"{ok}/{total} puntos verificados")
    return 0 if ok == total else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
