"""
Attestation — the result of a Verifier's verify() call.

docs/contract-freeze.md SS4 / knowledge/trust/03-escalera-verificacion-metodos.md
SS1.1-SS1.4. `rung` is restricted to {1,2,3,4,7}: rungs 5-6 (consensus/model
detection) are unrepresentable as an Attestation by construction — they can
only ever be a GuardrailSignal (blite.guardrails.signal), a disjoint type.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from blite.verification.anchor import AnchorKind
from blite.verification.evidence import Evidence

Verdict = Literal["pass", "fail", "inconclusive"]
"""Tri-state verdict (knowledge/trust/03 SS1.4): abstention is representable."""

AttestationRung = Literal[1, 2, 3, 4, 7]
"""The escalera rungs that produce an Attestation (5-6 do not — SS1.1)."""


class AttestationSubject(BaseModel):
    """What is being attested: a run, optionally a step within it (PRM, SS1.3)."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    step_id: str | None = None
    claim_digest: str


class Attestation(BaseModel):
    """A verifier's constancy about a claim — never an opinion (D18)."""

    model_config = ConfigDict(frozen=True)

    verifier_id: str
    anchor_kind: AnchorKind
    rung: AttestationRung
    verdict: Verdict
    evidence: Evidence
    subject: AttestationSubject
    issued_at: datetime
