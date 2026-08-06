"""Puntos 9 (sub-runs) y 10 (hash-chain) del checklist — ítem C5/M8 pieza 1
+ M28. Adversarial, como el resto del checklist: cada punto debe cazar SU
forja, y ninguno de los dos puede reprobar un Bundle emitido antes de que
existieran.

El punto 9 cierra una letra que llevaba congelada sin cumplirse: el anexo §4
manda que el verificador offline RECOMPUTE el hash del sub-run y lo compare
contra el `●ClaimEmitted` del raíz. Faltaban las dos mitades — el stream del
sub-run no viajaba en el Bundle, y el hash se computaba con otra fórmula
(M28). Con una sola de las dos, el punto seguiría siendo decorativo.
"""

from __future__ import annotations

import base64
import copy
import json
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from blite.certificate.bundle_check import check_bundle
from blite.certificate.canonical import canonicalize
from blite.certificate.dsse import sign
from blite.events.chain import chain_head_of_views, provenance_hash_of_views

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "scripts" / "example-bundle.json"


@pytest.fixture()
def bundle() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _failed_points(bundle: dict[str, Any]) -> set[int]:
    return {r.number for r in check_bundle(bundle) if not r.ok}


def _sub_run_stream(run_id: str = "sub-run-1") -> list[dict[str, Any]]:
    """Un stream de sub-run mínimo y VÁLIDO (abre en run.created, cierra en
    terminal) — la forma que `provenance_slice` deja pasar."""
    return [
        {
            "id": "0198c0de-0000-7000-8000-00000000f001",
            "stream_id": run_id,
            "seq": 1,
            "type": "run.created",
            "actor_id": "service:runtime",
            "domain_id": "d-default",
            "payload": {"run_id": run_id, "actor_id": "user:dylan"},
            "occurred_at": "2026-07-22T12:00:00.000000Z",
        },
        {
            "id": "0198c0de-0000-7000-8000-00000000f002",
            "stream_id": run_id,
            "seq": 2,
            "type": "run.completed",
            "actor_id": "service:runtime",
            "domain_id": "d-default",
            "payload": {},
            "occurred_at": "2026-07-22T12:00:01.000000Z",
        },
    ]


def _with_sub_run(bundle: dict[str, Any], *, empaquetado: bool) -> dict[str, Any]:
    """Inyecta en el stream del raíz un `claim.emitted` que declara el hash
    de un sub-run. El Bundle resultante NO pasa el punto 2 (el stream cambió
    y el hash firmado ya no casa) — a este archivo solo le importan 9 y 10,
    que son independientes de la firma."""
    forjado = copy.deepcopy(bundle)
    sub_stream = _sub_run_stream()
    forjado["stream"].insert(
        -1,
        {
            "id": "0198c0de-0000-7000-8000-00000000e001",
            "stream_id": "8f2c1a9b",
            "seq": 99,
            "type": "claim.emitted",
            "actor_id": "service:runtime",
            "domain_id": "d-default",
            "payload": {
                "claim_digest": "a" * 64,
                "claim_type": "solution",
                "is_conclusion": True,
                "sub_run_id": "sub-run-1",
                "sub_run_provenance_hash": provenance_hash_of_views(sub_stream),
            },
            "occurred_at": "2026-07-22T12:00:05.000000Z",
        },
    )
    if empaquetado:
        forjado["sub_run_streams"] = {"sub-run-1": sub_stream}
    return forjado


# ── Punto 9 · sub-runs ──────────────────────────────────────────────────


def test_punto_9_pasa_vacio_cuando_no_hay_claims_de_sub_run(
    bundle: dict[str, Any],
) -> None:
    """Un Bundle sin sub-runs no afirma NADA sobre sub-runs: el punto no
    tiene qué reprobar. Es lo que mantiene la extensión aditiva de verdad —
    los certificados ya emitidos no cambian de veredicto."""
    assert 9 not in _failed_points(bundle)


def test_punto_9_recomputa_el_hash_del_sub_run_empaquetado(
    bundle: dict[str, Any],
) -> None:
    assert 9 not in _failed_points(_with_sub_run(bundle, empaquetado=True))


def test_punto_9_falla_si_el_stream_del_sub_run_no_viaja(
    bundle: dict[str, Any],
) -> None:
    """Fail-closed: el certificado ampara trabajo que nadie puede recomputar.
    Este era EL estado del repo antes de C5 — `sub_run_id` como puntero sin
    integridad (freeze §13), y ningún punto lo notaba."""
    assert 9 in _failed_points(_with_sub_run(bundle, empaquetado=False))


def test_punto_9_caza_un_sub_run_reescrito(bundle: dict[str, Any]) -> None:
    """La forja que importa: se empaqueta un stream de sub-run distinto del
    que produjo el hash estampado."""
    forjado = _with_sub_run(bundle, empaquetado=True)
    forjado["sub_run_streams"]["sub-run-1"][0]["payload"]["run_id"] = "sub-run-FORJADO"

    assert 9 in _failed_points(forjado)


# ── Punto 10 · hash-chain ───────────────────────────────────────────────


def test_punto_10_verifica_el_head_firmado_del_bundle_vigente(
    bundle: dict[str, Any],
) -> None:
    assert 10 not in _failed_points(bundle)
    payload = json.loads(base64.b64decode(bundle["envelope"]["payload"]))
    assert payload["predicate"]["provenance_chain_head"] == chain_head_of_views(
        bundle["stream"]
    )


def test_punto_10_caza_un_stream_reescrito_bajo_el_head_firmado(
    bundle: dict[str, Any],
) -> None:
    bundle["stream"][1]["payload"]["job_id"] = "j-FORJADO"
    assert 10 in _failed_points(bundle)


def test_punto_10_no_verifica_lo_que_el_certificado_no_declara(
    bundle: dict[str, Any],
) -> None:
    """Opt-in honesto: un Bundle sin `provenance_chain_head` (emitido antes
    de que el writer encadenara) NO falla el punto — y tampoco finge haberlo
    verificado. El punto 2 sigue amparando el stream por otra vía."""
    # Arrange — se re-firma un payload sin el campo, como lo tendría un
    # bundle viejo. Se muta el payload SIN re-firmar: el punto 1 caerá, pero
    # el 10 lee el predicate igual y es lo único que este test observa.
    statement = json.loads(base64.b64decode(bundle["envelope"]["payload"]))
    del statement["predicate"]["provenance_chain_head"]
    bundle["envelope"]["payload"] = base64.b64encode(
        json.dumps(statement).encode()
    ).decode("ascii")

    # Assert
    assert 10 not in _failed_points(bundle)


def _resign_without_c5(bundle: dict[str, Any]) -> dict[str, Any]:
    """Reconstruye el Bundle tal como lo habría emitido el repo ANTES de C5:
    sin `provenance_chain_head` en el predicate y sin `sub_run_streams`. Se
    RE-FIRMA de verdad (llave propia del test) para que el punto 1 siga
    siendo un chequeo real y no un adorno."""
    viejo = copy.deepcopy(bundle)
    statement = json.loads(base64.b64decode(viejo["envelope"]["payload"]))
    statement["predicate"].pop("provenance_chain_head", None)
    viejo.pop("sub_run_streams", None)

    private_key = ed25519.Ed25519PrivateKey.generate()
    envelope = sign(
        payload_type=viejo["envelope"]["payloadType"],
        payload=canonicalize(statement),
        private_key=private_key,
        keyid="certificate:v1-viejo",
    )
    viejo["envelope"] = {
        "payloadType": envelope.payload_type,
        "payload": envelope.payload_b64,
        "signatures": [{"keyid": s.keyid, "sig": s.sig} for s in envelope.signatures],
    }
    viejo["public_key"] = base64.b64encode(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
    ).decode("ascii")
    return viejo


def test_un_bundle_viejo_conserva_sus_8_puntos(bundle: dict[str, Any]) -> None:
    """LA garantía de la extensión aditiva (DoD del ítem): un Bundle emitido
    antes de C5 —sin head de cadena y sin streams de sub-run— sigue
    verificando sus 8 puntos originales. Si algún punto 1-8 hubiera pasado a
    depender de lo nuevo, este test lo grita."""
    # Arrange
    viejo = _resign_without_c5(bundle)

    # Act
    resultados = {r.number: r for r in check_bundle(viejo)}

    # Assert — los 8 originales verdes; los nuevos, sin nada que reprobar
    assert [n for n in range(1, 9) if not resultados[n].ok] == []
    assert resultados[9].ok
    assert resultados[10].ok
