"""Deterministic, byte-reproducible figure and report derivation. Anchor: recompute-and-compare digests."""

from .annex import build_verification_annex
from .binding import CertificateBinding, Citation, build_binding
from .pdf import CompiledReport, UncitableFigureError, compile_report, template_digest
from .plotting import FigureSeries, FigureSpec, RenderedFigure, render_figure
from .slides import CompiledSlides, compile_slides, slides_template_digest
from .statement import (
    REPORT_PREDICATE_TYPE,
    build_report_statement,
    sign_report_statement,
)
from .tool import CompilePdf, CompileSlides, RenderFigure

__all__ = [
    "REPORT_PREDICATE_TYPE",
    "CertificateBinding",
    "Citation",
    "CompiledReport",
    "CompiledSlides",
    "CompilePdf",
    "CompileSlides",
    "FigureSeries",
    "FigureSpec",
    "RenderFigure",
    "RenderedFigure",
    "UncitableFigureError",
    "build_binding",
    "build_report_statement",
    "build_verification_annex",
    "compile_report",
    "compile_slides",
    "render_figure",
    "sign_report_statement",
    "slides_template_digest",
    "template_digest",
]
