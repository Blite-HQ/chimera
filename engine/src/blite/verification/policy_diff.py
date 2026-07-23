"""
Palanca EX-5, mitad Policy (freeze §6): ¿la Policy nueva ENDURECE a la vieja?

[S-F · EX-5] R-Pol1 pinnea por digest y la revocación Fase 1 es "none" — si
una Policy se endurece por vulnerabilidad descubierta, los cases en vuelo
correrían bajo la exigencia vieja sin alarma. ESTE módulo computa el
veredicto (¿subió la exigencia? ¿dónde?); el runtime (frontera Steven,
`policy_watch`) abre `●EscalationOpened` sobre los cases cuyo
`policy_digest` pinneado quedó por debajo. El pin NO cambia: la palanca es
alarma, jamás revocación ni re-pin.

Reglas del comparador (forma monotónica, "deny unless proven"):
- Se comparan reglas con el MISMO `match`; subir criticidad/min_level/
  required_legs, exigir anclas nuevas o endurecer `on_inconclusive`
  (mark < escalate_human < hold_run) = ENDURECE.
- Una regla nueva donde no había = ENDURECE (exigencia nueva).
- Quitar/bajar = NO endurece (ablandar no alarma — la palanca es de un solo
  sentido, como el piso por flags).
- Limitación Fase 1 declarada: `max_attestation_age` (frescura, v3.2) no
  entra al comparador todavía — comparar duraciones ISO llega con su seed.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from blite.verification.policy import (
    MatchCondition,
    VerificationPolicy,
    VerificationRule,
)

_CRITICALITY_ORDER: dict[str, int] = {"C0": 0, "C1": 1, "C2": 2, "C3": 3}
_LEVEL_ORDER: dict[str, int] = {"AL0": 0, "AL1": 1, "AL2": 2, "AL3": 3, "AL4": 4}
_ON_INCONCLUSIVE_ORDER: dict[str, int] = {"mark": 0, "escalate_human": 1, "hold_run": 2}


class PolicyHardening(BaseModel):
    """El veredicto: si endurece y por qué (las causas viajan a la escalación)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    hardened: bool
    causes: tuple[str, ...] = ()


def _match_key(match: MatchCondition) -> tuple[str | None, str | None]:
    return (match.side_effects, match.claim_type)


def _scope_label(match: MatchCondition) -> str:
    parts = [
        f"claim_type={match.claim_type}" if match.claim_type else None,
        f"side_effects={match.side_effects}" if match.side_effects else None,
    ]
    present = [p for p in parts if p]
    return ", ".join(present) if present else "match=any"


def _rule_hardenings(old: VerificationRule, new: VerificationRule) -> list[str]:
    scope = _scope_label(new.match)
    causes: list[str] = []
    if _CRITICALITY_ORDER[new.criticality] > _CRITICALITY_ORDER[old.criticality]:
        causes.append(f"[{scope}] criticality {old.criticality} → {new.criticality}")
    if _LEVEL_ORDER[new.min_level] > _LEVEL_ORDER[old.min_level]:
        causes.append(f"[{scope}] min_level {old.min_level} → {new.min_level}")
    if new.required_legs > old.required_legs:
        causes.append(
            f"[{scope}] required_legs {old.required_legs} → {new.required_legs}"
        )
    added_anchors = set(new.required_anchors) - set(old.required_anchors)
    if added_anchors:
        causes.append(f"[{scope}] required_anchors suma {sorted(added_anchors)}")
    if (
        _ON_INCONCLUSIVE_ORDER[new.on_inconclusive]
        > _ON_INCONCLUSIVE_ORDER[old.on_inconclusive]
    ):
        causes.append(
            f"[{scope}] on_inconclusive {old.on_inconclusive} → {new.on_inconclusive}"
        )
    return causes


def assess_hardening(
    old: VerificationPolicy, new: VerificationPolicy
) -> PolicyHardening:
    """Computa si `new` exige más que `old` y en qué dimensiones exactas."""
    old_by_match = {_match_key(rule.match): rule for rule in old.rules}
    causes: list[str] = []
    for rule in new.rules:
        previous = old_by_match.get(_match_key(rule.match))
        if previous is None:
            causes.append(f"[{_scope_label(rule.match)}] regla nueva donde no había")
            continue
        causes.extend(_rule_hardenings(previous, rule))
    return PolicyHardening(hardened=bool(causes), causes=tuple(causes))
