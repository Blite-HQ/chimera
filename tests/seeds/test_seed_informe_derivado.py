"""SEED · costura C↔B (Dylan) — el informe como derivación, PDF byte-reproducible (R4).

freeze §7 (Certificate/Bundle — `deliverables`, binding C3) / §12
(`Artifact`/`ContentStore`) + docs/specs/informe-derivado.md: el informe entero
reutiliza la receta de `capability-ingesta.md` (R2) aplicada al dominio de
reporte; el PDF se compila con Typst (`set document(date: none)`) para ser
byte-reproducible y digestable, y toda cifra citada DEBE resolver a un digest
presente en el certificado (binding C3, fail-closed). xfail:
`blite_cap_report` no existe todavía (Fase 1, dueño Dylan).
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.seed,
    pytest.mark.xfail(
        strict=False,
        reason=(
            "Fase 1 Dylan: capabilities/report/src/blite_cap_report (render_figure/"
            "compile_pdf) no existe todavía — docs/specs/informe-derivado.md"
        ),
    ),
]


def test_report_pdf_recompilation_is_byte_reproducible() -> None:
    """Contrato: recompilar el MISMO informe (mismos inputs por digest) produce
    el MISMO digest de PDF — `set document(date: none)` + plantilla versionada
    (informe-derivado.md §b). Sin esto, "verificar = recompilar y comparar
    digests" es letra muerta."""
    # Arrange
    from blite_cap_report.pdf import compile_report

    template_digest = "sha256:" + "a" * 64
    figure_digests = ("sha256:" + "b" * 64,)
    cifra_digests = ("sha256:" + "c" * 64,)

    # Act — dos compilaciones independientes de los mismos inputs pinneados
    first = compile_report(
        template_digest=template_digest,
        figure_digests=figure_digests,
        cifra_digests=cifra_digests,
    )
    second = compile_report(
        template_digest=template_digest,
        figure_digests=figure_digests,
        cifra_digests=cifra_digests,
    )

    # Assert
    assert first.digest == second.digest


def test_report_figures_use_the_derivation_recipe_shape() -> None:
    """Contrato: cada figura es una `DerivationProvenance` (capability-ingesta.md
    §Contrato) con `recipe.capability = "blite.report.render_figure"` — cero
    tipo nuevo para figuras, se reutiliza la receta R2 tal cual."""
    # Arrange / Act
    from blite.verification.provenance import DerivationProvenance

    figure_provenance = DerivationProvenance(
        kind="derivation",
        inputs=({"ref": "conclusion:claim-digest", "digest": "sha256:" + "d" * 64},),
        recipe={
            "capability": "blite.report.render_figure",
            "version": "0.1.0",
            "params_digest": "sha256:" + "e" * 64,
            "code_ref": "git:HEAD",
        },
        run_id="r1",
        assertions=(),
    )

    # Assert
    assert figure_provenance.recipe["capability"] == "blite.report.render_figure"


def test_citing_a_figure_not_in_the_certificate_fails_closed() -> None:
    """Contrato dueño (binding C3): una cifra cuyo digest NO resuelve contra
    `conclusions[]`/`attestations[]`/`deliverables[]` del certificado emitido
    hace fallar la derivación del PDF — jamás un informe con cifra sin
    sustento (informe-derivado.md §Binding cifra→certificado)."""
    # Arrange
    from blite_cap_report.pdf import UncitableFigureError, compile_report

    unresolvable_digest = "sha256:" + "0" * 64

    # Act / Assert
    with pytest.raises(UncitableFigureError):
        compile_report(
            template_digest="sha256:" + "a" * 64,
            figure_digests=(unresolvable_digest,),
            cifra_digests=(),
            certificate_conclusions=(),  # certificado sin esa conclusión
        )
