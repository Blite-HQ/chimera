"""
`Z3RuleBackend` — el backend formal del `RuleBackend` (Z3, MIT). Ítem C3/M3
(#103), spec `knowledge/trust/11-spec-rule-verifier-backend-z3.md`.

Tres decisiones que este archivo materializa:

1. **Presupuesto por `rlimit`, JAMÁS por reloj** (corrección #103 al spec):
   un timeout wall-clock hace que `unknown` dependa de la máquina, y el
   replay dejaría de ser determinista. `rlimit` cuenta trabajo del solver —
   mismo principio que `max_deterministic_time` en trust/10 §1.4. Por eso
   esta clase no expone ningún parámetro de tiempo: la tentación no existe.
2. **La explicabilidad es la evidencia** (§1.4): además del `unsat_core`
   nativo, se corre cada regla POR SEPARADO contra el candidato fijo, para
   que la lista de "qué rompió" sea COMPLETA. El core de Z3 es un
   subconjunto insatisfacible pequeño pero **no garantizado mínimo**: con
   dos reglas rotas puede traer una sola, y presentarlo como el diagnóstico
   completo sería engañoso.
3. **El candidato se fija ENTERO o no se chequea nada** (fail-closed): si un
   símbolo que las reglas usan queda libre, Z3 puede ELEGIR el valor que
   haga `sat` — un `pass` así diría "existe algún mundo donde se cumple"
   disfrazado de "el candidato cumple". Símbolo libre ⇒
   `VerificationProcessError`, jamás un veredicto.

Las conversiones de valor son exactas: un float entra como su fracción
binaria EXACTA (`Fraction`), nunca por un decimal re-parseado — la misma
disciplina anti-drift del anexo de canonicalización, aplicada a la frontera
Python↔SMT.
"""

from __future__ import annotations

# z3-solver no publica stubs completos bajo pyright strict — mismo criterio
# que los otros adapters del plano ante librerías de terceros: se silencian
# SOLO los reportes de tipos desconocidos de terceros; las firmas propias de
# este módulo siguen bajo strict.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
# pyright: reportUnknownParameterType=false, reportMissingParameterType=false
import hashlib
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

import z3

from blite.certificate.canonical import JSONValue, canonicalize
from blite.verification.evidence import PropertyCheck
from blite.verification.exact_solver import VerificationProcessError
from blite.verification.rule_backend import RuleResult, RuleStatus
from blite.verification.rule_set import RuleSet

DEFAULT_RLIMIT = 4_000_000
"""Presupuesto determinista por chequeo. Generoso para reglas lineales
(las del catálogo cierran en órdenes de magnitud menos) y finito para que un
fragmento duro se corte igual en toda máquina."""

_BUDGET_REASONS = ("resource", "canceled", "cancelled")
"""Razones crudas de Z3 que significan «se acabó el presupuesto». El único
presupuesto que este backend impone es `rlimit`, así que una cancelación
solo puede venir de ahí."""


def _sort_name(sort: Any) -> str:
    return str(sort)


def _used_symbols(assertion: Any, out: dict[str, Any]) -> None:
    """Recolecta las constantes NO interpretadas (los símbolos del dominio)
    con su sort, preguntándole a Z3 en vez de re-parsear el texto: el sort
    lo declara el artefacto y quien lo interpreta debe ser el mismo que
    después resuelve."""
    if z3.is_const(assertion) and assertion.decl().kind() == z3.Z3_OP_UNINTERPRETED:
        out[assertion.decl().name()] = assertion.sort()
        return
    for child in assertion.children():
        _used_symbols(child, out)


def _binding(name: str, sort: Any, value: object) -> Any:
    """`símbolo = valor` en el sort DECLARADO por el artefacto.

    El sort manda: un entero para un símbolo `Real` es legítimo (3 es real);
    un float para un `Int` NO se coacciona en silencio — sería el candidato
    redefiniendo el tipo del dominio."""
    const = z3.Const(name, sort)
    kind = _sort_name(sort)
    if kind == "Bool":
        if not isinstance(value, bool):
            msg = f"{name}: el rule-set lo declara Bool y el candidato trae {value!r}"
            raise VerificationProcessError(msg)
        return const == z3.BoolVal(value)
    if kind == "Int":
        if isinstance(value, bool) or not isinstance(value, int):
            msg = f"{name}: el rule-set lo declara Int y el candidato trae {value!r}"
            raise VerificationProcessError(msg)
        return const == z3.IntVal(value)
    if kind == "Real":
        if isinstance(value, bool) or not isinstance(value, int | float):
            msg = f"{name}: el rule-set lo declara Real y el candidato trae {value!r}"
            raise VerificationProcessError(msg)
        if isinstance(value, float) and not math.isfinite(value):
            msg = (
                f"{name}: {value!r} no es finito — un chequeo sobre NaN/Infinity "
                "no lo puede reproducir nadie (misma regla que C() en el anexo §2)"
            )
            raise VerificationProcessError(msg)
        exact = Fraction(value)
        return const == z3.Q(exact.numerator, exact.denominator)
    msg = (
        f"{name}: sort {kind!r} sin conversión definida — este backend cubre "
        "Bool/Int/Real (fail-closed: nada de adivinar la codificación)"
    )
    raise VerificationProcessError(msg)


@dataclass(frozen=True)
class Z3RuleBackend:
    """Backend formal sobre Z3. Sin parámetros de reloj por construcción."""

    rlimit: int = DEFAULT_RLIMIT

    name: str = field(default="z3", init=False)

    @property
    def params_digest_inputs(self) -> dict[str, JSONValue]:
        """Lo que entra al `verifier_params_digest` — explícito para que un
        parámetro nuevo no se cuele fuera de la procedencia."""
        return {"rlimit": self.rlimit}

    @property
    def binary_digest(self) -> str:
        return hashlib.sha256(f"z3-{z3.get_version_string()}".encode()).hexdigest()

    @property
    def params_digest(self) -> str:
        return hashlib.sha256(canonicalize(self.params_digest_inputs)).hexdigest()

    def check(self, rule_set: RuleSet, subject: Mapping[str, Any]) -> RuleResult:
        parsed = z3.parse_smt2_string(rule_set.source.decode("utf-8"))
        # `AstVector` se indexa pero no se declara iterable: materializarlo
        # una vez evita depender de eso en cada recorrido.
        assertions: list[Any] = [parsed[i] for i in range(len(parsed))]
        if len(assertions) != len(rule_set.rule_names):
            msg = (
                f"rule-set {rule_set.rule_set_id!r}: {len(assertions)} aserciones "
                f"parseadas vs {len(rule_set.rule_names)} nombres — el apareo "
                "posicional nombre↔regla no es confiable (fail-closed)"
            )
            raise VerificationProcessError(msg)

        symbols: dict[str, Any] = {}
        for assertion in assertions:
            _used_symbols(assertion, symbols)

        ajenos = sorted(set(subject) - set(symbols))
        if ajenos:
            msg = (
                f"rule-set {rule_set.rule_set_id!r} no declara ni usa "
                f"{ajenos!r} — el candidato pidió chequear algo que estas "
                "reglas no conocen (error de proceso, jamás fail ni pass)"
            )
            raise VerificationProcessError(msg)
        libres = sorted(set(symbols) - set(subject))
        if libres:
            msg = (
                f"el candidato deja {libres!r} sin valor: con un símbolo libre "
                "el solver ELIGE el valor que haga sat, y el pass diría "
                "«existe algún mundo donde se cumple», no «el candidato cumple»"
            )
            raise VerificationProcessError(msg)

        bindings = [
            _binding(name, sort, subject[name]) for name, sort in symbols.items()
        ]

        checks: list[PropertyCheck] = []
        for name, assertion in zip(rule_set.rule_names, assertions, strict=True):
            status, reason = self._solve(assertion, bindings)
            if status == "unknown":
                return RuleResult(
                    holds=False,
                    backend=self.name,
                    status="unknown",
                    checks=tuple(checks),
                    unknown_reason=reason,
                )
            passed = status == "sat"
            checks.append(
                PropertyCheck(
                    name=name,
                    passed=passed,
                    examples_run=1,
                    counterexample=(
                        None if passed else _counterexample(name, assertion, subject)
                    ),
                )
            )

        if all(check.passed for check in checks):
            return RuleResult(
                holds=True, backend=self.name, status="sat", checks=tuple(checks)
            )
        return RuleResult(
            holds=False,
            backend=self.name,
            status="unsat",
            checks=tuple(checks),
            unsat_core=self._core(rule_set, assertions, bindings),
        )

    def _solve(self, assertion: Any, bindings: list[Any]) -> tuple[RuleStatus, str]:
        """Un solver EFÍMERO por chequeo: compartir estado entre reglas haría
        el resultado dependiente del orden. Devuelve también la razón cruda
        del `unknown` (vacía en los otros dos casos) — sin estado mutable en
        una clase frozen."""
        solver = z3.Solver()
        solver.set("rlimit", self.rlimit)
        solver.add(assertion)
        for binding in bindings:
            solver.add(binding)
        result = solver.check()
        if result == z3.sat:
            return "sat", ""
        if result == z3.unsat:
            return "unsat", ""
        return "unknown", str(solver.reason_unknown())

    def _core(
        self, rule_set: RuleSet, assertions: list[Any], bindings: list[Any]
    ) -> tuple[str, ...]:
        """El core NATIVO de Z3: reglas rastreadas (`assert_and_track`) +
        candidato fijo sin rastrear — así el core solo puede contener nombres
        de regla, jamás una binding del candidato (trust/11 §1.4)."""
        solver = z3.Solver()
        solver.set(unsat_core=True)
        solver.set("rlimit", self.rlimit)
        for name, assertion in zip(rule_set.rule_names, assertions, strict=True):
            solver.assert_and_track(assertion, name)
        for binding in bindings:
            solver.add(binding)
        if solver.check() != z3.unsat:
            return ()
        return tuple(sorted(str(item) for item in solver.unsat_core()))


def _counterexample(name: str, assertion: Any, subject: Mapping[str, Any]) -> str:
    """Nombre de la regla + los valores que la rompen. Un `fail` con el
    nombre y sin los números es media explicación."""
    involved: dict[str, Any] = {}
    _used_symbols(assertion, involved)
    valores = ", ".join(f"{key}={subject[key]!r}" for key in sorted(involved))
    return f"{name} no se sostiene con {valores}"


def is_budget_reason(reason: str) -> bool:
    """¿El `unknown` fue por presupuesto agotado? El único presupuesto de
    este backend es `rlimit` (no hay reloj), así que una cancelación solo
    puede venir de ahí."""
    lowered = reason.lower()
    return any(token in lowered for token in _BUDGET_REASONS)


__all__ = ["DEFAULT_RLIMIT", "Z3RuleBackend", "is_budget_reason"]
