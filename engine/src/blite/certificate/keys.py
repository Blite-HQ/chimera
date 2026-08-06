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

import base64
from pathlib import Path
from typing import Protocol, runtime_checkable

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from blite.certificate.dsse import DSSEEnvelope, DSSESignature, pae

CERTIFICATE_PURPOSE = "certificate"
"""La llave que firma EL diferenciador: el certificado de confianza."""

ATTESTATION_PURPOSE = "attestation"
"""La de los sobres por constancia (C6). Separarla por `purpose` es lo que
permite que un despliegue le dé al verificador su PROPIA llave — la
separación S2 deja de depender de una promesa y pasa a depender de la
custodia."""

STATUS_LIST_PURPOSE = "status-list"
"""La que firma la lista de revocación (C7)."""


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


class LocalKeyProvider:
    """Escalón 1 de la custodia (P1-3): Ed25519 en el proceso.

    De `from_file` cuando el despliegue trae su llave (el keypair pertenece a
    la ORGANIZACIÓN operadora, no al software — doctrina §7), efímera cuando
    no. Que sea efímera no es un default cómodo: un certificado firmado con
    una llave que muere al reiniciar es honesto solo mientras nadie prometa
    lo contrario, y por eso el escalón 2 (Transit) existe."""

    def __init__(
        self, private_key: ed25519.Ed25519PrivateKey | None = None, *, version: int = 1
    ) -> None:
        self._key = private_key or ed25519.Ed25519PrivateKey.generate()
        self._version = version

    @classmethod
    def from_file(cls, path: Path, *, version: int = 1) -> LocalKeyProvider:
        """Carga una llave privada Ed25519 en PEM. El archivo es del
        despliegue: quién firma es dato de operación, jamás del código."""
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
        if not isinstance(key, ed25519.Ed25519PrivateKey):
            msg = f"{path}: no es una llave privada Ed25519 (freeze §7)"
            raise TypeError(msg)
        return cls(key, version=version)

    def keyid(self, purpose: str) -> str:
        return f"{purpose}:v{self._version}"

    def sign(self, purpose: str, pae_bytes: bytes) -> DSSESignature:
        return DSSESignature(
            keyid=self.keyid(purpose),
            sig=base64.b64encode(self._key.sign(pae_bytes)).decode("ascii"),
        )

    def public_key_pem(self, purpose: str) -> str:  # noqa: ARG002 — una llave por proceso
        return (
            self._key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode("ascii")
        )


def public_key_b64(provider: KeyProvider, purpose: str) -> str:
    """La pública del `purpose` en base64 CRUDO — la forma que viaja en el
    Bundle. El puerto habla PEM (formato de intercambio); el bundle lleva los
    32 bytes pelados porque es lo que `Ed25519PublicKey.from_public_bytes`
    consume del otro lado, sin parser de por medio."""
    key = serialization.load_pem_public_key(provider.public_key_pem(purpose).encode())
    if not isinstance(key, ed25519.Ed25519PublicKey):
        msg = f"la llave de {purpose!r} no es Ed25519 (freeze §7)"
        raise TypeError(msg)
    return base64.b64encode(
        key.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
    ).decode("ascii")


def sign_envelope(
    provider: KeyProvider, *, purpose: str, payload_type: str, payload: bytes
) -> DSSEEnvelope:
    """Firma por el PUERTO: el material de la llave jamás sale de la custodia.

    La diferencia con `dsse.sign` no es cosmética — ahí la llave privada es un
    argumento y quien la tenga puede firmar cualquier cosa; acá el llamador
    solo puede pedir «firmame estos bytes con el propósito X», que es
    exactamente lo que un HSM o Transit permiten y nada más."""
    return DSSEEnvelope(
        payload_type=payload_type,
        payload_b64=base64.b64encode(payload).decode("ascii"),
        signatures=(provider.sign(purpose, pae(payload_type, payload)),),
    )


__all__ = [
    "ATTESTATION_PURPOSE",
    "CERTIFICATE_PURPOSE",
    "STATUS_LIST_PURPOSE",
    "KeyProvider",
    "LocalKeyProvider",
    "public_key_b64",
    "sign_envelope",
]
