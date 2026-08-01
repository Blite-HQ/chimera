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
)
from blite.verification.verifier import Verifier

CTX = InvocationContext(
    run_id="run:test", actor_id="service:runtime", domain_id="dom:test"
)

_DATASET_ID = "tfim-corpus/chain-n8-h10@v1"
_CASE_ID = "chain-n8-h10"


def _record(
    expected: dict[str, float],
    tolerance: float = 0.05,
    dataset_id: str = _DATASET_ID,
    case_id: str = _CASE_ID,
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
    }
    digest = hashlib.sha256(canonicalize(view)).hexdigest()
    return GroundTruthRecord(
        dataset_id=dataset_id,
        case_id=case_id,
        expected=expected,
        tolerance=tolerance,
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
        assert att.anchor_digest == record.embedded_digest
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


class TestAnclaEnvenenada:
    """Auto-consistencia del ancla es un error de PROCESO, no un veredicto
    (docstring del módulo) — un digest embebido manipulado jamás produce un
    `fail` silencioso que acuse al candidato."""

    def test_digest_embebido_manipulado_levanta_process_error(self) -> None:
        record = _record({"Z0": 0.5})
        tampered = record.model_copy(update={"embedded_digest": "0" * 64})

        with pytest.raises(VerificationProcessError):
            make_verifier(tampered).verify(claim_for({"Z0": 0.5}), CTX)


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
