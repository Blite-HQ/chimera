#!/usr/bin/env python3
"""Genera los fixtures de contrato del informe (C3b —
docs/specs/informe-derivado.md §"Tests de contrato (fixtures de costura)").

Convención de fixtures de costura (docs/specs/README.md §"Fixtures de
costura — un solo origen", patrón heredado de `gen-example-bundle.py`): el
origen es Python — este script importa `blite_cap_report.plotting.render_figure`
y `blite_cap_report.pdf.compile_report` tal cual (cero segunda
implementación) y emite el fixture CANÓNICO a `tests/fixtures/contract/informe/`,
espejado byte-idéntico a `apps/studio/src/fixtures/contract/informe/` (Vite
solo importa dentro de `src/`).

Auto-validante (mismo espíritu que `gen-example-bundle.py`: el generador
jamás escribe un bundle que su propio checklist rechace): ANTES de escribir,
renderiza la figura y compila el PDF una SEGUNDA vez, independientemente, y
exige que ambos digests — y ambos bytes — coincidan con la primera corrida
(la regla dura de C1/C2: byte-reproducibilidad). Si no coinciden, aborta sin
escribir nada.

Los fixtures cargan SOLO digests + receta (`DerivationProvenance`), NUNCA el
SVG/PDF binario (informe-derivado.md §Tests de contrato: "NO el PDF
binario") — el binario es recomputable desde la receta pinneada, no necesita
viajar en el fixture.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from blite_cap_report.pdf import CompiledReport, compile_report, template_digest
from blite_cap_report.plotting import (
    FigureSeries,
    FigureSpec,
    RenderedFigure,
    render_figure,
)

REPO = Path(__file__).resolve().parent.parent
TESTS_FIXTURE_DIR = REPO / "tests" / "fixtures" / "contract" / "informe"
STUDIO_FIXTURE_DIR = (
    REPO / "apps" / "studio" / "src" / "fixtures" / "contract" / "informe"
)

_RUN_ID = "fixture-informe-example"


def _figure_spec() -> FigureSpec:
    """Caso representativo r-vs-p (mismo caso que
    `test_plotting_determinism.py::TestErrorbarAndReferenceLine` — serie con
    `y_err` + línea de referencia, el caso que ejercita el path completo de
    ErrorBar/ReferenceLine)."""
    return FigureSpec(
        kind="scatter",
        series=(
            FigureSeries(
                label="r(p)",
                x=(1.0, 2.0, 3.0, 4.0),
                y=(0.62, 0.75, 0.83, 0.89),
                y_err=(0.05, 0.04, 0.03, 0.03),
            ),
        ),
        title="Approximation ratio r vs circuit depth p",
        x_label="p (QAOA layers)",
        y_label="r (approximation ratio)",
        ref_lines=(1.0,),
    )


def _render() -> RenderedFigure:
    return render_figure(figure_spec=_figure_spec(), inputs=(), run_id=_RUN_ID)


def _compile(figure: RenderedFigure) -> CompiledReport:
    return compile_report(
        template_digest=template_digest(),
        figure_digests=(figure.digest,),
        cifra_digests=(),
        figure_svgs=(figure.svg_bytes,),
        run_id=_RUN_ID,
    )


def _verify_byte_reproducible(
    figure: RenderedFigure,
    figure_again: RenderedFigure,
    compiled: CompiledReport,
    compiled_again: CompiledReport,
) -> bool:
    checks = (
        ("figure.digest reproducible", figure.digest == figure_again.digest),
        ("figure.svg_bytes reproducible", figure.svg_bytes == figure_again.svg_bytes),
        ("pdf.digest reproducible", compiled.digest == compiled_again.digest),
        ("pdf.pdf_bytes reproducible", compiled.pdf_bytes == compiled_again.pdf_bytes),
    )
    for name, ok in checks:
        status = "OK" if ok else "FALLA"
        print(f"[{status}] {name}")
    return all(ok for _, ok in checks)


def _write_mirrors(name: str, payload: dict[str, Any]) -> None:
    """Una sola fuente, DOS salidas — mismo patrón que
    `gen-example-bundle.py`: `tests/fixtures/contract/informe/` (el
    canónico) y `apps/studio/src/fixtures/contract/informe/` (el espejo que
    Vite puede importar), byte-idénticas por construcción."""
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    for directory in (TESTS_FIXTURE_DIR, STUDIO_FIXTURE_DIR):
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / name
        path.write_text(text, encoding="utf-8")
        print(f"  {path}")


def main() -> int:
    figure = _render()
    figure_again = _render()
    compiled = _compile(figure)
    compiled_again = _compile(figure_again)

    if not _verify_byte_reproducible(figure, figure_again, compiled, compiled_again):
        print("\nABORT: figura o PDF no son byte-reproducibles — no se escribe nada")
        return 1

    figura_payload: dict[str, Any] = {
        "digest": figure.digest,
        "provenance": figure.provenance.model_dump(mode="json"),
    }
    pdf_payload: dict[str, Any] = {
        "digest": compiled.digest,
        "page_count": compiled.page_count,
        "provenance": compiled.provenance.model_dump(mode="json"),
    }

    print("\nEscribiendo figura-example.json:")
    _write_mirrors("figura-example.json", figura_payload)
    print("Escribiendo pdf-example.json:")
    _write_mirrors("pdf-example.json", pdf_payload)
    print("\nFixtures del informe generados (2 archivos x 2 ubicaciones).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
