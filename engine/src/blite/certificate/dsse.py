"""
DSSE envelope, PAE, and Ed25519 sign/verify.

docs/contract-freeze.md SS7 / knowledge/trust/02-trust-certificate-attestation.md
SS1.2. PAE (Pre-Authentication Encoding) is implemented as-is — it signs the
exact payload bytes, never a re-serialization (Regla 1 of the canonicalization
annex): "DSSEv1 <len(type)> <type> <len(payload)> <payload>".

The signing key is passed in by the caller (Ed25519PrivateKey) — this module
does not manage key custody. A future KeyProvider port (knowledge/trust/15)
supplies that key; this module only signs/verifies given one.
"""

from __future__ import annotations

import base64

from cryptography.hazmat.primitives.asymmetric import ed25519
from pydantic import BaseModel, ConfigDict


def pae(payload_type: str, payload: bytes) -> bytes:
    """PAE(payloadType, payload) = DSSEv1 <len(type)> <type> <len(payload)> <payload>."""
    type_bytes = payload_type.encode("utf-8")
    return (
        b"DSSEv1 "
        + str(len(type_bytes)).encode("ascii")
        + b" "
        + type_bytes
        + b" "
        + str(len(payload)).encode("ascii")
        + b" "
        + payload
    )


class DSSESignature(BaseModel):
    """One signature over a DSSE envelope's PAE bytes."""

    model_config = ConfigDict(frozen=True)

    keyid: str
    sig: str
    """Base64-encoded raw Ed25519 signature bytes."""


class DSSEEnvelope(BaseModel):
    """A signed payload — the payload bytes themselves, plus who signed them."""

    model_config = ConfigDict(frozen=True)

    payload_type: str
    payload_b64: str
    signatures: tuple[DSSESignature, ...]


def sign(
    *,
    payload_type: str,
    payload: bytes,
    private_key: ed25519.Ed25519PrivateKey,
    keyid: str,
) -> DSSEEnvelope:
    """Sign `payload` bytes as-is (Regla 1) — the caller canonicalizes first."""
    signature_bytes = private_key.sign(pae(payload_type, payload))
    return DSSEEnvelope(
        payload_type=payload_type,
        payload_b64=base64.b64encode(payload).decode("ascii"),
        signatures=(
            DSSESignature(
                keyid=keyid, sig=base64.b64encode(signature_bytes).decode("ascii")
            ),
        ),
    )


def verify(envelope: DSSEEnvelope, public_key: ed25519.Ed25519PublicKey) -> bytes:
    """Verify the envelope's first signature; return the decoded payload bytes.

    Raises cryptography.exceptions.InvalidSignature if verification fails —
    on a signed payload, that failure IS the answer, not an error to swallow.
    """
    payload_bytes = base64.b64decode(envelope.payload_b64)
    signature_bytes = base64.b64decode(envelope.signatures[0].sig)
    public_key.verify(signature_bytes, pae(envelope.payload_type, payload_bytes))
    return payload_bytes
