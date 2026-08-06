"""
DSSE por attestation — un sobre firmado por constancia, con predicate
modelado sobre **SLSA VSA** (Verification Summary Attestation). Ítem C6/M8
pieza 2 (research R3 §1).

**Por qué VSA y no vocabulario propio.** El formato estándar de «attestation
por verificación» ya existe y sus campos son casi exactamente los de una
`Attestation` + la Policy de Chimera: `verifier.id`, la policy aplicada, el
nivel alcanzado, `timeVerified`. Adoptar su FORMA (no su stack) hace que un
tercero con herramientas in-toto lea nuestras constancias sin traductor, y
nos ahorra inventar un vocabulario que después habría que defender.

**Qué cambia respecto de la Fase 1.** El freeze §7 [S-F · T6] resolvió que
las attestations viajaran EMBEBIDAS en el payload del certificado — una sola
firma — y dejó «DSSE por attestation individual» declarado como Fase 2, con
la separación S2 (Signer ≠ Verifier) anotada como limitación. Esta pieza la
levanta: cada constancia puede firmarse por separado, con su propia llave si
la custodia lo permite, y el sobre viaja junto al certificado. Es lo que
hace a M4 (constancia por isla) «de primera clase»: cada isla es un
documento firmado, no una entrada en una lista que alguien más firmó.

**Lo que NO cambia (extensión aditiva).** El certificado sigue llevando las
attestations embebidas: los bundles ya emitidos verifican igual y un
verificador viejo no ve nada raro. Los sobres son material ADICIONAL, y el
punto 7 del checklist exige que ambas vistas coincidan exactamente — un sobre
que ampare una constancia que el certificado no lleva (o al revés) es
incoherencia, no evidencia extra.
"""

from __future__ import annotations

import base64
from typing import Any

from blite.certificate.canonical import canonicalize
from blite.certificate.dsse import DSSEEnvelope
from blite.certificate.keys import ATTESTATION_PURPOSE, KeyProvider, sign_envelope

ATTESTATION_PAYLOAD_TYPE = "application/vnd.blite.verification-summary+json"
ATTESTATION_PREDICATE_TYPE = "https://blite.dev/VerificationSummary/v1"
STATEMENT_TYPE = "https://blite.dev/Statement/v1"


def attestation_statement(
    attestation: dict[str, Any], *, policy_digest: str
) -> dict[str, Any]:
    """Statement in-toto de UNA constancia, con predicate forma-VSA.

    El `subject` es el CLAIM (`claim:<digest>`): lo que esta constancia
    resume es un veredicto sobre ese claim, y atarla a otra cosa (el run, el
    verificador) permitiría re-usar el sobre para amparar un claim distinto.

    Los nombres de campo siguen a VSA donde VSA los tiene (`verifier`,
    `timeVerified`, `policy`, `verificationResult`) y usan los propios donde
    el vocabulario de Chimera es más fino que el estándar (`assuranceLevel`,
    `verifierClass`, `anchor`, `independenceGroup`) — mezclar sin decirlo
    sería peor que no adoptarlo."""
    return {
        "_type": STATEMENT_TYPE,
        "subject": [
            {
                "name": f"claim:{attestation['claim_digest']}",
                "digest": {"sha256": attestation["claim_digest"]},
            }
        ],
        "predicateType": ATTESTATION_PREDICATE_TYPE,
        "predicate": {
            "verifier": {
                "id": attestation["verifier_id"],
                "binaryDigest": attestation["verifier_binary_digest"],
                "paramsDigest": attestation["verifier_params_digest"],
            },
            "timeVerified": attestation["issued_at"],
            "policy": {"digest": policy_digest},
            "verificationResult": attestation["verdict"],
            "assuranceLevel": attestation["level"],
            "verifierClass": attestation["verifier_class"],
            "anchor": {
                "kind": attestation.get("anchor_kind"),
                "digest": attestation.get("anchor_digest"),
            },
            "independenceGroup": attestation["independence_group"],
            "resourceUri": _resource_uri(attestation),
        },
    }


def _resource_uri(attestation: dict[str, Any]) -> str:
    """`run/<run_id>` o `run/<run_id>/step/<step_id>` — la sub-entidad que
    esta constancia cubre (M4: una isla). Sin el `step_id` en el sobre, dos
    constancias por isla del mismo run serían indistinguibles firmadas."""
    step_id = attestation.get("step_id")
    base = f"run/{attestation['run_id']}"
    return base if step_id is None else f"{base}/step/{step_id}"


def sign_attestation(
    attestation: dict[str, Any],
    *,
    policy_digest: str,
    key_provider: KeyProvider,
) -> DSSEEnvelope:
    """Firma UNA constancia como sobre DSSE independiente, POR EL PUERTO y con
    su propio `purpose` (Regla 1: se firman los bytes canónicos exactos, y son
    esos los que viajan).

    El `purpose` separado es lo que permite que la custodia le dé al
    verificador una llave propia — sin él, «cada verificador firma lo suyo»
    seguiría dependiendo de que alguien se acuerde."""
    return sign_envelope(
        key_provider,
        purpose=ATTESTATION_PURPOSE,
        payload_type=ATTESTATION_PAYLOAD_TYPE,
        payload=canonicalize(
            attestation_statement(attestation, policy_digest=policy_digest)
        ),
    )


def envelope_to_wire(envelope: DSSEEnvelope) -> dict[str, Any]:
    """La forma que viaja en el Bundle — misma que la del certificado."""
    return {
        "payloadType": envelope.payload_type,
        "payload": envelope.payload_b64,
        "signatures": [{"keyid": s.keyid, "sig": s.sig} for s in envelope.signatures],
    }


def attestation_subject_digest(envelope_wire: dict[str, Any]) -> str:
    """El `claim_digest` que un sobre ampara, leído de sus BYTES FIRMADOS."""
    import json  # noqa: PLC0415 — import local: el módulo no necesita json en el resto

    statement = json.loads(base64.b64decode(envelope_wire["payload"]))
    return str(statement["subject"][0]["digest"]["sha256"])


__all__ = [
    "ATTESTATION_PAYLOAD_TYPE",
    "ATTESTATION_PREDICATE_TYPE",
    "attestation_statement",
    "attestation_subject_digest",
    "envelope_to_wire",
    "sign_attestation",
]
