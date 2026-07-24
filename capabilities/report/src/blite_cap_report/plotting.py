"""render_figure — figura genérica (series/ejes/tipo) → SVG byte-reproducible
+ su `DerivationProvenance` (informe-derivado.md §a "Cada figura = instancia
derivada"). Cero maquinaria de confianza nueva: reutiliza `DerivationProvenance`
/ `InputRef` de `blite.verification.provenance` tal cual, y `canonicalize` de
`blite.certificate.canonical` como ÚNICA puerta para `params_digest`.

Determinismo (§Determinismo, la regla dura de C1 — sin esto dos corridas
honestas producen bytes distintos y el PDF deja de ser recomputable):
  - `svg.hashsalt` fijo a una constante del repo (el default de matplotlib usa
    un salt basado en `id()`/hash de proceso, no reproducible entre corridas).
  - `SOURCE_DATE_EPOCH` fijado (convención reproducible-builds) durante el
    render, restaurado al salir.
  - `svg.fonttype = "path"`: texto → trazos, sin dependencia de fuentes
    (air-gap friendly, determinista entre entornos).
  - API orientada a objetos de matplotlib (`Figure` + `FigureCanvasSVG`),
    JAMÁS `pyplot` — evita estado global compartido entre renders.
  - `metadata={"Date": None}` en `savefig` — no se embebe timestamp.
"""

from __future__ import annotations

# matplotlib no publica stubs completos bajo pyright strict — se silencian
# SOLO los reportes de tipos desconocidos de terceros; las firmas propias de
# este módulo siguen bajo strict (mismo patrón que blite_cap_quantum.qaoa).
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
import hashlib
import io
import os
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from blite.certificate.canonical import JSONValue, canonicalize
from blite.verification.provenance import (
    DerivationProvenance,
    DerivationRecipe,
    InputRef,
)

if TYPE_CHECKING:
    # Solo para anotación de tipos — matplotlib se importa en runtime de forma
    # perezosa (extra `plot`, ver `_render_svg_bytes`), nunca al importar este
    # módulo (mismo patrón lazy-import que `blite_cap_sim`/`blite_cap_quantum`).
    from matplotlib.axes import Axes

# Constantes del repo (fijas, JAMÁS aleatorias) — ver docstring de módulo.
SVG_HASHSALT = "blite-report-v1"
SOURCE_DATE_EPOCH = "1700000000"
CAPABILITY_ID = "blite.report.render_figure"
CAPABILITY_VERSION = "0.1.0"


@dataclass(frozen=True)
class FigureSeries:
    """Una serie de datos a graficar. `y_err` habilita ErrorBar (caso r vs p)."""

    label: str
    x: tuple[float, ...]
    y: tuple[float, ...]
    y_err: tuple[float, ...] | None = None


@dataclass(frozen=True)
class FigureSpec:
    """Especificación completa y determinista de una figura genérica.

    Vocabulario genérico (series/ejes/tipo de gráfico) — ADR-029: ningún
    término de escenario vive aquí."""

    kind: Literal["line", "bar", "scatter"]
    series: tuple[FigureSeries, ...]
    title: str = ""
    x_label: str = ""
    y_label: str = ""
    ref_lines: tuple[float, ...] = ()
    dpi: int = 100
    figsize: tuple[float, float] = (6.0, 4.0)
    style: str = "default"


@dataclass(frozen=True)
class RenderedFigure:
    """Resultado de `render_figure`: la figura ES su `DerivationProvenance`."""

    digest: str
    svg_bytes: bytes
    provenance: DerivationProvenance


@contextmanager
def _pinned_source_date_epoch() -> Generator[None, None, None]:
    """Fija `SOURCE_DATE_EPOCH` durante el render y restaura el valor previo
    al salir (set+restore inmutable) — por si algún backend embebe timestamp."""
    previous = os.environ.get("SOURCE_DATE_EPOCH")
    os.environ["SOURCE_DATE_EPOCH"] = SOURCE_DATE_EPOCH
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("SOURCE_DATE_EPOCH", None)
        else:
            os.environ["SOURCE_DATE_EPOCH"] = previous


def _series_as_json(series: FigureSeries) -> JSONValue:
    return {
        "label": series.label,
        "x": list(series.x),
        "y": list(series.y),
        "y_err": list(series.y_err) if series.y_err is not None else None,
    }


def figure_spec_as_json(spec: FigureSpec) -> JSONValue:
    """TODOS los parámetros de render como `JSONValue` determinista — la
    ÚNICA entrada a `C(x)` para `params_digest` (Regla 2 del anexo, la puerta
    única de canonicalización). Público para que un verificador independiente
    recompute el mismo digest desde el mismo `FigureSpec`."""
    return {
        "kind": spec.kind,
        "series": [_series_as_json(s) for s in spec.series],
        "title": spec.title,
        "x_label": spec.x_label,
        "y_label": spec.y_label,
        "ref_lines": list(spec.ref_lines),
        "dpi": spec.dpi,
        "figsize": list(spec.figsize),
        "style": spec.style,
    }


def _draw_series(ax: Axes, spec: FigureSpec) -> None:
    """Dibuja cada serie según `kind`; ErrorBar si trae `y_err` (line/scatter),
    ReferenceLine horizontal por cada valor en `ref_lines`."""
    for series in spec.series:
        if series.y_err is not None and spec.kind in ("line", "scatter"):
            fmt = "o" if spec.kind == "scatter" else "-"
            ax.errorbar(
                series.x, series.y, yerr=series.y_err, fmt=fmt, label=series.label
            )
        elif spec.kind == "line":
            ax.plot(series.x, series.y, label=series.label)
        elif spec.kind == "scatter":
            ax.scatter(series.x, series.y, label=series.label)
        else:
            ax.bar(series.x, series.y, label=series.label)
    for ref_line in spec.ref_lines:
        ax.axhline(ref_line, linestyle="--", color="gray")


def _render_svg_bytes(spec: FigureSpec) -> bytes:
    """Renderiza `spec` a bytes SVG deterministas — `rc_context`/`style.context`
    scoped (no mutan `rcParams` global), API orientada a objetos sin `pyplot`."""
    import matplotlib.style as mplstyle
    from matplotlib import rc_context
    from matplotlib.backends.backend_svg import FigureCanvasSVG
    from matplotlib.figure import Figure

    # `mplstyle.context` DEBE ir afuera (se entra primero): el estilo
    # "default" resetea rcParams a `rcParamsDefault` (svg.hashsalt=None
    # incluido). `rc_context({...})` va adentro (se entra último) para que
    # nuestro hashsalt/fonttype fijos ganen sobre lo que el estilo resetee.
    # (Dict inline, no una variable aparte: así pyright infiere las claves
    # contra `RcKeyType` en vez de generalizarlas a `dict[str, str]`.)
    with (
        mplstyle.context(spec.style),
        _pinned_source_date_epoch(),
        rc_context({"svg.fonttype": "path", "svg.hashsalt": SVG_HASHSALT}),
    ):
        fig = Figure(figsize=spec.figsize, dpi=spec.dpi)
        ax = fig.add_subplot(111)
        _draw_series(ax, spec)
        ax.set_title(spec.title)
        ax.set_xlabel(spec.x_label)
        ax.set_ylabel(spec.y_label)
        if any(series.label for series in spec.series):
            ax.legend()
        FigureCanvasSVG(fig)
        buf = io.BytesIO()
        fig.savefig(buf, format="svg", metadata={"Date": None})
        return buf.getvalue()


def _build_recipe(params_digest: str) -> DerivationRecipe:
    return {
        "capability": CAPABILITY_ID,
        "version": CAPABILITY_VERSION,
        "params_digest": params_digest,
        "code_ref": "git:HEAD",
    }


def render_figure(
    *, figure_spec: FigureSpec, inputs: tuple[InputRef, ...], run_id: str
) -> RenderedFigure:
    """Render determinista → SVG byte-reproducible + su `DerivationProvenance`.

    `params_digest = C(x)` sobre `figure_spec_as_json(figure_spec)` (la única
    puerta de canonicalización). La figura ES una `DerivationProvenance` con
    `recipe.capability = "blite.report.render_figure"`."""
    params_digest = (
        "sha256:"
        + hashlib.sha256(canonicalize(figure_spec_as_json(figure_spec))).hexdigest()
    )
    provenance = DerivationProvenance(
        kind="derivation",
        inputs=inputs,
        recipe=_build_recipe(params_digest),
        run_id=run_id,
        assertions=(),
    )
    svg_bytes = _render_svg_bytes(figure_spec)
    digest = "sha256:" + hashlib.sha256(svg_bytes).hexdigest()
    return RenderedFigure(digest=digest, svg_bytes=svg_bytes, provenance=provenance)
