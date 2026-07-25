"""annex.py — el anexo de verificación machine-readable
(docs/specs/informe-derivado.md §c "Trazabilidad visible").

La tabla `artefacto → digest → certificado` COMPLETA, incluido el PDF final.
El PDF no puede citarse a sí mismo DENTRO de su propia plantilla Typst — su
digest solo existe DESPUÉS de compilar — así que esta tabla vive como una
estructura independiente, computada tras `compile_report`, que un verificador
externo puede recomputar. Mismo espíritu que el checklist de 7 puntos de
`scripts/verify-bundle.py`: nada se afirma sin que su digest esté ahí.
"""

from __future__ import annotations

from blite.certificate.canonical import JSONValue
from blite_cap_report.binding import CertificateBinding

_TEMPLATE_REF = "template"
_PDF_REF = "pdf"


def _cert_for(binding: CertificateBinding | None, digest: str) -> str | None:
    """`cert_id` del binding si resuelve, `None` si no hay binding o la cifra
    no resuelve contra ninguna entrada del certificado."""
    if binding is None:
        return None
    citation = binding.resolve(digest)
    return citation.cert_id if citation is not None else None


def _row(
    binding: CertificateBinding | None, *, artifact_ref: str, digest: str
) -> JSONValue:
    return {
        "artifact_ref": artifact_ref,
        "digest": digest,
        "cert": _cert_for(binding, digest),
    }


def build_verification_annex(
    *,
    template_digest: str,
    figure_digests: tuple[str, ...],
    cifra_digests: tuple[str, ...],
    pdf_digest: str,
    binding: CertificateBinding | None,
) -> dict[str, JSONValue]:
    """Enumera TODOS los deliverables del informe — plantilla, cada figura,
    cada cifra citada y el PDF final — con su digest y el `cert_id` que lo
    resuelve (`None` si no resuelve). Determinista: cero timestamps, salida
    puramente función de sus argumentos, canonicalize-able tal cual."""
    rows: list[JSONValue] = [
        _row(binding, artifact_ref=_TEMPLATE_REF, digest=template_digest)
    ]
    for index, digest in enumerate(figure_digests):
        rows.append(_row(binding, artifact_ref=f"figure:{index}", digest=digest))
    for index, digest in enumerate(cifra_digests):
        rows.append(_row(binding, artifact_ref=f"cifra:{index}", digest=digest))
    rows.append(_row(binding, artifact_ref=_PDF_REF, digest=pdf_digest))
    return {"rows": rows}
