# blite-cap-report

Deterministic, byte-reproducible figure and report derivation.

`render_figure` renders a generic `FigureSpec` (series/axes/kind — no scenario
terms, ADR-029) to SVG bytes using matplotlib's object-oriented API (no
`pyplot`, no global state). The figure itself is a
`blite.verification.provenance.DerivationProvenance`: its `recipe.params_digest`
is `C(x)` (`blite.certificate.canonical.canonicalize`) over every render
parameter, and its own identity is `sha256:<hex>` of the exact SVG bytes.

## Determinism

Two renders of the same `FigureSpec` MUST produce byte-identical SVG output —
otherwise a downstream PDF built from these figures is not recomputable
(`docs/specs/informe-derivado.md` §Determinismo):

- `svg.hashsalt` is pinned to a repo constant (matplotlib's default salt is
  derived from `id()`/process hash and is not reproducible across runs).
- `SOURCE_DATE_EPOCH` is pinned to a fixed value for the duration of the
  render (reproducible-builds convention), restored afterwards.
- `svg.fonttype = "path"` converts text to vector outlines — no font-file
  dependency, works air-gapped, and removes a source of cross-environment
  drift.
- Rendering uses the matplotlib object-oriented API (`Figure` +
  `FigureCanvasSVG`) directly, never `pyplot`, avoiding shared global state
  between renders.
- `metadata={"Date": None}` on `savefig` prevents an embedded timestamp.

Install the plotting extra to use this capability:

```
uv add blite-cap-report[plot]
```
