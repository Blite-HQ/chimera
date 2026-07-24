"""Deterministic, byte-reproducible figure and report derivation. Anchor: recompute-and-compare digests."""

from .annex import build_verification_annex
from .binding import CertificateBinding, Citation, build_binding
from .pdf import CompiledReport, UncitableFigureError, compile_report, template_digest
from .plotting import FigureSeries, FigureSpec, RenderedFigure, render_figure
from .statement import (
    REPORT_PREDICATE_TYPE,
    build_report_statement,
    sign_report_statement,
)
from .tool import CompilePdf, RenderFigure

__all__ = [
    "REPORT_PREDICATE_TYPE",
    "CertificateBinding",
    "Citation",
    "CompiledReport",
    "CompilePdf",
    "FigureSeries",
    "FigureSpec",
    "RenderFigure",
    "RenderedFigure",
    "UncitableFigureError",
    "build_binding",
    "build_report_statement",
    "build_verification_annex",
    "compile_report",
    "render_figure",
    "sign_report_statement",
    "template_digest",
]
