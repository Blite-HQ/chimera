"""
PropertyRuleVerifier — el adapter `property_rule` (ancla `rule`, techo AL2).
Vocabulario §4 / docs/specs/generalidad-retos.md §Contrato-3/4.

Alcance v1 (letra de la spec, punto 3): «`PropertyRuleVerifier` v1 corre los
checks de `PropertyCheck`/`MetamorphicRelation` ya congelados; el backend
Z3/`RuleSet` con digest es el ítem C3/M3 (#103, sesión C-2) — esta spec NO
lo duplica.» Este módulo es exactamente eso: checks Python deterministas
sobre el catálogo C2 (`knowledge/quantum/04-estadistica-evidencia.md` §5) —
nada de SMT, nada de `RuleSet` versionado con digest, nada de Hypothesis
(ese es el backend formal/muestreado de `knowledge/trust/11-spec-rule-
verifier-backend-z3.md`, fuera de alcance aquí). `CLASS_CEILINGS
["property_rule"] == "AL2"` (attestation.py): el techo es DELIBERADO — un
chequeo puntual sobre el subject dado, sin prueba formal, jamás finge más
fuerza que la que tiene.

Diseño — las REGLAS son CÓDIGO, la SELECCIÓN de reglas es DATO: dos
registros a nivel de módulo (`PROPERTY_RULES`/`METAMORPHIC_RULES`) mapean un
NOMBRE estable a un callable del engine. El claim solo transporta nombres
(`properties`/`relations`, strings) — nunca un cuerpo de regla ejecutable.
Ningún `eval`, ninguna ejecución de algo que llegue por la red: si un
nombre no está en su registro, es un intento de invocar una regla que este
engine no conoce, y eso es un error de PROCESO (fail-closed) — jamás un
`fail` silencioso que dejaría pasar un check inexistente como si hubiera
corrido, y jamás un `pass` que un nombre desconocido pudiera fabricar.
Misma disciplina de «el conocimiento vive en datos, jamás en código
ejecutado desde afuera» que ADR-029 aplica a las capabilities.

Reglas que un claim selecciona pero no puede evaluar (falta una clave de
`subject`) son el MISMO tipo de error: el candidato pidió un chequeo
inevaluable, no es que el chequeo haya fallado. `VerificationProcessError`
en los tres casos (nombre desconocido, selección vacía, clave faltante) —
nunca `verdict: fail` (eso acusaría al candidato) ni `pass` (eso inflaría
la evidencia).
"""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast

# numpy: NO es una dependencia nueva de este módulo — mismo argumento que
# `exact_diagonalization.py` (pandapower>=3.5.4, dependencia DIRECTA de
# chimera-engine, ya hard-requiere numpy en uv.lock). numpy/scipy no
# publican stubs completos bajo pyright strict — se silencian SOLO los
# reportes de tipos desconocidos de terceros; las firmas propias de este
# módulo siguen bajo strict.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
import numpy as np
from pydantic import BaseModel, ConfigDict

from blite.certificate.canonical import JSONValue, canonicalize
from blite.verification.anchor import AnchorKind
from blite.verification.attestation import Attestation, Verdict, VerifierClass
from blite.verification.claim import claim_view_digest
from blite.verification.context import InvocationContext
from blite.verification.evidence import (
    MetamorphicRelation,
    PropertyCheck,
    PropertyRulePredicate,
)
from blite.verification.exact_solver import VerificationProcessError
from blite.verification.verifier import Determinism

_RULESET_VERSION = "builtin-v1"


class PropertyRuleClaim(BaseModel):
    """Claim: «`subject` sostiene las `properties` y `relations` nombradas».

    La selección (`properties`/`relations`) es DATO; el cuerpo de cada
    regla vive en `PROPERTY_RULES`/`METAMORPHIC_RULES`, del lado del
    engine — ver docstring del módulo."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    subject: dict[str, Any]
    properties: tuple[str, ...]
    relations: tuple[str, ...] = ()
    canonical_statement: str
    scope: dict[str, Any]


def _require(subject: Mapping[str, Any], key: str, rule_name: str) -> Any:
    """Cada regla valida sus propias claves de `subject`. Ausente ⇒ error de
    PROCESO — la regla fue seleccionada pero es inevaluable, jamás un
    `fail` (que acusaría al candidato) ni un `pass` silencioso (que
    fingiría haber corrido un chequeo que nunca corrió)."""
    if key not in subject:
        msg = (
            f"{rule_name}: falta subject[{key!r}] — regla seleccionada pero "
            "inevaluable (VerificationProcessError, jamás fail ni pass)"
        )
        raise VerificationProcessError(msg)
    return subject[key]


def _augmented_subject(
    subject: Mapping[str, Any], tolerance: float
) -> Mapping[str, Any]:
    """Copia INMUTABLE de `subject` con `tolerance` inyectada. Los callables
    de los registros solo reciben `subject` (firma fija, §Diseño del
    docstring del módulo) — el umbral del verificador viaja como una clave
    más en vez de un segundo argumento posicional; cualquier `tolerance`
    que el propio `subject` trajera queda sobrescrita por la del
    verificador (la autoridad de tolerancia es siempre la instancia que
    verifica, nunca el candidato)."""
    return {**subject, "tolerance": tolerance}


# ── PROPERTY_RULES — catálogo C2 puntual (knowledge/quantum/04 §5) ───────


def kernel_diagonal_unit(subject: Mapping[str, Any]) -> PropertyCheck:
    """Catálogo C2 punto 1: K(x,x) = 1 dentro de `tolerance` para todo i."""
    kernel = _require(subject, "kernel", "kernel_diagonal_unit")
    tolerance = _require(subject, "tolerance", "kernel_diagonal_unit")
    matrix = np.asarray(kernel, dtype=float)
    diagonal = np.diagonal(matrix)
    deviations = np.abs(diagonal - 1.0)
    worst = int(np.argmax(deviations))
    passed = bool(np.all(deviations <= tolerance))
    counterexample = (
        None
        if passed
        else f"K[{worst}][{worst}] = {float(diagonal[worst])!r} (esperado 1 ± {tolerance})"
    )
    return PropertyCheck(
        name="kernel_diagonal_unit",
        passed=passed,
        examples_run=int(diagonal.shape[0]),
        counterexample=counterexample,
    )


def kernel_symmetric(subject: Mapping[str, Any]) -> PropertyCheck:
    """Catálogo C2 punto 2: K = Kᵀ dentro de `tolerance`."""
    kernel = _require(subject, "kernel", "kernel_symmetric")
    tolerance = _require(subject, "tolerance", "kernel_symmetric")
    matrix = np.asarray(kernel, dtype=float)
    n = int(matrix.shape[0])
    diff = np.abs(matrix - matrix.T)
    worst = float(np.max(diff)) if n > 1 else 0.0
    passed = worst <= tolerance
    counterexample = None
    if not passed:
        i, j = (int(idx) for idx in np.unravel_index(np.argmax(diff), diff.shape))
        counterexample = (
            f"K[{i}][{j}]={float(matrix[i, j])!r} != "
            f"K[{j}][{i}]={float(matrix[j, i])!r} (|Δ|={worst!r} > {tolerance})"
        )
    return PropertyCheck(
        name="kernel_symmetric",
        passed=passed,
        examples_run=n * (n - 1) // 2,
        counterexample=counterexample,
    )


def kernel_psd(subject: Mapping[str, Any]) -> PropertyCheck:
    """Catálogo C2 punto 3: λ_min(K) ≥ -`tolerance` (`numpy.linalg.eigvalsh`
    — K es simétrica por construcción del reto, `eigvalsh` es la rutina
    correcta para ese caso, más barata y numéricamente estable que `eig`)."""
    kernel = _require(subject, "kernel", "kernel_psd")
    tolerance = _require(subject, "tolerance", "kernel_psd")
    matrix = np.asarray(kernel, dtype=float)
    eigenvalues = np.linalg.eigvalsh(matrix)
    lambda_min = float(np.min(eigenvalues))
    passed = lambda_min >= -tolerance
    counterexample = None if passed else f"λ_min(K) = {lambda_min!r} < -{tolerance}"
    return PropertyCheck(
        name="kernel_psd",
        passed=passed,
        examples_run=int(eigenvalues.shape[0]),
        counterexample=counterexample,
    )


def labels_binary(subject: Mapping[str, Any]) -> PropertyCheck:
    """Toda etiqueta ∈ {0, 1} — precondición de un clasificador binario."""
    labels = _require(subject, "labels", "labels_binary")
    n = len(labels)
    bad = next(
        ((idx, value) for idx, value in enumerate(labels) if value not in (0, 1)),
        None,
    )
    passed = bad is None
    counterexample = (
        None if bad is None else f"labels[{bad[0]}] = {bad[1]!r} (esperado 0 o 1)"
    )
    return PropertyCheck(
        name="labels_binary",
        passed=passed,
        examples_run=n,
        counterexample=counterexample,
    )


def folds_partition(subject: Mapping[str, Any]) -> PropertyCheck:
    """La asignación de folds sellada (spec §4: `folds_digest` comprometido
    ANTES de cualquier `fit`) debe ser una partición TOTAL: cada fila tiene
    exactamente un fold, los ids son contiguos desde 0 y ningún fold está
    vacío. Un hueco en la numeración ES un fold vacío — misma condición,
    una sola pasada."""
    folds = _require(subject, "folds", "folds_partition")
    n = len(folds)
    counts = Counter(folds)
    if not counts:
        return PropertyCheck(
            name="folds_partition",
            passed=False,
            examples_run=0,
            counterexample="folds vacío: no hay filas para particionar",
        )
    lowest, highest = min(counts), max(counts)
    empty_ids = [
        fold_id for fold_id in range(highest + 1) if counts.get(fold_id, 0) == 0
    ]
    passed = lowest == 0 and not empty_ids
    if passed:
        counterexample = None
    elif lowest != 0:
        counterexample = f"fold ids no arrancan en 0 (mínimo observado {lowest})"
    else:
        counterexample = (
            f"fold {empty_ids[0]} vacío — 0 filas asignadas (hueco en la partición)"
        )
    return PropertyCheck(
        name="folds_partition",
        passed=passed,
        examples_run=n,
        counterexample=counterexample,
    )


def predictions_aligned(subject: Mapping[str, Any]) -> PropertyCheck:
    """`len(predictions) == len(labels)` — sin esto ninguna métrica
    posterior (accuracy, McNemar) está siquiera bien planteada."""
    predictions = _require(subject, "predictions", "predictions_aligned")
    labels = _require(subject, "labels", "predictions_aligned")
    passed = len(predictions) == len(labels)
    counterexample = (
        None
        if passed
        else f"len(predictions)={len(predictions)} != len(labels)={len(labels)}"
    )
    return PropertyCheck(
        name="predictions_aligned",
        passed=passed,
        examples_run=max(len(predictions), len(labels)),
        counterexample=counterexample,
    )


PROPERTY_RULES: dict[str, Callable[[Mapping[str, Any]], PropertyCheck]] = {
    "kernel_diagonal_unit": kernel_diagonal_unit,
    "kernel_symmetric": kernel_symmetric,
    "kernel_psd": kernel_psd,
    "labels_binary": labels_binary,
    "folds_partition": folds_partition,
    "predictions_aligned": predictions_aligned,
}


# ── METAMORPHIC_RULES — relaciones metamórficas del catálogo C2 ──────────


def kernel_transpose_invariance(subject: Mapping[str, Any]) -> MetamorphicRelation:
    """Recomputa la comparación K vs Kᵀ tras transponer — la MISMA
    condición de `kernel_symmetric`, expresada como relación metamórfica
    (`expected_relation="invariant"`: transponer no debería cambiar el
    resultado de la comparación consigo misma)."""
    kernel = _require(subject, "kernel", "kernel_transpose_invariance")
    tolerance = _require(subject, "tolerance", "kernel_transpose_invariance")
    matrix = np.asarray(kernel, dtype=float)
    held = bool(np.allclose(matrix, matrix.T, atol=tolerance, rtol=0.0))
    transform_digest = hashlib.sha256(
        canonicalize({"transform": "transpose"})
    ).hexdigest()
    return MetamorphicRelation(
        name="kernel_transpose_invariance",
        transform_digest=transform_digest,
        expected_relation="invariant",
        held=held,
    )


def labels_shuffled_degrades(subject: Mapping[str, Any]) -> MetamorphicRelation:
    """El detector de fuga del catálogo C2 (`knowledge/quantum/04-
    estadistica-evidencia.md` §5 punto 4): re-entrenar con las etiquetas
    barajadas al azar debe rendir ≈ la clase mayoritaria — una tubería que
    TODAVÍA rinde bien con etiquetas rotas está filtrando información fuera
    del split de train (KB2-02 §2.1), «la propiedad más barata y letal del
    reto». La relación SOSTIENE (`held=True`) cuando la accuracy barajada
    NO supera a la real en más de `tolerance`; degrada = sano, mejora o
    empata de más = fuga."""
    accuracy = _require(subject, "accuracy", "labels_shuffled_degrades")
    accuracy_shuffled = _require(
        subject, "accuracy_shuffled", "labels_shuffled_degrades"
    )
    tolerance = _require(subject, "tolerance", "labels_shuffled_degrades")
    seed = _require(subject, "seed", "labels_shuffled_degrades")
    held = accuracy_shuffled <= accuracy + tolerance
    transform_digest = hashlib.sha256(
        canonicalize({"transform": "shuffle-labels", "seed": seed})
    ).hexdigest()
    return MetamorphicRelation(
        name="labels_shuffled_degrades",
        transform_digest=transform_digest,
        expected_relation="invariant",
        held=held,
    )


METAMORPHIC_RULES: dict[str, Callable[[Mapping[str, Any]], MetamorphicRelation]] = {
    "kernel_transpose_invariance": kernel_transpose_invariance,
    "labels_shuffled_degrades": labels_shuffled_degrades,
}


def claim_digest_of(claim: PropertyRuleClaim) -> str:
    """Delegación al helper común (§7 del anexo) — un solo lugar computa la
    vista claim↔digest."""
    return claim_view_digest(claim.canonical_statement, claim.scope)


def _default_binary_digest() -> str:
    """No hay solver/paquete externo que versionar aquí (a diferencia de
    CP-SAT/eigh): el "binario" es el propio conjunto de reglas del engine,
    versionado por `_RULESET_VERSION` — mismo patrón que
    `ground_truth._default_binary_digest`."""
    return hashlib.sha256(f"property-rule-{_RULESET_VERSION}".encode()).hexdigest()


@dataclass(frozen=True)
class PropertyRuleVerifier:
    """Adapter de la clase `property_rule` (ancla `rule`, techo AL2 —
    honesto: sin prueba formal, ver docstring del módulo). Corre los
    `PROPERTY_RULES`/`METAMORPHIC_RULES` que el claim nombra sobre su
    `subject` y falla-cerrado ante nombre desconocido, selección vacía o
    clave de `subject` faltante (los tres son error de PROCESO, jamás un
    veredicto)."""

    verifier_id: str
    independence_group: str
    anchor_digest: str
    tolerance: float = 1e-9
    verifier_binary_digest: str = field(default_factory=_default_binary_digest)

    # Campos de instancia (init=False) y no ClassVar: el Protocol `Verifier`
    # los declara como atributos de instancia — pyright exige que coincidan
    # (mismo patrón que exact_diagonalization.py/exact_solver.py).
    verifier_class: VerifierClass = field(default="property_rule", init=False)
    anchor_kind: AnchorKind = field(default="rule", init=False)
    determinism: Determinism = field(default="deterministic", init=False)

    @property
    def _params(self) -> dict[str, JSONValue]:
        return {
            "ruleset": _RULESET_VERSION,
            "tolerance": self.tolerance,
            # cast: `list[str]` no es `list[JSONValue]` bajo invarianza de
            # `list` — los NOMBRES son str, JSONValue de sobra los admite.
            "properties": cast("list[JSONValue]", sorted(PROPERTY_RULES)),
            "relations": cast("list[JSONValue]", sorted(METAMORPHIC_RULES)),
        }

    @property
    def verifier_params_digest(self) -> str:
        return hashlib.sha256(canonicalize(self._params)).hexdigest()

    def verify_all(self, claim: Any, ctx: InvocationContext) -> tuple[Attestation, ...]:
        """Constancia ÚNICA (default del puerto, freeze §7 [MEJORADO
        C-6/#106]): este adapter no tiene sub-entidades que verificar por
        separado. Se declara explícito porque el adapter satisface `Verifier`
        de forma ESTRUCTURAL — no hereda el cuerpo del default del Protocol."""
        return (self.verify(claim, ctx),)

    def verify(self, claim: Any, ctx: InvocationContext) -> Attestation:
        if not isinstance(claim, PropertyRuleClaim):
            msg = f"claim {type(claim).__name__} no es un PropertyRuleClaim"
            raise VerificationProcessError(msg)

        if not claim.properties and not claim.relations:
            msg = (
                "PropertyRuleClaim sin properties NI relations — un "
                "verificador que no chequea nada jamás emite pass "
                "(fail-closed, docs/specs/generalidad-retos.md §Contrato-3)"
            )
            raise VerificationProcessError(msg)

        subject = _augmented_subject(claim.subject, self.tolerance)
        checks = tuple(self._run_property(name, subject) for name in claim.properties)
        relations = tuple(self._run_relation(name, subject) for name in claim.relations)

        verdict: Verdict = (
            "pass"
            if all(check.passed for check in checks)
            and all(relation.held for relation in relations)
            else "fail"
        )

        return Attestation(
            verifier_id=self.verifier_id,
            verifier_class=self.verifier_class,
            anchor_kind=self.anchor_kind,
            level="AL2",
            verdict=verdict,
            scope=claim.scope,
            independence_group=self.independence_group,
            run_id=ctx.run_id,
            claim_digest=claim_digest_of(claim),
            verifier_binary_digest=self.verifier_binary_digest,
            verifier_params_digest=self.verifier_params_digest,
            # verdict pass/fail exige anchor_digest (freeze T3/D10) — este
            # verificador no tiene rama `inconclusive`, así que siempre lo
            # pasa (nunca None).
            anchor_digest=self.anchor_digest,
            predicate=PropertyRulePredicate(
                properties=checks,
                relations=relations,
                backend=_RULESET_VERSION,
            ),
            issued_at=datetime.now(UTC),
        )

    @staticmethod
    def _run_property(name: str, subject: Mapping[str, Any]) -> PropertyCheck:
        rule = PROPERTY_RULES.get(name)
        if rule is None:
            msg = f"{name!r}: propiedad desconocida — no está en PROPERTY_RULES (fail-closed)"
            raise VerificationProcessError(msg)
        return rule(subject)

    @staticmethod
    def _run_relation(name: str, subject: Mapping[str, Any]) -> MetamorphicRelation:
        rule = METAMORPHIC_RULES.get(name)
        if rule is None:
            msg = (
                f"{name!r}: relación desconocida — no está en METAMORPHIC_RULES "
                "(fail-closed)"
            )
            raise VerificationProcessError(msg)
        return rule(subject)
