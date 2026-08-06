"""El puerto `KeyProvider` cableado de verdad — ítem C8/M8 pieza 4.

El puerto existía desde S-G y NADIE lo usaba: `assemble`/`dsse` recibían la
llave privada como argumento. La diferencia no es cosmética — con la llave
como argumento, quien la tenga firma lo que quiera; con el puerto, el
llamador solo puede pedir «firmame estos bytes con el propósito X», que es
exactamente lo que un HSM o un Transit permiten y nada más.

Estos tests fijan las dos propiedades que hacen el escalón 2 (OpenBao) un
drop-in: el emisor NUNCA toca material de llave, y los `purpose` están
separados para que la custodia pueda darle al verificador una llave propia
(separación S2).
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from blite.certificate.assemble import assemble_bundle
from blite.certificate.bundle_check import check_bundle
from blite.certificate.dsse import DSSESignature, pae
from blite.certificate.keys import (
    ATTESTATION_PURPOSE,
    CERTIFICATE_PURPOSE,
    KeyProvider,
    LocalKeyProvider,
    public_key_b64,
    sign_envelope,
)
from blite.events import create_event_store
from blite.events.event import Event
from blite.runtime.content_store import InMemoryContentStore
from blite.runtime.dispatch import ProfileDispatcher
from blite.runtime.loop import execute_run
from blite.runtime.registry import EntryPointRegistry
from blite_capability.manifest import CapabilityManifest

REPO = Path(__file__).resolve().parents[3]
POLICY_BYTES = (
    REPO / "distributions" / "chimera" / "policies" / "verification-default.yaml"
).read_bytes()


class _EchoCapability:
    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id="cap.echo",
            description="test capability",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            side_effects="pure",
            required_permission="capability:invoke",
            interaction="request_response",
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return {"echoed": inputs["x"]}


def _run_stream() -> tuple[Event, ...]:
    store = create_event_store()
    execute_run(
        store,
        EntryPointRegistry({"cap.echo": _EchoCapability()}),
        ProfileDispatcher(),
        InMemoryContentStore(),
        run_id="run-keys",
        actor_id="user:dylan",
        domain_id="domain-a",
        max_steps=8,
        policy_digest="pol-digest-1",
        capability_id="cap.echo",
        inputs={"x": 21},
    )
    return store.read_stream("run-keys")


class _CustodiaQueCuenta:
    """Doble del puerto que registra QUÉ se le pidió firmar y con qué
    propósito — la forma de probar que el emisor no ve la llave: no puede,
    porque este objeto nunca la expone."""

    def __init__(self) -> None:
        self._key = ed25519.Ed25519PrivateKey.generate()
        self.pedidos: list[tuple[str, int]] = []

    def keyid(self, purpose: str) -> str:
        return f"{purpose}:v9"

    def sign(self, purpose: str, pae_bytes: bytes) -> DSSESignature:
        self.pedidos.append((purpose, len(pae_bytes)))
        return DSSESignature(
            keyid=self.keyid(purpose),
            sig=base64.b64encode(self._key.sign(pae_bytes)).decode("ascii"),
        )

    def public_key_pem(self, purpose: str) -> str:  # noqa: ARG002
        return (
            self._key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode("ascii")
        )


# ── El adapter local (escalón 1) ────────────────────────────────────────


def test_el_local_satisface_el_puerto() -> None:
    assert isinstance(LocalKeyProvider(), KeyProvider)


def test_el_keyid_sigue_la_convencion_purpose_version() -> None:
    """`<purpose>:v<version>` (freeze §7): la versión la administra la
    custodia, y rotarla cambia el keyid sin tocar código."""
    provider = LocalKeyProvider(version=3)

    assert provider.keyid(CERTIFICATE_PURPOSE) == "certificate:v3"
    assert provider.keyid(ATTESTATION_PURPOSE) == "attestation:v3"


def test_la_llave_del_despliegue_se_carga_de_archivo(tmp_path: Path) -> None:
    """«El keypair pertenece a la organización operadora, no al software»
    (freeze §7): quién firma es dato de operación."""
    # Arrange
    key = ed25519.Ed25519PrivateKey.generate()
    path = tmp_path / "certificate.pem"
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    # Act
    provider = LocalKeyProvider.from_file(path)

    # Assert — la misma llave, no una nueva
    assert public_key_b64(provider, CERTIFICATE_PURPOSE) == base64.b64encode(
        key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
    ).decode("ascii")


def test_un_archivo_que_no_es_ed25519_no_carga(tmp_path: Path) -> None:
    path = tmp_path / "rara.pem"
    path.write_bytes(b"-----BEGIN PRIVATE KEY-----\nno soy una llave\n")

    with pytest.raises(ValueError):
        LocalKeyProvider.from_file(path)


def test_la_firma_por_el_puerto_es_sobre_el_pae_exacto() -> None:
    """Regla 1 del anexo: se firman los bytes PAE, jamás una
    re-serialización."""
    provider = LocalKeyProvider()
    payload = b'{"hola":"mundo"}'

    envelope = sign_envelope(
        provider,
        purpose=CERTIFICATE_PURPOSE,
        payload_type="application/vnd.test+json",
        payload=payload,
    )

    publica = ed25519.Ed25519PublicKey.from_public_bytes(
        base64.b64decode(public_key_b64(provider, CERTIFICATE_PURPOSE))
    )
    publica.verify(
        base64.b64decode(envelope.signatures[0].sig),
        pae("application/vnd.test+json", payload),
    )
    assert base64.b64decode(envelope.payload_b64) == payload


# ── El emisor firma SIN ver la llave ────────────────────────────────────


def test_el_ensamblador_solo_pide_firmas_por_el_puerto() -> None:
    """LA propiedad que hace del escalón 2 un drop-in: `assemble_bundle` no
    recibe material de llave, así que da igual si vive en el proceso o en
    OpenBao. Este doble ni siquiera expone la privada."""
    # Arrange
    custodia = _CustodiaQueCuenta()

    # Act
    bundle = assemble_bundle(
        stream=_run_stream(),
        conclusions=(),
        policy_yaml=POLICY_BYTES,
        key_provider=custodia,
    )

    # Assert — se pidió el certificado (1) y un sobre por constancia (0 aquí)
    assert [purpose for purpose, _ in custodia.pedidos] == [CERTIFICATE_PURPOSE]
    assert all(r.ok for r in check_bundle(bundle)), [
        (r.number, r.failures) for r in check_bundle(bundle) if not r.ok
    ]


def test_el_bundle_publica_la_llave_de_los_sobres_aunque_sea_la_misma() -> None:
    """El anillo se publica SIEMPRE: si mañana la custodia le da al propósito
    `attestation` una llave distinta, el verificador ya la busca donde
    corresponde. Descubrir «funcionaba porque era la misma llave» el día del
    despliegue con custodia real es exactamente lo que esto evita."""
    provider = LocalKeyProvider()

    bundle = assemble_bundle(
        stream=_run_stream(),
        conclusions=(),
        policy_yaml=POLICY_BYTES,
        key_provider=provider,
    )

    assert bundle["attestation_public_keys"] == {
        provider.keyid(ATTESTATION_PURPOSE): public_key_b64(
            provider, ATTESTATION_PURPOSE
        )
    }
