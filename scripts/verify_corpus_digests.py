#!/usr/bin/env python3
"""Verifica los 6 JSON del corpus: digest interno (islanding/01 SS1.6) y tabla del freeze SS15.3.

Correr desde la raiz del repo:  uv run python scripts/verify_corpus_digests.py
Regla 15.3: el digest manda (no los bytes del archivo - fines de linea no cuentan).
"""

import glob
import hashlib
import json

ESPERADOS_FREEZE_15_3 = {
    "ieee9-uniforme":  "dee38cdeea9bb35305de94308169368216838503673d3be57f0e7bea42677520",
    "ieee9-flujo":     "59fb22e6ec0afd3b3caf34fb4e46b2f8003c1ea8524fcd8b06dabd3f1c52477b",
    "ieee14-uniforme": "fb9c3780d9cf06a25910b631e92c83f3c6ce5272192f216fee6101b12dd32bd4",
    "ieee14-flujo":    "c7880bb0d254d2d5f91c21cfd7cf0a5ac1cb9c88261c15b94cb7b22d6fd896ad",
    "ieee30-uniforme": "a864122e83585d19921fcb00857aea1b8f4f4248a291a7a6f9d98e1b2df25a5b",
    "ieee30-flujo":    "a3aed52a8c59cc2a1e44073995eb755e75e04725e997729d0fc8f662ad08c600",
}


def main() -> None:
    ok = True
    archivos = sorted(glob.glob("knowledge/islanding/corpus/*.json"))
    if len(archivos) != 6:
        print(f"AVISO: se esperaban 6 archivos, hay {len(archivos)}")
    for f in archivos:
        reg = json.load(open(f, encoding="utf-8"))
        embebido = reg.pop("digest")
        calculado = hashlib.sha256(
            json.dumps(reg, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        ).hexdigest()
        nombre = f.replace("\\", "/").split("/")[-1][:-5]
        interno = "interno OK " if calculado == embebido else "INTERNO ROTO"
        freeze = "freeze OK" if embebido == ESPERADOS_FREEZE_15_3.get(nombre) else "!= FREEZE"
        ok = ok and calculado == embebido and embebido == ESPERADOS_FREEZE_15_3.get(nombre)
        print(f"{nombre:18s} {interno}  {freeze}")
    print()
    if ok:
        print("VEREDICTO: 6/6 digests correctos - la regeneracion reproduce la identidad congelada")
        print("(si git marca los archivos como modified, es solo formato/fines de linea:")
        print(" restauralos con  git restore knowledge/islanding/corpus/  - el congelado manda)")
    else:
        print("VEREDICTO: HAY DIFERENCIAS - regla del freeze: se REPORTA, no se sobreescribe.")
        print("Restaurar con:  git restore knowledge/islanding/corpus/")


if __name__ == "__main__":
    main()
