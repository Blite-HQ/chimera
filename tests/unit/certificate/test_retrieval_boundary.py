"""Frontera freeze §7 nota 10 — contenido recuperado jamás es evidencia.

Guard puro (`assert_retrieved_not_in_evidence`) + la marca tipada
(`RetrievedRef`), ejercitados SIN infraestructura de run. La integración con
un run/bundle real vive en `test_assemble.py::TestRetrievalBoundary` — ambos
niveles son de primera clase (P12 tramo 1, handoff P-rt)."""

from __future__ import annotations

import hashlib

import pytest

from blite.certificate.predicate import Assumption, Conclusion
from blite.certificate.retrieval_boundary import (
    RetrievedContentInEvidenceError,
    RetrievedRef,
    assert_retrieved_not_in_evidence,
)

_RETRIEVED_DIGEST = hashlib.sha256(b"kb-fragment").hexdigest()
_EXECUTION_DIGEST = hashlib.sha256(b"execution-claim").hexdigest()


def _retrieved() -> RetrievedRef:
    return RetrievedRef(name="doc:kb-42", digest=_RETRIEVED_DIGEST)


def _conclusion(digest: str) -> Conclusion:
    return Conclusion(
        claim_digest=digest,
        canonical_statement="stmt",
        scope={"k": "v"},
        verdict="verified",
        level="AL2",
    )


def _attestation(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "claim_digest": _EXECUTION_DIGEST,
        "anchor_digest": "anchor-x",
        "evidence_digests": (),
    }
    base.update(overrides)
    return base


class TestRetrievedRefHappyPath:
    """El camino feliz: recuperado → assumptions, y nada más."""

    def test_as_assumption_is_the_only_typed_conversion(self) -> None:
        # Arrange
        ref = _retrieved()

        # Act
        assumption = ref.as_assumption("un fragmento citado, no evidencia")

        # Assert
        assert isinstance(assumption, Assumption)
        assert assumption.ref is not None
        assert assumption.ref.digest == _RETRIEVED_DIGEST
        assert assumption.ref.name == "doc:kb-42"

    def test_has_no_conversion_towards_conclusion_or_attestation(self) -> None:
        ref = _retrieved()

        assert not hasattr(ref, "as_conclusion")
        assert not hasattr(ref, "as_attestation")


class TestGuardHappyPath:
    def test_a_retrieved_digest_kept_out_of_evidence_passes(self) -> None:
        # Arrange — el digest recuperado no coincide con ningún claim ni
        # attestation: exactamente el camino feliz (va solo a assumptions).
        # Act / Assert — no debe lanzar.
        assert_retrieved_not_in_evidence(
            retrieved_refs=(_retrieved(),),
            conclusions=(_conclusion(_EXECUTION_DIGEST),),
            attestations=(_attestation(),),
        )

    def test_no_retrieved_refs_is_a_no_op_default(self) -> None:
        # Arrange — sin refs declarados (el default de todo caller hoy, sin
        # productor de retrieval), incluso un digest compartido no dispara.
        # Act / Assert
        assert_retrieved_not_in_evidence(
            retrieved_refs=(),
            conclusions=(_conclusion(_RETRIEVED_DIGEST),),
            attestations=(_attestation(claim_digest=_RETRIEVED_DIGEST),),
        )


class TestGuardViolation:
    """El camino que revienta: recuperado → conclusions o Attestation."""

    def test_retrieved_digest_as_a_conclusion_claim_digest_explodes(self) -> None:
        with pytest.raises(RetrievedContentInEvidenceError, match="freeze §7"):
            assert_retrieved_not_in_evidence(
                retrieved_refs=(_retrieved(),),
                conclusions=(_conclusion(_RETRIEVED_DIGEST),),
                attestations=(),
            )

    def test_retrieved_digest_as_an_attestation_claim_digest_explodes(self) -> None:
        with pytest.raises(RetrievedContentInEvidenceError, match="Attestation"):
            assert_retrieved_not_in_evidence(
                retrieved_refs=(_retrieved(),),
                conclusions=(),
                attestations=(_attestation(claim_digest=_RETRIEVED_DIGEST),),
            )

    def test_retrieved_digest_inside_evidence_digests_explodes(self) -> None:
        with pytest.raises(RetrievedContentInEvidenceError):
            assert_retrieved_not_in_evidence(
                retrieved_refs=(_retrieved(),),
                conclusions=(),
                attestations=(_attestation(evidence_digests=(_RETRIEVED_DIGEST,)),),
            )

    def test_retrieved_digest_as_anchor_digest_explodes(self) -> None:
        with pytest.raises(RetrievedContentInEvidenceError):
            assert_retrieved_not_in_evidence(
                retrieved_refs=(_retrieved(),),
                conclusions=(),
                attestations=(_attestation(anchor_digest=_RETRIEVED_DIGEST),),
            )

    def test_error_message_names_the_offending_digest(self) -> None:
        with pytest.raises(RetrievedContentInEvidenceError, match=_RETRIEVED_DIGEST):
            assert_retrieved_not_in_evidence(
                retrieved_refs=(_retrieved(),),
                conclusions=(_conclusion(_RETRIEVED_DIGEST),),
                attestations=(),
            )
