"""Genera un TrustCertificate v0 de ejemplo, firmado DSSE (Ed25519).

Fixture para el Studio (ficha B3): construye el Statement in-toto-style
(nota 02 SS1.3) para el run IEEE-14 del spike (mismos verifiers/rungs que
`apps/studio/src/spike/ieee14.ts::RUN_VERIFICATION`), lo canonicaliza con el
mismo C(x) del anexo de canonicalizacion
(docs/contract-freeze-anexo-canonicalizacion.md SS2 — subset RFC 8785/JCS,
importado del engine: blite.certificate.canonical — fuente unica), firma el PAE de
DSSE con una llave Ed25519 efimera, y valida el roundtrip de la firma antes
de escribir el envelope a apps/studio/src/fixtures/certificate.example.json.

La llave privada es efimera y SOLO para demo: se genera en memoria, se usa,
y nunca se persiste a disco. El keyid ("example-2026") deja explicito que
esta NO es la llave real del engine.
"""

import base64
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

# --- C(x): fuente unica — el engine (stress final post-convergencia, 2026-07-22) ---
# La copia embebida anterior usaba repr() crudo y divergia de
# engine/certificate/canonical.py en la banda [1e-6, 1e-4) — exactamente el
# drift "dos implementaciones honestas, hashes distintos" que el anexo prohibe.
from blite.certificate.canonical import canonicalize

# --- DSSE PAE (Pre-Authentication Encoding) — spec real, no el atajo de la nota 02 ---

PAYLOAD_TYPE = "application/vnd.blite.trust-certificate+json"


def dsse_pae(payload_type: str, payload_bytes: bytes) -> bytes:
    """PAE(payloadType, payload) = DSSEv1 <len(type)> <type> <len(payload)> <payload>."""
    type_bytes = payload_type.encode("utf-8")
    return (
        b"DSSEv1"
        + b" "
        + str(len(type_bytes)).encode("ascii")
        + b" "
        + type_bytes
        + b" "
        + str(len(payload_bytes)).encode("ascii")
        + b" "
        + payload_bytes
    )


# --- Statement (TrustCertificate v0) — consistente con el run IEEE-14 del spike ---

RUN_ID = "8f2c1a9b"
FAKE_PROVENANCE_HASH = hashlib.sha256(
    f"chimera-demo-run-{RUN_ID}-ieee14-partition-stream".encode("ascii")
).hexdigest()


def build_statement() -> dict[str, Any]:
    return {
        "_type": "https://blite.dev/Statement/v0",
        "subject": [
            {
                "name": f"run:{RUN_ID}",
                "digest": {"sha256": FAKE_PROVENANCE_HASH},
            }
        ],
        "predicateType": "https://blite.dev/TrustCertificate/v0",
        "predicate": {
            "run_id": RUN_ID,
            "actor": {"id": "user:dylan", "kind": "human", "domain_id": "d-default"},
            # Escalon agregado = el mas debil del camino critico (nota 03);
            # igual a RUN_VERIFICATION.aggregateRung en spike/ieee14.ts.
            "aggregate_rung": 3,
            "unanchored_steps": 0,
            "attestations": [
                {
                    "verifier_id": "ortools-cpsat",
                    "anchor_kind": "solver",
                    "rung": 1,
                    "verdict": "pass",
                    "method": "cpsat-differential",
                    "summary": "Corte = optimo exacto (CP-SAT, status OPTIMAL)",
                    "evidence": {
                        "differential": {
                            "status": "OPTIMAL",
                            "objective": 3,
                            "reference_objective": 3,
                        }
                    },
                },
                {
                    "verifier_id": "pandapower-powerflow",
                    "anchor_kind": "execution",
                    "rung": 2,
                    "verdict": "pass",
                    "method": "pandapower-powerflow",
                    "summary": "Ambas islas factibles por ejecucion de flujo de potencia",
                    "evidence": {
                        "powerflow_converged": True,
                        "max_voltage_deviation_pu": 0.018,
                    },
                },
                {
                    "verifier_id": "ieee14-known-optimum",
                    "anchor_kind": "dataset",
                    "rung": 3,
                    "verdict": "pass",
                    "method": "corpus-match",
                    "summary": "Coincide con la particion optima conocida del corpus IEEE-14",
                    "evidence": {"corpus_id": "ieee14-known-optimum", "matched": True},
                },
            ],
            "policy_id": "chimera-default@0.1.0",
            "issued_at": "2026-07-07T18:00:00.000000Z",
        },
    }


def main() -> int:
    statement = build_statement()
    payload_bytes = canonicalize(statement)

    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    pae_bytes = dsse_pae(PAYLOAD_TYPE, payload_bytes)
    signature_bytes = private_key.sign(pae_bytes)

    payload_b64 = base64.b64encode(payload_bytes).decode("ascii")
    sig_b64 = base64.b64encode(signature_bytes).decode("ascii")

    envelope = {
        "payloadType": PAYLOAD_TYPE,
        "payload": payload_b64,
        "signatures": [{"keyid": "example-2026", "sig": sig_b64}],
    }

    # --- Validacion del roundtrip (el punto de "de paso valida la firma") ---
    all_checks_passed = True

    recomputed_payload = base64.b64decode(payload_b64)
    recomputed_pae = dsse_pae(PAYLOAD_TYPE, recomputed_payload)
    try:
        public_key.verify(signature_bytes, recomputed_pae)
        print(
            "PASS: la firma verifica sobre el PAE recomputado del payload decodificado"
        )
    except InvalidSignature:
        all_checks_passed = False
        print("FAIL: la firma NO verifica sobre el PAE recomputado (roundtrip roto)")

    mutated_payload = bytearray(recomputed_payload)
    mutated_payload[0] ^= 0xFF
    mutated_pae = dsse_pae(PAYLOAD_TYPE, bytes(mutated_payload))
    try:
        public_key.verify(signature_bytes, mutated_pae)
        all_checks_passed = False
        print("FAIL: la firma verifico sobre un payload mutado (deberia haber fallado)")
    except InvalidSignature:
        print("PASS: mutar 1 byte del payload invalida la firma, como se espera")

    if not all_checks_passed:
        return 1

    repo_root = Path(__file__).resolve().parent.parent
    output_path = (
        repo_root / "apps" / "studio" / "src" / "fixtures" / "certificate.example.json"
    )
    output_path.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
    print(f"\nEnvelope escrito en {output_path}")

    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    public_b64 = base64.b64encode(public_bytes).decode("ascii")
    print(f"Llave publica Ed25519 (base64, DEMO/EFIMERA, no persistida): {public_b64}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
