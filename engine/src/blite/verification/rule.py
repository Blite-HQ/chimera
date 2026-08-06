"""
`RuleVerifier` — el adapter genérico del ancla `rule`. Ítem C3/M3 (#103),
spec `knowledge/trust/11-spec-rule-verifier-backend-z3.md`.

Verifica que un candidato cumple **un conjunto de reglas del dominio que
llega como DATO** (`RuleSet`, artefacto SMT-LIB 2 con digest). El adapter no
sabe de dominios: el conocimiento eléctrico, químico o de negocio vive en
`knowledge/`, versionado, y el `anchor_digest` de la constancia ES el digest
de ese artefacto — quien audite sabe exactamente CONTRA QUÉ reglas se
verificó.

**Qué prueba y qué no (la honestidad del AL2).** Este adapter comprueba que
el `subject` DECLARADO por el claim satisface las reglas. No recomputa el
subject desde la realidad — eso es trabajo de otras clases (`execution`
corre el simulador, `ground_truth` contrasta contra corpus). Por eso su
techo es AL2 y por eso una conclusión C3 exige más de una pata: el rule-check
dice «los números declarados son consistentes con el dominio», no «los
números son ciertos».

**Relación con `PropertyRuleVerifier`** (`property_rule.py`, del reto 2):
misma CLASE (`property_rule`, ancla `rule`, techo AL2), distinto origen de
las reglas — allá son código del engine con la SELECCIÓN como dato (catálogo
C2 de kernels y métricas, que no se expresa en SMT); acá son datos SMT-LIB
con digest. Coexisten a propósito: son dos backends del mismo puerto
conceptual, y ninguno de los dos finge la fuerza del otro.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from blite.verification.anchor import AnchorKind
from blite.verification.attestation import (
    Attestation,
    InconclusiveReason,
    Verdict,
    VerifierClass,
)
from blite.verification.claim import claim_view_digest
from blite.verification.context import InvocationContext
from blite.verification.evidence import PropertyRulePredicate
from blite.verification.exact_solver import VerificationProcessError
from blite.verification.rule_backend import RuleBackend, RuleResult
from blite.verification.rule_set import RuleSet
from blite.verification.rule_z3 import is_budget_reason
from blite.verification.verifier import Determinism


class RuleClaim(BaseModel):
    """Claim: «`subject` satisface el `RuleSet` declarado».

    `subject` mapea CADA símbolo que las reglas usan a su valor concreto —
    el backend falla fuerte si sobra o falta alguno (un símbolo libre
    convertiría el `pass` en «existe algún mundo donde se cumple»)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    subject: dict[str, Any]
    canonical_statement: str
    scope: dict[str, Any]


@dataclass(frozen=True)
class RuleVerifier:
    """Adapter del ancla `rule` sobre un `RuleBackend` intercambiable."""

    verifier_id: str
    independence_group: str
    rule_set: RuleSet
    backend: RuleBackend

    # Campos de instancia (init=False), como el resto de adapters: el
    # Protocol `Verifier` los declara como atributos de instancia.
    verifier_class: VerifierClass = field(default="property_rule", init=False)
    """La v1 solo alcanza `property_rule` (#103). La clase REAL de cada
    constancia la decide el resultado (freeze §4: es por-`Attestation`) —
    cuando un backend con prueba re-validable exista, este default deja de
    ser el único valor posible y `verify` lo estampará desde el resultado."""
    anchor_kind: AnchorKind = field(default="rule", init=False)
    determinism: Determinism = field(default="deterministic", init=False)

    @property
    def verifier_binary_digest(self) -> str:
        return self.backend.binary_digest

    @property
    def verifier_params_digest(self) -> str:
        return self.backend.params_digest

    def verify(self, claim: Any, ctx: InvocationContext) -> Attestation:
        if not isinstance(claim, RuleClaim):
            msg = f"claim {type(claim).__name__} no es un RuleClaim"
            raise VerificationProcessError(msg)

        result = self.backend.check(self.rule_set, claim.subject)
        self._reject_unceremonious_promotion(result)

        verdict, reason = _verdict_of(result)
        return Attestation(
            verifier_id=self.verifier_id,
            verifier_class=self.verifier_class,
            anchor_kind=self.anchor_kind,
            level="AL2",
            verdict=verdict,
            inconclusive_reason=reason,
            scope=claim.scope,
            independence_group=self.independence_group,
            run_id=ctx.run_id,
            claim_digest=claim_view_digest(claim.canonical_statement, claim.scope),
            verifier_binary_digest=self.verifier_binary_digest,
            verifier_params_digest=self.verifier_params_digest,
            # El ancla ES el artefacto de reglas: su digest pinnea, byte a
            # byte, contra qué se verificó (Regla 1 del anexo).
            anchor_digest=self.rule_set.rule_digest,
            predicate=PropertyRulePredicate(
                properties=result.checks,
                backend=result.backend,
                status=result.status,
                unsat_core=result.unsat_core,
                rule_set_id=self.rule_set.rule_set_id,
                rule_digest=self.rule_set.rule_digest,
            ),
            issued_at=datetime.now(UTC),
        )

    @staticmethod
    def _reject_unceremonious_promotion(result: RuleResult) -> None:
        """Cero techos rotos (#103). Un backend que devuelve prueba formal
        no se puede atender hoy de ninguna de las dos maneras posibles:
        emitirla como `formal_exact` exige extender el predicate CONGELADO
        (freeze §4-iii — `FormalExactPredicate` exige hoy un `differential`
        que una prueba de reglas no tiene), y degradarla a AL2 en silencio
        escondería evidencia que el verificador SÍ produjo. Fail-loud
        nombrando la ceremonia que falta."""
        if result.verifier_class == "property_rule" and result.proof is None:
            return
        msg = (
            f"el backend {result.backend!r} devolvió clase "
            f"{result.verifier_class!r} con proof={result.proof is not None}: "
            "emitir `formal_exact` exige la ceremonia pendiente sobre el "
            "predicate congelado (arm de prueba de reglas en "
            "`FormalExactPredicate`, freeze §4-iii) — la v1 con Z3 emite "
            "`property_rule` AL2 y no infla ni esconde el resultado (#103)"
        )
        raise VerificationProcessError(msg)


def _verdict_of(result: RuleResult) -> tuple[Verdict, InconclusiveReason | None]:
    """Tri-estado (D4): `unknown` es abstención con razón tipada, jamás un
    `fail` — acusar al candidato de algo que nadie probó sería exactamente
    la deshonestidad que el tri-estado existe para impedir."""
    if result.status == "unknown":
        reason: InconclusiveReason = (
            "budget_exhausted"
            if is_budget_reason(result.unknown_reason or "")
            else "undecidable"
        )
        return "inconclusive", reason
    return ("pass" if result.holds else "fail"), None


__all__ = ["RuleClaim", "RuleVerifier"]
