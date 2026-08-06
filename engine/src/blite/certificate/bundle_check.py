"""
Checklist del Bundle — freeze §7 (T11 + SF-P0-1/P1-4/P2-4 + stress-final
2026-07-22) + `docs/specs/harness-agentico.md` §Contrato-5 (punto 8, replay)
+ ítem C5/M8 (puntos 9 y 10). [S-G track Dylan #1 · Mejorado C-2]

Los 8 puntos originales NO cambian de semántica: los puntos 9 y 10 son
extensión ADITIVA y ninguno de los dos puede reprobar un Bundle emitido antes
de existir (el 9 solo mira claims de sub-run, que un bundle sin sub-runs no
tiene; el 10 solo verifica si el certificado DECLARA un head de cadena).

El Bundle mínimo = envelope DSSE del certificado (attestations EMBEBIDAS en el
payload — una sola firma) + descriptores de anclas/verificadores + la Policy
pinneada (bytes exactos del YAML) + el stream del run + los bytes de los
deliverables. Cada punto reporta sus fallas; lista vacía = OK. Fail-closed:
lo que no se puede verificar FALLA, jamás se omite.

Punto 8 (A5, `blite.runtime.replay`) materializa R1: "el certificado DSSE
verifica ⟺ el replay fue fiel" — un `replay.divergence` en el stream tumba
el bundle SIN IMPORTAR que los puntos 1-7 (firma, hashes, patas) verifiquen.

Fórmulas (anexo de canonicalización, CONGELADO):
- provenance_hash = SHA-256("blite/provenance/v1\\n" ‖ C(view(e_i))‖0x0A …) hex
- claim_digest    = SHA-256("blite/claim/v1\\n" ‖ C({canonical_statement, scope})) hex
- policy_digest   = SHA-256(bytes exactos del YAML) — Regla 1, digest de artefacto
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Any

import yaml
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519

from blite.certificate.canonical import canonicalize
from blite.certificate.dsse import DSSEEnvelope, DSSESignature
from blite.certificate.dsse import verify as dsse_verify
from blite.certificate.predicate import Conclusion, compute_titular_level
from blite.events.chain import chain_head_of_views, provenance_hash_of_views
from blite.events.rules import TERMINAL_RUN_EVENTS

CLAIM_PREFIX = b"blite/claim/v1\n"

# Techos por clase decisoria (freeze §4). formal_exact alcanza AL4 SOLO con
# checker independiente (proof) — sin proof su techo efectivo es AL3 (punto 7).
CLASS_CEILINGS: dict[str, str] = {
    "formal_exact": "AL4",
    "execution": "AL3",
    "ground_truth": "AL3",
    "property_rule": "AL2",
    "consensus_replication": "AL2",
    "human_expert": "AL3",
}

# Copia PROPIA (no importada de `predicate`) a propósito: el verificador
# offline no confía en el emisor (D20) — ver predicate.py líneas 52-54.
_LEVEL_ORDER: dict[str, int] = {"AL0": 0, "AL1": 1, "AL2": 2, "AL3": 3, "AL4": 4}

# pass↔verified · fail↔refuted (freeze §7 punto 7)
_VERDICT_MAP = {"verified": "pass", "refuted": "fail"}


@dataclass(frozen=True)
class PointResult:
    """Resultado de un punto del checklist — fallas vacías = OK."""

    number: int
    name: str
    failures: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.failures


def _decode_predicate(bundle: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """(statement, predicate) desde el payload_b64 — Regla 1: los bytes firmados."""
    payload = base64.b64decode(bundle["envelope"]["payload"])
    statement = json.loads(payload)
    return statement, statement["predicate"]


def punto_1_firma_pae(bundle: dict[str, Any]) -> tuple[str, ...]:
    """(1) Firma/PAE del envelope — Ed25519 sobre los bytes PAE exactos."""
    try:
        envelope = DSSEEnvelope(
            payload_type=bundle["envelope"]["payloadType"],
            payload_b64=bundle["envelope"]["payload"],
            signatures=tuple(
                DSSESignature(keyid=s["keyid"], sig=s["sig"])
                for s in bundle["envelope"]["signatures"]
            ),
        )
        key = ed25519.Ed25519PublicKey.from_public_bytes(
            base64.b64decode(bundle["public_key"])
        )
        dsse_verify(envelope, key)
    except InvalidSignature:
        return ("la firma NO verifica sobre el PAE del payload",)
    except (KeyError, ValueError) as exc:
        return (f"envelope/llave malformados: {exc}",)
    return ()


def punto_2_provenance_hash(bundle: dict[str, Any]) -> tuple[str, ...]:
    """(2) Recompute del provenance_hash contra el stream (corte: freeze §2)."""
    failures: list[str] = []
    stream: list[dict[str, Any]] = bundle.get("stream", [])
    if not stream:
        return ("bundle sin stream: el hash no es recomputable (fail-closed)",)
    if stream[0].get("type") != "run.created":
        failures.append("el stream no abre con run.created")
    if stream[-1].get("type") not in TERMINAL_RUN_EVENTS:
        failures.append("el stream no cierra en el evento terminal (corte del hash)")
    seqs = [e.get("seq") for e in stream]
    if seqs != list(range(1, len(stream) + 1)):
        failures.append(f"seq no es 1..n estricto: {seqs}")
    recomputed = provenance_hash_of_views(stream)
    statement, predicate = _decode_predicate(bundle)
    subject_digest = statement["subject"][0]["digest"]["sha256"]
    if recomputed != subject_digest:
        failures.append(
            f"provenance_hash recomputado {recomputed[:12]}… ≠ subject {subject_digest[:12]}…"
        )
    if predicate.get("provenance_hash") not in (None, subject_digest):
        failures.append(
            "predicate.provenance_hash ≠ subject.digest (incoherencia interna)"
        )
    return tuple(failures)


def punto_3_deliverables(bundle: dict[str, Any]) -> tuple[str, ...]:
    """(3) Digests de deliverables contra los bytes (anti-TOCTOU)."""
    failures: list[str] = []
    _, predicate = _decode_predicate(bundle)
    contents: dict[str, str] = bundle.get("deliverable_contents", {})
    for deliverable in predicate.get("deliverables", []):
        digest = deliverable["digest"]
        blob_b64 = contents.get(digest)
        if blob_b64 is None:
            failures.append(
                f"deliverable {deliverable['artifact_ref']}: bytes ausentes del bundle"
            )
            continue
        recomputed = hashlib.sha256(base64.b64decode(blob_b64)).hexdigest()
        if recomputed != digest:
            failures.append(
                f"deliverable {deliverable['artifact_ref']}: digest {recomputed[:12]}… ≠ {digest[:12]}…"
            )
    return tuple(failures)


def punto_4_titular(bundle: dict[str, Any]) -> tuple[str, ...]:
    """(4) titular_level = mín(level_efectivo) — socavamiento SF-P2-4 incluido."""
    _, predicate = _decode_predicate(bundle)
    conclusions = tuple(Conclusion(**c) for c in predicate.get("conclusions", []))
    computed = compute_titular_level(conclusions)
    stamped = predicate.get("titular_level")
    if stamped != computed:
        return (
            f"titular_level estampado {stamped!r} ≠ cómputo {computed!r} (inflación)",
        )
    return ()


def punto_5_pass_ancla(bundle: dict[str, Any]) -> tuple[str, ...]:
    """(5) pass ⇒ anchor_digest presente Y resolviendo contra un descriptor
    empaquetado (SF-P0-1: presencia no basta — ancla fantasma)."""
    failures: list[str] = []
    _, predicate = _decode_predicate(bundle)
    descriptors = {d["anchor_digest"] for d in bundle.get("anchor_descriptors", [])}
    for att in predicate.get("attestations", []):
        if att["verdict"] != "pass":
            continue
        anchor = att.get("anchor_digest")
        if not anchor:
            failures.append(f"{att['verifier_id']}: pass sin anchor_digest (D10)")
        elif anchor not in descriptors:
            failures.append(
                f"{att['verifier_id']}: anchor_digest {anchor[:12]}… sin descriptor en el Bundle"
            )
    return tuple(failures)


def punto_6_claim_digest(bundle: dict[str, Any]) -> tuple[str, ...]:
    """(6) Recompute de claim_digest = SHA-256("blite/claim/v1\\n" ‖ C(view(claim)))."""
    failures: list[str] = []
    _, predicate = _decode_predicate(bundle)
    for conclusion in predicate.get("conclusions", []):
        view = {
            "canonical_statement": conclusion["canonical_statement"],
            "scope": conclusion["scope"],
        }
        recomputed = hashlib.sha256(CLAIM_PREFIX + canonicalize(view)).hexdigest()
        if recomputed != conclusion["claim_digest"]:
            failures.append(
                f"claim {conclusion['claim_digest'][:12]}…: recompute {recomputed[:12]}… no coincide"
            )
    return tuple(failures)


def _coherencia_de_grupos(attestations: list[dict[str, Any]]) -> tuple[str, ...]:
    """Extensión del punto 7 (freeze §7 [MEJORADO C-6/#106]): las constancias
    de un MISMO verificador en un MISMO run comparten `independence_group`.

    Sin esta regla, la granularidad por isla (C4/M4) sería una máquina de
    inflar patas: partir un verdict global en N constancias y darle a cada
    una su propio grupo convierte UN verificador en las N «patas
    independientes» que la Policy exige. El conteo de abajo cuenta grupos
    distintos; esta regla se asegura de que un grupo distinto signifique de
    verdad otra fuente de evidencia."""
    grupos: dict[tuple[str, str], set[str]] = {}
    for att in attestations:
        clave = (att.get("run_id", ""), att["verifier_id"])
        grupos.setdefault(clave, set()).add(att["independence_group"])
    return tuple(
        f"{verifier_id}: {len(vistos)} independence_group distintos en el mismo "
        f"run ({sorted(vistos)}) — un solo verificador no son varias patas (C-6)"
        for (_run, verifier_id), vistos in sorted(grupos.items())
        if len(vistos) > 1
    )


def punto_7_attestations_patas(bundle: dict[str, Any]) -> tuple[str, ...]:
    """(7) Conclusión↔attestations (pass↔verified) · techo por clase · proof AL4
    · patas por independence_group ≥ Policy pinneada; not_required_declared EXENTAS.
    Extensión C-6/#106: coherencia de grupos por verificador (anti-inflación)."""
    failures: list[str] = []
    _, predicate = _decode_predicate(bundle)

    policy_bytes = base64.b64decode(bundle.get("policy_yaml_b64", ""))
    if not policy_bytes:
        return ("Policy pinneada ausente del Bundle (stress-final #1 — fail-closed)",)
    policy_digest = hashlib.sha256(policy_bytes).hexdigest()
    if policy_digest != predicate.get("policy_digest"):
        failures.append(
            f"policy_digest {policy_digest[:12]}… ≠ predicate {str(predicate.get('policy_digest'))[:12]}…"
        )
    rules: list[dict[str, Any]] = yaml.safe_load(policy_bytes).get("rules", [])

    attestations = predicate.get("attestations", [])
    failures.extend(_coherencia_de_grupos(attestations))
    for conclusion in predicate.get("conclusions", []):
        verdict = conclusion["verdict"]
        if verdict == "not_required_declared":
            continue  # exentas por definición (su level_efectivo ya es AL0)
        if verdict == "inconclusive":
            continue  # sin mapeo pass/fail exigible; el socavamiento (punto 4) las cubre
        expected = _VERDICT_MAP[verdict]
        matching = [
            a
            for a in attestations
            if a["claim_digest"] == conclusion["claim_digest"]
            and a["verdict"] == expected
        ]
        cid = conclusion["claim_digest"][:12]
        if not matching:
            failures.append(
                f"claim {cid}…: sin attestation {expected!r} que lo sostenga"
            )
            continue
        for att in matching:
            ceiling = CLASS_CEILINGS.get(att["verifier_class"])
            if ceiling is None:
                failures.append(
                    f"{att['verifier_id']}: verifier_class fuera del vocabulario"
                )
                continue
            if _LEVEL_ORDER[att["level"]] > _LEVEL_ORDER[ceiling]:
                failures.append(
                    f"{att['verifier_id']}: level {att['level']} sobre el techo {ceiling}"
                )
            if att["level"] == "AL4":
                proof = att.get("predicate", {}).get("proof", {})
                if not {"certificate_ref", "checker_id", "checker_verdict"} <= set(
                    proof
                ):
                    failures.append(
                        f"{att['verifier_id']}: AL4 sin proof completo (§4-iii)"
                    )
        rule = next(
            (
                r
                for r in rules
                if r.get("match", {}).get("claim_type") == conclusion.get("claim_type")
            ),
            None,
        )
        if rule is None:
            failures.append(
                f"claim {cid}…: sin regla de Policy para claim_type "
                f"{conclusion.get('claim_type')!r} (fail-closed)"
            )
            continue
        legs = len({a["independence_group"] for a in matching})
        required = int(rule.get("required_legs", 1))
        if legs < required:
            failures.append(
                f"claim {cid}…: {legs} pata(s) por independence_group < {required} exigidas"
            )
        anchors_present = {a.get("anchor_kind") for a in matching}
        for kind in rule.get("required_anchors", []):
            if kind not in anchors_present:
                failures.append(f"claim {cid}…: ancla requerida {kind!r} ausente")
    return tuple(failures)


def punto_8_replay_fidelidad(bundle: dict[str, Any]) -> tuple[str, ...]:
    """(8) `replay.divergence` en el stream ⇒ el bundle FALLA — R1
    (`docs/specs/harness-agentico.md` §Contrato-5): "el certificado DSSE
    verifica ⟺ el replay fue fiel". SIN IMPORTAR que la firma DSSE (punto 1)
    o el resto del checklist verifiquen: ninguno de los puntos 1-7 lee el
    stream buscando divergencias de replay — este es el único que lo hace."""
    failures: list[str] = []
    stream: list[dict[str, Any]] = bundle.get("stream", [])
    for event in stream:
        if event.get("type") == "replay.divergence":
            payload = event.get("payload", {})
            failures.append(
                "replay.divergence en el stream "
                f"(effect_kind={payload.get('effect_kind')!r}, "
                f"step_id={payload.get('step_id')!r}): el replay NO fue fiel"
            )
    return tuple(failures)


def punto_9_sub_runs(bundle: dict[str, Any]) -> tuple[str, ...]:
    """(9) Recompute del `sub_run_provenance_hash` de cada sub-run que aportó
    claims — el anexo de canonicalización §4 lo MANDA desde que se congeló:
    «el verificador offline recomputa el hash del sub-run y lo compara contra
    el payload del `●ClaimEmitted` que el hash del raíz ya ampara».

    Hasta hoy era letra muerta por dos razones que este punto cierra juntas:
    el stream del sub-run no viajaba en el Bundle (`assemble_bundle` lo
    empaqueta desde C5) y el hash se computaba con OTRA fórmula (M28 lo
    reconcilió a la del anexo). Sin las dos, `sub_run_id` era «un puntero sin
    integridad» (freeze §13) y el certificado citaba trabajo que no podía
    demostrar.

    Fail-closed: un claim que declara `sub_run_provenance_hash` SIN su stream
    empaquetado FALLA — el certificado estaría amparando trabajo que nadie
    puede recomputar. Un bundle sin claims de sub-run pasa vacío (no afirma
    nada sobre sub-runs)."""
    failures: list[str] = []
    stream: list[dict[str, Any]] = bundle.get("stream", [])
    packaged: dict[str, list[dict[str, Any]]] = bundle.get("sub_run_streams", {})

    for event in stream:
        if event.get("type") != "claim.emitted":
            continue
        payload = event.get("payload", {})
        declarado = payload.get("sub_run_provenance_hash")
        if not declarado:
            continue
        sub_run_id = payload.get("sub_run_id")
        views = packaged.get(sub_run_id) if sub_run_id is not None else None
        if views is None:
            failures.append(
                f"claim del sub-run {sub_run_id!r} declara hash "
                f"{str(declarado)[:12]}… pero su stream NO viaja en el Bundle "
                "(no es recomputable — fail-closed)"
            )
            continue
        try:
            recomputado = provenance_hash_of_views(views)
        except (KeyError, TypeError, ValueError) as exc:
            failures.append(
                f"sub-run {sub_run_id!r}: stream no canonicalizable ({exc})"
            )
            continue
        if recomputado != declarado:
            failures.append(
                f"sub-run {sub_run_id!r}: recompute {recomputado[:12]}… ≠ "
                f"declarado {str(declarado)[:12]}… (el trabajo amparado no es ese)"
            )
    return tuple(failures)


def punto_10_hash_chain(bundle: dict[str, Any]) -> tuple[str, ...]:
    """(10) Recompute del hash-chain por evento contra el head FIRMADO
    (anexo §4 Fase 2; ítem C5/M8 pieza 1).

    Opt-in por diseño: un Bundle emitido antes de que el writer encadenara no
    lleva `provenance_chain_head`, y exigírselo convertiría «extensión
    aditiva» en «los certificados viejos dejan de valer». Sin head declarado
    este punto no verifica nada Y NO INVENTA que sí — el resto del checklist
    (en particular el punto 2) sigue amparando el stream. Con head declarado,
    la cadena se recomputa entera desde las vistas empaquetadas: no hace
    falta un hash por evento en el Bundle."""
    _, predicate = _decode_predicate(bundle)
    declarado = predicate.get("provenance_chain_head")
    if not declarado:
        return ()
    stream: list[dict[str, Any]] = bundle.get("stream", [])
    if not stream:
        return ("head de cadena declarado sin stream que lo sostenga (fail-closed)",)
    recomputado = chain_head_of_views(stream)
    if recomputado != declarado:
        return (
            f"head de cadena recomputado {recomputado[:12]}… ≠ firmado "
            f"{str(declarado)[:12]}…",
        )
    return ()


_PUNTOS = (
    ("firma/PAE del envelope", punto_1_firma_pae),
    ("recompute del provenance_hash", punto_2_provenance_hash),
    ("digests de deliverables", punto_3_deliverables),
    ("titular_level = mín(level_efectivo)", punto_4_titular),
    ("pass ⇒ ancla con descriptor", punto_5_pass_ancla),
    ("recompute de claim_digest", punto_6_claim_digest),
    ("attestations: techos, proof AL4, patas vs Policy", punto_7_attestations_patas),
    (
        "fidelidad de replay: sin replay.divergence en el stream",
        punto_8_replay_fidelidad,
    ),
    ("recompute del provenance de cada sub-run aportante", punto_9_sub_runs),
    ("recompute del hash-chain contra el head firmado", punto_10_hash_chain),
)


def check_bundle(bundle: dict[str, Any]) -> tuple[PointResult, ...]:
    """Corre los 8 puntos; cada uno reporta aparte (ninguno corta a los demás)."""
    results: list[PointResult] = []
    for number, (name, fn) in enumerate(_PUNTOS, start=1):
        try:
            failures = fn(bundle)
        except Exception as exc:  # noqa: BLE001 — fail-closed: excepción = punto fallido
            failures = (f"error verificando: {exc!r}",)
        results.append(PointResult(number=number, name=name, failures=failures))
    return tuple(results)
