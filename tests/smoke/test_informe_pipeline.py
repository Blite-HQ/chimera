"""Smoke — integración viva del informe (checkpoint 7, lado C del par C↔D).

Corre el pipeline COMPLETO del Dominio C contra la instancia certificada real
de la Fase 0 (`scripts/example-bundle.json`, el mismo bundle que valida
`verify-bundle.py` 7/7): decodifica su certificado, RENDERIZA una figura que
grafica una conclusión certificada, COMPILA el informe PDF con el binding
cifra→certificado ENFORCED contra el certificado real, y construye el anexo de
verificación + el Statement in-toto del informe. Es la prueba de que la costura
C↔B cierra extremo a extremo — no una unidad aislada:

  render_figure → compile_report(binding real, fail-closed) → verification annex
  → report Statement (DSSE) — todo byte-reproducible, todo recomputable.

DoD de costura (05-plan-paralelo.md regla NUEVA #2) = integración viva. Docker
no está disponible en este WSL, así que la evidencia es este pipeline Python
EJECUTADO en la suite (no `docker compose up`); el cambio a datos reales de B
(cuando B publique sus instancias cr6/cr8) es la tarea de 5 min de la tabla de
interacciones — hoy consume el bundle de ejemplo, que ES una instancia
certificada válida.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, cast

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from blite.certificate.dsse import verify as dsse_verify
from blite.certificate.predicate import Conclusion, Deliverable
from blite_cap_report.annex import build_verification_annex
from blite_cap_report.binding import UncitableFigureError, build_binding
from blite_cap_report.pdf import compile_report, template_digest
from blite_cap_report.plotting import FigureSeries, FigureSpec, render_figure
from blite_cap_report.statement import (
    REPORT_PREDICATE_TYPE,
    build_report_statement,
    sign_report_statement,
)

_EXAMPLE_BUNDLE = (
    Path(__file__).resolve().parents[2] / "scripts" / "example-bundle.json"
)


def _load_real_certificate() -> dict[str, Any]:
    """El predicate del certificado EMITIDO en la Fase 0 — la instancia
    certificada que el informe cita (no un fixture inventado por el dominio)."""
    bundle = cast("dict[str, Any]", json.loads(_EXAMPLE_BUNDLE.read_text("utf-8")))
    payload = base64.b64decode(cast("str", bundle["envelope"]["payload"]))
    statement = cast("dict[str, Any]", json.loads(payload))
    return cast("dict[str, Any]", statement["predicate"])


def _certified_figure_and_report() -> tuple[Any, Any, str, str]:
    """Renderiza una figura que grafica la conclusión certificada y compila el
    informe con el binding real ENFORCED. Devuelve (rendered, compiled, cert_id,
    conclusion_digest)."""
    predicate = _load_real_certificate()
    cert_id = cast("str", predicate["run_id"])
    conclusions = tuple(
        Conclusion(**cast("dict[str, Any]", c)) for c in predicate["conclusions"]
    )
    root_deliverables = tuple(
        Deliverable(**cast("dict[str, Any]", d)) for d in predicate["deliverables"]
    )
    conclusion_digest = "sha256:" + conclusions[0].claim_digest

    # (1) Figura que grafica la conclusión certificada — su insumo la pinnea.
    rendered = render_figure(
        figure_spec=FigureSpec(
            kind="scatter",
            series=(
                FigureSeries(
                    label="r(p)",
                    x=(1.0, 2.0, 3.0),
                    y=(0.62, 0.78, 0.85),
                    y_err=(0.04, 0.03, 0.02),
                ),
            ),
            title="Aproximación vs óptimo certificado",
            x_label="p",
            y_label="r",
            ref_lines=(1.0,),
        ),
        inputs=({"ref": f"conclusion:{cert_id}", "digest": conclusion_digest},),
        run_id=cert_id,
    )

    # (2) La figura es un deliverable propio del sub-run del informe: entra al
    # conjunto resoluble junto a los deliverables del certificado raíz.
    report_deliverables = (
        *root_deliverables,
        Deliverable(artifact_ref="figure:0", digest=rendered.digest),
    )

    # (3) Compila el informe con el binding real ENFORCED (fail-closed).
    compiled = compile_report(
        template_digest=template_digest(),
        figure_digests=(rendered.digest,),
        cifra_digests=(conclusion_digest,),
        certificate_conclusions=conclusions,
        certificate_deliverables=report_deliverables,
        cert_id=cert_id,
        figure_svgs=(rendered.svg_bytes,),
    )
    return rendered, compiled, cert_id, conclusion_digest


def test_report_compiles_against_the_real_phase0_certificate() -> None:
    """El informe compila citando una conclusión REAL del certificado emitido —
    binding enforced, sin cifra sin sustento, dentro del presupuesto de 8 pág."""
    _, compiled, _, _ = _certified_figure_and_report()
    assert compiled.digest.startswith("sha256:")
    assert compiled.page_count <= 8
    assert compiled.provenance.recipe["capability"] == "blite.report.compile_pdf"


def test_end_to_end_pipeline_is_byte_reproducible() -> None:
    """Recompilar TODO el pipeline (misma instancia certificada) produce el
    mismo digest de PDF — "verificar = recompilar y comparar" (informe §b)."""
    _, first, _, _ = _certified_figure_and_report()
    _, second, _, _ = _certified_figure_and_report()
    assert first.digest == second.digest


def test_citing_a_number_absent_from_the_real_certificate_fails_closed() -> None:
    """Una cifra cuyo digest NO está en el certificado real hace fallar la
    derivación (fail-closed) — nunca un informe con una cifra sin sustento."""
    predicate = _load_real_certificate()
    conclusions = tuple(
        Conclusion(**cast("dict[str, Any]", c)) for c in predicate["conclusions"]
    )
    with pytest.raises(UncitableFigureError):
        compile_report(
            template_digest=template_digest(),
            figure_digests=(),
            cifra_digests=("sha256:" + "0" * 64,),  # no está en el certificado
            certificate_conclusions=conclusions,
            cert_id=cast("str", predicate["run_id"]),
        )


def test_verification_annex_binds_every_artifact_to_the_real_certificate() -> None:
    """El anexo artefacto→digest→certificado enumera figura, cifra y el PDF
    final, cada uno atado al cert_id real (patrón showyourwork, informe §c)."""
    rendered, compiled, cert_id, conclusion_digest = _certified_figure_and_report()
    predicate = _load_real_certificate()
    conclusions = tuple(
        Conclusion(**cast("dict[str, Any]", c)) for c in predicate["conclusions"]
    )
    binding = build_binding(
        cert_id=cert_id,
        conclusions=conclusions,
        deliverables=(Deliverable(artifact_ref="figure:0", digest=rendered.digest),),
    )
    annex = build_verification_annex(
        template_digest=template_digest(),
        figure_digests=(rendered.digest,),
        cifra_digests=(conclusion_digest,),
        pdf_digest=compiled.digest,
        binding=binding,
    )
    rows = cast("list[dict[str, Any]]", annex["rows"])
    refs = {row["artifact_ref"] for row in rows}
    assert {"template", "figure:0", "cifra:0", "pdf"} <= refs
    # la cifra (conclusión real) y la figura (deliverable) resuelven al cert real
    bound = {row["artifact_ref"]: row["cert"] for row in rows}
    assert bound["cifra:0"] == cert_id
    assert bound["figure:0"] == cert_id


def test_report_statement_pins_the_pdf_and_signs_offline() -> None:
    """El Statement in-toto del informe pinnea el PDF por digest, declara
    claim_type=derivation, y su firma DSSE verifica offline (informe
    §Trazabilidad al run raíz + §Statement SDK)."""
    _, compiled, cert_id, _ = _certified_figure_and_report()
    statement = build_report_statement(
        compiled=compiled, cert_id=cert_id, sub_run_id="informe-8f2c1a9b"
    )
    assert statement["predicateType"] == REPORT_PREDICATE_TYPE
    subject = cast("list[dict[str, Any]]", statement["subject"])
    assert subject[0]["digest"]["sha256"] == compiled.digest.removeprefix("sha256:")
    predicate = cast("dict[str, Any]", statement["predicate"])
    assert predicate["claim_type"] == "derivation"

    private_key = ed25519.Ed25519PrivateKey.generate()
    envelope = sign_report_statement(
        statement=statement, private_key=private_key, keyid="informe:test"
    )
    # verifica offline con la pública — la firma ES la respuesta (Regla 1).
    payload = dsse_verify(envelope, private_key.public_key())
    assert json.loads(payload)["predicateType"] == REPORT_PREDICATE_TYPE
