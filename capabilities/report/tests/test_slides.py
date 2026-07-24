"""TDD: C3b — the slide deck is another derivation (informe-derivado.md §b,
extended to a presentation surface). Same byte-reproducibility property as
`compile_report`, same recipe shape (`recipe.capability =
"blite.report.compile_slides"`), same fail-closed binding contract imported
from `binding.py` (never reimplemented)."""

from __future__ import annotations

import pytest

from blite.certificate.predicate import Conclusion
from blite_cap_report.binding import UncitableFigureError
from blite_cap_report.slides import compile_slides, slides_template_digest

_TEMPLATE_DIGEST = slides_template_digest()


class TestByteReproducibility:
    def test_two_compiles_of_same_inputs_are_byte_identical(self) -> None:
        # Arrange
        figure_digests = ("sha256:" + "b" * 64,)
        cifra_digests = ("sha256:" + "c" * 64,)

        # Act
        first = compile_slides(
            template_digest=_TEMPLATE_DIGEST,
            figure_digests=figure_digests,
            cifra_digests=cifra_digests,
        )
        second = compile_slides(
            template_digest=_TEMPLATE_DIGEST,
            figure_digests=figure_digests,
            cifra_digests=cifra_digests,
        )

        # Assert
        assert first.digest == second.digest
        assert first.pdf_bytes == second.pdf_bytes


class TestProvenanceShape:
    def test_provenance_capability_is_compile_slides_and_inputs_carry_all_digests(
        self,
    ) -> None:
        # Arrange
        figure_digest = "sha256:" + "b" * 64
        cifra_digest = "sha256:" + "c" * 64

        # Act
        compiled = compile_slides(
            template_digest=_TEMPLATE_DIGEST,
            figure_digests=(figure_digest,),
            cifra_digests=(cifra_digest,),
        )

        # Assert
        recipe = compiled.provenance.recipe
        assert recipe["capability"] == "blite.report.compile_slides"
        refs = {entry["ref"]: entry["digest"] for entry in compiled.provenance.inputs}
        assert refs["template"] == _TEMPLATE_DIGEST
        assert refs["figure:0"] == figure_digest
        assert refs["cifra:0"] == cifra_digest


class TestBindingFailClosed:
    def test_binding_is_enforced_only_when_a_certificate_is_provided(self) -> None:
        # Arrange / Act — no certificate at all: compiles even though the
        # digests do not resolve anywhere (recompilation/determinism mode).
        compiled = compile_slides(
            template_digest=_TEMPLATE_DIGEST,
            figure_digests=("sha256:" + "b" * 64,),
            cifra_digests=(),
            certificate_conclusions=None,
        )
        assert compiled.digest

        # Act / Assert — an EMPTY certificate resolves nothing: fail-closed.
        with pytest.raises(UncitableFigureError):
            compile_slides(
                template_digest=_TEMPLATE_DIGEST,
                figure_digests=("sha256:" + "b" * 64,),
                cifra_digests=(),
                certificate_conclusions=(),
            )

    def test_a_cifra_that_does_not_resolve_fails_closed(self) -> None:
        # Arrange — a certificate IS provided, but the cited cifra is not in
        # it — same C3 rule as `compile_report`'s binding contract.
        conclusion = Conclusion(
            claim_digest="a" * 64,
            canonical_statement="r >= p (example claim)",
            scope={"instance": "example"},
            verdict="verified",
            level="AL2",
        )
        unresolvable_digest = "sha256:" + "0" * 64

        # Act / Assert
        with pytest.raises(UncitableFigureError):
            compile_slides(
                template_digest=_TEMPLATE_DIGEST,
                figure_digests=(),
                cifra_digests=(unresolvable_digest,),
                certificate_conclusions=(conclusion,),
            )

    def test_a_resolving_certificate_compiles(self) -> None:
        # Arrange — claim_digest is bare hex (no prefix); figure_digests
        # carry the "sha256:" prefix — normalization must reconcile both.
        claim_hex = "d" * 64
        conclusion = Conclusion(
            claim_digest=claim_hex,
            canonical_statement="r >= p (example claim)",
            scope={"instance": "example"},
            verdict="verified",
            level="AL2",
        )

        # Act
        compiled = compile_slides(
            template_digest=_TEMPLATE_DIGEST,
            figure_digests=("sha256:" + claim_hex,),
            cifra_digests=(),
            certificate_conclusions=(conclusion,),
        )

        # Assert
        assert compiled.digest
        assert compiled.slide_count >= 1


class TestSlideCount:
    def test_slide_count_is_at_least_one_with_no_figures_or_cifras(self) -> None:
        # Act
        compiled = compile_slides(
            template_digest=_TEMPLATE_DIGEST,
            figure_digests=(),
            cifra_digests=(),
        )

        # Assert — title slide + summary slide, at minimum.
        assert compiled.slide_count >= 1

    def test_slide_count_grows_by_one_per_cited_figure(self) -> None:
        # Arrange
        from blite_cap_report.plotting import FigureSeries, FigureSpec, render_figure

        spec = FigureSpec(
            kind="line", series=(FigureSeries(label="a", x=(1.0, 2.0), y=(1.0, 2.0)),)
        )
        rendered = render_figure(figure_spec=spec, inputs=(), run_id="r1")

        # Act
        without_figure = compile_slides(
            template_digest=_TEMPLATE_DIGEST, figure_digests=(), cifra_digests=()
        )
        with_figure = compile_slides(
            template_digest=_TEMPLATE_DIGEST,
            figure_digests=(rendered.digest,),
            cifra_digests=(),
            figure_svgs=(rendered.svg_bytes,),
        )

        # Assert — exactly one extra slide for the one cited figure.
        assert with_figure.slide_count == without_figure.slide_count + 1
