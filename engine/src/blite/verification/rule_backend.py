"""
`RuleBackend` — el puerto INTERNO del `RuleVerifier`. Ítem C3/M3 (#103),
spec `knowledge/trust/11-spec-rule-verifier-backend-z3.md` §1.1/§1.3.

Un adapter (`RuleVerifier`), varios backends, una regla-como-dato. El puerto
es interno al adapter (como `ExecutionHarness` en trust/12): el `Verifier`
congelado del freeze §4 no cambia de forma por esto.

**La salida `proof` se tipa desde el día 1 aunque la v1 sea Z3-solo**
(decisión #103): la ruta a `formal_exact` verificable offline por un tercero
es cvc5 → certificado **Alethe** → checker **Carcara** empaquetado en el
bundle (freeze §4-iii: `proof {certificate_ref, checker_id,
checker_verdict}`). Un puerto que no tipara la prueba obligaría a cambiar su
firma para admitirla — y entonces "el upgrade es un drop-in" sería falso.

Lo que la v1 NO hace, y por qué está bien: ningún backend de esta versión
produce `proof`, así que ninguna `Attestation` sale como `formal_exact`. El
techo honesto de un chequeo sin prueba re-validable es AL2 (`property_rule`,
freeze §4) y ahí se queda — cero techos rotos. El adapter falla FUERTE si un
backend devuelve una prueba, porque emitirla exige extender el predicate
congelado: la ceremonia se registra, no se improvisa.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from blite.verification.evidence import PropertyCheck
from blite.verification.rule_set import RuleSet

RuleStatus = Literal["sat", "unsat", "unknown"]
"""Crudo del backend formal (trust/11 §1.1) — `unknown` es tri-estado real,
jamás se colapsa a `fail`."""

RuleVerifierClass = Literal["formal_exact", "property_rule"]
"""Las dos clases que un chequeo de reglas puede sostener (freeze §4). Cuál
sale NO lo decide el adapter: lo decide el RESULTADO (con prueba
re-validable ⇒ `formal_exact`; chequeo sobre el candidato dado ⇒
`property_rule`, techo AL2)."""


class RuleProof(BaseModel):
    """El certificado de prueba que hace `formal_exact` verificable offline.

    Espejo de `evidence.Proof` (freeze §4-iii) + `proof_format`: el formato
    es lo que permite que un tercero elija su propio checker (Alethe tiene
    más de uno) en vez de confiar en el nuestro."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    certificate_ref: str
    checker_id: str
    checker_verdict: str
    proof_format: str


class RuleResult(BaseModel):
    """Lo que un backend devuelve — datos, jamás una `Attestation` (quién
    tiene autoridad para emitir constancias es el adapter, no el solver)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    holds: bool
    """¿El candidato satisface el conjunto? `False` también cuando el
    backend no pudo decidir — «se sostiene» exige haberlo comprobado."""
    backend: str
    verifier_class: RuleVerifierClass = "property_rule"
    status: RuleStatus
    checks: tuple[PropertyCheck, ...] = ()
    """Chequeo regla-a-regla: la lista AUTORITATIVA de qué rompe el
    candidato. El core de abajo es evidencia SMT nativa pero puede ser
    parcial (§1.4) — leerlo como "solo esta regla falla" sería un error."""
    unsat_core: tuple[str, ...] = ()
    """Subconjunto insatisfacible pequeño, NO garantizado mínimo (trust/11
    §1.4, limitación documentada de Z3)."""
    unknown_reason: str | None = None
    """Razón cruda del backend cuando `status == "unknown"` (presupuesto
    agotado, fragmento indecidible…) — el adapter la traduce a la razón
    tipada de la `Attestation`."""
    proof: RuleProof | None = None


@runtime_checkable
class RuleBackend(Protocol):
    """El backend intercambiable. `name` distingue la implementación en la
    evidencia (`python`, `z3`, `cvc5`…) — vocabulario ABIERTO a propósito:
    el puerto existe para que un tercero enchufe el suyo."""

    @property
    def name(self) -> str: ...

    @property
    def binary_digest(self) -> str:
        """Pinnea el prover que corrió — sin esto el replay no es auditable."""
        ...

    @property
    def params_digest(self) -> str:
        """Pinnea el presupuesto/opciones — dos `unknown` con presupuestos
        distintos no son la misma evidencia."""
        ...

    def check(self, rule_set: RuleSet, subject: Mapping[str, Any]) -> RuleResult: ...


__all__ = [
    "RuleBackend",
    "RuleProof",
    "RuleResult",
    "RuleStatus",
    "RuleVerifierClass",
]
