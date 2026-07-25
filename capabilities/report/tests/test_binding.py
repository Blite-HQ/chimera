"""TDD: C3 — binding cifra→certificado (docs/specs/informe-derivado.md
§Binding cifra→certificado). `CertificateBinding`/`build_binding` as
first-class values, `compile_report`'s fail-closed extension to
attestations/deliverables (not just conclusions), and the machine-readable
verification annex (`build_verification_annex`)."""

from __future__ import annotations

import pytest

from blite.certificate.canonical import JSONValue, canonicalize
from blite.certificate.predicate import Conclusion, Deliverable
from blite_cap_report.annex import build_verification_annex
from blite_cap_report.binding import Citation, build_binding
from blite_cap_report.pdf import (
    CompiledReport,
    UncitableFigureError,
    compile_report,
    template_digest,
)

_TEMPLATE_DIGEST = template_digest()


def _conclusion(claim_digest: str) -> Conclusion:
    return Conclusion(
        claim_digest=claim_digest,
        canonical_statement="r >= p (example claim)",
        scope={"instance": "example"},
        verdict="verified",
        level="AL2",
    )


class TestBuildBindingResolvesEachSource:
    def test_resolves_a_conclusion_by_claim_digest(self) -> None:
        # Arrange
        claim_hex = "a" * 64
        binding = build_binding(cert_id="cert-1", conclusions=(_conclusion(claim_hex),))

        # Act
        citation = binding.resolve("sha256:" + claim_hex)

        # Assert
        assert citation == Citation(
            digest=claim_hex, kind="conclusion", cert_id="cert-1"
        )

    def test_resolves_an_attestation_by_claim_digest(self) -> None:
        # Arrange — raw predicate dict shape (scripts/gen-example-bundle.py).
        claim_hex = "b" * 64
        binding = build_binding(
            cert_id="cert-1",
            attestations=({"verifier_id": "ortools-cpsat", "claim_digest": claim_hex},),
        )

        # Act
        citation = binding.resolve(claim_hex)

        # Assert
        assert citation is not None
        assert citation.kind == "attestation"
        assert citation.cert_id == "cert-1"

    def test_resolves_a_deliverable_by_digest(self) -> None:
        # Arrange
        digest_hex = "c" * 64
        deliverable = Deliverable(artifact_ref="partition.json", digest=digest_hex)
        binding = build_binding(cert_id="cert-1", deliverables=(deliverable,))

        # Act
        citation = binding.resolve("sha256:" + digest_hex)

        # Assert
        assert citation is not None
        assert citation.kind == "deliverable"
        assert citation.cert_id == "cert-1"


class TestNormalization:
    def test_normalizes_the_sha256_prefix_on_both_the_stored_and_looked_up_digest(
        self,
    ) -> None:
        # Arrange — the conclusion is registered WITH the prefix.
        claim_hex = "d" * 64
        conclusion = Conclusion(
            claim_digest="sha256:" + claim_hex,
            canonical_statement="r >= p",
            scope={},
            verdict="verified",
            level="AL1",
        )
        binding = build_binding(cert_id="cert-1", conclusions=(conclusion,))

        # Act / Assert — resolves whether looked up bare or prefixed.
        assert binding.resolve(claim_hex) is not None
        assert binding.resolve("sha256:" + claim_hex) is not None

    def test_resolvable_exposes_the_normalized_digest_set(self) -> None:
        # Arrange
        claim_hex = "1" * 64
        binding = build_binding(cert_id="cert-1", conclusions=(_conclusion(claim_hex),))

        # Act / Assert
        assert binding.resolvable == frozenset({claim_hex})


class TestAbsentDigest:
    def test_a_digest_not_registered_anywhere_resolves_to_none(self) -> None:
        # Arrange
        binding = build_binding(cert_id="cert-1", conclusions=(_conclusion("e" * 64),))

        # Act / Assert
        assert binding.resolve("sha256:" + "f" * 64) is None


class TestCompileReportBindingExtension:
    def test_a_cifra_resolving_only_to_a_deliverable_compiles(self) -> None:
        # Arrange — before C3's extension, only conclusions were resolvable;
        # this digest resolves EXCLUSIVELY via a deliverable.
        digest_hex = "2" * 64
        deliverable = Deliverable(artifact_ref="partition.json", digest=digest_hex)

        # Act
        compiled = compile_report(
            template_digest=_TEMPLATE_DIGEST,
            figure_digests=(),
            cifra_digests=("sha256:" + digest_hex,),
            certificate_conclusions=(),
            certificate_attestations=(),
            certificate_deliverables=(deliverable,),
            cert_id="cert-xyz",
        )

        # Assert
        assert compiled.digest

    def test_a_cifra_resolving_to_nothing_still_fails_closed(self) -> None:
        # Act / Assert
        with pytest.raises(UncitableFigureError):
            compile_report(
                template_digest=_TEMPLATE_DIGEST,
                figure_digests=(),
                cifra_digests=("sha256:" + "3" * 64,),
                certificate_conclusions=(),
                certificate_attestations=(),
                certificate_deliverables=(),
                cert_id="cert-xyz",
            )

    def test_the_conclusions_only_backward_compatible_signature_still_works(
        self,
    ) -> None:
        # Arrange — C2's original call shape, no attestations/deliverables/cert_id.
        claim_hex = "4" * 64

        # Act
        compiled = compile_report(
            template_digest=_TEMPLATE_DIGEST,
            figure_digests=("sha256:" + claim_hex,),
            cifra_digests=(),
            certificate_conclusions=(_conclusion(claim_hex),),
        )

        # Assert
        assert compiled.digest

    def test_two_compiles_with_the_same_full_binding_are_byte_identical(self) -> None:
        # Arrange — byte-reproducibility must survive the C3 extension.
        digest_hex = "5" * 64
        deliverable = Deliverable(artifact_ref="d.json", digest=digest_hex)

        def _compile() -> CompiledReport:
            return compile_report(
                template_digest=_TEMPLATE_DIGEST,
                figure_digests=(),
                cifra_digests=("sha256:" + digest_hex,),
                certificate_conclusions=(),
                certificate_attestations=(),
                certificate_deliverables=(deliverable,),
                cert_id="cert-xyz",
            )

        # Act
        first = _compile()
        second = _compile()

        # Assert
        assert first.digest == second.digest
        assert first.pdf_bytes == second.pdf_bytes

    def test_a_different_cert_id_changes_the_compiled_pdf(self) -> None:
        # Arrange — proves cert_id actually reaches the rendered footer/annex
        # (without parsing the PDF): a different cert_id must yield different
        # bytes for the SAME resolved binding.
        digest_hex = "6" * 64
        deliverable = Deliverable(artifact_ref="d.json", digest=digest_hex)

        def _compile(cert_id: str) -> CompiledReport:
            return compile_report(
                template_digest=_TEMPLATE_DIGEST,
                figure_digests=(),
                cifra_digests=("sha256:" + digest_hex,),
                certificate_conclusions=(),
                certificate_attestations=(),
                certificate_deliverables=(deliverable,),
                cert_id=cert_id,
            )

        # Act
        first = _compile("cert-a")
        second = _compile("cert-b")

        # Assert
        assert first.digest != second.digest


class TestBuildVerificationAnnex:
    def test_enumerates_template_figures_cifras_and_the_final_pdf(self) -> None:
        # Arrange
        binding = build_binding(
            cert_id="cert-1",
            deliverables=(Deliverable(artifact_ref="d.json", digest="7" * 64),),
        )

        # Act
        annex = build_verification_annex(
            template_digest=_TEMPLATE_DIGEST,
            figure_digests=("sha256:" + "8" * 64,),
            cifra_digests=("sha256:" + "7" * 64,),
            pdf_digest="sha256:" + "9" * 64,
            binding=binding,
        )
        payload = canonicalize(annex)

        # Assert — every artifact_ref shows up in the canonicalized payload.
        for ref in (b"template", b"figure:0", b"cifra:0", b"pdf"):
            assert ref in payload

    def test_cert_resolves_when_bound_and_is_null_otherwise(self) -> None:
        # Arrange
        binding = build_binding(
            cert_id="cert-1",
            deliverables=(Deliverable(artifact_ref="d.json", digest="7" * 64),),
        )

        # Act
        annex = build_verification_annex(
            template_digest=_TEMPLATE_DIGEST,
            figure_digests=(),
            cifra_digests=("sha256:" + "7" * 64,),
            pdf_digest="sha256:" + "9" * 64,
            binding=binding,
        )
        payload = canonicalize(annex)

        # Assert — the bound cifra carries "cert-1"; the PDF's own digest was
        # never registered in the binding, so it stays null.
        assert b'"cert":"cert-1"' in payload
        assert b'"cert":null' in payload

    def test_is_deterministic_and_canonicalizable(self) -> None:
        # Arrange
        def _annex() -> dict[str, JSONValue]:
            return build_verification_annex(
                template_digest=_TEMPLATE_DIGEST,
                figure_digests=("sha256:" + "8" * 64,),
                cifra_digests=(),
                pdf_digest="sha256:" + "9" * 64,
                binding=None,
            )

        # Act
        first = _annex()
        second = _annex()

        # Assert
        assert canonicalize(first) == canonicalize(second)
