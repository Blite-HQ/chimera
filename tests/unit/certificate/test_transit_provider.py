"""`TransitKeyProvider` — escalón 2 de la custodia (OpenBao Transit).
Ítem C8/M8 pieza 4.

Estos tests hablan HTTP contra un transporte controlado que responde con las
formas REALES de la API de Transit (`vault:v1:<b64>` para la firma, `data.keys
["1"].public_key` en PEM para la pública). No son un mock del adapter: el
adapter corre entero, con su parseo y sus errores. El round-trip contra un
OpenBao de verdad se corre aparte, contra el compose — un doble de protocolo
prueba que hablamos el protocolo que creemos, no que el servidor real lo
hable igual.

Lo que cuidan, en orden: que se firme el PAE tal cual, que el `keyid` salga
de la VERSIÓN que Transit reporta (rotar la llave cambia el keyid sin código
de por medio) y que cualquier respuesta rara EXPLOTE — firmar es la operación
que no admite degradación silenciosa.
"""

from __future__ import annotations

import base64
import json

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from blite.certificate.keys import KeyProvider, public_key_b64
from blite.certificate.keys_transit import TransitError, TransitKeyProvider

CLAVE = ed25519.Ed25519PrivateKey.generate()

# LA forma real: Transit devuelve la pública Ed25519 en base64 CRUDO (32
# bytes), NO en PEM. Se verificó contra un OpenBao 2.6.1 de verdad — la
# primera versión de este doble asumía PEM y el adapter explotaba contra el
# servidor real. Un doble escrito de memoria prueba lo que uno cree.
PUBLICA_B64 = base64.b64encode(
    CLAVE.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
).decode("ascii")

PEM = (
    CLAVE.public_key()
    .public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    .decode("ascii")
)


def _transporte(
    *, version: str = "1", publica: str = PUBLICA_B64
) -> httpx.MockTransport:
    """Responde como OpenBao Transit: firma versionada y pública en base64."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Vault-Token"] == "token-de-prueba"
        if request.url.path.endswith("/keys/chimera-certificate"):
            return httpx.Response(
                200, json={"data": {"keys": {version: {"public_key": publica}}}}
            )
        if request.url.path.endswith("/sign/chimera-certificate"):
            cuerpo = json.loads(request.read())
            firma = base64.b64encode(
                CLAVE.sign(base64.b64decode(cuerpo["input"]))
            ).decode("ascii")
            return httpx.Response(
                200, json={"data": {"signature": f"vault:v{version}:{firma}"}}
            )
        return httpx.Response(404, json={"errors": ["ruta desconocida"]})

    return httpx.MockTransport(handler)


def _provider(**kwargs: object) -> TransitKeyProvider:
    transporte = kwargs.pop("transport", None) or _transporte()
    return TransitKeyProvider(
        address="http://openbao:8200",
        token="token-de-prueba",  # noqa: S106 — doble de protocolo, no un secreto
        client=httpx.Client(transport=transporte),  # type: ignore[arg-type]
        **kwargs,  # type: ignore[arg-type]
    )


def test_el_transit_satisface_el_puerto() -> None:
    assert isinstance(_provider(), KeyProvider)


def test_la_firma_verifica_contra_la_publica_que_transit_reporta() -> None:
    """El round-trip completo del adapter: firma remota, verificación local."""
    # Arrange
    provider = _provider()
    pae_bytes = b"DSSEv1 4 test 5 hola!"

    # Act
    firma = provider.sign("certificate", pae_bytes)

    # Assert
    publica = ed25519.Ed25519PublicKey.from_public_bytes(
        base64.b64decode(public_key_b64(provider, "certificate"))
    )
    publica.verify(base64.b64decode(firma.sig), pae_bytes)


def test_el_keyid_sale_de_la_version_que_reporta_transit() -> None:
    """Rotar la llave en la custodia cambia el `keyid` del certificado sin
    tocar código — que es lo que la convención `<purpose>:v<version>`
    prometía y con una llave en memoria no se podía cumplir."""
    assert _provider(transport=_transporte(version="7")).keyid("certificate") == (
        "certificate:v7"
    )
    assert (
        _provider(transport=_transporte(version="7")).sign("certificate", b"x").keyid
        == "certificate:v7"
    )


def test_transit_caido_explota_en_vez_de_degradar() -> None:
    """Firmar no admite degradación silenciosa: una firma «de respaldo» hecha
    con otra llave sería peor que no firmar."""

    def caido(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("conexión rechazada")

    provider = _provider(transport=httpx.MockTransport(caido))

    with pytest.raises(TransitError, match="inalcanzable"):
        provider.sign("certificate", b"x")


def test_un_403_de_transit_explota_con_el_cuerpo_a_la_vista() -> None:
    """El operador necesita ver QUÉ dijo la custodia — un token sin permiso
    de firma y un mount equivocado se diagnostican distinto."""

    def prohibido(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"errors": ["permission denied"]})

    provider = _provider(transport=httpx.MockTransport(prohibido))

    with pytest.raises(TransitError, match="permission denied"):
        provider.sign("certificate", b"x")


def test_una_firma_con_forma_inesperada_explota() -> None:
    """Si Transit deja de responder `vault:v<n>:<b64>`, el adapter no
    improvisa un parseo — la firma es el último lugar donde adivinar."""

    def raro(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"signature": "no-soy-una-firma"}})

    provider = _provider(transport=httpx.MockTransport(raro))

    with pytest.raises(TransitError, match="firma inesperada"):
        provider.sign("certificate", b"x")


def test_una_llave_sin_versiones_explota() -> None:
    def vacia(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"keys": {}}})

    provider = _provider(transport=httpx.MockTransport(vacia))

    with pytest.raises(TransitError, match="no tiene versiones"):
        provider.public_key_pem("certificate")


def test_una_publica_en_pem_tambien_se_acepta() -> None:
    """El adapter no puede romperse por recibir el formato que su propio
    puerto declara: si una versión futura de Transit devuelve PEM, sirve
    igual."""
    provider = _provider(transport=_transporte(publica=PEM))

    assert "BEGIN PUBLIC KEY" in provider.public_key_pem("certificate")


def test_una_publica_que_no_es_ni_pem_ni_base64_explota() -> None:
    provider = _provider(transport=_transporte(publica="no-soy-una-llave!!"))

    with pytest.raises(TransitError, match="no es PEM ni base64"):
        provider.public_key_pem("certificate")
