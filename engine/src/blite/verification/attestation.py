"""
Attestation — la constancia de un Verifier sobre un claim. Vocabulario §4.

docs/contract-freeze.md §4: la escalera 1-7 quedó SUPERSEDIDA — la **clase**
dice el método, el **AL** dice la fuerza (con techos), la criticidad (Policy)
dice cuánta fuerza se exige. `VerifierClass` no tiene valor `"model"` POR
CONSTRUCCIÓN (INV-2/PR2 — gate de tipos). Endurecimientos [S-F]:
- `anchor_digest` nullable SOLO si `verdict = inconclusive` (T3/D10 — un
  pass/fail sin ancla es irrepresentable; espejo del CHECK del esquema).
- `independence_group` obligatorio (el conteo de patas C3 es por grupo).
- binding a 4 digests + `predicate` por clase + `evidence_digests` refs
  content-addressed (§12) — la evidence deja de ser unión embebida.
- AL4 exige clase `formal_exact` + `proof {certificate_ref, checker_id,
  checker_verdict}` dentro del predicate (§4-iii — re-validación en el bundle).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

from blite.verification.anchor import AnchorKind
from blite.verification.evidence import ClassPredicate
from blite.verification.policy import AssuranceLevel

Verdict = Literal["pass", "fail", "inconclusive"]
"""Tri-estado (D4): la abstención es representable — jamás un pass por defecto."""

VerifierClass = Literal[
    "formal_exact",
    "execution",
    "ground_truth",
    "property_rule",
    "consensus_replication",
    "human_expert",
]
"""freeze §4 — sin "model" por construcción (INV-2/PR2, gate de tipos)."""

InconclusiveReason = Literal[
    "timeout",
    "undecidable",
    "conflict",
    "undermined_premise",
    "no_applicable_anchor",
    "anchor_requires_unauthorized_egress",
    "budget_exhausted",
]
"""La lista tipada de la spec v3.2 (freeze §4)."""

# Techos por clase (freeze §4). formal_exact alcanza AL4 SOLO con checker
# independiente (proof). Nota: `bundle_check` mantiene su PROPIA copia a
# propósito — el verificador offline no confía en el emisor (D20).
CLASS_CEILINGS: dict[str, AssuranceLevel] = {
    "formal_exact": "AL4",
    "execution": "AL3",
    "ground_truth": "AL3",
    "property_rule": "AL2",
    "consensus_replication": "AL2",
    "human_expert": "AL3",
}

_LEVEL_ORDER: dict[str, int] = {"AL0": 0, "AL1": 1, "AL2": 2, "AL3": 3, "AL4": 4}


class Attestation(BaseModel):
    """La constancia de un verificador — jamás una opinión (D18)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    verifier_id: str
    verifier_class: VerifierClass
    anchor_kind: AnchorKind | None = None
    level: AssuranceLevel
    verdict: Verdict
    inconclusive_reason: InconclusiveReason | None = None
    scope: dict[str, Any]
    independence_group: str
    run_id: str
    step_id: str | None = None
    claim_digest: str
    verifier_binary_digest: str
    verifier_params_digest: str
    anchor_digest: str | None = None
    predicate: ClassPredicate
    evidence_digests: tuple[str, ...] = ()
    issued_at: datetime
    """Semántica VALID_AS_OF (S5): todo veredicto vale a su instante."""

    @model_validator(mode="after")
    def _letra_del_freeze(self) -> Attestation:
        # [S-F · T3] pass/fail sin ancla es irrepresentable (D10)
        if self.verdict != "inconclusive" and self.anchor_digest is None:
            msg = f"verdict {self.verdict!r} sin anchor_digest es irrepresentable (T3/D10)"
            raise ValueError(msg)
        # tri-estado honesto: inconclusive lleva su razón tipada
        if self.verdict == "inconclusive" and self.inconclusive_reason is None:
            msg = "inconclusive sin reason tipada (v3.2 — la abstención se explica)"
            raise ValueError(msg)
        # techos por clase (freeze §4)
        ceiling = CLASS_CEILINGS[self.verifier_class]
        if _LEVEL_ORDER[self.level] > _LEVEL_ORDER[ceiling]:
            msg = (
                f"level {self.level} sobre el techo {ceiling} de {self.verifier_class}"
            )
            raise ValueError(msg)
        # AL4 = formal_exact CON checker independiente (§4-iii)
        if self.level == "AL4" and getattr(self.predicate, "proof", None) is None:
            msg = "AL4 exige proof {certificate_ref, checker_id, checker_verdict} (§4-iii)"
            raise ValueError(msg)
        # el predicate ES de la clase (discriminado)
        if self.predicate.method != self.verifier_class:
            msg = f"predicate {self.predicate.method!r} no es de la clase {self.verifier_class!r}"
            raise ValueError(msg)
        return self
