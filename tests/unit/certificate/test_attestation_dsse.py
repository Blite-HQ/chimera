"""DSSE por attestation con predicate forma-VSA — ítem C6/M8 pieza 2.

El freeze §7 [S-F · T6] resolvió para Fase 1 «attestations EMBEBIDAS, una
sola firma» y dejó el sobre individual declarado como Fase 2, con la
separación S2 (Signer ≠ Verifier) anotada como limitación. Estos tests fijan
el levantamiento: cada constancia puede firmarse aparte —con su propia llave
si la custodia lo permite— y el punto 7 exige que las dos vistas del bundle
(embebida y firmada) digan EXACTAMENTE lo mismo.

La pregunta que el checklist responde no es «¿están firmados?» sino «¿firman
lo mismo que el certificado dice?»: un sobre de más es evidencia colada por
la puerta de atrás; uno de menos es una firma que alguien decidió no dar.
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
from blite.certificate.keys import (
    ATTESTATION_PURPOSE,
    LocalKeyProvider,
    public_key_b64,
)
from blite.certificate.vsa import (
    ATTESTATION_PREDICATE_TYPE,
    attestation_statement,
    envelope_to_wire,
    sign_attestation,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "scripts" / "example-bundle.json"

POLICY_DIGEST = "b" * 64

ATTESTATION: dict[str, Any] = {
    "verifier_id": "pandapower-powerflow",
    "verifier_class": "execution",
    "anchor_kind": "execution",
    "anchor_digest": "a" * 64,
    "level": "AL3",
    "verdict": "pass",
    "independence_group": "leg-execution",
    "run_id": "8f2c1a9b",
    "step_id": "island-1",
    "claim_digest": "c" * 64,
    "verifier_binary_digest": "d" * 64,
    "verifier_params_digest": "e" * 64,
    "issued_at": "2026-08-05T12:00:00.000000Z",
}


@pytest.fixture()
def bundle() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _failed_points(bundle: dict[str, Any]) -> set[int]:
    return {r.number for r in check_bundle(bundle) if not r.ok}


# ── Forma del statement (VSA adoptada, no inventada) ────────────────────


def test_el_subject_del_sobre_es_el_claim_y_no_el_run() -> None:
    """Lo que una constancia resume es un veredicto SOBRE UN CLAIM. Atarla al
    run permitiría reusar el sobre para amparar otro claim del mismo run."""
    statement = attestation_statement(ATTESTATION, policy_digest=POLICY_DIGEST)

    assert statement["subject"][0]["digest"]["sha256"] == ATTESTATION["claim_digest"]
    assert statement["predicateType"] == ATTESTATION_PREDICATE_TYPE


def test_el_predicate_habla_vsa_donde_vsa_tiene_palabra() -> None:
    """Se adopta la FORMA del estándar (`verifier`, `timeVerified`, `policy`,
    `verificationResult`) para que un tercero con herramientas in-toto lea
    esto sin traductor — y se usan campos propios donde el vocabulario de
    Chimera es más fino que el de VSA."""
    predicado = attestation_statement(ATTESTATION, policy_digest=POLICY_DIGEST)[
        "predicate"
    ]

    assert predicado["verifier"]["id"] == "pandapower-powerflow"
    assert predicado["timeVerified"] == ATTESTATION["issued_at"]
    assert predicado["policy"]["digest"] == POLICY_DIGEST
    assert predicado["verificationResult"] == "pass"
    assert predicado["assuranceLevel"] == "AL3"
    assert predicado["verifierClass"] == "execution"
    assert predicado["independenceGroup"] == "leg-execution"


def test_el_recurso_distingue_la_isla_que_la_constancia_cubre() -> None:
    """M4 «de primera clase»: sin el `step_id` en el sobre, dos constancias
    por isla del mismo run serían indistinguibles una vez firmadas."""
    con_isla = attestation_statement(ATTESTATION, policy_digest=POLICY_DIGEST)
    sin_isla = attestation_statement(
        {**ATTESTATION, "step_id": None}, policy_digest=POLICY_DIGEST
    )

    assert con_isla["predicate"]["resourceUri"] == "run/8f2c1a9b/step/island-1"
    assert sin_isla["predicate"]["resourceUri"] == "run/8f2c1a9b"


# ── El punto 7 sobre los sobres ─────────────────────────────────────────


def test_el_bundle_vigente_trae_un_sobre_por_constancia_y_verifica(
    bundle: dict[str, Any],
) -> None:
    payload = json.loads(base64.b64decode(bundle["envelope"]["payload"]))

    assert len(bundle["attestation_envelopes"]) == len(
        payload["predicate"]["attestations"]
    )
    assert 7 not in _failed_points(bundle)


def test_un_sobre_con_firma_forjada_reprueba_el_punto_7(
    bundle: dict[str, Any],
) -> None:
    sobre = bundle["attestation_envelopes"][0]
    crudo = bytearray(base64.b64decode(sobre["signatures"][0]["sig"]))
    crudo[0] ^= 0xFF
    sobre["signatures"][0]["sig"] = base64.b64encode(bytes(crudo)).decode()

    assert 7 in _failed_points(bundle)


def test_un_sobre_de_mas_reprueba_el_punto_7(bundle: dict[str, Any]) -> None:
    """Evidencia colada por la puerta de atrás: una constancia firmada que el
    certificado NO embebe no cuenta — el payload firmado del certificado
    sigue siendo la lista autoritativa."""
    # Arrange — un sobre legítimamente firmado, pero de una constancia ajena
    private_key = ed25519.Ed25519PrivateKey.generate()
    forjado = copy.deepcopy(bundle)
    forjado["attestation_public_keys"] = {
        "attestation:intruso": base64.b64encode(
            private_key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        ).decode("ascii")
    }
    forjado["attestation_envelopes"].append(
        envelope_to_wire(
            sign_attestation(
                {**ATTESTATION, "verifier_id": "verificador-fantasma"},
                policy_digest=POLICY_DIGEST,
                key_provider=LocalKeyProvider(private_key),
            )
        )
    )

    # Assert
    assert 7 in _failed_points(forjado)


def test_una_constancia_sin_sobre_reprueba_el_punto_7(
    bundle: dict[str, Any],
) -> None:
    """Y la asimetría contraria: si el bundle trae sobres, los trae para
    TODAS. Quitar el de una constancia es exactamente cómo se vería alguien
    negándose a firmar la que no le conviene."""
    bundle["attestation_envelopes"].pop()

    assert 7 in _failed_points(bundle)


def test_un_bundle_sin_sobres_conserva_su_punto_7(bundle: dict[str, Any]) -> None:
    """Opt-in: los bundles emitidos antes de C6 no traen sobres y su punto 7
    sigue decidiéndose por las attestations embebidas, como siempre."""
    del bundle["attestation_envelopes"]

    assert 7 not in _failed_points(bundle)


def test_el_sobre_puede_venir_de_otra_llave_que_la_del_certificado(
    bundle: dict[str, Any],
) -> None:
    """La razón de ser de la pieza (separación S2, Signer ≠ Verifier): el
    verificador puede firmar SU constancia con su propia llave, y el bundle
    la trae en el anillo. Con una sola firma para todo, «el verificador
    firma lo que verificó» era una limitación declarada, no un hecho."""
    # Arrange — se re-firman TODAS las constancias con una llave distinta
    payload = json.loads(base64.b64decode(bundle["envelope"]["payload"]))
    del_verificador = LocalKeyProvider(ed25519.Ed25519PrivateKey.generate())
    bundle["attestation_envelopes"] = [
        envelope_to_wire(
            sign_attestation(
                att,
                policy_digest=payload["predicate"]["policy_digest"],
                key_provider=del_verificador,
            )
        )
        for att in payload["predicate"]["attestations"]
    ]
    bundle["attestation_public_keys"] = {
        del_verificador.keyid(ATTESTATION_PURPOSE): public_key_b64(
            del_verificador, ATTESTATION_PURPOSE
        )
    }

    # Assert
    assert 7 not in _failed_points(bundle)
