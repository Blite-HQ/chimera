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

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from blite.verification.anchor import AnchorKind

SideEffects = Literal["pure", "reversible-external", "irreversible-external"]
AssuranceLevel = Literal["AL0", "AL1", "AL2", "AL3", "AL4"]
Criticality = Literal["C0", "C1", "C2", "C3"]

_CRITICALITY_ORDER: dict[str, int] = {"C0": 0, "C1": 1, "C2": 2, "C3": 3}


class KernelRequirement(BaseModel):
    """Una fila de la matriz por criticidad del kernel (freeze §6)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    min_level: AssuranceLevel
    required_legs: int = Field(ge=0)
    """Patas por independence_group; C0 = declarado, 0 patas (única fila con 0)."""
    anchor_authority_min: str | None = None
    """C3: el ancla debe ser ≥ `curated_internal` (taxonomía del registro, §4)."""
    requires_non_self_generated_leg: bool = False
    """C3: ≥1 pata no-self_generated."""
    formalization: Literal["nativa", "revisada"] | None = None
    """C3: formalización nativa o revisada."""


# Matriz por criticidad — el default del kernel que toda Policy hereda
# (freeze §6): C0 declarado/0 · C1 AL1/1 · C2 AL2/1 · C3 AL3/2 patas +
# ancla ≥ curated_internal + ≥1 pata no-self_generated + formalización.
KERNEL_MATRIX: dict[Criticality, KernelRequirement] = {
    "C0": KernelRequirement(min_level="AL0", required_legs=0),
    "C1": KernelRequirement(min_level="AL1", required_legs=1),
    "C2": KernelRequirement(min_level="AL2", required_legs=1),
    "C3": KernelRequirement(
        min_level="AL3",
        required_legs=2,
        anchor_authority_min="curated_internal",
        requires_non_self_generated_leg=True,
        formalization="nativa",
    ),
}


def criticality_floor(
    *,
    world: bool = False,
    irreversible: bool = False,
    affects_third_party: bool = False,
) -> Criticality | None:
    """Pisos por flags (freeze §6, PR2/PR4): `world` ⇒ C2;
    `irreversible ∧ affects_third_party` ⇒ C3 con gate BLOQUEANTE (la esquina
    se satisface por no-acción). Sin flag que aplique ⇒ None (manda la base)."""
    if irreversible and affects_third_party:
        return "C3"
    if world:
        return "C2"
    return None


def effective_criticality(
    base: Criticality,
    *,
    world: bool = False,
    irreversible: bool = False,
    affects_third_party: bool = False,
) -> Criticality:
    """La criticidad efectiva = máx(base, piso por flags) — el piso solo sube."""
    floor = criticality_floor(
        world=world, irreversible=irreversible, affects_third_party=affects_third_party
    )
    if floor is None or _CRITICALITY_ORDER[base] >= _CRITICALITY_ORDER[floor]:
        return base
    return floor


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
    required_legs: int = Field(default=1, ge=1, strict=True)
    """Independent verification legs; counted per independence_group (C3 => 2).

    ge=1: cero/negativos son basura sin semantica (stress final 2026-07-22);
    strict evita la coercion bool->int de Python.
    """
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

    # ── Campos v3.2 adoptados (freeze §6) — opcionales: el YAML 0.2.0 valida ──
    max_attestation_age: dict[str, str] = Field(default_factory=dict)
    """Frescura por claim_type/criticidad — clave → duración ISO 8601 (v3.2)."""
    trusted_signer_roots: tuple[str, ...] = ()
    """Raíces de confianza para firmas de attestations externas (v3.2)."""
    audience_profiles: dict[str, Any] = Field(default_factory=dict)
    """Perfiles de audiencia del certificado (v3.2) — forma libre en Fase 1."""
    retention: str | None = None
    """Política de retención declarada (v3.2)."""
