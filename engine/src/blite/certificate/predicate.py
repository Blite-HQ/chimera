"""
Predicate mínimo del mes — freeze §7, la letra chica como tipos. [S-G]

docs/contract-freeze.md §7: `{run_id, actor, conclusions[{claim_digest,
canonical_statement, scope, verdict, level}], titular_level (mínimo del camino
crítico — jamás promedio), assumptions[{statement, ref?{name, digest}}],
deliverables[{artifact_ref, digest}], unanchored_steps/coverage_stats,
policy_digest, calculus_version, valid_as_of, revocation: "none"}`.

Reglas duras codificadas aquí (no en el emisor — fail-closed por tipo):
- [S-F · T2] `titular_level := mín(conclusions[].level_efectivo)`;
  `conclusions = []` ⇒ AL0, jamás un AL vacuo por mínimo de conjunto vacío.
- [S-F stress · SF-P2-4] `level_efectivo := AL0` si `verdict ∈ {refuted,
  inconclusive, not_required_declared}` — un claim no-verificado del camino
  crítico no sostiene titular alto. Un titular estampado que no coincida con
  el cómputo EXPLOTA en validación (inflar el titular es fraude de cálculo).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

AssuranceLevel = Literal["AL0", "AL1", "AL2", "AL3", "AL4"]
ConclusionVerdict = Literal[
    "verified", "refuted", "inconclusive", "not_required_declared"
]

_LEVEL_ORDER: dict[str, int] = {"AL0": 0, "AL1": 1, "AL2": 2, "AL3": 3, "AL4": 4}
_UNDERMINING_VERDICTS = frozenset({"refuted", "inconclusive", "not_required_declared"})


class AssumptionRef(BaseModel):
    """Referencia recuperable de una asunción: `{name, digest}` (freeze §7)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    digest: str


class Assumption(BaseModel):
    """`{statement, ref?}` — el alcance visible antes que el número (freeze §7)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    statement: str
    ref: AssumptionRef | None = None


class Conclusion(BaseModel):
    """Una conclusión del camino crítico — completo, jamás una selección."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_digest: str
    canonical_statement: str
    scope: dict[str, Any]
    verdict: ConclusionVerdict
    level: AssuranceLevel

    @property
    def level_efectivo(self) -> AssuranceLevel:
        """[S-F stress · SF-P2-4] regla de socavamiento (spec v3.2 §125)."""
        if self.verdict in _UNDERMINING_VERDICTS:
            return "AL0"
        return self.level


class Deliverable(BaseModel):
    """`{artifact_ref, digest}` — binding anti-TOCTOU (freeze §7)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    artifact_ref: str
    digest: str


def compute_titular_level(conclusions: tuple[Conclusion, ...]) -> AssuranceLevel:
    """[S-F · T2] mín(level_efectivo) del camino crítico; vacío ⇒ AL0."""
    if not conclusions:
        return "AL0"
    return min((c.level_efectivo for c in conclusions), key=_LEVEL_ORDER.__getitem__)


class TrustCertificatePredicate(BaseModel):
    """El predicate mínimo del mes (freeze §7) — Fase 1, `revocation: "none"`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    actor: str
    conclusions: tuple[Conclusion, ...]
    titular_level: AssuranceLevel
    assumptions: tuple[Assumption, ...]
    deliverables: tuple[Deliverable, ...]
    unanchored_steps: int = Field(default=0, ge=0)
    coverage_stats: dict[str, Any] = Field(default_factory=dict)
    policy_digest: str
    calculus_version: str
    valid_as_of: datetime
    revocation: Literal["none"] = "none"

    @model_validator(mode="after")
    def _titular_es_el_computo(self) -> TrustCertificatePredicate:
        computed = compute_titular_level(self.conclusions)
        if self.titular_level != computed:
            msg = (
                f"titular_level={self.titular_level!r} no es el cómputo "
                f"{computed!r} (freeze §7 [S-F · T2]: mínimo del camino "
                "crítico, jamás promedio — inflar el titular es fraude de cálculo)"
            )
            raise ValueError(msg)
        return self
