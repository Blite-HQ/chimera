#!/usr/bin/env python3
"""Verifica TODO `knowledge/islanding/corpus/*.json`: digest interno
(islanding/01 SS1.6, self-consistencia) sobre cada archivo, más identidad
pinneada para dos tablas de instancias conocidas.

Correr desde la raiz del repo:  uv run python scripts/verify_corpus_digests.py
Regla 15.3: el digest manda (no los bytes del archivo - fines de linea no cuentan).

Dos tablas de identidad pinneada, disjuntas por nombre de archivo:
- `ESPERADOS_FREEZE_15_3` — los 8 IEEE del freeze SS15.3. CONGELADA/INMUTABLE:
  jamas se le agrega ni se le edita una fila (regla del freeze: un cambio
  aqui se REPORTA, nunca se sobreescribe el corpus para que combine).
- `ESPERADOS_CHIMERA_B2` — las 6 instancias nuevas de B2 (cr6/cr8 x
  {uniforme,voltaje}, copiadas verbatim del espejo reto1-vanilla; ice x
  {uniforme,voltaje}, derivadas por `scripts/gen_corpus_ice.py` a traves de
  `blite.ingesta.geojson.to_graph`). Pinneada tambien: un cambio silencioso
  en la derivacion (o una regeneracion con otro snapshot) debe romper este
  guard, no pasar inadvertido.

Cualquier archivo del corpus que NO aparezca en ninguna tabla solo se
verifica por self-consistencia interna (nunca fue una suposicion de "deben
ser exactamente 8" - el corpus crece; el guard corre sobre TODO lo que haya
en el directorio).
"""

import glob
import hashlib
import json

ESPERADOS_FREEZE_15_3 = {
    "ieee6-uniforme": "bcce660e0dac057db322999496612bb48b1f51e947180b7f8c77af5b4bca2928",
    "ieee6-flujo": "0e29de1161f14dcdd5a9ffe3e9620f52868197e46b931e35a39b04611411a9e5",
    "ieee9-uniforme": "dee38cdeea9bb35305de94308169368216838503673d3be57f0e7bea42677520",
    "ieee9-flujo": "59fb22e6ec0afd3b3caf34fb4e46b2f8003c1ea8524fcd8b06dabd3f1c52477b",
    "ieee14-uniforme": "fb9c3780d9cf06a25910b631e92c83f3c6ce5272192f216fee6101b12dd32bd4",
    "ieee14-flujo": "c7880bb0d254d2d5f91c21cfd7cf0a5ac1cb9c88261c15b94cb7b22d6fd896ad",
    "ieee30-uniforme": "a864122e83585d19921fcb00857aea1b8f4f4248a291a7a6f9d98e1b2df25a5b",
    "ieee30-flujo": "a3aed52a8c59cc2a1e44073995eb755e75e04725e997729d0fc8f662ad08c600",
}

ESPERADOS_CHIMERA_B2 = {
    "cr6-uniforme": "e8b2121c61399aa758a356835f1e849e435377ebc2eadf0dd08356c702b680db",
    "cr6-voltaje": "aab9f07fd8e7f6be84d90fc97493de3603b82b3dec80627699051dc706e3dd0c",
    "cr8-uniforme": "66bb6c5ae0eadb1c697436ea36c069b3bf3c3a4ef436d1eda9540a3e79f91392",
    "cr8-voltaje": "0af00267250f0838ce5445659238c180fe88771383001aa4c745e36462d1aa5b",
    "ice-uniforme": "0078d201ff590345598ab0d7698a724cc642eaec4dca660a4ec66361402485a7",
    "ice-voltaje": "7bcda6747ac19bda4f8ef9cedc87a5d8c1185a459a08c5c6beb9662ee12d9d0d",
}


def _tabla_pin(nombre: str) -> tuple[str, str | None]:
    """(etiqueta de la tabla, digest esperado) — None si el archivo no esta
    pinneado en ninguna tabla (solo se le exige self-consistencia)."""
    if nombre in ESPERADOS_FREEZE_15_3:
        return "freeze-15.3", ESPERADOS_FREEZE_15_3[nombre]
    if nombre in ESPERADOS_CHIMERA_B2:
        return "chimera-b2", ESPERADOS_CHIMERA_B2[nombre]
    return "sin-tabla", None


def main() -> int:
    ok = True
    archivos = sorted(glob.glob("knowledge/islanding/corpus/*.json"))
    internos_ok = 0
    pinneados_ok = 0
    pinneados_total = 0

    for f in archivos:
        reg = json.load(open(f, encoding="utf-8"))
        embebido = reg.pop("digest")
        calculado = hashlib.sha256(
            json.dumps(
                reg, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode()
        ).hexdigest()
        nombre = f.replace("\\", "/").split("/")[-1][:-5]
        interno_ok = calculado == embebido
        internos_ok += int(interno_ok)

        tabla, esperado = _tabla_pin(nombre)
        if esperado is not None:
            pinneados_total += 1
            pin_ok = embebido == esperado
            pinneados_ok += int(pin_ok)
        else:
            pin_ok = True  # sin tabla -> no reprueba el veredicto por esto

        ok = ok and interno_ok and pin_ok
        interno_txt = "interno OK " if interno_ok else "INTERNO ROTO"
        pin_txt = {
            "freeze-15.3": "freeze OK" if pin_ok else "!= FREEZE",
            "chimera-b2": "b2 OK" if pin_ok else "!= B2",
            "sin-tabla": "sin tabla pinneada",
        }[tabla]
        print(f"{nombre:18s} {interno_txt}  {pin_txt}")

    print()
    print(
        f"internos: {internos_ok}/{len(archivos)}   "
        f"pinneados: {pinneados_ok}/{pinneados_total} "
        f"(freeze-15.3={len(ESPERADOS_FREEZE_15_3)}, chimera-b2={len(ESPERADOS_CHIMERA_B2)})"
    )
    if ok:
        print(
            f"VEREDICTO: {len(archivos)}/{len(archivos)} digests internos OK, "
            f"{pinneados_ok}/{pinneados_total} coinciden con su tabla pinneada"
        )
        print(
            "(si git marca los archivos como modified, es solo formato/fines de linea:"
        )
        print(
            " restauralos con  git restore knowledge/islanding/corpus/  - el congelado manda)"
        )
        return 0

    print(
        "VEREDICTO: HAY DIFERENCIAS - regla del freeze: se REPORTA, no se sobreescribe."
    )
    print("Restaurar con:  git restore knowledge/islanding/corpus/")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
