"""JWT de sesión — freeze §8 (claims) + §9 P1-9 (cookie, decidido). [C2/M2]

Firma Ed25519/EdDSA (jamás HS256) VÍA el puerto `KeyProvider` del §7;
verificar solo necesita la llave pública (S2: Signer ≠ Verifier). Claims:
`iss/sub/kind/domain_id/permissions/act/iat/exp`. Fail-closed: token
expirado, manipulado, de otro issuer o mal formado ⇒ `SessionTokenError` —
jamás una Identity parcial.
"""

from __future__ import annotations

import base64
import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from blite.certificate.dsse import DSSESignature
from blite.identity.identity import Identity
from blite.identity.jwt import (
    SESSION_PURPOSE,
    SessionTokenError,
    encode_session_jwt,
    verify_session_jwt,
)

_ISSUER = "chimera-api"
_NOW = 1_800_000_000


class _LocalKeyProvider:
    """Escalón 1 de la escalera de custodia (P1-3): llave en memoria."""

    def __init__(self) -> None:
        self._key = ed25519.Ed25519PrivateKey.generate()

    def keyid(self, purpose: str) -> str:
        return f"{purpose}:v1"

    def sign(self, purpose: str, pae_bytes: bytes) -> DSSESignature:
        sig = self._key.sign(pae_bytes)
        return DSSESignature(
            keyid=self.keyid(purpose), sig=base64.b64encode(sig).decode("ascii")
        )

    def public_key_pem(self, purpose: str) -> str:
        return (
            self._key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode("ascii")
        )


def _identity() -> Identity:
    return Identity(
        id="user:local-operator",
        kind="human",
        domain_id="domain-default",
        permissions=frozenset({"capability:invoke", "capability:ingest:derive"}),
    )


def _roundtrip() -> tuple[str, _LocalKeyProvider]:
    provider = _LocalKeyProvider()
    token = encode_session_jwt(
        _identity(),
        key_provider=provider,
        issuer=_ISSUER,
        ttl_seconds=3600,
        now=_NOW,
    )
    return token, provider


def test_roundtrip_reconstruye_la_identity() -> None:
    token, provider = _roundtrip()
    identity = verify_session_jwt(
        token,
        public_key_pem=provider.public_key_pem(SESSION_PURPOSE),
        issuer=_ISSUER,
        now=_NOW + 10,
    )
    assert identity == _identity()


def test_claims_del_freeze_y_alg_eddsa() -> None:
    """freeze §8: iss/sub/kind/domain_id/permissions/act/iat/exp; EdDSA."""
    token, _ = _roundtrip()
    header_b64, payload_b64, _sig = token.split(".")

    def _decode(part: str) -> dict[str, object]:
        return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))

    header = _decode(header_b64)
    payload = _decode(payload_b64)
    assert header["alg"] == "EdDSA"
    assert header["kid"] == f"{SESSION_PURPOSE}:v1"
    assert payload["iss"] == _ISSUER
    assert payload["sub"] == "user:local-operator"
    assert payload["kind"] == "human"
    assert payload["domain_id"] == "domain-default"
    assert sorted(payload["permissions"]) == [  # type: ignore[arg-type]
        "capability:ingest:derive",
        "capability:invoke",
    ]
    assert payload["act"] == []
    assert payload["iat"] == _NOW
    assert payload["exp"] == _NOW + 3600


def test_token_expirado_falla_cerrado() -> None:
    token, provider = _roundtrip()
    with pytest.raises(SessionTokenError):
        verify_session_jwt(
            token,
            public_key_pem=provider.public_key_pem(SESSION_PURPOSE),
            issuer=_ISSUER,
            now=_NOW + 3601,
        )


def test_token_manipulado_falla_cerrado() -> None:
    token, provider = _roundtrip()
    header_b64, payload_b64, sig_b64 = token.split(".")
    payload = json.loads(
        base64.urlsafe_b64decode(payload_b64 + "=" * (-len(payload_b64) % 4))
    )
    payload["permissions"] = ["override:apply:global"]
    forged = (
        base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    )
    with pytest.raises(SessionTokenError):
        verify_session_jwt(
            f"{header_b64}.{forged}.{sig_b64}",
            public_key_pem=provider.public_key_pem(SESSION_PURPOSE),
            issuer=_ISSUER,
            now=_NOW + 10,
        )


def test_issuer_distinto_falla_cerrado() -> None:
    token, provider = _roundtrip()
    with pytest.raises(SessionTokenError):
        verify_session_jwt(
            token,
            public_key_pem=provider.public_key_pem(SESSION_PURPOSE),
            issuer="otro-emisor",
            now=_NOW + 10,
        )


def test_basura_falla_cerrado() -> None:
    _, provider = _roundtrip()
    with pytest.raises(SessionTokenError):
        verify_session_jwt(
            "no.es.jwt",
            public_key_pem=provider.public_key_pem(SESSION_PURPOSE),
            issuer=_ISSUER,
            now=_NOW,
        )
