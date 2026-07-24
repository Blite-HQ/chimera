"""statement.py — el informe como Statement in-toto firmado
(docs/specs/informe-derivado.md §Trazabilidad al run raíz).

El informe corre como sub-run del run raíz y produce un claim propio,
`claim_type: "derivation"` (ya registrado, cero extensión nueva aquí). Este
módulo reutiliza LA MISMA forma Statement/predicate que
`scripts/gen-example-bundle.py` usa para el TrustCertificate —
`{_type, subject:[{name, digest:{sha256}}], predicateType, predicate}`
(knowledge/trust/02) — cero maquinaria de confianza nueva, y firma con
`blite.certificate.dsse.sign` tal cual: este módulo NO reimplementa DSSE/PAE.

Determinista por construcción: `build_report_statement` es una función pura
de `compiled`/`cert_id`/`sub_run_id` — nunca embebe `datetime.now()`.
"""

from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric import ed25519

from blite.certificate.canonical import JSONValue, canonicalize
from blite.certificate.dsse import DSSEEnvelope, sign
from blite_cap_report.pdf import CompiledReport

REPORT_PREDICATE_TYPE = "https://blite.dev/ReportDerivation/v1"

_STATEMENT_TYPE = "https://blite.dev/Statement/v1"
_REPORT_PAYLOAD_TYPE = "application/vnd.blite.report-derivation+json"
_SHA256_PREFIX = "sha256:"
_CLAIM_TYPE_DERIVATION = "derivation"


def _normalize(digest: str) -> str:
    return digest.removeprefix(_SHA256_PREFIX)


def build_report_statement(
    *,
    compiled: CompiledReport,
    cert_id: str,
    sub_run_id: str,
) -> dict[str, JSONValue]:
    """Statement in-toto del informe como derivación (informe-derivado.md
    §Trazabilidad al run raíz): `subject` pinnea el PDF por su digest;
    `predicate` carga la MISMA receta que `compiled.provenance.recipe`
    (nunca una copia divergente) más `cert_id` y `claim_type: "derivation"`.
    Sin timestamp — dos construcciones con los mismos argumentos producen
    el mismo resultado byte a byte tras `canonicalize`."""
    recipe = compiled.provenance.recipe
    recipe_json: JSONValue = {
        "capability": recipe["capability"],
        "version": recipe["version"],
        "params_digest": recipe["params_digest"],
        "code_ref": recipe["code_ref"],
    }
    inputs_json: JSONValue = [
        {"ref": entry["ref"], "digest": entry["digest"]}
        for entry in compiled.provenance.inputs
    ]
    predicate: JSONValue = {
        "recipe": recipe_json,
        "inputs": inputs_json,
        "cert_id": cert_id,
        "claim_type": _CLAIM_TYPE_DERIVATION,
    }
    return {
        "_type": _STATEMENT_TYPE,
        "subject": [
            {
                "name": f"report:{sub_run_id}",
                "digest": {"sha256": _normalize(compiled.digest)},
            }
        ],
        "predicateType": REPORT_PREDICATE_TYPE,
        "predicate": predicate,
    }


def sign_report_statement(
    *,
    statement: dict[str, JSONValue],
    private_key: ed25519.Ed25519PrivateKey,
    keyid: str,
) -> DSSEEnvelope:
    """Firma `canonicalize(statement)` con `blite.certificate.dsse.sign`
    (Regla 1: se firman los bytes canonicalizados exactos, nunca una
    re-serialización) — reutiliza el módulo DSSE tal cual, sin reimplementar
    PAE ni el envelope."""
    payload = canonicalize(statement)
    return sign(
        payload_type=_REPORT_PAYLOAD_TYPE,
        payload=payload,
        private_key=private_key,
        keyid=keyid,
    )
