"""
DSSE envelope + PAE + Ed25519 signing (ficha B2 piece 3).

docs/contract-freeze.md SS7 / knowledge/trust/02-trust-certificate-attestation.md
SS1.2. Payload bytes come from canonicalize() (Regla 1 composes with Regla 2:
C() produces the digests/payload that go INTO the Statement; PAE signs those
exact bytes — never a re-serialization, per the annex).
"""

from __future__ import annotations

import base64

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519
from pydantic import ValidationError

from blite.certificate.canonical import JSONValue, canonicalize
from blite.certificate.dsse import DSSEEnvelope, pae, sign, verify

PAYLOAD_TYPE = "application/vnd.blite.trust-certificate+json"


def _statement() -> dict[str, JSONValue]:
    return {
        "_type": "https://blite.dev/Statement/v0",
        "subject": [{"name": "run:8f2c1a9b", "digest": {"sha256": "a" * 64}}],
        "predicateType": "https://blite.dev/TrustCertificate/v0",
        "predicate": {"run_id": "8f2c1a9b", "aggregate_rung": 1},
    }


# ── PAE ──────────────────────────────────────────────────────────────────


def test_pae_encodes_type_and_payload_with_explicit_length_prefixes() -> None:
    encoded = pae("application/json", b"hi")
    assert encoded == b"DSSEv1 16 application/json 2 hi"


def test_pae_distinguishes_payloads_with_the_same_concatenated_bytes() -> None:
    # Without length-prefixing, ("ab", "c") and ("a", "bc") could collide.
    assert pae("ab", b"c") != pae("a", b"bc")


# ── sign / verify round-trip ────────────────────────────────────────────


def test_sign_then_verify_round_trips() -> None:
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    payload_bytes = canonicalize(_statement())

    envelope = sign(
        payload_type=PAYLOAD_TYPE,
        payload=payload_bytes,
        private_key=private_key,
        keyid="chimera-2026:v1",
    )

    assert isinstance(envelope, DSSEEnvelope)
    assert envelope.payload_type == PAYLOAD_TYPE
    assert base64.b64decode(envelope.payload_b64) == payload_bytes
    assert envelope.signatures[0].keyid == "chimera-2026:v1"

    verified_payload = verify(envelope, public_key)
    assert verified_payload == payload_bytes


def test_mutating_one_byte_of_the_payload_invalidates_the_signature() -> None:
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    payload_bytes = canonicalize(_statement())

    envelope = sign(
        payload_type=PAYLOAD_TYPE,
        payload=payload_bytes,
        private_key=private_key,
        keyid="chimera-2026:v1",
    )

    mutated_payload = bytearray(base64.b64decode(envelope.payload_b64))
    mutated_payload[0] ^= 0xFF
    tampered = DSSEEnvelope(
        payload_type=envelope.payload_type,
        payload_b64=base64.b64encode(bytes(mutated_payload)).decode("ascii"),
        signatures=envelope.signatures,
    )

    with pytest.raises(InvalidSignature):
        verify(tampered, public_key)


def test_verify_rejects_a_signature_from_a_different_key() -> None:
    private_key = ed25519.Ed25519PrivateKey.generate()
    other_public_key = ed25519.Ed25519PrivateKey.generate().public_key()
    payload_bytes = canonicalize(_statement())

    envelope = sign(
        payload_type=PAYLOAD_TYPE,
        payload=payload_bytes,
        private_key=private_key,
        keyid="chimera-2026:v1",
    )

    with pytest.raises(InvalidSignature):
        verify(envelope, other_public_key)


def test_dsse_envelope_is_frozen() -> None:
    private_key = ed25519.Ed25519PrivateKey.generate()
    envelope = sign(
        payload_type=PAYLOAD_TYPE,
        payload=canonicalize(_statement()),
        private_key=private_key,
        keyid="chimera-2026:v1",
    )
    with pytest.raises(ValidationError):
        envelope.payload_type = "tampered"
