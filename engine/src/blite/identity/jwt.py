"""
JWT de sesión — la letra del freeze §8 hecha código. [C2/M2]

«JWT emitido/verificado por el engine con llave local: claims
`iss/sub/kind/domain_id/permissions/act/iat/exp`; firma Ed25519/EdDSA
(no HS256), vía el mismo puerto `KeyProvider` del §7.» El transporte es
cookie (freeze §9 P1-9, decidido) — eso es del borde HTTP, no de aquí.

Compacto JWS firmado POR EL PUERTO (la llave jamás sale de la custodia —
P1-3); verificar solo necesita la llave pública PEM (S2: Signer ≠
Verifier, mismo diseño que `certificate.dsse.verify`). Fail-closed: TODA
falla (expiración, firma, issuer, forma) es `SessionTokenError` — jamás
una Identity parcial ni un fallback.
"""

from __future__ import annotations

import base64
import binascii
import json
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.serialization import load_pem_public_key

from blite.certificate.keys import KeyProvider
from blite.identity.identity import Identity

SESSION_PURPOSE = "session"
DEFAULT_TTL_SECONDS = 8 * 60 * 60
"""Vida de una sesión local de operador — dato del despliegue, no doctrina."""

_ALG = "EdDSA"


class SessionTokenError(Exception):
    """Token de sesión inválido — expirado, manipulado, ajeno o mal formado."""


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(part: str) -> bytes:
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


def encode_session_jwt(
    identity: Identity,
    *,
    key_provider: KeyProvider,
    issuer: str,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    now: int | None = None,
    act: tuple[str, ...] = (),
) -> str:
    """Emite el JWT de la Identity — firma por el puerto, jamás llave cruda.

    `act` (RFC 8693) = cadena de delegación; vacía para una sesión directa.
    """
    issued_at = int(time.time()) if now is None else now
    header = {
        "alg": _ALG,
        "typ": "JWT",
        "kid": key_provider.keyid(SESSION_PURPOSE),
    }
    payload = {
        "iss": issuer,
        "sub": identity.id,
        "kind": identity.kind,
        "domain_id": identity.domain_id,
        "permissions": sorted(identity.permissions),
        "act": list(act),
        "iat": issued_at,
        "exp": issued_at + ttl_seconds,
    }
    signing_input = (
        f"{_b64url(json.dumps(header, separators=(',', ':')).encode())}."
        f"{_b64url(json.dumps(payload, separators=(',', ':')).encode())}"
    )
    signature = key_provider.sign(SESSION_PURPOSE, signing_input.encode("ascii"))
    sig_raw = base64.b64decode(signature.sig)
    return f"{signing_input}.{_b64url(sig_raw)}"


def verify_session_jwt(
    token: str,
    *,
    public_key_pem: str,
    issuer: str,
    now: int | None = None,
) -> Identity:
    """Verifica firma, vigencia e issuer; reconstruye la Identity — o explota."""
    moment = int(time.time()) if now is None else now
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
        header = json.loads(_b64url_decode(header_b64))
        payload = json.loads(_b64url_decode(payload_b64))
        sig_raw = _b64url_decode(sig_b64)
    except (ValueError, json.JSONDecodeError, binascii.Error) as exc:
        msg = "token de sesión mal formado"
        raise SessionTokenError(msg) from exc

    if header.get("alg") != _ALG:
        msg = f"alg {header.get('alg')!r} rechazado — solo EdDSA (freeze §8)"
        raise SessionTokenError(msg)

    public_key = load_pem_public_key(public_key_pem.encode("ascii"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    try:
        public_key.verify(sig_raw, signing_input)  # type: ignore[union-attr, call-arg]
    except (InvalidSignature, AttributeError, TypeError) as exc:
        msg = "firma del token de sesión inválida"
        raise SessionTokenError(msg) from exc

    if payload.get("iss") != issuer:
        msg = f"issuer {payload.get('iss')!r} no es {issuer!r}"
        raise SessionTokenError(msg)
    exp = payload.get("exp")
    if not isinstance(exp, int) or moment >= exp:
        msg = "token de sesión expirado"
        raise SessionTokenError(msg)

    try:
        return Identity(
            id=payload["sub"],
            kind=payload["kind"],
            domain_id=payload["domain_id"],
            permissions=frozenset(payload["permissions"]),
        )
    except (KeyError, ValueError, TypeError) as exc:
        msg = "claims del token no reconstruyen una Identity válida"
        raise SessionTokenError(msg) from exc
