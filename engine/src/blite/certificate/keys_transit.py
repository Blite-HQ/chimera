"""
`TransitKeyProvider` — escalón 2 de la custodia: OpenBao Transit. Ítem C8/M8
pieza 4 (research R3 §6; trust/15).

**Qué cambia de verdad.** Con el escalón 1 la llave que firma EL diferenciador
vive en la memoria del proceso: quien logre leer ese proceso puede firmar
certificados indefinidamente y nadie se entera. Con Transit, el proceso NUNCA
ve el material — pide firmas por HTTP y OpenBao decide. Robar el token del
proceso permite firmar MIENTRAS el token vale, y queda en el audit log de
OpenBao. Es la misma diferencia que hay entre tener la llave y tener acceso.

**Single instance a propósito** (precisión de research R3 a trust/15): el
quorum de 3 de OpenBao es para ALTA DISPONIBILIDAD, no para seguridad. Un
despliegue de un nodo con Raft integrado ya da custodia real; exigir quorum
aquí habría sido copiar una recomendación sin entender qué resuelve.

**El puerto no cambia** — es el MISMO `KeyProvider` (trust/15) que la escalera
declaró desde el día 1, y por eso este adapter es un drop-in: el emisor del
certificado no sabe si firma local o remoto. El escalón 3 (PKCS#11/HSM) entra
por la misma puerta.

Notas de forma de la API de Transit:
- `POST /v1/<mount>/sign/<key>` con `{"input": base64(bytes)}` → firma en
  `vault:v<n>:<base64>`; el `v<n>` es la versión de la LLAVE y se usa tal cual
  para el `keyid`, así que rotar la llave cambia el keyid sin código de por
  medio (que es lo que la convención `<purpose>:v<version>` prometía);
- `GET /v1/<mount>/keys/<key>` → `data.keys["<n>"].public_key` en **base64
  CRUDO** para ed25519 (32 bytes), NO en PEM — verificado contra un OpenBao
  2.6.1 real; el adapter convierte, porque el puerto habla PEM;
- se firma el PAE tal cual (Regla 1 del anexo: jamás una re-serialización).
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass, field
from typing import Any, cast

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from blite.certificate.dsse import DSSESignature

DEFAULT_MOUNT = "transit"
DEFAULT_TIMEOUT_S = 5.0


def _as_pem(public_key: str) -> str:
    """Transit devuelve la pública Ed25519 en **base64 CRUDO** (32 bytes), no
    en PEM — verificado contra un OpenBao 2.6.1 real, y es donde un doble de
    protocolo escrito de memoria se equivoca. El puerto `KeyProvider` habla
    PEM (formato de intercambio), así que la conversión vive aquí, en el
    adapter, que es quien conoce el dialecto de su custodia.

    Se acepta PEM tal cual por si una versión futura lo devuelve así: el
    adapter no puede romperse por recibir el formato que su propio puerto
    declara."""
    if "BEGIN PUBLIC KEY" in public_key:
        return public_key
    try:
        crudo = base64.b64decode(public_key, validate=True)
        return (
            ed25519.Ed25519PublicKey.from_public_bytes(crudo)
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode("ascii")
        )
    except (ValueError, binascii.Error) as exc:
        msg = f"la pública de Transit no es PEM ni base64 de 32 bytes: {exc}"
        raise TransitError(msg) from exc


class TransitError(RuntimeError):
    """La custodia no respondió lo que debía. Fail-loud SIEMPRE: firmar es la
    operación que no admite degradación silenciosa — una firma "de respaldo"
    hecha con otra llave sería peor que no firmar."""


@dataclass(frozen=True)
class TransitKeyProvider:
    """`KeyProvider` sobre OpenBao Transit. Una llave por `purpose`."""

    address: str
    token: str
    mount: str = DEFAULT_MOUNT
    key_prefix: str = "chimera"
    timeout_s: float = DEFAULT_TIMEOUT_S
    client: httpx.Client | None = field(default=None, compare=False)
    """Inyectable para tests; sin él se abre uno por llamada."""

    def _key_name(self, purpose: str) -> str:
        return f"{self.key_prefix}-{purpose}"

    def _request(
        self, method: str, path: str, json: dict[str, str] | None = None
    ) -> dict[str, Any]:
        url = f"{self.address.rstrip('/')}/v1/{self.mount}/{path}"
        headers = {"X-Vault-Token": self.token}
        try:
            if self.client is not None:
                response = self.client.request(
                    method, url, headers=headers, json=json, timeout=self.timeout_s
                )
            else:
                with httpx.Client(timeout=self.timeout_s) as client:
                    response = client.request(method, url, headers=headers, json=json)
        except httpx.HTTPError as exc:
            msg = f"Transit inalcanzable en {url}: {exc}"
            raise TransitError(msg) from exc
        if response.status_code >= 400:
            msg = f"Transit respondió {response.status_code} a {method} {url}: {response.text}"
            raise TransitError(msg)
        payload: Any = response.json()
        data: Any = (
            cast("dict[str, Any]", payload).get("data")
            if isinstance(payload, dict)
            else None
        )
        if not isinstance(data, dict):
            msg = f"Transit respondió sin `data` a {method} {url}"
            raise TransitError(msg)
        return cast("dict[str, Any]", data)

    def _latest_version(self, purpose: str) -> tuple[str, str]:
        """(versión, PEM público) de la ÚLTIMA versión de la llave."""
        data = self._request("GET", f"keys/{self._key_name(purpose)}")
        keys: Any = data.get("keys")
        if not isinstance(keys, dict) or not keys:
            msg = f"la llave {self._key_name(purpose)!r} no tiene versiones en Transit"
            raise TransitError(msg)
        versiones = cast("dict[str, Any]", keys)
        latest = max(versiones, key=int)
        entrada: Any = versiones[latest]
        # Transit anida `{"public_key": …}` por versión; se tolera la forma
        # plana por si un mount ajeno la devuelve así — el fail-loud de abajo
        # cubre cualquier otra cosa.
        public_key: Any = (
            cast("dict[str, Any]", entrada).get("public_key")
            if isinstance(entrada, dict)
            else str(entrada)
        )
        if not isinstance(public_key, str) or not public_key:
            msg = f"la llave {self._key_name(purpose)!r} no expone llave pública"
            raise TransitError(msg)
        return str(latest), _as_pem(public_key)

    def keyid(self, purpose: str) -> str:
        version, _ = self._latest_version(purpose)
        return f"{purpose}:v{version}"

    def sign(self, purpose: str, pae_bytes: bytes) -> DSSESignature:
        data = self._request(
            "POST",
            f"sign/{self._key_name(purpose)}",
            json={"input": base64.b64encode(pae_bytes).decode("ascii")},
        )
        raw: Any = data.get("signature")
        if not isinstance(raw, str) or not raw.startswith("vault:"):
            msg = f"Transit devolvió una firma inesperada: {raw!r}"
            raise TransitError(msg)
        _, version, sig_b64 = raw.split(":", 2)
        return DSSESignature(keyid=f"{purpose}:{version}", sig=sig_b64)

    def public_key_pem(self, purpose: str) -> str:
        _, pem = self._latest_version(purpose)
        return pem


__all__ = ["DEFAULT_MOUNT", "TransitError", "TransitKeyProvider"]
