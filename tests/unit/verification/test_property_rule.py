"""PropertyRuleVerifier (catálogo C2, ancla `rule`) — el tercer adapter de
`docs/specs/generalidad-retos.md` §Contrato-3/4. Fórmulas y catálogo de
propiedades/metamórficas en `knowledge/quantum/04-estadistica-evidencia.md`
§5; alcance v1 (checks Python puntuales, SIN backend Z3/`RuleSet` con
digest) en la misma spec, punto 3 — el ítem C3/M3 (#103) queda fuera.

Igual que `test_exact_diagonalization.py`: cada helper de este archivo
reconstruye su propio subject a mano en vez de importar constantes del
módulo bajo prueba — si un cálculo aquí y el del módulo concuerdan, ninguno
comparte un bug de convención por accidente.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any

import pytest
from pydantic import ValidationError

from blite.certificate.canonical import JSONValue, canonicalize
from blite.verification.attestation import Attestation
from blite.verification.context import InvocationContext
from blite.verification.evidence import PropertyRulePredicate
from blite.verification.exact_solver import VerificationProcessError
from blite.verification.property_rule import (
    METAMORPHIC_RULES,
    PROPERTY_RULES,
    PropertyRuleClaim,
    PropertyRuleVerifier,
)
from blite.verification.verifier import Verifier

CTX = InvocationContext(
    run_id="run:test", actor_id="service:runtime", domain_id="dom:test"
)
ANCHOR_DIGEST = hashlib.sha256(b"anchor:property-rule-builtin-v1").hexdigest()

# ── Fixture base — satisface las 6 propiedades + las 2 relaciones a la vez ──

_KERNEL = (
    (1.0, 0.1, 0.05, 0.02),
    (0.1, 1.0, 0.08, 0.03),
    (0.05, 0.08, 1.0, 0.04),
    (0.02, 0.03, 0.04, 1.0),
)
_LABELS = (0, 1, 0, 1)
_PREDICTIONS = (0, 1, 1, 1)
_FOLDS = (0, 0, 1, 1)
_ACCURACY = 0.75
_ACCURACY_SHUFFLED = 0.5
_SEED = 42

ALL_PROPERTIES = (
    "kernel_diagonal_unit",
    "kernel_symmetric",
    "kernel_psd",
    "labels_binary",
    "folds_partition",
    "predictions_aligned",
)
ALL_RELATIONS = ("kernel_transpose_invariance", "labels_shuffled_degrades")


def _subject(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "kernel": copy.deepcopy(_KERNEL),
        "labels": _LABELS,
        "predictions": _PREDICTIONS,
        "folds": _FOLDS,
        "accuracy": _ACCURACY,
        "accuracy_shuffled": _ACCURACY_SHUFFLED,
        "seed": _SEED,
    }
    base.update(overrides)
    return base


def _claim(
    *,
    properties: tuple[str, ...] = ALL_PROPERTIES,
    relations: tuple[str, ...] = ALL_RELATIONS,
    subject: dict[str, Any] | None = None,
) -> PropertyRuleClaim:
    return PropertyRuleClaim(
        subject=subject if subject is not None else _subject(),
        properties=properties,
        relations=relations,
        canonical_statement="el subject sostiene las propiedades/relaciones seleccionadas",
        scope={"reto": "C2"},
    )


def make_verifier(**overrides: Any) -> PropertyRuleVerifier:
    params: dict[str, Any] = {
        "verifier_id": "verifier:property-rule-c2",
        "independence_group": "leg-property-rule",
        "anchor_digest": ANCHOR_DIGEST,
    }
    params.update(overrides)
    return PropertyRuleVerifier(**params)


def predicate_of(att: Attestation) -> PropertyRulePredicate:
    """Narrowing del union ClassPredicate a la evidencia property_rule."""
    assert isinstance(att.predicate, PropertyRulePredicate)
    return att.predicate


class TestVeredictoPass:
    """Las 6 propiedades + las 2 relaciones sostienen simultáneamente sobre
    el subject base ⇒ pass, AL2, un `PropertyCheck` por propiedad
    seleccionada, todos `passed=True`."""

    def test_subject_valido_pasa_con_todas_las_reglas(self) -> None:
        att = make_verifier().verify(_claim(), CTX)

        assert att.verdict == "pass"
        assert att.level == "AL2"
        assert att.anchor_digest == ANCHOR_DIGEST
        predicate = predicate_of(att)
        assert predicate.backend == "builtin-v1"
        assert {check.name for check in predicate.properties} == set(ALL_PROPERTIES)
        assert all(check.passed for check in predicate.properties)
        assert {relation.name for relation in predicate.relations} == set(ALL_RELATIONS)
        assert all(relation.held for relation in predicate.relations)


class TestUnaSolaPropiedadPorViolacionDirigida:
    """Una prueba POR regla de propiedad: rompe exactamente la condición que
    esa regla chequea y nada más — `passed=False` + `counterexample`
    poblado."""

    def test_kernel_diagonal_unit_falla_con_diagonal_rota(self) -> None:
        broken = [list(row) for row in _KERNEL]
        broken[0][0] = 0.9
        claim = _claim(
            properties=("kernel_diagonal_unit",),
            relations=(),
            subject=_subject(kernel=broken),
        )

        att = make_verifier().verify(claim, CTX)

        assert att.verdict == "fail"
        check = predicate_of(att).properties[0]
        assert check.name == "kernel_diagonal_unit"
        assert check.passed is False
        assert check.counterexample is not None

    def test_kernel_symmetric_falla_con_asimetria(self) -> None:
        broken = [list(row) for row in _KERNEL]
        broken[0][1] = 0.9  # broken[1][0] sigue en 0.1 -> asimétrico
        claim = _claim(
            properties=("kernel_symmetric",),
            relations=(),
            subject=_subject(kernel=broken),
        )

        att = make_verifier().verify(claim, CTX)

        assert att.verdict == "fail"
        check = predicate_of(att).properties[0]
        assert check.name == "kernel_symmetric"
        assert check.passed is False
        assert check.counterexample is not None

    def test_kernel_psd_falla_con_autovalor_negativo_bajo_tolerancia(self) -> None:
        # eigvalsh([[1,1.5],[1.5,1]]) = [-0.5, 2.5] -- muy por debajo de -tol.
        negative_definite = [[1.0, 1.5], [1.5, 1.0]]
        claim = _claim(
            properties=("kernel_psd",),
            relations=(),
            subject=_subject(kernel=negative_definite),
        )

        att = make_verifier().verify(claim, CTX)

        assert att.verdict == "fail"
        check = predicate_of(att).properties[0]
        assert check.name == "kernel_psd"
        assert check.passed is False
        assert check.counterexample is not None

    def test_labels_binary_falla_con_etiqueta_fuera_del_alfabeto(self) -> None:
        claim = _claim(
            properties=("labels_binary",),
            relations=(),
            subject=_subject(labels=(0, 1, 2, 0)),
        )

        att = make_verifier().verify(claim, CTX)

        assert att.verdict == "fail"
        check = predicate_of(att).properties[0]
        assert check.name == "labels_binary"
        assert check.passed is False
        assert check.counterexample is not None

    def test_folds_partition_falla_con_hueco_en_la_numeracion(self) -> None:
        # Fold 1 nunca aparece: hueco == fold vacío (misma condición).
        claim = _claim(
            properties=("folds_partition",),
            relations=(),
            subject=_subject(folds=(0, 0, 2, 2)),
        )

        att = make_verifier().verify(claim, CTX)

        assert att.verdict == "fail"
        check = predicate_of(att).properties[0]
        assert check.name == "folds_partition"
        assert check.passed is False
        assert check.counterexample is not None

    def test_folds_partition_falla_con_ids_que_no_arrancan_en_0(self) -> None:
        claim = _claim(
            properties=("folds_partition",),
            relations=(),
            subject=_subject(folds=(1, 1, 2, 2)),
        )

        att = make_verifier().verify(claim, CTX)

        assert att.verdict == "fail"
        check = predicate_of(att).properties[0]
        assert check.passed is False
        assert check.counterexample is not None

    def test_folds_partition_falla_con_folds_vacio(self) -> None:
        claim = _claim(
            properties=("folds_partition",),
            relations=(),
            subject=_subject(folds=()),
        )

        att = make_verifier().verify(claim, CTX)

        assert att.verdict == "fail"
        check = predicate_of(att).properties[0]
        assert check.passed is False
        assert check.examples_run == 0
        assert check.counterexample is not None

    def test_predictions_aligned_falla_con_largo_distinto(self) -> None:
        claim = _claim(
            properties=("predictions_aligned",),
            relations=(),
            subject=_subject(predictions=(0, 1)),  # labels tiene 4
        )

        att = make_verifier().verify(claim, CTX)

        assert att.verdict == "fail"
        check = predicate_of(att).properties[0]
        assert check.name == "predictions_aligned"
        assert check.passed is False
        assert check.counterexample is not None


class TestRelacionesMetamorficas:
    """`labels_shuffled_degrades` es el detector de fuga (knowledge/quantum/
    04 §5 punto 4): sostiene cuando barajar etiquetas NO mejora la
    accuracy; deja de sostener cuando sí la mejora materialmente (señal de
    leakage)."""

    def test_labels_shuffled_degrades_sostiene_cuando_la_barajada_no_mejora(self) -> None:
        claim = _claim(
            properties=(),
            relations=("labels_shuffled_degrades",),
            subject=_subject(accuracy=0.75, accuracy_shuffled=0.50),
        )

        att = make_verifier().verify(claim, CTX)

        assert att.verdict == "pass"
        relation = predicate_of(att).relations[0]
        assert relation.name == "labels_shuffled_degrades"
        assert relation.held is True

    def test_labels_shuffled_degrades_no_sostiene_cuando_la_barajada_mejora(self) -> None:
        claim = _claim(
            properties=(),
            relations=("labels_shuffled_degrades",),
            subject=_subject(accuracy=0.60, accuracy_shuffled=0.90),
        )

        att = make_verifier().verify(claim, CTX)

        assert att.verdict == "fail"
        relation = predicate_of(att).relations[0]
        assert relation.held is False

    def test_kernel_transpose_invariance_no_sostiene_con_asimetria(self) -> None:
        broken = [list(row) for row in _KERNEL]
        broken[0][1] = 0.9
        claim = _claim(
            properties=(),
            relations=("kernel_transpose_invariance",),
            subject=_subject(kernel=broken),
        )

        att = make_verifier().verify(claim, CTX)

        assert att.verdict == "fail"
        relation = predicate_of(att).relations[0]
        assert relation.name == "kernel_transpose_invariance"
        assert relation.held is False


class TestFailClosed:
    """§Contrato-3: nombre desconocido, selección vacía y clave de subject
    faltante son error de PROCESO — jamás fail (acusaría al candidato) ni
    pass (inflaría la evidencia)."""

    def test_nombre_de_propiedad_desconocido_levanta_process_error(self) -> None:
        claim = _claim(properties=("no-existe",), relations=())

        with pytest.raises(VerificationProcessError):
            make_verifier().verify(claim, CTX)

    def test_nombre_de_relacion_desconocida_levanta_process_error(self) -> None:
        claim = _claim(properties=(), relations=("no-existe",))

        with pytest.raises(VerificationProcessError):
            make_verifier().verify(claim, CTX)

    def test_seleccion_vacia_levanta_process_error(self) -> None:
        claim = _claim(properties=(), relations=())

        with pytest.raises(VerificationProcessError):
            make_verifier().verify(claim, CTX)

    def test_clave_de_subject_faltante_levanta_process_error_no_fail(self) -> None:
        claim = _claim(
            properties=("kernel_psd",),
            relations=(),
            subject={"labels": _LABELS},  # sin "kernel"
        )

        with pytest.raises(VerificationProcessError):
            make_verifier().verify(claim, CTX)

    def test_claim_de_tipo_incorrecto_levanta_process_error(self) -> None:
        with pytest.raises(VerificationProcessError):
            make_verifier().verify(object(), CTX)


class TestRegistros:
    """Los dos registros de PROPERTY_RULES/METAMORPHIC_RULES exponen
    exactamente las reglas de v1 — pin de forma (no exhaustivo sobre
    comportamiento, ya cubierto arriba)."""

    def test_property_rules_expone_las_seis_reglas(self) -> None:
        assert set(PROPERTY_RULES) == set(ALL_PROPERTIES)

    def test_metamorphic_rules_expone_las_dos_relaciones(self) -> None:
        assert set(METAMORPHIC_RULES) == set(ALL_RELATIONS)


class TestTechoAL2:
    """El techo `property_rule` es AL2 (`CLASS_CEILINGS`). Regresión de una
    línea (mismo patrón que `TestTechoAL4` de exact_diagonalization): el
    freeze (`Attestation._letra_del_freeze`) muerde AL3 sin proof — este
    verificador jamás debería intentar emitir más fuerza que un chequeo
    puntual sin prueba formal."""

    def test_al3_levanta(self) -> None:
        att = make_verifier().verify(_claim(), CTX)

        with pytest.raises(ValidationError):
            Attestation(
                verifier_id=att.verifier_id,
                verifier_class=att.verifier_class,
                anchor_kind=att.anchor_kind,
                level="AL3",
                verdict=att.verdict,
                scope=att.scope,
                independence_group=att.independence_group,
                run_id=att.run_id,
                claim_digest=att.claim_digest,
                verifier_binary_digest=att.verifier_binary_digest,
                verifier_params_digest=att.verifier_params_digest,
                anchor_digest=att.anchor_digest,
                predicate=att.predicate,
                issued_at=att.issued_at,
            )


class TestParamsDigest:
    """Tolerancia distinta ⇒ `verifier_params_digest` distinto (mismo
    mecanismo C-14 que `exact_diagonalization`/`exact_solver`) — el
    conjunto de reglas expuestas por los registros también entra al
    digest (vía `_params`, privado — no se accede desde el test), así que
    agregar una regla nueva al engine lo cambiaría también."""

    def test_cambia_con_tolerance(self) -> None:
        base = make_verifier()
        distinto = make_verifier(tolerance=1e-6)

        assert base.verifier_params_digest != distinto.verifier_params_digest


class TestDeterminismo:
    def test_dos_corridas_identicas_salvo_issued_at(self) -> None:
        claim = _claim()
        verifier = make_verifier()

        a = verifier.verify(claim, CTX).model_dump(exclude={"issued_at"})
        b = verifier.verify(claim, CTX).model_dump(exclude={"issued_at"})

        assert a == b


class TestAtributosDelPuertoYProtocolo:
    def test_atributos(self) -> None:
        verifier = make_verifier()

        assert verifier.verifier_class == "property_rule"
        assert verifier.anchor_kind == "rule"
        assert verifier.determinism == "deterministic"
        assert isinstance(verifier, Verifier)


class TestClaimDigest:
    def test_sigue_la_convencion_del_anexo(self) -> None:
        claim = _claim()
        att = make_verifier().verify(claim, CTX)

        view: dict[str, JSONValue] = {
            "canonical_statement": claim.canonical_statement,
            "scope": claim.scope,
        }
        expected = hashlib.sha256(
            b"blite/claim/v1\n" + canonicalize(view)
        ).hexdigest()
        assert att.claim_digest == expected
