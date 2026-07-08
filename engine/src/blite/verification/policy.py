"""
VerificationPolicy — declarative, versioned "what must be anchored, how hard".

docs/contract-freeze.md SS6 / knowledge/trust/05-verificacion-adaptativa-politica-tradeoffs.md
SS1.2 (ADR-017): the engine owns this type; the policy DATA lives in the
distribution (distributions/chimera/policies/), never hardcoded here — the
verification stage is mechanical, the exigency is data.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from blite.verification.anchor import AnchorKind

SideEffects = Literal["pure", "reversible-external", "irreversible-external"]


class MatchCondition(BaseModel):
    """What a rule applies to. Unset fields match any value."""

    model_config = ConfigDict(frozen=True)

    side_effects: SideEffects | None = None
    claim_type: str | None = None


class VerificationRule(BaseModel):
    """One row of the policy: for claims matching `match`, require this much."""

    model_config = ConfigDict(frozen=True)

    match: MatchCondition
    min_rung: int
    required_anchors: tuple[AnchorKind, ...] = ()
    escalation: Literal["human"] | None = None
    on_inconclusive: Literal["mark", "escalate_human", "hold_run"]
    """Never governs egress (Inv-E) — only the run's verification state."""


class VerificationPolicy(BaseModel):
    """A versioned, auditable set of verification rules."""

    model_config = ConfigDict(frozen=True)

    policy_id: str
    version: str
    rules: tuple[VerificationRule, ...]
