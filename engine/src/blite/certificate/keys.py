"""
KeyProvider — el puerto de custodia de llaves (trust/15, freeze §7). [S-G Etapa 0]

`keyid = "<purpose>:v<version>"`. Escalera de custodia (P1-3, decidida):
escalón 1 = env/archivo (hoy) → escalón 2 = OpenBao Transit (Fase 2) →
escalón 3 = PKCS#11/HSM — MISMO Protocol, declarado desde ya. Doctrina:
"el keypair del certificado pertenece a la organización operadora, no al
software" — quién firma es dato del despliegue.

Separación S2 (Signer ≠ Verifier) en el diseño del puerto: firmar exige el
puerto completo; verificar solo necesita la llave pública (que viaja con el
despliegue/Bundle) — por eso `public_key_pem` es parte del contrato y
`blite.certificate.dsse.verify` no toca este puerto.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from blite.certificate.dsse import DSSESignature


@runtime_checkable
class KeyProvider(Protocol):
    """El único camino a una firma — el material de la llave jamás sale del puerto."""

    def keyid(self, purpose: str) -> str:
        """`"<purpose>:v<version>"` — la versión la administra la custodia."""
        ...

    def sign(self, purpose: str, pae_bytes: bytes) -> DSSESignature:
        """Firma los bytes PAE exactos (Regla 1 del anexo: jamás re-serializar)."""
        ...

    def public_key_pem(self, purpose: str) -> str:
        """La llave pública del purpose — lo único que el lado verificador necesita."""
        ...
