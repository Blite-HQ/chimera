#!/usr/bin/env python3
"""Genera el Bundle de ejemplo del checklist + el fixture del Studio.

Vocabulario vigente (clase + AL + criticidad — freeze §4). Es auto-validante:
corre TODOS los puntos de `blite.certificate.bundle_check` y solo escribe si
dan el 100% — el generador no puede producir un fixture que su propio
verificador rechace. Escribe DOS salidas desde el MISMO bundle (una sola
fuente):

- `scripts/example-bundle.json` — el Bundle completo (checklist/verify-bundle).
- `apps/studio/src/fixtures/certificate.example.json` — solo el envelope DSSE
  (lo que `CertificateView` consume, nota 18 §2.3). Supersede a
  `gen-example-trust-certificate.py` (reobra ET-9, 2026-07-22: el fixture
  viejo hablaba `rung` + política muerta @0.1.0).

La llave Ed25519 es efímera y solo-demo (jamás se persiste); la pública viaja
en el bundle SOLO como comodidad del fixture — en producción llega por el
canal de distribución de la organización, no dentro del bundle.
"""

from __future__ import annotations

import base64
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from blite.certificate.bundle_check import CLAIM_PREFIX, check_bundle
from blite.certificate.canonical import canonicalize
from blite.certificate.keys import LocalKeyProvider
from blite.certificate.vsa import envelope_to_wire, sign_attestation
from blite.events.chain import chain_head_of_views, provenance_hash_of_views

REPO = Path(__file__).resolve().parent.parent
POLICY_PATH = (
    REPO / "distributions" / "chimera" / "policies" / "verification-default.yaml"
)
OUTPUT_PATH = REPO / "scripts" / "example-bundle.json"
STUDIO_FIXTURE_PATH = (
    REPO / "apps" / "studio" / "src" / "fixtures" / "certificate.example.json"
)

PAYLOAD_TYPE = "application/vnd.blite.trust-certificate+json"
RUN_ID = "8f2c1a9b"
DOMAIN = "d-default"


def _event(i: int, type_: str, actor: str, payload: dict[str, Any]) -> dict[str, Any]:
    """view(e) exacto del anexo §3 — 8 campos, occurred_at RFC3339 con 6 fraccionales."""
    return {
        "id": f"0198c0de-0000-7000-8000-00000000000{i}",
        "stream_id": RUN_ID,
        "seq": i,
        "type": type_,
        "actor_id": actor,
        "domain_id": DOMAIN,
        "payload": payload,
        "occurred_at": f"2026-07-22T12:00:0{i}.000000Z",
    }


CANONICAL_STATEMENT = (
    "La partición propuesta de ieee14 es el óptimo exacto del corte bajo las "
    "restricciones declaradas"
)
SCOPE = {
    "instance": "ieee14",
    "problem": "islanding-partition",
    "constraints": "declared-v1",
}
_CLAIM_DIGEST = hashlib.sha256(
    CLAIM_PREFIX
    + canonicalize({"canonical_statement": CANONICAL_STATEMENT, "scope": SCOPE})
).hexdigest()


def main() -> int:
    policy_bytes = POLICY_PATH.read_bytes()
    policy_digest = hashlib.sha256(policy_bytes).hexdigest()

    # --- Stream del run (freeze §3: run.created carga TODO lo de la proyección) ---
    stream = [
        _event(
            1,
            "run.created",
            "user:dylan",
            {
                "run_id": RUN_ID,
                "actor_id": "user:dylan",
                "domain_id": DOMAIN,
                "max_steps": 8,
                "policy_digest": policy_digest,
                "parent_run_id": None,
            },
        ),
        _event(
            2,
            "capability.job.submitted",
            "service:runtime",
            {"job_id": "j1", "step_id": "s1"},
        ),
        _event(3, "capability.job.completed", "service:runtime", {"job_id": "j1"}),
        # [C15] El `claim.emitted` con sus PORTADORES (§6 [stress-final]): sin
        # él, el evaluador de la Policy no puede saber los `side_effects` de
        # la conclusión y ninguna regla que los restrinja aplica — fail-closed.
        # Un run real siempre lo emite (el orquestador lo hace antes de cada
        # `verification.completed`); este fixture lo omitía y por eso parecía
        # verificar contra una regla que en realidad no le correspondía.
        _event(
            4,
            "claim.emitted",
            "service:runtime",
            {
                "claim_digest": _CLAIM_DIGEST,
                "claim_type": "solution",
                "is_conclusion": True,
                "world": False,
                "irreversible": False,
                "affects_third_party": False,
            },
        ),
        _event(
            5,
            "verification.completed",
            "service:runtime",
            {"verdict": "pass", "policy_id": "chimera-default@0.2.0"},
        ),
        _event(6, "run.completed", "service:runtime", {}),
    ]
    provenance_hash = provenance_hash_of_views(stream)

    # --- Conclusión + claim_digest por la fórmula del anexo §5 ---
    canonical_statement, scope, claim_digest = (
        CANONICAL_STATEMENT,
        SCOPE,
        _CLAIM_DIGEST,
    )

    anchor_solver = hashlib.sha256(b"anchor:cpsat-reference-v1").hexdigest()
    anchor_exec = hashlib.sha256(b"anchor:pandapower-case14-v1").hexdigest()

    attestations = [
        {
            "verifier_id": "ortools-cpsat",
            "verifier_class": "formal_exact",
            "run_id": RUN_ID,
            "anchor_kind": "solver",
            "verdict": "pass",
            "level": "AL3",
            "independence_group": "leg-formal",
            "claim_digest": claim_digest,
            "verifier_binary_digest": hashlib.sha256(b"ortools-9.14").hexdigest(),
            "verifier_params_digest": hashlib.sha256(b"cpsat-params-v1").hexdigest(),
            "anchor_digest": anchor_solver,
            "predicate": {"differential": {"status": "OPTIMAL", "objective": 3}},
            "evidence_digests": [],
            "issued_at": "2026-07-22T12:00:04.000000Z",
        },
        {
            "verifier_id": "pandapower-powerflow",
            "verifier_class": "execution",
            "run_id": RUN_ID,
            "anchor_kind": "execution",
            "verdict": "pass",
            "level": "AL3",
            "independence_group": "leg-execution",
            "claim_digest": claim_digest,
            "verifier_binary_digest": hashlib.sha256(b"pandapower-3.5.4").hexdigest(),
            "verifier_params_digest": hashlib.sha256(
                b"powerflow-params-v1"
            ).hexdigest(),
            "anchor_digest": anchor_exec,
            "predicate": {"reruns": 1, "timed_out": False},
            "evidence_digests": [],
            "issued_at": "2026-07-22T12:00:04.000000Z",
        },
    ]

    deliverable_bytes = b'{"islands":[[0,1,2,3,4,5,6],[7,8,9,10,11,12,13]]}\n'
    deliverable_digest = hashlib.sha256(deliverable_bytes).hexdigest()

    predicate = {
        "run_id": RUN_ID,
        "actor": "user:dylan",
        "provenance_hash": provenance_hash,
        "conclusions": [
            {
                "claim_digest": claim_digest,
                "canonical_statement": canonical_statement,
                "scope": scope,
                "verdict": "verified",
                "level": "AL3",
                "claim_type": "solution",
            }
        ],
        "titular_level": "AL3",
        "assumptions": [
            {
                "statement": "Se verifica contra anclas declaradas, no contra la realidad última (SC3)",
                "ref": {"name": "verification-default.yaml", "digest": policy_digest},
            }
        ],
        "deliverables": [
            {"artifact_ref": "partition.json", "digest": deliverable_digest}
        ],
        "unanchored_steps": 0,
        "coverage_stats": {},
        "policy_digest": policy_digest,
        # [C5/M8 pieza 1] Head del hash-chain sobre el MISMO corte — punto 10.
        "provenance_chain_head": chain_head_of_views(stream),
        "calculus_version": "cal-2.4",
        "valid_as_of": "2026-07-22T12:00:06.000000Z",
        "revocation": "none",
        "attestations": attestations,
    }
    statement = {
        "_type": "https://blite.dev/Statement/v1",
        "subject": [{"name": f"run:{RUN_ID}", "digest": {"sha256": provenance_hash}}],
        "predicateType": "https://blite.dev/TrustCertificate/v1",
        "predicate": predicate,
    }

    payload_bytes = canonicalize(statement)
    private_key = ed25519.Ed25519PrivateKey.generate()
    key_provider = LocalKeyProvider(private_key)
    signature = private_key.sign(
        b"DSSEv1 "
        + str(len(PAYLOAD_TYPE.encode())).encode()
        + b" "
        + PAYLOAD_TYPE.encode()
        + b" "
        + str(len(payload_bytes)).encode()
        + b" "
        + payload_bytes
    )
    public_b64 = base64.b64encode(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
    ).decode("ascii")

    bundle = {
        "envelope": {
            "payloadType": PAYLOAD_TYPE,
            "payload": base64.b64encode(payload_bytes).decode("ascii"),
            "signatures": [
                {
                    "keyid": "certificate:v1-example",
                    "sig": base64.b64encode(signature).decode("ascii"),
                }
            ],
        },
        "public_key": public_b64,
        "stream": stream,
        "anchor_descriptors": [
            {
                "anchor_digest": anchor_solver,
                "kind": "solver",
                "provenance": "cpsat-reference-v1",
            },
            {
                "anchor_digest": anchor_exec,
                "kind": "execution",
                "provenance": "pandapower-case14-v1",
            },
        ],
        "verifier_descriptors": [
            {
                "verifier_id": a["verifier_id"],
                "binary_digest": a["verifier_binary_digest"],
            }
            for a in attestations
        ],
        "policy_yaml_b64": base64.b64encode(policy_bytes).decode("ascii"),
        "deliverable_contents": {
            deliverable_digest: base64.b64encode(deliverable_bytes).decode("ascii")
        },
        # [C6/M8 pieza 2] Un sobre DSSE por constancia (predicate forma-VSA).
        "attestation_envelopes": [
            envelope_to_wire(
                sign_attestation(
                    attestation,
                    policy_digest=policy_digest,
                    key_provider=key_provider,
                )
            )
            for attestation in attestations
        ],
    }

    # --- Auto-validación: el generador jamás escribe un bundle que no dé el 100% ---
    results = check_bundle(bundle)
    total = len(results)
    for r in results:
        status = "OK" if r.ok else f"FALLA {r.failures}"
        print(f"[{r.number}/{total}] {status} — {r.name}")
    if not all(r.ok for r in results):
        print("ABORT: el bundle generado no pasa su propio checklist")
        return 1

    OUTPUT_PATH.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    print(f"\nBundle escrito en {OUTPUT_PATH} ({total}/{total})")

    # Fixture del Studio: SOLO el envelope (CertificateView consume DsseEnvelope,
    # nota 18 §2.3) — mismo bundle ya validado, jamás una segunda fuente.
    STUDIO_FIXTURE_PATH.write_text(
        json.dumps(bundle["envelope"], indent=2) + "\n", encoding="utf-8"
    )
    print(f"Fixture del Studio escrito en {STUDIO_FIXTURE_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
