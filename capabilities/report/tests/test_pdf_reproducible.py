"""TDD: la regla dura de C2 (informe-derivado.md §b) — el PDF final es una
`DerivationProvenance` byte-reproducible, y toda cifra/figura citada DEBE
resolver contra el certificado cuando uno se aporta (binding fail-closed,
§Binding cifra→certificado)."""

from __future__ import annotations

from blite.certificate.predicate import Conclusion
from blite_cap_report.pdf import (
    UncitableFigureError,
    compile_report,
    template_digest,
)

_TEMPLATE_DIGEST = template_digest()


class TestByteReproducibility:
    def test_two_compiles_of_same_inputs_are_byte_identical(self) -> None:
        # Arrange
        figure_digests = ("sha256:" + "b" * 64,)
        cifra_digests = ("sha256:" + "c" * 64,)

        # Act
        first = compile_report(
            template_digest=_TEMPLATE_DIGEST,
            figure_digests=figure_digests,
            cifra_digests=cifra_digests,
        )
        second = compile_report(
            template_digest=_TEMPLATE_DIGEST,
            figure_digests=figure_digests,
            cifra_digests=cifra_digests,
        )

        # Assert
        assert first.digest == second.digest
        assert first.pdf_bytes == second.pdf_bytes


class TestDigestChangesWithInputs:
    def test_different_digests_yield_a_different_pdf(self) -> None:
        # Arrange / Act
        base = compile_report(
            template_digest=_TEMPLATE_DIGEST,
            figure_digests=("sha256:" + "b" * 64,),
            cifra_digests=(),
        )
        changed = compile_report(
            template_digest=_TEMPLATE_DIGEST,
            figure_digests=("sha256:" + "f" * 64,),
            cifra_digests=(),
        )

        # Assert — the annex table depends on the digests, so the PDF differs.
        assert base.digest != changed.digest


class TestPageBudget:
    def test_pdf_is_within_the_eight_page_budget(self) -> None:
        # Act
        compiled = compile_report(
            template_digest=_TEMPLATE_DIGEST,
            figure_digests=("sha256:" + "b" * 64,),
            cifra_digests=("sha256:" + "c" * 64,),
        )

        # Assert
        assert compiled.page_count <= 8
        assert compiled.page_count >= 1


class TestProvenanceShape:
    def test_provenance_capability_is_compile_pdf_and_inputs_carry_all_digests(
        self,
    ) -> None:
        # Arrange
        figure_digest = "sha256:" + "b" * 64
        cifra_digest = "sha256:" + "c" * 64

        # Act
        compiled = compile_report(
            template_digest=_TEMPLATE_DIGEST,
            figure_digests=(figure_digest,),
            cifra_digests=(cifra_digest,),
        )

        # Assert
        recipe = compiled.provenance.recipe
        assert recipe["capability"] == "blite.report.compile_pdf"
        refs = {entry["ref"]: entry["digest"] for entry in compiled.provenance.inputs}
        assert refs["template"] == _TEMPLATE_DIGEST
        assert refs["figure:0"] == figure_digest
        assert refs["cifra:0"] == cifra_digest


class TestBindingFailClosed:
    def test_binding_is_enforced_only_when_a_certificate_is_provided(self) -> None:
        # Arrange / Act — no certificate at all: compiles even though the
        # digests do not resolve anywhere (recompilation/determinism mode).
        compiled = compile_report(
            template_digest=_TEMPLATE_DIGEST,
            figure_digests=("sha256:" + "b" * 64,),
            cifra_digests=(),
            certificate_conclusions=None,
        )
        assert compiled.digest

        # Act / Assert — an EMPTY certificate resolves nothing: fail-closed.
        try:
            compile_report(
                template_digest=_TEMPLATE_DIGEST,
                figure_digests=("sha256:" + "b" * 64,),
                cifra_digests=(),
                certificate_conclusions=(),
            )
        except UncitableFigureError:
            pass
        else:
            raise AssertionError("expected UncitableFigureError")

    def test_a_resolving_certificate_compiles(self) -> None:
        # Arrange — claim_digest is bare hex (no prefix); figure_digests
        # carry the "sha256:" prefix — `_normalize` must reconcile both.
        claim_hex = "d" * 64
        conclusion = Conclusion(
            claim_digest=claim_hex,
            canonical_statement="r >= p (example claim)",
            scope={"instance": "example"},
            verdict="verified",
            level="AL2",
        )

        # Act
        compiled = compile_report(
            template_digest=_TEMPLATE_DIGEST,
            figure_digests=("sha256:" + claim_hex,),
            cifra_digests=(),
            certificate_conclusions=(conclusion,),
        )

        # Assert
        assert compiled.digest
        assert compiled.page_count <= 8
