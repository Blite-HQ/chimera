"""Prueba de inclusión ENGRAPADA — ítem C9/M8 pieza 5 (#105).

El descarte de Rekor estaba registrado dos veces y era CORRECTO para lo que
descartaba: emisión keyless con Fulcio, que exige hablar con una CA al firmar.
Lo que entra es otra cosa — un log privado del que se saca una prueba que
viaja DENTRO del bundle y se verifica con aritmética, sin contactar a nadie.

Estos tests construyen árboles de Merkle a mano (RFC 6962) y comprueban que
la verificación acepta lo incluido, rechaza lo que no lo está, y —lo que de
verdad importa— rechaza una prueba VÁLIDA de OTRO documento.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from blite.certificate.bundle_check import check_bundle
from blite.certificate.transparency import (
    entry_bytes,
    leaf_hash,
    staple,
    verify_inclusion,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "scripts" / "example-bundle.json"


@pytest.fixture()
def bundle() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _nodo(izq: bytes, der: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + izq + der).digest()


def _arbol(entradas: list[bytes]) -> tuple[str, list[list[str]]]:
    """Raíz + prueba de inclusión de CADA hoja, computadas aparte del módulo
    bajo prueba: si ambos coinciden, ninguno hereda un bug de convención."""
    nivel = [bytes.fromhex(leaf_hash(e)) for e in entradas]
    pruebas: list[list[str]] = [[] for _ in entradas]
    indices = list(range(len(entradas)))
    while len(nivel) > 1:
        siguiente: list[bytes] = []
        for i in range(0, len(nivel), 2):
            if i + 1 < len(nivel):
                for hoja, idx in enumerate(indices):
                    if idx == i:
                        pruebas[hoja].append(nivel[i + 1].hex())
                    elif idx == i + 1:
                        pruebas[hoja].append(nivel[i].hex())
                siguiente.append(_nodo(nivel[i], nivel[i + 1]))
            else:
                siguiente.append(nivel[i])
        indices = [idx // 2 for idx in indices]
        nivel = siguiente
    return nivel[0].hex(), pruebas


def test_una_hoja_incluida_verifica() -> None:
    entradas = [b"cert-a", b"cert-b", b"cert-c", b"cert-d"]
    raiz, pruebas = _arbol(entradas)

    for i, entrada in enumerate(entradas):
        assert verify_inclusion(
            leaf=leaf_hash(entrada),
            index=i,
            tree_size=len(entradas),
            proof=pruebas[i],
            root=raiz,
        )


def test_un_arbol_impar_tambien_verifica() -> None:
    """El caso que rompe una implementación ingenua: el último nodo de un
    nivel impar sube sin combinarse y NO consume prueba."""
    entradas = [b"cert-a", b"cert-b", b"cert-c"]
    raiz, pruebas = _arbol(entradas)

    for i, entrada in enumerate(entradas):
        assert verify_inclusion(
            leaf=leaf_hash(entrada),
            index=i,
            tree_size=len(entradas),
            proof=pruebas[i],
            root=raiz,
        )


def test_una_hoja_que_no_esta_no_verifica() -> None:
    entradas = [b"cert-a", b"cert-b"]
    raiz, pruebas = _arbol(entradas)

    assert not verify_inclusion(
        leaf=leaf_hash(b"cert-fabricado"),
        index=0,
        tree_size=2,
        proof=pruebas[0],
        root=raiz,
    )


def test_el_prefijo_de_hoja_impide_pasar_un_nodo_interno_por_hoja() -> None:
    """RFC 6962 §2.1: sin los prefijos 0x00/0x01, un nodo interno se puede
    presentar como hoja y probar la inclusión de algo que nunca se registró."""
    assert leaf_hash(b"x") != hashlib.sha256(b"x").hexdigest()
    assert leaf_hash(b"x") == hashlib.sha256(b"\x00x").hexdigest()


# ── El punto 12 del checklist ───────────────────────────────────────────


def test_sin_prueba_el_punto_12_declara_que_no_comprobo(bundle: dict[str, Any]) -> None:
    punto = check_bundle(bundle)[-1]

    assert punto.ok
    assert any("no comprobada" in nota for nota in punto.notes)


def test_con_prueba_valida_el_punto_12_pasa(bundle: dict[str, Any]) -> None:
    # Arrange — el certificado registrado junto a otros tres
    entradas = [entry_bytes(bundle), b"otro-1", b"otro-2", b"otro-3"]
    raiz, pruebas = _arbol(entradas)
    engrapado = staple(
        bundle,
        {
            "log_id": "chimera-transparency",
            "leaf_hash": leaf_hash(entradas[0]),
            "index": 0,
            "tree_size": 4,
            "proof": pruebas[0],
            "root": raiz,
        },
    )

    # Act
    punto = check_bundle(engrapado)[-1]

    # Assert
    assert punto.ok, punto.failures
    assert any("chimera-transparency" in nota for nota in punto.notes)


def test_una_prueba_valida_de_otro_documento_reprueba(bundle: dict[str, Any]) -> None:
    """LA forja que un `verify` descuidado deja pasar: la prueba es
    matemáticamente correcta, pero prueba la inclusión de otra cosa."""
    # Arrange
    entradas = [b"otro-certificado", b"relleno"]
    raiz, pruebas = _arbol(entradas)
    engrapado = staple(
        bundle,
        {
            "log_id": "chimera-transparency",
            "leaf_hash": leaf_hash(entradas[0]),
            "index": 0,
            "tree_size": 2,
            "proof": pruebas[0],
            "root": raiz,
        },
    )

    # Assert
    punto = check_bundle(engrapado)[-1]
    assert not punto.ok
    assert "no es la de este" in punto.failures[0]


def test_una_prueba_manipulada_reprueba(bundle: dict[str, Any]) -> None:
    entradas = [entry_bytes(bundle), b"otro-1"]
    raiz, _ = _arbol(entradas)
    engrapado = staple(
        bundle,
        {
            "log_id": "chimera-transparency",
            "leaf_hash": leaf_hash(entradas[0]),
            "index": 0,
            "tree_size": 2,
            "proof": ["f" * 64],
            "root": raiz,
        },
    )

    punto = check_bundle(engrapado)[-1]
    assert not punto.ok
    assert "NO lleva a la raíz" in punto.failures[0]
