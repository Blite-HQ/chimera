"""
RenderFigure / CompilePdf — render a generic figure (series/axes/kind)
deterministically to byte-reproducible SVG, and compile the final report PDF
deterministically from a versioned Typst template plus cited digests.

Registered as entry points:
  blite.capabilities["blite.report.render_figure"]
  blite.capabilities["blite.report.compile_pdf"]
Heavy dependency (matplotlib) loaded lazily (install via extras):
  uv add blite-cap-report[plot]
typst is a CORE dependency (informe-derivado.md §b) — always installed.
"""

from __future__ import annotations

import base64
from typing import Any, cast

from blite.certificate.predicate import Conclusion
from blite.verification.provenance import InputRef
from blite_cap_report.pdf import compile_report
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


_COMPILE_PDF_MANIFEST = CapabilityManifest(
    id="blite.report.compile_pdf",
    description=(
        "Compile the final report PDF deterministically from a versioned "
        "Typst template plus cited figure/cifra digests (byte-reproducible; "
        "fail-closed if a cited digest does not resolve against the "
        "certificate)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "template_digest": {"type": "string"},
            "figure_digests": {"type": "array", "items": {"type": "string"}},
            "cifra_digests": {"type": "array", "items": {"type": "string"}},
            "certificate_conclusions": {
                "type": "array",
                "items": {"type": "object"},
                "description": (
                    "Omit/null to skip binding (recompilation mode); an "
                    "array (possibly empty) enforces it, fail-closed."
                ),
            },
            "figure_svgs_base64": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Base64-encoded SVG bytes to embed, one per figure.",
            },
            "run_id": {"type": "string"},
            "title": {"type": "string"},
        },
        "required": ["template_digest"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "digest": {"type": "string"},
            "pdf_base64": {"type": "string"},
            "page_count": {"type": "integer"},
            "provenance_recipe": {"type": "object"},
        },
        "required": ["digest", "pdf_base64", "page_count", "provenance_recipe"],
    },
    tags=("reporting", "deterministic", "pure"),
)


def _build_digest_tuple(raw: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(raw, list):
        msg = f"CompilePdf: input '{field_name}' must be an array"
        raise ValueError(msg)
    result: list[str] = []
    for item in cast("list[Any]", raw):
        if not isinstance(item, str):
            msg = f"CompilePdf: each '{field_name}' entry must be a string"
            raise ValueError(msg)
        result.append(item)
    return tuple(result)


def _build_conclusions(raw: Any) -> tuple[Conclusion, ...] | None:
    """`None` (key absent/null) skips binding; an array (possibly empty)
    enforces it — the tri-state that `compile_report` expects."""
    if raw is None:
        return None
    if not isinstance(raw, list):
        msg = "CompilePdf: input 'certificate_conclusions' must be an array"
        raise ValueError(msg)
    return tuple(
        Conclusion(**cast("dict[str, Any]", item)) for item in cast("list[Any]", raw)
    )


def _build_figure_svgs(raw: Any) -> tuple[bytes, ...] | None:
    if raw is None:
        return None
    if not isinstance(raw, list):
        msg = "CompilePdf: input 'figure_svgs_base64' must be an array"
        raise ValueError(msg)
    return tuple(base64.b64decode(cast("str", item)) for item in cast("list[Any]", raw))


class CompilePdf:
    """Generic capability: compile the final report PDF deterministically."""

    @property
    def manifest(self) -> CapabilityManifest:
        return _COMPILE_PDF_MANIFEST

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        template_digest = inputs.get("template_digest")
        if not isinstance(template_digest, str) or not template_digest:
            msg = "CompilePdf: input 'template_digest' (str) is required"
            raise ValueError(msg)
        figure_digests = _build_digest_tuple(
            inputs.get("figure_digests", []), "figure_digests"
        )
        cifra_digests = _build_digest_tuple(
            inputs.get("cifra_digests", []), "cifra_digests"
        )
        certificate_conclusions = _build_conclusions(
            inputs.get("certificate_conclusions")
        )
        figure_svgs = _build_figure_svgs(inputs.get("figure_svgs_base64"))
        run_id = inputs.get("run_id")
        run_id = run_id if isinstance(run_id, str) and run_id else "report"
        title = inputs.get("title")
        title = (
            title
            if isinstance(title, str) and title
            else "Informe de derivación certificada"
        )

        compiled = compile_report(
            template_digest=template_digest,
            figure_digests=figure_digests,
            cifra_digests=cifra_digests,
            certificate_conclusions=certificate_conclusions,
            figure_svgs=figure_svgs,
            run_id=run_id,
            title=title,
        )
        return {
            "digest": compiled.digest,
            "pdf_base64": base64.b64encode(compiled.pdf_bytes).decode("ascii"),
            "page_count": compiled.page_count,
            "provenance_recipe": dict(compiled.provenance.recipe),
        }
