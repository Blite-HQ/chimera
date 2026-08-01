"""GroundTruthVerifier — el adapter `ground_truth` genérico (ancla
`dataset`). Vocabulario §4 / docs/specs/generalidad-retos.md §Contrato-3/4;
receta 11 §2 (dos patas C3 por construcción: este verificador contrasta
contra series CONGELADAS, grupo de independencia distinto del recompute
vivo de `ExactDiagonalizationVerifier`).

Genérico por diseño (sirve también al reto 2 más adelante): el corpus
usado aquí es el de C3 (`tfim-corpus/...`) solo como instancia de prueba —
el verificador mismo no sabe nada de TFIM, únicamente de labels y valores.
"""

from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError

from blite.certificate.canonical import JSONValue, canonicalize
from blite.verification.attestation import Attestation
from blite.verification.context import InvocationContext
from blite.verification.evidence import GroundTruthPredicate
from blite.verification.exact_solver import VerificationProcessError
from blite.verification.ground_truth import (
    GroundTruthClaim,
    GroundTruthRecord,
    GroundTruthVerifier,
    build_ground_truth_record,
)
from blite.verification.verifier import Verifier

CTX = InvocationContext(
    run_id="run:test", actor_id="service:runtime", domain_id="dom:test"
)

_DATASET_ID = "tfim-corpus/chain-n8-h10@v1"
_CASE_ID = "chain-n8-h10"
_SOURCE_DIGEST = "s" * 64


def _record(
    expected: dict[str, float],
    tolerance: float = 0.05,
    dataset_id: str = _DATASET_ID,
    case_id: str = _CASE_ID,
    source_digest: str = _SOURCE_DIGEST,
) -> GroundTruthRecord:
    """Construye un record con digest embebido self-consistente — MISMA
    vista/algoritmo que `ground_truth._record_digest` (no se importa: el
    test recomputa por su cuenta, como la propia doctrina del corpus
    exige)."""
    view: dict[str, JSONValue] = {
        "dataset_id": dataset_id,
        "case_id": case_id,
        "expected": dict(expected),
        "tolerance": tolerance,
        "source_digest": source_digest,
    }
    digest = hashlib.sha256(canonicalize(view)).hexdigest()
    return GroundTruthRecord(
        dataset_id=dataset_id,
        case_id=case_id,
        expected=expected,
        tolerance=tolerance,
        source_digest=source_digest,
        embedded_digest=digest,
    )


def make_verifier(record: GroundTruthRecord) -> GroundTruthVerifier:
    return GroundTruthVerifier(
        verifier_id="verifier:ground-truth-tfim",
        independence_group="leg-dataset-ed",
        record=record,
    )


def claim_for(observed: dict[str, float], case_id: str = _CASE_ID) -> GroundTruthClaim:
    return GroundTruthClaim(
        case_id=case_id,
        observed=observed,
        canonical_statement="las series observadas concuerdan con el corpus congelado",
        scope={"case_id": case_id},
    )


def predicate_of(att: Attestation) -> GroundTruthPredicate:
    """Narrowing del union ClassPredicate a la evidencia ground_truth."""
    assert isinstance(att.predicate, GroundTruthPredicate)
    return att.predicate


# Series de referencia reales (recomputadas del corpus C3, N=8, h/J=1.0,
# t=1.0 — mismos números de oro de test_exact_diagonalization.py) — usarlas
# aquí evita inventar constantes arbitrarias sin anclaje físico.
_EXPECTED_N8_H10: dict[str, float] = {
    "Z0": -0.033021664,
    "ZZ0": 0.434250562,
}


class TestVeredictoPass:
    def test_observado_igual_al_esperado_pasa(self) -> None:
        record = _record(_EXPECTED_N8_H10)
        att = make_verifier(record).verify(claim_for(dict(_EXPECTED_N8_H10)), CTX)

        assert att.verdict == "pass"
        assert att.level == "AL3"
        assert att.anchor_digest == record.source_digest
        pred = predicate_of(att)
        assert pred.match is True
        assert pred.tolerance == 0.05
        assert pred.dataset_id == _DATASET_ID
        assert pred.case_id == _CASE_ID


class TestVeredictoFail:
    def test_observado_fuera_de_tolerancia_falla(self) -> None:
        record = _record(_EXPECTED_N8_H10)
        observed = dict(_EXPECTED_N8_H10)
        observed["ZZ0"] = 0.9  # excede 5% de la escala L∞ del grupo

        att = make_verifier(record).verify(claim_for(observed), CTX)

        assert att.verdict == "fail"
        assert predicate_of(att).match is False


class TestAutoConsistenciaDelRegistro:
    """Auto-consistencia del REGISTRO es un error de PROCESO, no un
    veredicto (docstring del módulo) — un `embedded_digest` que no coincide
    con el recomputado sobre los campos propios del record (incluido
    `source_digest`) jamás produce un `fail` silencioso que acuse al
    candidato. Esto es record-integrity, DISTINTO de detectar tampering del
    artefacto fuente (eso lo cubre `source_digest`, Part 1 del dispatcher —
    ver `TestAnclaEsElSourceDigest` para la distinción con `anchor_digest`)."""

    def test_digest_embebido_manipulado_levanta_process_error(self) -> None:
        record = _record({"Z0": 0.5})
        tampered = record.model_copy(update={"embedded_digest": "0" * 64})

        with pytest.raises(VerificationProcessError):
            make_verifier(tampered).verify(claim_for({"Z0": 0.5}), CTX)

    def test_source_digest_reconstruido_sin_recomputar_embedded_levanta(
        self,
    ) -> None:
        """Reconstruir el record con OTRO `source_digest` (p. ej. un
        artefacto fuente distinto) sin recomputar `embedded_digest` también
        es una inconsistencia del registro — `source_digest` entra a la
        vista que `_record_digest` hashea (docstring de `_record_digest`)."""
        record = _record({"Z0": 0.5}, source_digest="a" * 64)
        drifted = record.model_copy(update={"source_digest": "b" * 64})

        with pytest.raises(VerificationProcessError):
            make_verifier(drifted).verify(claim_for({"Z0": 0.5}), CTX)


class TestAnclaEsElSourceDigest:
    """El `anchor_digest` de la Attestation es `record.source_digest` (el
    artefacto fuente congelado), NUNCA `record.embedded_digest` (el chequeo
    de auto-consistencia del registro en memoria) — el fix del defecto
    circular (Part 0): la Attestation debe bindear a los bytes exactos del
    corpus, no a un dato que el propio código que construye el record podría
    reconstruir de cualquier forma internamente consistente."""

    def test_anchor_digest_es_source_digest_no_embedded_digest(self) -> None:
        record = _record({"Z0": 0.5}, source_digest="c" * 64)
        assert record.source_digest != record.embedded_digest

        att = make_verifier(record).verify(claim_for({"Z0": 0.5}), CTX)

        assert att.anchor_digest == record.source_digest
        assert att.anchor_digest != record.embedded_digest


class TestConjuntoDeLabels:
    def test_label_faltante_en_observed_levanta_process_error(self) -> None:
        record = _record({"Z0": 0.5, "ZZ0": 0.4})

        with pytest.raises(VerificationProcessError):
            make_verifier(record).verify(claim_for({"Z0": 0.5}), CTX)

    def test_label_extra_en_observed_levanta_process_error(self) -> None:
        record = _record({"Z0": 0.5})

        with pytest.raises(VerificationProcessError):
            make_verifier(record).verify(
                claim_for({"Z0": 0.5, "extra": 0.1}), CTX
            )


class TestFormaDelPredicate:
    def test_digests_tienen_forma_sha256(self) -> None:
        record = _record({"Z0": 0.672315358})
        att = make_verifier(record).verify(claim_for({"Z0": 0.672315358}), CTX)

        pred = predicate_of(att)
        assert len(pred.expected_digest) == 64
        assert len(pred.observed_digest) == 64
        int(pred.expected_digest, 16)  # es hex válido
        int(pred.observed_digest, 16)


class TestAtributosDelPuertoYProtocolo:
    def test_atributos(self) -> None:
        verifier = make_verifier(_record({"Z0": 0.5}))

        assert verifier.verifier_class == "ground_truth"
        assert verifier.anchor_kind == "dataset"
        assert verifier.determinism == "deterministic"
        assert isinstance(verifier, Verifier)


class TestClaimDeTipoIncorrecto:
    def test_claim_no_groundtruth_levanta_process_error(self) -> None:
        with pytest.raises(VerificationProcessError):
            make_verifier(_record({"Z0": 0.5})).verify(object(), CTX)


class TestNivelAL3:
    def test_pass_y_fail_quedan_en_al3(self) -> None:
        record = _record(_EXPECTED_N8_H10)

        passing = make_verifier(record).verify(
            claim_for(dict(_EXPECTED_N8_H10)), CTX
        )
        failing_observed = dict(_EXPECTED_N8_H10)
        failing_observed["ZZ0"] = 0.9
        failing = make_verifier(record).verify(claim_for(failing_observed), CTX)

        assert passing.level == "AL3"
        assert failing.level == "AL3"


class TestDeterminismo:
    def test_dos_corridas_identicas_salvo_issued_at(self) -> None:
        record = _record(_EXPECTED_N8_H10)
        verifier = make_verifier(record)
        claim = claim_for(dict(_EXPECTED_N8_H10))

        a = verifier.verify(claim, CTX).model_dump(exclude={"issued_at"})
        b = verifier.verify(claim, CTX).model_dump(exclude={"issued_at"})

        assert a == b


class TestClaimDigest:
    def test_sigue_la_convencion_del_anexo(self) -> None:
        record = _record(_EXPECTED_N8_H10)
        claim = claim_for(dict(_EXPECTED_N8_H10))
        att = make_verifier(record).verify(claim, CTX)

        view: dict[str, JSONValue] = {
            "canonical_statement": claim.canonical_statement,
            "scope": claim.scope,
        }
        expected = hashlib.sha256(
            b"blite/claim/v1\n" + canonicalize(view)
        ).hexdigest()
        assert att.claim_digest == expected


class TestValidacionDeEntrada:
    def test_record_extra_field_levanta(self) -> None:
        with pytest.raises(ValidationError):
            GroundTruthRecord.model_validate(
                {
                    "dataset_id": _DATASET_ID,
                    "case_id": _CASE_ID,
                    "expected": {"Z0": 0.5},
                    "tolerance": 0.05,
                    "source_digest": "0" * 64,
                    "embedded_digest": "0" * 64,
                    "campo_inesperado": True,
                }
            )

    def test_claim_extra_field_levanta(self) -> None:
        with pytest.raises(ValidationError):
            GroundTruthClaim.model_validate(
                {
                    "case_id": _CASE_ID,
                    "observed": {"Z0": 0.5},
                    "canonical_statement": "x",
                    "scope": {},
                    "campo_inesperado": True,
                }
            )


class TestBuildGroundTruthRecord:
    """`build_ground_truth_record` computa `embedded_digest` con el MISMO
    algoritmo que `verify()` recomputa — un caller externo (el dispatcher de
    `chimera_api.instance_verifiers`) nunca lo reimplementa a mano."""

    def test_record_construido_pasa_su_propia_verificacion(self) -> None:
        record = build_ground_truth_record(
            dataset_id=_DATASET_ID,
            case_id=_CASE_ID,
            expected=dict(_EXPECTED_N8_H10),
            tolerance=0.05,
            source_digest="d" * 64,
        )

        att = make_verifier(record).verify(claim_for(dict(_EXPECTED_N8_H10)), CTX)

        assert att.verdict == "pass"
        assert att.anchor_digest == "d" * 64

    def test_dos_construcciones_iguales_dan_el_mismo_embedded_digest(self) -> None:
        a = build_ground_truth_record(
            dataset_id=_DATASET_ID,
            case_id=_CASE_ID,
            expected=dict(_EXPECTED_N8_H10),
            tolerance=0.05,
            source_digest="e" * 64,
        )
        b = build_ground_truth_record(
            dataset_id=_DATASET_ID,
            case_id=_CASE_ID,
            expected=dict(_EXPECTED_N8_H10),
            tolerance=0.05,
            source_digest="e" * 64,
        )

        assert a.embedded_digest == b.embedded_digest
