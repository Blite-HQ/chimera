"""Deterministic, byte-reproducible figure and report derivation. Anchor: recompute-and-compare digests."""

from .pdf import CompiledReport, UncitableFigureError, compile_report, template_digest
from .plotting import FigureSeries, FigureSpec, RenderedFigure, render_figure
from .tool import CompilePdf, RenderFigure

__all__ = [
    "CompiledReport",
    "CompilePdf",
    "FigureSeries",
    "FigureSpec",
    "RenderFigure",
    "RenderedFigure",
    "UncitableFigureError",
    "compile_report",
    "render_figure",
    "template_digest",
]
