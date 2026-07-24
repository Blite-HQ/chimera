"""Deterministic, byte-reproducible figure and report derivation. Anchor: recompute-and-compare digests."""

from .plotting import FigureSeries, FigureSpec, RenderedFigure, render_figure
from .tool import RenderFigure

__all__ = [
    "RenderFigure",
    "render_figure",
    "RenderedFigure",
    "FigureSpec",
    "FigureSeries",
]
