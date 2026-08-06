"""
Ensamblador del Bundle — el certificado se PROYECTA del stream de un run
vivo, jamás se fabrica a mano. [S-G · confianza]

Freeze §7: el Bundle mínimo = envelope DSSE (attestations embebidas — una
sola firma) + descriptores de anclas/verificadores + Policy pinneada (bytes
exactos) + stream del run + bytes de deliverables. Este módulo es el emisor;
el juez es `bundle_check` (D20: el checker no confía en el emisor — mantiene
sus propias copias de techos y orden de niveles).

Doctrina event-sourced: los claims salen de `claim.emitted`, las
attestations de `verification.completed` — si no está en el log, no entra al
certificado. Fail-closed (`AssembleError`): stream sin terminal, seq rotas o
una conclusión declarada que el run jamás emitió NO producen certificado.

Determinismo: todo se deriva de los inputs (el `valid_as_of` es el
`occurred_at` del evento terminal) — mismo stream + misma llave ⇒ mismos
bytes firmables. La llave la trae el caller (custodia = KeyProvider futuro).
"""

from __future__ import annotations

import base64
import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, cast

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from blite.certificate.canonical import canonicalize
from blite.certificate.dsse import sign
from blite.certificate.predicate import (
    AssuranceLevel,
    Conclusion,
    ConclusionVerdict,
    compute_titular_level,
)
from blite.events.chain import (
    chain_head_of_views,
    event_view,
    provenance_hash_of_views,
)
from blite.events.event import Event
from blite.events.rules import TERMINAL_RUN_EVENTS
from blite.events.store import EventStore
from blite.verification.claim import claim_view_digest

PAYLOAD_TYPE = "application/vnd.blite.trust-certificate+json"
STATEMENT_TYPE = "https://blite.dev/Statement/v1"
PREDICATE_TYPE = "https://blite.dev/TrustCertificate/v1"

_SC3_ASSUMPTION = (
    "Se verifica contra anclas declaradas, no contra la realidad última (SC3)"
)

# Orden local para el mínimo de niveles del emisor. `bundle_check` y
# `predicate` mantienen los suyos a propósito (D20) — no se comparten.
_LEVEL_ORDER: dict[str, int] = {"AL0": 0, "AL1": 1, "AL2": 2, "AL3": 3, "AL4": 4}


class AssembleError(RuntimeError):
    """Fail-closed del emisor: sin evidencia en el log no hay certificado."""


@dataclass(frozen=True)
class ConclusionDeclaration:
    """La conclusión que el caller declara — el stream decide su verdict."""

    canonical_statement: str
    scope: dict[str, Any]
    claim_type: str | None = None


def _validate_stream(views: Sequence[dict[str, Any]]) -> None:
    if not views:
        raise AssembleError("stream vacío: no hay run que certificar")
    if views[0]["type"] != "run.created":
        raise AssembleError("el stream no abre con run.created (corte freeze §2)")
    if views[-1]["type"] not in TERMINAL_RUN_EVENTS:
        raise AssembleError(
            "el stream no cierra en un evento terminal — un run vivo no se certifica"
        )
    seqs = [v["seq"] for v in views]
    if seqs != list(range(1, len(views) + 1)):
        raise AssembleError(f"seq no es 1..n estricto: {seqs}")


def _conclusion_from(
    declaration: ConclusionDeclaration,
    attestations: Sequence[dict[str, Any]],
    emitted_digests: frozenset[str],
) -> Conclusion:
    digest = claim_view_digest(declaration.canonical_statement, declaration.scope)
    if digest not in emitted_digests:
        raise AssembleError(
            f"claim {digest[:12]}… no fue emitido por el run — el certificado "
            "solo ampara claims presentes en el stream"
        )
    matching = [a for a in attestations if a["claim_digest"] == digest]
    if not matching:
        raise AssembleError(
            f"claim {digest[:12]}… sin attestations en el stream (fail-closed)"
        )
    verdicts = {a["verdict"] for a in matching}
    verdict: ConclusionVerdict
    level: AssuranceLevel
    if "fail" in verdicts:
        # Cualquier pata que refuta, refuta — mínimo, jamás promedio.
        verdict, level = "refuted", "AL0"
    elif "inconclusive" in verdicts:
        verdict, level = "inconclusive", "AL0"
    else:
        verdict = "verified"
        level = cast(
            "AssuranceLevel",
            min((a["level"] for a in matching), key=_LEVEL_ORDER.__getitem__),
        )
    return Conclusion(
        claim_digest=digest,
        canonical_statement=declaration.canonical_statement,
        scope=declaration.scope,
        verdict=verdict,
        level=level,
        claim_type=declaration.claim_type,
    )


def sub_run_streams_for(
    store: EventStore, stream: Sequence[Event]
) -> dict[str, tuple[Event, ...]]:
    """Los streams de los sub-runs que aportaron claims a este raíz.

    [M28 · C5] Se derivan del propio stream (los `claim.emitted` que traen
    `sub_run_id`), no de una lista que el caller mantenga: si el certificado
    ampara transitivamente el trabajo de un sub-run, el material para
    recomputarlo tiene que salir del MISMO log que lo declaró. El punto 9 del
    checklist falla si un claim declara un hash cuyo stream no viaja — así
    que olvidar esto no produce un certificado silenciosamente débil, produce
    un certificado que no verifica."""
    sub_run_ids = {
        event.payload["sub_run_id"]
        for event in stream
        if event.type == "claim.emitted" and event.payload.get("sub_run_id")
    }
    return {
        sub_run_id: store.read_stream(sub_run_id) for sub_run_id in sorted(sub_run_ids)
    }


def assemble_bundle(
    *,
    stream: Sequence[Event],
    conclusions: Sequence[ConclusionDeclaration],
    policy_yaml: bytes,
    signing_key: ed25519.Ed25519PrivateKey,
    keyid: str,
    anchor_descriptors: Sequence[dict[str, Any]] = (),
    deliverables: Sequence[tuple[str, bytes]] = (),
    sub_run_streams: Mapping[str, Sequence[Event]] = MappingProxyType({}),
    calculus_version: str = "cal-2.4",
    policy_ref_name: str = "verification-default.yaml",
) -> dict[str, Any]:
    """Proyecta el certificado del stream, lo firma (DSSE) y arma el Bundle.

    El retorno es el dict que `check_bundle` consume — el caller decide si lo
    valida (los tests lo hacen SIEMPRE: el emisor no se auto-declara 7/7).
    """
    views = [event_view(e) for e in stream]
    _validate_stream(views)

    provenance_hash = provenance_hash_of_views(views)

    created_payload: dict[str, Any] = views[0]["payload"]
    try:
        run_id: str = created_payload["run_id"]
        actor: str = created_payload["actor_id"]
    except KeyError as exc:
        msg = f"run.created sin campo obligatorio {exc} (freeze §3)"
        raise AssembleError(msg) from exc

    emitted_digests = frozenset(
        v["payload"]["claim_digest"] for v in views if v["type"] == "claim.emitted"
    )
    attestations: list[dict[str, Any]] = [
        v["payload"]["attestation"]
        for v in views
        if v["type"] == "verification.completed"
    ]

    conclusion_models = tuple(
        _conclusion_from(d, attestations, emitted_digests) for d in conclusions
    )
    titular = compute_titular_level(conclusion_models)
    policy_digest = hashlib.sha256(policy_yaml).hexdigest()

    deliverable_entries: list[dict[str, str]] = []
    deliverable_contents: dict[str, str] = {}
    for artifact_ref, blob in deliverables:
        digest = hashlib.sha256(blob).hexdigest()
        deliverable_entries.append({"artifact_ref": artifact_ref, "digest": digest})
        deliverable_contents[digest] = base64.b64encode(blob).decode("ascii")

    predicate: dict[str, Any] = {
        "run_id": run_id,
        "actor": actor,
        "provenance_hash": provenance_hash,
        "conclusions": [c.model_dump() for c in conclusion_models],
        "titular_level": titular,
        "assumptions": [
            {
                "statement": _SC3_ASSUMPTION,
                "ref": {"name": policy_ref_name, "digest": policy_digest},
            }
        ],
        "deliverables": deliverable_entries,
        "unanchored_steps": 0,
        "coverage_stats": {},
        "policy_digest": policy_digest,
        # [C5/M8 pieza 1] Head del hash-chain por evento en el corte del run
        # (anexo §4). Va DENTRO del payload firmado a propósito: un valor de
        # integridad que viviera fuera de la firma sería un número que nadie
        # atestigua. Es recomputable desde el `stream` empaquetado — punto 10
        # del checklist. Cuando la Fase 2 lo promueva a `provenance_hash`
        # "sin cambiar forma", este campo desaparece y `subject.digest`
        # pasa a llevar ESTE valor; hasta entonces conviven sin ambigüedad.
        "provenance_chain_head": chain_head_of_views(views),
        "calculus_version": calculus_version,
        "valid_as_of": views[-1]["occurred_at"],
        "revocation": "none",
        "attestations": attestations,
    }
    statement: dict[str, Any] = {
        "_type": STATEMENT_TYPE,
        "subject": [{"name": f"run:{run_id}", "digest": {"sha256": provenance_hash}}],
        "predicateType": PREDICATE_TYPE,
        "predicate": predicate,
    }

    payload_bytes = canonicalize(statement)
    envelope = sign(
        payload_type=PAYLOAD_TYPE,
        payload=payload_bytes,
        private_key=signing_key,
        keyid=keyid,
    )
    public_b64 = base64.b64encode(
        signing_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).decode("ascii")

    seen: set[str] = set()
    verifier_descriptors: list[dict[str, str]] = []
    for att in attestations:
        if att["verifier_id"] not in seen:
            seen.add(att["verifier_id"])
            verifier_descriptors.append(
                {
                    "verifier_id": att["verifier_id"],
                    "binary_digest": att["verifier_binary_digest"],
                }
            )

    return {
        "envelope": {
            "payloadType": envelope.payload_type,
            "payload": envelope.payload_b64,
            "signatures": [
                {"keyid": s.keyid, "sig": s.sig} for s in envelope.signatures
            ],
        },
        "public_key": public_b64,
        "stream": views,
        "anchor_descriptors": list(anchor_descriptors),
        "verifier_descriptors": verifier_descriptors,
        "policy_yaml_b64": base64.b64encode(policy_yaml).decode("ascii"),
        "deliverable_contents": deliverable_contents,
        # [M28 · C5] Los streams de los sub-runs que aportaron claims. Sin
        # ellos, el `sub_run_provenance_hash` que el stream del raíz estampa
        # es letra muerta: el anexo §4 manda RECOMPUTARLO offline, y no se
        # puede recomputar lo que no viaja. Punto 9 del checklist.
        "sub_run_streams": {
            sub_run_id: [event_view(event) for event in events]
            for sub_run_id, events in sub_run_streams.items()
        },
    }
