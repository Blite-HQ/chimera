"""TDD: la regla dura de C1 (informe-derivado.md §Determinismo) — dos renders
del MISMO spec deben producir bytes SVG idénticos, o el PDF derivado deja de
ser recomputable. `params_digest` pasa por la única puerta de
canonicalización (`blite.certificate.canonical.canonicalize`)."""

from __future__ import annotations

import hashlib

from blite.certificate.canonical import canonicalize
from blite_cap_report.plotting import (
    FigureSeries,
    FigureSpec,
    figure_spec_as_json,
    render_figure,
)


def _line_spec() -> FigureSpec:
    return FigureSpec(
        kind="line",
        series=(
            FigureSeries(label="approx-ratio", x=(1.0, 2.0, 3.0), y=(0.5, 0.7, 0.9)),
        ),
        title="Example figure",
        x_label="p",
        y_label="r",
    )


class TestByteReproducibility:
    def test_two_renders_of_the_same_spec_are_byte_identical(self) -> None:
        # Arrange
        spec = _line_spec()

        # Act
        a = render_figure(figure_spec=spec, inputs=(), run_id="run-1")
        b = render_figure(figure_spec=spec, inputs=(), run_id="run-1")

        # Assert
        assert a.digest == b.digest
        assert a.svg_bytes == b.svg_bytes


class TestDerivationProvenanceShape:
    def test_figure_is_a_derivation_provenance_with_render_figure_capability(
        self,
    ) -> None:
        # Act
        rendered = render_figure(figure_spec=_line_spec(), inputs=(), run_id="run-1")

        # Assert
        assert rendered.provenance.kind == "derivation"
        assert rendered.provenance.recipe["capability"] == "blite.report.render_figure"


class TestParamsDigestIsTheCanonicalizationGate:
    def test_params_digest_is_the_canonicalization_gate(self) -> None:
        # Arrange
        spec = _line_spec()

        # Act
        rendered = render_figure(figure_spec=spec, inputs=(), run_id="run-1")
        expected_digest = (
            "sha256:"
            + hashlib.sha256(canonicalize(figure_spec_as_json(spec))).hexdigest()
        )
        recomputed_again = (
            "sha256:"
            + hashlib.sha256(canonicalize(figure_spec_as_json(spec))).hexdigest()
        )

        # Assert
        assert rendered.provenance.recipe["params_digest"] == expected_digest
        assert expected_digest == recomputed_again


class TestDigestChangesWithParams:
    def test_different_spec_yields_different_digest(self) -> None:
        # Arrange
        spec_a = _line_spec()
        spec_b = FigureSpec(
            kind=spec_a.kind,
            series=spec_a.series,
            title="Different title",
            x_label=spec_a.x_label,
            y_label=spec_a.y_label,
        )

        # Act
        a = render_figure(figure_spec=spec_a, inputs=(), run_id="run-1")
        b = render_figure(figure_spec=spec_b, inputs=(), run_id="run-1")

        # Assert
        assert a.digest != b.digest
        assert (
            a.provenance.recipe["params_digest"] != b.provenance.recipe["params_digest"]
        )


class TestErrorbarAndReferenceLine:
    def test_errorbar_and_reference_line_render_without_error(self) -> None:
        # Arrange — cubre el caso r-vs-p: serie con y_err + línea de referencia
        spec = FigureSpec(
            kind="scatter",
            series=(
                FigureSeries(
                    label="r(p)",
                    x=(1.0, 2.0, 3.0),
                    y=(0.6, 0.75, 0.82),
                    y_err=(0.05, 0.04, 0.03),
                ),
            ),
            title="r vs p",
            x_label="p (layers)",
            y_label="r (approximation ratio)",
            ref_lines=(1.0,),
        )

        # Act
        a = render_figure(figure_spec=spec, inputs=(), run_id="run-1")
        b = render_figure(figure_spec=spec, inputs=(), run_id="run-1")

        # Assert
        assert len(a.svg_bytes) > 0
        assert a.digest == b.digest
