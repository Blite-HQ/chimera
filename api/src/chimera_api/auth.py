"""
Sesión del API — JWT en cookie (freeze §9 P1-9) hecho código, 401-obligatorio
en toda ruta que resuelve identidad. [C2/M2 → F1.2]

La identidad del actor es dato del despliegue (doctrina §7: «el keypair
pertenece a la organización operadora, no al software»): `POST /auth/session`
emite el JWT del OPERADOR configurado (`CHIMERA_OPERATOR_ID` /
`CHIMERA_OPERATOR_PERMISSIONS`) firmado Ed25519 por el puerto `KeyProvider`
(escalón 1: llave efímera en memoria — misma custodia que la llave del
certificado del API; OpenBao Transit es el escalón 2, ítem C8 de C-2).

Regla fail-closed, sin excepción (F1.2 aplicado):
- cookie AUSENTE ⇒ 401.
- cookie INVÁLIDA (expirada/manipulada/ajena) ⇒ 401.
Los dos casos reciben el mismo trato: ningún camino de código fabrica una
Identity, ni siquiera la del operador por default. El placeholder `user:api`
ya había muerto; ahora también murió el fallback que ocupaba su lugar.

Honestidad sobre lo que este flip agrega y lo que NO agrega, para que nadie
lo lea como más de lo que es: `SessionAuth.issue()` no recibe nada de la
request — siempre emite la identidad del operador configurado por el
despliegue (`CHIMERA_OPERATOR_ID`, default `user:local-operator`). O sea que
el flip no agrega seguridad real — cualquiera pide cookie primero. Lo que sí
logra: que la identidad venga SIEMPRE de un token firmado y que ningún
camino de código la fabrique.
"""

# pyright: reportUnusedFunction=false
# ^ Los handlers de FastAPI se registran por DECORADOR (`@router.get/post`), no
#   por llamada: pyright los ve como funciones locales que nadie usa. Silenciar
#   la regla acá —y solo acá— evita 15 falsos positivos sin apagar la
#   comprobación en el resto del proyecto, donde una función sin usar SÍ es
#   señal de código muerto.

from __future__ import annotations

import base64
import os
import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from fastapi import APIRouter, HTTPException, Request, Response

from blite.certificate.dsse import DSSESignature
from blite.identity.identity import Identity
from blite.identity.jwt import (
    DEFAULT_TTL_SECONDS,
    SESSION_PURPOSE,
    SessionTokenError,
    encode_session_jwt,
    verify_session_jwt,
)

SESSION_COOKIE = "chimera_session"
SESSION_ISSUER = "chimera-api"

_OPERATOR_ID_ENV = "CHIMERA_OPERATOR_ID"
_OPERATOR_PERMISSIONS_ENV = "CHIMERA_OPERATOR_PERMISSIONS"
_COOKIE_SECURE_ENV = "CHIMERA_SESSION_COOKIE_SECURE"
_TRUTHY = frozenset({"1", "true", "yes"})
_DEFAULT_OPERATOR_ID = "user:local-operator"
_DEFAULT_OPERATOR_PERMISSIONS = (
    "capability:invoke",
    "capability:ingest:external-source",
    "capability:ingest:derive",
)
_KIND_BY_PREFIX: dict[str, str] = {
    "user": "human",
    "agent": "agent",
    "service": "service",
}


class EphemeralSessionKeys:
    """`KeyProvider` escalón 1 (P1-3): Ed25519 en memoria, vida de la app.

    Reiniciar el API invalida las sesiones — correcto para un despliegue
    local de operador único; la custodia durable llega con Transit (C8).
    """

    def __init__(self) -> None:
        self._key = ed25519.Ed25519PrivateKey.generate()

    def keyid(self, purpose: str) -> str:
        return f"{purpose}:v1"

    def sign(self, purpose: str, pae_bytes: bytes) -> DSSESignature:
        signature = self._key.sign(pae_bytes)
        return DSSESignature(
            keyid=self.keyid(purpose),
            sig=base64.b64encode(signature).decode("ascii"),
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


def _operator_identity(domain_id: str) -> Identity:
    """La Identity del operador del despliegue — leída de env POR REQUEST
    (configuración viva del despliegue, jamás cache de import)."""
    operator_id = os.environ.get(_OPERATOR_ID_ENV, _DEFAULT_OPERATOR_ID)
    raw_permissions = os.environ.get(_OPERATOR_PERMISSIONS_ENV)
    permissions = (
        frozenset(p.strip() for p in raw_permissions.split(",") if p.strip())
        if raw_permissions
        else frozenset(_DEFAULT_OPERATOR_PERMISSIONS)
    )
    prefix = operator_id.partition(":")[0]
    kind = _KIND_BY_PREFIX.get(prefix, "human")
    return Identity(
        id=operator_id,
        kind=kind,  # type: ignore[arg-type] — el Literal lo valida pydantic al construir
        domain_id=domain_id,
        permissions=permissions,
    )


class SessionAuth:
    """La sesión de seguridad del API: emite y verifica el JWT en cookie."""

    def __init__(self, domain_id: str) -> None:
        self._keys = EphemeralSessionKeys()
        self._domain_id = domain_id

    def issue(self, response: Response) -> dict[str, object]:
        """Emite la sesión del operador y la deja en cookie HttpOnly."""
        identity = _operator_identity(self._domain_id)
        now = int(time.time())
        token = encode_session_jwt(
            identity,
            key_provider=self._keys,
            issuer=SESSION_ISSUER,
            now=now,
        )
        response.set_cookie(
            SESSION_COOKIE,
            token,
            httponly=True,
            samesite="lax",
            max_age=DEFAULT_TTL_SECONDS,
            path="/",
            # `Secure` es dato del despliegue (revisión C-1): en http plano
            # (walking skeleton local) el navegador/curl DESCARTA cookies
            # Secure — degradación silenciosa al operador default; un
            # despliegue TLS (Fargate) DEBE encender el env.
            secure=os.environ.get(_COOKIE_SECURE_ENV, "").lower() in _TRUTHY,
        )
        return {
            "actor_id": identity.id,
            "expires_at": now + DEFAULT_TTL_SECONDS,
        }

    def identity_from(self, request: Request) -> Identity:
        """La Identity de la request: SIEMPRE de una cookie de sesión válida.

        Cookie AUSENTE ⇒ 401. Cookie presente pero INVÁLIDA (expirada,
        manipulada, ajena) ⇒ 401. Mismo trato para las dos — fail-closed
        sin fallback (F1.2): este método jamás fabrica una Identity, ni
        siquiera la del operador por default.
        """
        token = request.cookies.get(SESSION_COOKIE)
        if token is None:
            raise HTTPException(
                status_code=401,
                detail="sesión requerida — autenticar con POST /auth/session",
            )
        try:
            return verify_session_jwt(
                token,
                public_key_pem=self._keys.public_key_pem(SESSION_PURPOSE),
                issuer=SESSION_ISSUER,
            )
        except SessionTokenError as exc:
            raise HTTPException(
                status_code=401,
                detail="sesión inválida o expirada — renovar con POST /auth/session",
            ) from exc


def create_auth_router(session_auth: SessionAuth) -> APIRouter:
    router = APIRouter()

    @router.post("/auth/session")
    def create_session(response: Response) -> dict[str, object]:
        return session_auth.issue(response)

    @router.get("/me")
    def read_me(request: Request) -> dict[str, object]:
        """Quién está operando (P6/M15 — el bloque de usuario del Studio).

        Resuelve la identidad por la MISMA vía que las rutas de escritura
        (`identity_from`), a propósito: si el Studio mostrara un usuario y
        los eventos estamparan otro en `actor_id`, el bloque estaría
        mintiendo sobre quién firma. Por eso también hereda el fail-closed —
        una cookie rota devuelve 401 acá igual que en `POST /runs`, en vez de
        degradar al operador local y contar dos versiones de quién sos.

        No expone `domain_id` ni `spiffe_id`: el Studio no los usa y una
        superficie de lectura no reparte más de lo que su consumidor pide.
        """
        identity = session_auth.identity_from(request)
        return {
            "id": identity.id,
            "kind": identity.kind,
            "permissions": sorted(identity.permissions),
        }

    return router
