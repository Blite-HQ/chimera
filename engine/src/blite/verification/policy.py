"""
VerificationPolicy — declarative, versioned "what must be anchored, how hard".

docs/contract-freeze.md SS6 / knowledge/trust/05-verificacion-adaptativa-politica-tradeoffs.md
SS1.2 (ADR-017): the engine owns this type; the policy DATA lives in the
distribution (distributions/chimera/policies/), never hardcoded here — the
verification stage is mechanical, the exigency is data.

[S-F 2026-07-20] `min_rung` replaced by the frozen vocabulary (freeze SS4/SS6):
criticality C0-C3 decides how much strength is demanded, assurance level
AL0-AL4 is the floor, and C3 counts independent legs. The 1-7 ladder no longer
exists anywhere a `policy_digest` could pin it. The full Policy seed (flag
floors, v3.2 fields) is S-G.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from blite.verification.anchor import AnchorKind

SideEffects = Literal["pure", "reversible-external", "irreversible-external"]
AssuranceLevel = Literal["AL0", "AL1", "AL2", "AL3", "AL4"]
Criticality = Literal["C0", "C1", "C2", "C3"]


class MatchCondition(BaseModel):
    """What a rule applies to. Unset fields match any value."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    side_effects: SideEffects | None = None
    claim_type: str | None = None


class VerificationRule(BaseModel):
    """One row of the policy: for claims matching `match`, require this much."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    match: MatchCondition
    criticality: Criticality
    min_level: AssuranceLevel
    required_legs: int = 1
    """Independent verification legs; counted per independence_group (C3 => 2)."""
    required_anchors: tuple[AnchorKind, ...] = ()
    escalation: Literal["human"] | None = None
    on_inconclusive: Literal["mark", "escalate_human", "hold_run"]
    """Never governs egress (Inv-E) — only the run's verification state."""


class VerificationPolicy(BaseModel):
    """A versioned, auditable set of verification rules."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    policy_id: str
    version: str
    rules: tuple[VerificationRule, ...]
