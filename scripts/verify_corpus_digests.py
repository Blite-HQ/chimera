#!/usr/bin/env python3
"""Verifica TODOS los corpus versionados: digest interno (islanding/01 SS1.6,
self-consistencia) sobre cada archivo, más identidad pinneada para las tablas
de instancias conocidas.

Correr desde la raiz del repo:  uv run python scripts/verify_corpus_digests.py
Regla 15.3: el digest manda (no los bytes del archivo - fines de linea no cuentan).

Directorios cubiertos (`DIRECTORIOS_CORPUS`): el corpus de islanding (reto 1),
el corpus TFIM del reto 3 (generado por scripts/gen_corpus_tfim.py) y el corpus
tabular del reto 2 (generado por scripts/gen_corpus_tabular.py). Todos usan
el MISMO algoritmo de digest embebido — SHA-256 del JSON canonico sin el campo
`digest` — porque la regla de identidad de S-C generalizo la de islanding sin
cambiarle el algoritmo.

Tablas de identidad pinneada, disjuntas por nombre de archivo:
- `ESPERADOS_FREEZE_15_3` — los 8 IEEE del freeze SS15.3. CONGELADA/INMUTABLE:
  jamas se le agrega ni se le edita una fila (regla del freeze: un cambio
  aqui se REPORTA, nunca se sobreescribe el corpus para que combine).
- `ESPERADOS_CHIMERA_B2` — las 6 instancias nuevas de B2 (cr6/cr8 x
  {uniforme,voltaje}, copiadas verbatim del espejo reto1-vanilla; ice x
  {uniforme,voltaje}, derivadas por `scripts/gen_corpus_ice.py` a traves de
  `blite.ingesta.geojson.to_graph`). Pinneada tambien: un cambio silencioso
  en la derivacion (o una regeneracion con otro snapshot) debe romper este
  guard, no pasar inadvertido.
- `ESPERADOS_TFIM_C3` — los 9 puntos del corpus C3 (3 N x 3 h/J) generados por
  `scripts/gen_corpus_tfim.py` a traves de `blite.numeric.exact_evolve`. Pinneada:
  un cambio en la convencion del operador, en el protocolo de quench o en el
  tiempo de evolucion mueve las series y debe romper este guard.
- `ESPERADOS_TABULAR_C2` — la instancia sintetica sellada del corpus C2
  (generada por `scripts/gen_corpus_tabular.py`; `procedencia:
  "synthetic_generated"` — ver docs/mejorado/03-research.md R1). Pinneada: un
  cambio en la semilla, la frontera de decision o el ruido/faltantes movería
  el CSV y el registro, y debe romper este guard.

Cualquier archivo del corpus que NO aparezca en ninguna tabla solo se
verifica por self-consistencia interna (nunca fue una suposicion de "deben
ser exactamente 8" - el corpus crece; el guard corre sobre TODO lo que haya
en el directorio).
"""

import glob
import hashlib
import json

DIRECTORIOS_CORPUS = (
    "knowledge/islanding/corpus",
    "knowledge/tfim/corpus",
    "knowledge/tabular/corpus",
)

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


ESPERADOS_TFIM_C3 = {
    "chain-n6-h05": "d273194d0483d01c27653d91e6d8ad610939ab58c786b128cf309ab8aeee0a7b",
    "chain-n6-h10": "71b7330aa355e7d66db13e64d1f9ab222f51611ade62410a9fec1915f3068658",
    "chain-n6-h20": "f986afda7bba169f225667298c8764372b351097782749a9ec8f8bb518f6cbe6",
    "chain-n8-h05": "6f5830ecc8b2d1e30f3e37714ffcda66cb2f604514d17510fa054cbb64e2b785",
    "chain-n8-h10": "ef3764daa9ad9a4bf75bc3ad472609b7872a320fe073985bcfa9f9648b3771d5",
    "chain-n8-h20": "9bd7354e2ce3ffe747ac2086180d2f8f20b30761a5446a1a422f1aac8cd5ffcd",
    "chain-n12-h05": "ba46885f3acaf1b5972afd6404c5de7ad10a8cd6aab702fa6ee8a8ef6554e0fd",
    "chain-n12-h10": "c12a862ef2c3f80275481f217f2658fe6e042cb0021117758abe7497bdb9ed3f",
    "chain-n12-h20": "3afefe46a97fe18494c9680c5519b502105046707e68205f69a7d6ca75a8fb2a",
}

ESPERADOS_TABULAR_C2 = {
    "synthetic-binary": "ec2ca00a91a073d523a1eb10d62b49490d7ab7d97e32a181927aa55d1f8871b8",
}


def _dirs_txt() -> str:
    """Los directorios del corpus como los espera `git restore`."""
    return " ".join(f"{d}/" for d in DIRECTORIOS_CORPUS)


def _tabla_pin(nombre: str) -> tuple[str, str | None]:
    """(etiqueta de la tabla, digest esperado) — None si el archivo no esta
    pinneado en ninguna tabla (solo se le exige self-consistencia)."""
    if nombre in ESPERADOS_FREEZE_15_3:
        return "freeze-15.3", ESPERADOS_FREEZE_15_3[nombre]
    if nombre in ESPERADOS_CHIMERA_B2:
        return "chimera-b2", ESPERADOS_CHIMERA_B2[nombre]
    if nombre in ESPERADOS_TFIM_C3:
        return "tfim-c3", ESPERADOS_TFIM_C3[nombre]
    if nombre in ESPERADOS_TABULAR_C2:
        return "tabular-c2", ESPERADOS_TABULAR_C2[nombre]
    return "sin-tabla", None


def main() -> int:
    ok = True
    archivos = sorted(
        f for d in DIRECTORIOS_CORPUS for f in glob.glob(f"{d}/*.json")
    )
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
            "tfim-c3": "tfim OK" if pin_ok else "!= TFIM",
            "tabular-c2": "tabular OK" if pin_ok else "!= TABULAR",
            "sin-tabla": "sin tabla pinneada",
        }[tabla]
        print(f"{nombre:18s} {interno_txt}  {pin_txt}")

    print()
    print(
        f"internos: {internos_ok}/{len(archivos)}   "
        f"pinneados: {pinneados_ok}/{pinneados_total} "
        f"(freeze-15.3={len(ESPERADOS_FREEZE_15_3)}, "
        f"chimera-b2={len(ESPERADOS_CHIMERA_B2)}, tfim-c3={len(ESPERADOS_TFIM_C3)}, "
        f"tabular-c2={len(ESPERADOS_TABULAR_C2)})"
    )
    if ok:
        print(
            f"VEREDICTO: {len(archivos)}/{len(archivos)} digests internos OK, "
            f"{pinneados_ok}/{pinneados_total} coinciden con su tabla pinneada"
        )
        print(
            "(si git marca los archivos como modified, es solo formato/fines de linea:"
        )
        print(f" restauralos con  git restore {_dirs_txt()} - el congelado manda)")
        return 0

    print(
        "VEREDICTO: HAY DIFERENCIAS - regla del freeze: se REPORTA, no se sobreescribe."
    )
    print(f"Restaurar con:  git restore {_dirs_txt()}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
