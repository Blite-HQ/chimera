"""`RuleVerifier` + puerto `RuleBackend` + `RuleSet` como datos — ítem C3/M3
(#103; spec `knowledge/trust/11-spec-rule-verifier-backend-z3.md`).

Lo que estos tests fijan, en orden de importancia:

1. **La regla es DATO, no código** — el `RuleSet` es un artefacto SMT-LIB 2
   versionado cuyo `rule_digest` son los BYTES EXACTOS del archivo (Regla 1
   del anexo de canonicalización, igual que `policy_digest`): comentarios y
   formato son parte de lo distribuido.
2. **La explicabilidad es la evidencia** (trust/11 §1.4): un `fail` dice QUÉ
   reglas rompe el candidato, no solo QUE falla.
3. **El presupuesto es `rlimit`, jamás reloj** — el determinismo del replay
   exige que el punto de corte no dependa de la máquina; agotarlo es
   `inconclusive` con razón tipada, jamás `fail` (eso acusaría al candidato
   de algo que nadie probó).
4. **Cero techos rotos** (#103): la v1 con Z3 emite `property_rule` AL2
   honesto. Un backend que devolviera una prueba formal NO se emite en
   silencio como AL2 ni se infla a `formal_exact` — explota nombrando la
   ceremonia que falta (la ruta cvc5→Alethe→Carcara).
"""

from __future__ import annotations

# z3-solver no publica stubs — mismo criterio que el módulo bajo prueba.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
import hashlib
from pathlib import Path
from typing import Any

import pytest

from blite.verification.attestation import Attestation
from blite.verification.context import InvocationContext
from blite.verification.evidence import PropertyRulePredicate
from blite.verification.exact_solver import VerificationProcessError
from blite.verification.rule import RuleClaim, RuleVerifier
from blite.verification.rule_backend import RuleBackend, RuleProof, RuleResult
from blite.verification.rule_set import RuleSet, RuleSetError, load_rule_set
from blite.verification.rule_z3 import Z3RuleBackend
from blite.verification.verifier import Verifier

CTX = InvocationContext(
    run_id="run:test", actor_id="service:runtime", domain_id="dom:test"
)

REPO = Path(__file__).resolve().parents[3]

# Artefacto de prueba GENÉRICO (sin vocabulario de escenario): dos reglas
# nombradas sobre tres símbolos. El artefacto real del dominio eléctrico vive
# en knowledge/ y tiene su propio test abajo.
SOURCE = """; rule-set-id: unit-rules@0.1.0
; Artefacto de prueba — dos reglas nombradas sobre magnitudes escalares.
(declare-fun quantity () Int)
(declare-fun observed () Real)
(declare-fun tolerance () Real)

(assert (! (>= quantity 2) :named at_least_two))
(assert (! (<= observed tolerance) :named within_tolerance))
""".encode()

SUBJECT_OK: dict[str, Any] = {"quantity": 3, "observed": 0.5, "tolerance": 1.0}


def _rule_set() -> RuleSet:
    return RuleSet.parse(SOURCE)


def _verifier(**overrides: Any) -> RuleVerifier:
    base: dict[str, Any] = {
        "verifier_id": "z3-rules",
        "independence_group": "leg-rule",
        "rule_set": _rule_set(),
        "backend": Z3RuleBackend(),
    }
    return RuleVerifier(**{**base, **overrides})


def _claim(subject: dict[str, Any]) -> RuleClaim:
    return RuleClaim(
        subject=subject,
        canonical_statement="El candidato satisface el conjunto de reglas declarado",
        scope={"rule_set": "unit-rules@0.1.0"},
    )


# ── RuleSet: la regla como DATO versionado con digest de artefacto ───────


def test_el_rule_digest_son_los_bytes_exactos_del_artefacto() -> None:
    """Regla 1 del anexo (igual que `policy_digest`): el digest es del
    ARCHIVO, no de una re-serialización — comentarios y formato incluidos.
    Re-parsear para canonicalizar reintroduciría la fragilidad que el anexo
    existe para matar."""
    # Arrange / Act
    rule_set = RuleSet.parse(SOURCE)

    # Assert
    assert rule_set.rule_digest == hashlib.sha256(SOURCE).hexdigest()


def test_un_comentario_distinto_cambia_el_digest_aunque_las_reglas_sean_iguales() -> (
    None
):
    """Corolario de la Regla 1: el artefacto distribuido cambió, y el
    certificado debe poder decirlo."""
    # Arrange
    con_comentario = SOURCE.replace(b"; Artefacto de prueba", b"; Artefacto EDITADO")

    # Act
    original, editado = RuleSet.parse(SOURCE), RuleSet.parse(con_comentario)

    # Assert
    assert original.rule_names == editado.rule_names
    assert original.rule_digest != editado.rule_digest


def test_el_rule_set_id_se_lee_del_propio_artefacto() -> None:
    """Fuente única de identidad (misma convención que el digest embebido de
    los JSON del corpus): el id viaja DENTRO del artefacto — un cargador que
    lo recibe por parámetro permite que id y bytes deriven en silencio."""
    assert RuleSet.parse(SOURCE).rule_set_id == "unit-rules@0.1.0"


def test_un_artefacto_sin_rule_set_id_no_carga() -> None:
    """Sin identidad declarada, la attestation no puede decir QUÉ reglas
    corrió — fail-closed en el cargador, jamás un id inventado."""
    with pytest.raises(RuleSetError, match="rule-set-id"):
        RuleSet.parse(b"(declare-fun x () Int)\n(assert (! (> x 0) :named p))\n")


def test_una_regla_sin_nombre_no_carga() -> None:
    """Una regla sin `:named` es una regla que el unsat core no puede
    señalar (trust/11 §1.4): la explicabilidad dejaría de ser exigible sin
    que nada fallara."""
    sin_nombre = b"; rule-set-id: x@1\n(declare-fun x () Int)\n(assert (> x 0))\n"

    with pytest.raises(RuleSetError, match="sin `:named`"):
        RuleSet.parse(sin_nombre)


def test_un_artefacto_sin_reglas_no_carga() -> None:
    """Un verificador que no chequea nada jamás emite `pass` — misma
    disciplina que `PropertyRuleVerifier` con selección vacía."""
    with pytest.raises(RuleSetError, match="sin reglas"):
        RuleSet.parse(b"; rule-set-id: vacio@1\n(declare-fun x () Int)\n")


def test_load_rule_set_lee_los_bytes_del_disco(tmp_path: Path) -> None:
    """El artefacto que se distribuye ES el archivo — el cargador no lo
    normaliza al leerlo."""
    # Arrange
    path = tmp_path / "reglas.smt2"
    path.write_bytes(SOURCE)

    # Act
    rule_set = load_rule_set(path)

    # Assert
    assert rule_set.rule_digest == hashlib.sha256(path.read_bytes()).hexdigest()
    assert rule_set.rule_names == ("at_least_two", "within_tolerance")


# ── Backend Z3: sat/unsat/unknown y el core como evidencia ───────────────


def test_el_candidato_que_cumple_da_sat_y_todas_las_reglas_pasan() -> None:
    # Arrange
    backend = Z3RuleBackend()

    # Act
    result = backend.check(_rule_set(), SUBJECT_OK)

    # Assert
    assert result.status == "sat"
    assert result.holds is True
    assert [(c.name, c.passed) for c in result.checks] == [
        ("at_least_two", True),
        ("within_tolerance", True),
    ]
    assert result.unsat_core == ()


def test_el_core_nombra_las_reglas_que_el_candidato_rompe() -> None:
    """EL diferenciador frente a un `fail` opaco (trust/11 §1.4): QUÉ falla,
    no solo QUE falla."""
    # Arrange — rompe UNA de las dos reglas
    backend = Z3RuleBackend()

    # Act
    result = backend.check(_rule_set(), {**SUBJECT_OK, "observed": 5.0})

    # Assert
    assert result.status == "unsat"
    assert result.holds is False
    assert result.unsat_core == ("within_tolerance",)
    assert [(c.name, c.passed) for c in result.checks] == [
        ("at_least_two", True),
        ("within_tolerance", False),
    ]


def test_dos_reglas_rotas_se_reportan_las_dos() -> None:
    """El core de Z3 es un subconjunto insatisfacible PEQUEÑO, no garantizado
    mínimo (limitación documentada en trust/11 §1.4): puede traer una sola de
    las dos. Por eso la lista autoritativa de "qué rompió el candidato" es el
    chequeo regla-a-regla, no el core — un core corto jamás debe leerse como
    "solo esta regla falla"."""
    # Arrange
    backend = Z3RuleBackend()

    # Act
    result = backend.check(
        _rule_set(), {"quantity": 1, "observed": 5.0, "tolerance": 1.0}
    )

    # Assert — las DOS reglas rotas aparecen en los checks
    assert [c.name for c in result.checks if not c.passed] == [
        "at_least_two",
        "within_tolerance",
    ]
    assert set(result.unsat_core) <= {"at_least_two", "within_tolerance"}
    assert result.unsat_core  # el core existe y es subconjunto de las rotas


def test_el_contraejemplo_de_cada_regla_rota_cita_los_valores_involucrados() -> None:
    """Un `fail` con el nombre de la regla y sin los números es media
    explicación."""
    result = Z3RuleBackend().check(_rule_set(), {**SUBJECT_OK, "observed": 5.0})

    (roto,) = [c for c in result.checks if not c.passed]
    assert roto.counterexample is not None
    assert "observed=5.0" in roto.counterexample
    assert "tolerance=1.0" in roto.counterexample


def test_el_presupuesto_es_rlimit_y_agotarlo_es_unknown_jamas_fail() -> None:
    """trust/11 §1.3 [#103]: `rlimit`, JAMÁS timeout de reloj — el
    determinismo del replay exige que el punto de corte no dependa de la
    máquina (mismo principio que `max_deterministic_time` de la nota 10)."""
    # Arrange — regla no lineal dura + presupuesto ridículo
    dura = RuleSet.parse(
        b"; rule-set-id: dura@1\n"
        b"(declare-fun x () Int)\n(declare-fun y () Int)\n"
        b"(assert (! (= (* x x x) (+ (* y y y) 42)) :named cubica))\n"
    )
    backend = Z3RuleBackend(rlimit=1)

    # Act
    result = backend.check(dura, {"x": 0, "y": 0})

    # Assert
    assert result.status == "unknown"
    assert result.holds is False
    assert result.unknown_reason is not None


def test_el_backend_z3_no_acepta_timeout_de_reloj() -> None:
    """La forma del backend impide la tentación: no hay parámetro de reloj
    que setear (si lo hubiera, alguien lo usaría y el replay dejaría de ser
    determinista)."""
    assert not hasattr(Z3RuleBackend(), "timeout_ms")
    assert "timeout" not in Z3RuleBackend().params_digest_inputs


# ── Honestidad de la frontera candidato↔reglas ──────────────────────────


def test_un_simbolo_que_el_rule_set_no_declara_es_error_de_proceso() -> None:
    """El candidato pidió que se chequeara algo que estas reglas no
    conocen — es error de PROCESO, jamás un `fail` (que lo acusaría) ni un
    `pass` (que fingiría haber chequeado)."""
    with pytest.raises(VerificationProcessError, match="no declara"):
        Z3RuleBackend().check(_rule_set(), {**SUBJECT_OK, "inventado": 1})


def test_un_simbolo_declarado_sin_valor_en_el_candidato_es_error_de_proceso() -> None:
    """LA propiedad de honestidad del adapter: con un símbolo libre, Z3
    puede ELEGIR el valor que haga sat y el `pass` sería una mentira —
    "encontré ALGÚN mundo donde se cumple" disfrazado de "el candidato
    cumple"."""
    incompleto = {"quantity": 3, "observed": 0.5}  # falta `tolerance`

    with pytest.raises(VerificationProcessError, match="sin valor"):
        Z3RuleBackend().check(_rule_set(), incompleto)


def test_un_valor_de_sort_equivocado_es_error_de_proceso() -> None:
    """`quantity` está declarada Int: un float no se coacciona en silencio."""
    with pytest.raises(VerificationProcessError, match="quantity"):
        Z3RuleBackend().check(_rule_set(), {**SUBJECT_OK, "quantity": 2.5})


def test_un_float_no_finito_es_error_de_proceso() -> None:
    """Misma regla que `C()` en el anexo §2: NaN/Infinity fallan fuerte,
    jamás entran a un chequeo cuyo resultado nadie puede reproducir."""
    with pytest.raises(VerificationProcessError, match="finito"):
        Z3RuleBackend().check(_rule_set(), {**SUBJECT_OK, "observed": float("inf")})


# ── RuleVerifier: la Attestation que sale ───────────────────────────────


def test_el_rule_verifier_satisface_el_puerto_verifier() -> None:
    assert isinstance(_verifier(), Verifier)


def test_pass_emite_property_rule_al2_con_el_ancla_del_rule_set() -> None:
    """#103: la v1 con Z3 emite `property_rule` AL2 honesto (techo de la
    clase, freeze §4). El ancla ES el artefacto de reglas — su digest."""
    # Act
    attestation = _verifier().verify(_claim(SUBJECT_OK), CTX)

    # Assert
    assert isinstance(attestation, Attestation)
    assert attestation.verdict == "pass"
    assert attestation.verifier_class == "property_rule"
    assert attestation.level == "AL2"
    assert attestation.anchor_kind == "rule"
    assert attestation.anchor_digest == _rule_set().rule_digest


def test_la_evidencia_carga_rule_set_id_y_rule_digest() -> None:
    """Sin ellos la verificación no es reproducible: nadie sabría CONTRA QUÉ
    reglas se verificó (trust/11 §1.5, campos aditivos del ítem C3/M3)."""
    predicate = _verifier().verify(_claim(SUBJECT_OK), CTX).predicate

    assert isinstance(predicate, PropertyRulePredicate)
    assert predicate.backend == "z3"
    assert predicate.status == "sat"
    assert predicate.rule_set_id == "unit-rules@0.1.0"
    assert predicate.rule_digest == _rule_set().rule_digest


def test_fail_lleva_el_core_y_los_checks_a_la_evidencia() -> None:
    # Act
    attestation = _verifier().verify(_claim({**SUBJECT_OK, "observed": 5.0}), CTX)
    predicate = attestation.predicate

    # Assert
    assert attestation.verdict == "fail"
    assert isinstance(predicate, PropertyRulePredicate)
    assert predicate.status == "unsat"
    assert predicate.unsat_core == ("within_tolerance",)
    assert [c.name for c in predicate.properties if not c.passed] == [
        "within_tolerance"
    ]


def test_unknown_emite_inconclusive_con_razon_tipada() -> None:
    """Tri-estado (D4): la abstención es representable y se explica — jamás
    un `fail` por presupuesto agotado."""
    # Arrange
    dura = RuleSet.parse(
        b"; rule-set-id: dura@1\n"
        b"(declare-fun x () Int)\n(declare-fun y () Int)\n"
        b"(assert (! (= (* x x x) (+ (* y y y) 42)) :named cubica))\n"
    )

    # Act
    attestation = _verifier(rule_set=dura, backend=Z3RuleBackend(rlimit=1)).verify(
        _claim({"x": 0, "y": 0}), CTX
    )

    # Assert
    assert attestation.verdict == "inconclusive"
    assert attestation.inconclusive_reason == "budget_exhausted"


def test_el_binary_digest_pinnea_la_version_de_z3() -> None:
    """Replay: la constancia dice con QUÉ prover se corrió."""
    import z3

    esperado = hashlib.sha256(f"z3-{z3.get_version_string()}".encode()).hexdigest()
    assert Z3RuleBackend().binary_digest == esperado


def test_el_params_digest_cambia_con_el_rlimit() -> None:
    """El presupuesto es parte de la corrida: dos `unknown` con presupuestos
    distintos no son la misma evidencia."""
    assert (
        Z3RuleBackend(rlimit=1).params_digest != Z3RuleBackend(rlimit=2).params_digest
    )


def test_el_claim_ajeno_es_error_de_proceso() -> None:
    with pytest.raises(VerificationProcessError, match="RuleClaim"):
        _verifier().verify({"subject": {}}, CTX)


# ── La frontera de la prueba formal (diseño listo, v1 sin emisor) ────────


class _BackendConPrueba:
    """Doble del puerto que devuelve una prueba formal — la ruta
    cvc5→Alethe→Carcara que el puerto YA tipa y que ningún backend de la v1
    implementa."""

    name = "cvc5-falso"
    binary_digest = hashlib.sha256(b"cvc5-falso").hexdigest()
    params_digest = hashlib.sha256(b"cvc5-falso-params").hexdigest()
    params_digest_inputs: dict[str, object] = {}

    def check(self, rule_set: RuleSet, subject: dict[str, Any]) -> RuleResult:
        return RuleResult(
            holds=True,
            backend=self.name,
            verifier_class="formal_exact",
            status="unsat",
            proof=RuleProof(
                certificate_ref="sha256:" + "0" * 64,
                checker_id="carcara@1.0",
                checker_verdict="holds",
                proof_format="alethe",
            ),
        )


def test_el_puerto_tipa_la_salida_proof_aunque_la_v1_sea_z3_solo() -> None:
    """El diseño del puerto lleva la prueba desde el día 1 (#103) — que
    ningún backend de la v1 la produzca no es excusa para no tiparla."""
    assert isinstance(_BackendConPrueba(), RuleBackend)


def test_una_prueba_formal_no_se_emite_en_silencio_ni_se_infla() -> None:
    """Cero techos rotos: emitir `formal_exact` exige extender el predicate
    congelado (freeze §4-iii: `proof {certificate_ref, checker_id,
    checker_verdict}`) — ceremonia registrada, no un salto de clase que
    alguien note después. Y degradarla a AL2 en silencio escondería
    evidencia. Fail-loud nombrando la ceremonia."""
    verificador = _verifier(backend=_BackendConPrueba())

    with pytest.raises(VerificationProcessError, match="ceremonia"):
        verificador.verify(_claim(SUBJECT_OK), CTX)


# ── El artefacto real del dominio, verificado como dato distribuido ──────


def test_el_rule_set_del_dominio_carga_y_sus_reglas_estan_nombradas() -> None:
    """El conocimiento del dominio vive en `knowledge/`, versionado y con
    digest — el verificador es agnóstico (corrección #4 de trust/11)."""
    # Act
    rule_set = load_rule_set(
        REPO / "knowledge" / "islanding" / "rules" / "particion.smt2"
    )

    # Assert
    assert rule_set.rule_set_id.startswith("particion-rules@")
    assert len(rule_set.rule_names) >= 4
    assert all(rule_set.rule_names)


def test_una_particion_sana_pasa_el_rule_set_del_dominio() -> None:
    # Arrange
    rule_set = load_rule_set(
        REPO / "knowledge" / "islanding" / "rules" / "particion.smt2"
    )
    sano = {
        "n_islands": 2,
        "min_island_buses": 7,
        "islands_without_source": 0,
        "max_abs_imbalance_mw": 0.4,
        "imbalance_tolerance_mw": 1.0,
        "served_load_mw": 95.0,
        "total_load_mw": 100.0,
        "min_served_fraction": 0.9,
    }

    # Act
    result = Z3RuleBackend().check(rule_set, sano)

    # Assert
    assert result.status == "sat"
    assert all(c.passed for c in result.checks)


def test_una_isla_sin_fuente_rompe_la_regla_que_la_nombra() -> None:
    """El caso que el dominio existe para atrapar, con el nombre de la regla
    a la vista."""
    # Arrange
    rule_set = load_rule_set(
        REPO / "knowledge" / "islanding" / "rules" / "particion.smt2"
    )
    enferma = {
        "n_islands": 2,
        "min_island_buses": 7,
        "islands_without_source": 1,
        "max_abs_imbalance_mw": 0.4,
        "imbalance_tolerance_mw": 1.0,
        "served_load_mw": 95.0,
        "total_load_mw": 100.0,
        "min_served_fraction": 0.9,
    }

    # Act
    result = Z3RuleBackend().check(rule_set, enferma)

    # Assert
    assert result.holds is False
    assert [c.name for c in result.checks if not c.passed] == ["source_per_island"]
