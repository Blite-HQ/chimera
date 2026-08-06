"""StatusList — revocación comprobable sin romper el air-gap. Ítem C7/M8
pieza 3.

`revocation: "none"` era el único campo del certificado que decía «no hay
forma de saber si esto fue retirado». Estos tests fijan la salida: la lista
es un artefacto estático FIRMADO con forma W3C Bitstring, el certificado
estampa dónde está su bit, y `verify-bundle` la consulta SOLO si se la dan —
declarando, cuando no, que la revocación no se comprobó.
"""

from __future__ import annotations

import base64
import gzip
import json
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from blite.certificate.bundle_check import check_bundle
from blite.certificate.keys import LocalKeyProvider
from blite.certificate.status_list import (
    MIN_ENTRIES,
    StatusListEntry,
    build_status_list,
    is_revoked,
    revoke_certificate,
    revoked_indices_for,
    sign_status_list,
    verify_status_list,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "scripts" / "example-bundle.json"

LISTA_ID = "chimera-revocacion@2026"
INDICE = 42


@pytest.fixture()
def bundle() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _clave() -> ed25519.Ed25519PrivateKey:
    return ed25519.Ed25519PrivateKey.generate()


def _publica(key: ed25519.Ed25519PrivateKey) -> str:
    return base64.b64encode(
        key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
    ).decode("ascii")


def _con_entrada(
    bundle: dict[str, Any], key: ed25519.Ed25519PrivateKey
) -> dict[str, Any]:
    """El bundle re-firmado declarando su posición en la lista. (El punto 1
    verifica contra `public_key`, así que la llave de la lista y la del
    certificado son la misma en este montaje — el caso de llaves distintas es
    el de C6/anillo.)"""
    from blite.certificate.canonical import canonicalize  # noqa: PLC0415
    from blite.certificate.dsse import sign  # noqa: PLC0415

    statement = json.loads(base64.b64decode(bundle["envelope"]["payload"]))
    statement["predicate"]["revocation"] = "status_list"
    statement["predicate"]["status_list_entry"] = {
        "status_list_id": LISTA_ID,
        "status_list_index": INDICE,
        "status_purpose": "revocation",
    }
    envelope = sign(
        payload_type=bundle["envelope"]["payloadType"],
        payload=canonicalize(statement),
        private_key=key,
        keyid="certificate:v1-status",
    )
    return {
        **bundle,
        "envelope": {
            "payloadType": envelope.payload_type,
            "payload": envelope.payload_b64,
            "signatures": [
                {"keyid": s.keyid, "sig": s.sig} for s in envelope.signatures
            ],
        },
        "public_key": _publica(key),
        # Los sobres por constancia quedan firmados con la llave vieja: se
        # quitan para que este archivo mida SOLO el punto 11.
        "attestation_envelopes": [],
    }


# ── Forma del bitstring (W3C adoptada) ──────────────────────────────────


def test_la_lista_vacia_no_revoca_a_nadie() -> None:
    lista = build_status_list(
        status_list_id=LISTA_ID, revoked_indices=set(), issued_at="2026-08-05T00:00:00Z"
    )

    assert is_revoked(lista, 0) is False
    assert is_revoked(lista, INDICE) is False


def test_el_indice_cero_es_el_bit_mas_significativo_del_primer_byte() -> None:
    """W3C §Bitstring — la convención importa: leerla al revés revocaría
    certificados ajenos en silencio."""
    lista = build_status_list(
        status_list_id=LISTA_ID, revoked_indices={0}, issued_at="2026-08-05T00:00:00Z"
    )

    crudo = gzip.decompress(base64.b64decode(lista.encoded_list))
    assert crudo[0] == 0x80
    assert is_revoked(lista, 0) is True
    assert is_revoked(lista, 1) is False


def test_la_lista_tiene_el_minimo_de_privacidad_de_rebano() -> None:
    """El mínimo de 16 KB no es capacidad: una lista del tamaño justo delata
    cuántos certificados hay y, con un índice, a cuál pertenece."""
    lista = build_status_list(
        status_list_id=LISTA_ID, revoked_indices={1}, issued_at="2026-08-05T00:00:00Z"
    )

    crudo = gzip.decompress(base64.b64decode(lista.encoded_list))
    assert len(crudo) * 8 >= MIN_ENTRIES
    # y aun así viaja en unos cientos de bytes
    assert len(lista.encoded_list) < 1000


def test_la_misma_lista_produce_los_mismos_bytes() -> None:
    """Sin `mtime=0`, gzip estampa la hora y el artefacto cambiaría en cada
    emisión — cualquier digest sobre él sería inútil."""
    argumentos: dict[str, Any] = {
        "status_list_id": LISTA_ID,
        "revoked_indices": {7, 9},
        "issued_at": "2026-08-05T00:00:00Z",
    }

    assert build_status_list(**argumentos) == build_status_list(**argumentos)


def test_un_indice_fuera_de_la_lista_es_error_no_un_no_revocado() -> None:
    """Responder «no revocado» a una pregunta que la lista no cubre sería
    inventar — y justo del lado cómodo."""
    lista = build_status_list(
        status_list_id=LISTA_ID, revoked_indices=set(), issued_at="2026-08-05T00:00:00Z"
    )

    with pytest.raises(ValueError, match="fuera de la lista"):
        is_revoked(lista, MIN_ENTRIES + 1)


# ── La lista como artefacto firmado ─────────────────────────────────────


def test_la_lista_firmada_se_verifica_desde_sus_bytes() -> None:
    key = _clave()
    lista = build_status_list(
        status_list_id=LISTA_ID,
        revoked_indices={INDICE},
        issued_at="2026-08-05T00:00:00Z",
    )

    artefacto = sign_status_list(lista, key_provider=LocalKeyProvider(key))

    assert verify_status_list(artefacto, _publica(key)) == lista


def test_una_lista_forjada_no_verifica() -> None:
    """Una lista sin verificar es peor que ninguna: cualquiera produciría una
    donde el certificado que le molesta aparece revocado."""
    from cryptography.exceptions import InvalidSignature  # noqa: PLC0415

    key = _clave()
    lista = build_status_list(
        status_list_id=LISTA_ID, revoked_indices=set(), issued_at="2026-08-05T00:00:00Z"
    )
    artefacto = sign_status_list(lista, key_provider=LocalKeyProvider(key))

    with pytest.raises(InvalidSignature):
        verify_status_list(artefacto, _publica(_clave()))


# ── Punto 11 del checklist ──────────────────────────────────────────────


def test_sin_lista_el_punto_11_declara_que_no_comprobo(bundle: dict[str, Any]) -> None:
    """LA semántica congelada de `VALID_AS_OF`, dicha en voz alta: el punto
    no falla (la verificación offline es completa) y tampoco finge."""
    con_entrada = _con_entrada(bundle, _clave())

    resultados = {r.number: r for r in check_bundle(con_entrada)}
    punto = resultados[max(resultados)]

    assert punto.ok
    assert any("NO comprobada" in nota for nota in punto.notes)


def test_un_certificado_revocado_reprueba(bundle: dict[str, Any]) -> None:
    key = _clave()
    con_entrada = _con_entrada(bundle, key)
    artefacto = sign_status_list(
        build_status_list(
            status_list_id=LISTA_ID,
            revoked_indices={INDICE},
            issued_at="2026-08-05T00:00:00Z",
        ),
        key_provider=LocalKeyProvider(key),
    )

    resultados = {r.number: r for r in check_bundle(con_entrada, status_list=artefacto)}
    punto = resultados[max(resultados)]

    assert not punto.ok
    assert any("REVOCADO" in falla for falla in punto.failures)


def test_un_certificado_vigente_pasa_con_la_fecha_de_la_lista(
    bundle: dict[str, Any],
) -> None:
    key = _clave()
    con_entrada = _con_entrada(bundle, key)
    artefacto = sign_status_list(
        build_status_list(
            status_list_id=LISTA_ID,
            revoked_indices={INDICE + 1},
            issued_at="2026-08-05T00:00:00Z",
        ),
        key_provider=LocalKeyProvider(key),
    )

    resultados = {r.number: r for r in check_bundle(con_entrada, status_list=artefacto)}
    punto = resultados[max(resultados)]

    assert punto.ok
    assert any("2026-08-05T00:00:00Z" in nota for nota in punto.notes)


def test_una_lista_de_otro_id_no_responde_la_pregunta(bundle: dict[str, Any]) -> None:
    """Presentar una lista cualquiera no vale: tiene que ser LA que el
    certificado nombra, o «no revocado» sería sobre otra cosa."""
    key = _clave()
    con_entrada = _con_entrada(bundle, key)
    artefacto = sign_status_list(
        build_status_list(
            status_list_id="otra-lista@2026",
            revoked_indices=set(),
            issued_at="2026-08-05T00:00:00Z",
        ),
        key_provider=LocalKeyProvider(key),
    )

    resultados = {r.number: r for r in check_bundle(con_entrada, status_list=artefacto)}

    assert not resultados[max(resultados)].ok


def test_un_bundle_sin_entrada_declara_que_no_publica_lista(
    bundle: dict[str, Any],
) -> None:
    """Los certificados ya emitidos autodeclaran `revocation: "none"` y su
    punto 11 pasa diciendo exactamente eso — sin lista que consultar."""
    resultados = {r.number: r for r in check_bundle(bundle)}
    punto = resultados[max(resultados)]

    assert punto.ok
    assert any("no publica lista" in nota for nota in punto.notes)


# ── La lista se DERIVA del log, no se mantiene a mano ───────────────────


def test_la_revocacion_es_un_hecho_del_log_y_la_lista_se_deriva() -> None:
    """Una lista mantenida a mano sería estado paralelo sin procedencia: la
    pregunta «¿por qué está revocado esto?» no tendría respuesta auditable.
    El bit sale del evento, nunca al revés."""
    # Arrange
    from blite.events import create_event_store  # noqa: PLC0415

    store = create_event_store()
    store.append(
        stream_id="run-x",
        type="run.created",
        actor_id="user:dylan",
        domain_id="d-default",
        payload={"run_id": "run-x"},
    )
    store.append(
        stream_id="run-x",
        type="run.completed",
        actor_id="service:runtime",
        domain_id="d-default",
        payload={},
    )

    # Act — revocar DESPUÉS del terminal (familia de cierre, fuera del corte)
    revoke_certificate(
        store,
        run_id="run-x",
        domain_id="d-default",
        entry=StatusListEntry(status_list_id=LISTA_ID, status_list_index=INDICE),
        reason="el ancla del corpus resultó estar mal derivada",
        actor_id="user:dylan",
    )

    # Assert
    evento = store.read_stream("run-x")[-1]
    assert evento.type == "certificate.revoked"
    assert evento.actor_id == "user:dylan"
    assert evento.payload["reason"]
    assert revoked_indices_for(store, LISTA_ID) == {INDICE}
    assert revoked_indices_for(store, "otra-lista@2026") == set()

    lista = build_status_list(
        status_list_id=LISTA_ID,
        revoked_indices=revoked_indices_for(store, LISTA_ID),
        issued_at="2026-08-05T00:00:00Z",
    )
    assert is_revoked(lista, INDICE) is True
