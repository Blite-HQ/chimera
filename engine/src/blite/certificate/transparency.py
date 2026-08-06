"""
Testigo de transparencia con **prueba engrapada** — ítem C9/M8 pieza 5
(decisión #105; research R3).

**Por qué esto RE-ENTRA.** El descarte estaba registrado dos veces («Sigstore/
Fulcio/Rekor rompen air-gap», freeze §7; «overkill», research de Planeado) y
era CORRECTO para lo que se estaba descartando: emisión *keyless* con Fulcio,
que exige hablar con una CA en línea en el momento de firmar. Lo que entra
ahora es otra cosa: un log privado (`rekor-server-posix`: un binario y un
disco) del que se extrae **una prueba de inclusión que viaja DENTRO del
bundle**. Verificarla no contacta a nadie — se recomputa el camino de Merkle
hasta la raíz del checkpoint firmado, con aritmética y nada más.

**Qué agrega sobre la firma que ya existe.** La firma dice «esto lo emitió
quien tiene la llave». No dice *cuándo* ni impide que el emisor produzca DOS
certificados distintos para el mismo run y le muestre uno a cada auditor. Un
log append-only con inclusión probada sí: el certificado que no está en el log
se distingue del que sí, y dos versiones del mismo run quedan ambas
registradas. Es la propiedad que crece con el flip OSS — mientras el emisor y
el auditor son la misma gente, importa poco; cuando no lo son, es todo.

**Fase 1 de esta pieza:** verificación OFFLINE de la prueba engrapada
(RFC 6962 §2.1.1, el mismo algoritmo que usan los logs de Certificate
Transparency). La sumisión al log corre bajo el perfil `transparency` del
compose y es opcional por diseño: un bundle sin prueba verifica igual y el
checklist lo DICE, en vez de fingir que comprobó.
"""

from __future__ import annotations

import base64
import hashlib
from typing import Any

LEAF_PREFIX = b"\x00"
NODE_PREFIX = b"\x01"
"""RFC 6962 §2.1: los prefijos distinguen una hoja de un nodo interno. Sin
ellos, un atacante puede presentar un nodo interno como si fuera una hoja
(«second preimage attack») y probar la inclusión de algo que nunca se
registró."""


def leaf_hash(entry: bytes) -> str:
    """`MTH({d}) = SHA-256(0x00 ‖ d)` — la hoja del árbol de Merkle."""
    return hashlib.sha256(LEAF_PREFIX + entry).hexdigest()


def _node(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(NODE_PREFIX + left + right).digest()


def verify_inclusion(
    *, leaf: str, index: int, tree_size: int, proof: list[str], root: str
) -> bool:
    """Prueba de inclusión de RFC 6962 §2.1.1, recomputada localmente.

    `leaf`/`root`/`proof` en hex; `index` es la posición 0-based de la hoja y
    `tree_size` el tamaño del árbol al momento del checkpoint. Devuelve
    `True` solo si el camino lleva EXACTAMENTE a la raíz declarada."""
    if index < 0 or tree_size <= 0 or index >= tree_size:
        return False
    nodo = bytes.fromhex(leaf)
    restantes = list(proof)
    posicion, tamano = index, tree_size
    while tamano > 1:
        if not restantes:
            return False
        hermano = bytes.fromhex(restantes.pop(0))
        if posicion % 2 == 1:
            nodo = _node(hermano, nodo)
        elif posicion + 1 < tamano:
            nodo = _node(nodo, hermano)
        else:
            # Nodo derecho incompleto: sube sin combinar y NO consume prueba.
            restantes.insert(0, hermano.hex())
        posicion //= 2
        tamano = (tamano + 1) // 2
    return not restantes and nodo.hex() == root


def entry_bytes(bundle: dict[str, Any]) -> bytes:
    """Qué se registra en el log: los BYTES FIRMADOS del certificado.

    No el bundle entero (el stream y los deliverables cambian de tamaño y no
    aportan a la pregunta «¿este certificado existe?») ni una re-serialización
    del predicate (Regla 1 del anexo: lo que se ampara son los bytes que se
    firmaron)."""
    return base64.b64decode(bundle["envelope"]["payload"])


def staple(bundle: dict[str, Any], proof: dict[str, Any]) -> dict[str, Any]:
    """Engrapa la prueba al bundle — copia nueva, el original no se muta."""
    return {**bundle, "transparency_proof": proof}


__all__ = [
    "LEAF_PREFIX",
    "NODE_PREFIX",
    "entry_bytes",
    "leaf_hash",
    "staple",
    "verify_inclusion",
]
