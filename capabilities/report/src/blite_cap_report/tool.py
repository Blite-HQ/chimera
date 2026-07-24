"""
RenderFigure — render a generic figure (series/axes/kind) deterministically
to byte-reproducible SVG.

Registered as entry point: blite.capabilities["blite.report.render_figure"]
Heavy dependency (matplotlib) loaded lazily (install via extras):
  uv add blite-cap-report[plot]
"""

from __future__ import annotations

from typing import Any, cast

from blite.verification.provenance import InputRef
from blite_cap_report.plotting import FigureSeries, FigureSpec, render_figure
from blite_capability.manifest import CapabilityManifest

# `blite_cap_report.plotting` no importa matplotlib a nivel de módulo (lazy,
# ver `_render_svg_bytes`) — este import top-level NO obliga a instalar el
# extra `plot` solo por cargar `blite_cap_report.tool`.

_MANIFEST = CapabilityManifest(
    id="blite.report.render_figure",
    description=(
        "Render a generic figure (series, axes, chart kind) deterministically "
        "to byte-reproducible SVG."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["line", "bar", "scatter"]},
            "series": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "x": {"type": "array", "items": {"type": "number"}},
                        "y": {"type": "array", "items": {"type": "number"}},
                        "y_err": {"type": "array", "items": {"type": "number"}},
                    },
                    "required": ["label", "x", "y"],
                },
            },
            "title": {"type": "string"},
            "x_label": {"type": "string"},
            "y_label": {"type": "string"},
            "ref_lines": {"type": "array", "items": {"type": "number"}},
            "dpi": {"type": "integer"},
            "figsize": {"type": "array", "items": {"type": "number"}},
            "style": {"type": "string"},
            "run_id": {"type": "string"},
            "provenance_inputs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "ref": {"type": "string"},
                        "digest": {"type": "string"},
                    },
                    "required": ["ref", "digest"],
                },
            },
        },
        "required": ["kind", "series", "run_id"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "digest": {"type": "string"},
            "svg": {"type": "string"},
            "provenance_recipe": {"type": "object"},
        },
        "required": ["digest", "svg", "provenance_recipe"],
    },
    tags=("reporting", "deterministic", "pure"),
)


def _build_figure_series(raw: Any) -> FigureSeries:
    if not isinstance(raw, dict):
        msg = "RenderFigure: each 'series' entry must be an object"
        raise ValueError(msg)
    entry = cast("dict[str, Any]", raw)
    label, x, y = entry.get("label"), entry.get("x"), entry.get("y")
    if not isinstance(label, str) or not isinstance(x, list) or not isinstance(y, list):
        msg = "RenderFigure: series requires 'label' (str), 'x' (array), 'y' (array)"
        raise ValueError(msg)
    y_err = entry.get("y_err")
    return FigureSeries(
        label=label,
        x=tuple(float(v) for v in cast("list[Any]", x)),
        y=tuple(float(v) for v in cast("list[Any]", y)),
        y_err=tuple(float(v) for v in cast("list[Any]", y_err))
        if isinstance(y_err, list)
        else None,
    )


def _build_figsize(raw: Any) -> tuple[float, float]:
    if not isinstance(raw, list) or len(cast("list[Any]", raw)) != 2:
        return (6.0, 4.0)
    values = cast("list[Any]", raw)
    return (float(values[0]), float(values[1]))


def _build_figure_spec(inputs: dict[str, Any]) -> FigureSpec:
    kind = inputs.get("kind")
    series_raw = inputs.get("series")
    if kind not in ("line", "bar", "scatter"):
        msg = "RenderFigure: input 'kind' must be one of line|bar|scatter"
        raise ValueError(msg)
    if not isinstance(series_raw, list) or not series_raw:
        msg = "RenderFigure: input 'series' (non-empty array) is required"
        raise ValueError(msg)
    figsize = _build_figsize(inputs.get("figsize"))
    return FigureSpec(
        kind=kind,
        series=tuple(_build_figure_series(s) for s in cast("list[Any]", series_raw)),
        title=str(inputs.get("title", "")),
        x_label=str(inputs.get("x_label", "")),
        y_label=str(inputs.get("y_label", "")),
        ref_lines=tuple(
            float(v) for v in cast("list[Any]", inputs.get("ref_lines", []))
        ),
        dpi=int(inputs.get("dpi", 100)),
        figsize=figsize,
        style=str(inputs.get("style", "default")),
    )


def _build_provenance_inputs(raw: Any) -> tuple[InputRef, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        msg = "RenderFigure: input 'provenance_inputs' must be an array"
        raise ValueError(msg)
    result: list[InputRef] = []
    for raw_item in cast("list[Any]", raw):
        if not isinstance(raw_item, dict):
            msg = "RenderFigure: each provenance_inputs entry must be an object"
            raise ValueError(msg)
        item = cast("dict[str, Any]", raw_item)
        ref, digest = item.get("ref"), item.get("digest")
        if not isinstance(ref, str) or not isinstance(digest, str):
            msg = "RenderFigure: each provenance_inputs entry needs 'ref' and 'digest' (str)"
            raise ValueError(msg)
        result.append({"ref": ref, "digest": digest})
    return tuple(result)


class RenderFigure:
    """Generic capability: render a series/axes figure deterministically to SVG."""

    @property
    def manifest(self) -> CapabilityManifest:
        return _MANIFEST

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Invoke the capability. Heavy deps (matplotlib) loaded lazily on first call."""
        try:
            return self._invoke_impl(inputs)
        except ImportError as exc:
            raise ImportError(
                f"RenderFigure: optional dependency missing. "
                f"Install blite-cap-report[plot]: {exc}"
            ) from exc

    def _invoke_impl(self, inputs: dict[str, Any]) -> dict[str, Any]:
        run_id = inputs.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            msg = "RenderFigure: input 'run_id' (str) is required"
            raise ValueError(msg)
        spec = _build_figure_spec(inputs)
        provenance_inputs = _build_provenance_inputs(inputs.get("provenance_inputs"))
        rendered = render_figure(
            figure_spec=spec, inputs=provenance_inputs, run_id=run_id
        )
        return {
            "digest": rendered.digest,
            "svg": rendered.svg_bytes.decode("utf-8"),
            "provenance_recipe": dict(rendered.provenance.recipe),
        }
