"""compile_slides — the slide deck as another derivation (C3, extending
informe-derivado.md §b's PDF-derivation recipe to a presentation surface).

Same recipe shape as `pdf.py::compile_report` (`recipe.capability =
"blite.report.compile_slides"`), same byte-reproducibility property
(`set document(date: none)` in `slides.typ` + Typst's content-derived `/ID`),
and the SAME fail-closed binding contract — imported from `binding.py`, never
reimplemented: `build_full_binding`/`enforce_binding`/`resolve_cert_id` are
the ONE cifra→certificado resolution shared with `compile_report`.

Data is injected via `sys_inputs` exactly like `report.typ` — never raw
string interpolation into the Typst source (injection risk). `sys_inputs`
values are strings; `data` travels as canonicalized JSON
(`blite.certificate.canonical.canonicalize`) and figures as UTF-8 SVG text.
"""

from __future__ import annotations

# Same silencing as pdf.py — typst-py's `sys_inputs` payload is a dict shape
# pyright cannot always fully resolve; scoped to this module only.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
from typing import Any

from blite.certificate.canonical import JSONValue, canonicalize
from blite.certificate.predicate import Conclusion, Deliverable
from blite.verification.provenance import (
    DerivationProvenance,
    DerivationRecipe,
    InputRef,
)
from blite_cap_report.binding import (
    CertificateBinding,
    build_full_binding,
    enforce_binding,
    resolve_cert_id,
)
from blite_cap_report.pdf_pages import count_pdf_pages

CAPABILITY_ID = "blite.report.compile_slides"
CAPABILITY_VERSION = "0.1.0"

_SHA256_PREFIX = "sha256:"
_TEMPLATE_RESOURCE = ("template", "slides.typ")
_DEFAULT_TITLE = "Informe de derivación certificada"


@dataclass(frozen=True)
class CompiledSlides:
    """Result of `compile_slides`: the deck IS its `DerivationProvenance`."""

    digest: str
    pdf_bytes: bytes
    provenance: DerivationProvenance
    slide_count: int


def _template_bytes() -> bytes:
    resource = resources.files("blite_cap_report").joinpath(*_TEMPLATE_RESOURCE)
    return resource.read_bytes()


def slides_template_digest() -> str:
    """Digest of the bundled, versioned `slides.typ` template — pinned by its
    own digest exactly like `pdf.py::template_digest()`. Public so an
    independent verifier can recompute it from the same package."""
    return _SHA256_PREFIX + hashlib.sha256(_template_bytes()).hexdigest()


def _normalize(digest: str) -> str:
    return digest.removeprefix(_SHA256_PREFIX)


def _short_digest(digest: str) -> str:
    return _SHA256_PREFIX + _normalize(digest)[:12]


def _build_inputs(
    template_digest_value: str,
    figure_digests: tuple[str, ...],
    cifra_digests: tuple[str, ...],
) -> tuple[InputRef, ...]:
    result: list[InputRef] = [{"ref": "template", "digest": template_digest_value}]
    for index, digest in enumerate(figure_digests):
        result.append({"ref": f"figure:{index}", "digest": digest})
    for index, digest in enumerate(cifra_digests):
        result.append({"ref": f"cifra:{index}", "digest": digest})
    return tuple(result)


def _params_digest(
    *,
    title: str,
    template_digest_value: str,
    figure_digests: tuple[str, ...],
    cifra_digests: tuple[str, ...],
    cert_id: str,
    binding_active: bool,
) -> str:
    """Same tri-state `cert_id` treatment as `pdf.py::_params_digest`: it
    only enters the payload when a binding is active — otherwise the footer
    always renders `"unbound"` regardless of `cert_id`, so two calls that
    differ ONLY in an inactive `cert_id` must still collapse to the same
    params_digest (they render byte-identical decks)."""
    payload: JSONValue = {
        "title": title,
        "template_digest": template_digest_value,
        "figure_digests": list(figure_digests),
        "cifra_digests": list(cifra_digests),
        "cert_id": cert_id if binding_active else None,
    }
    return _SHA256_PREFIX + hashlib.sha256(canonicalize(payload)).hexdigest()


def _build_recipe(params_digest: str) -> DerivationRecipe:
    return {
        "capability": CAPABILITY_ID,
        "version": CAPABILITY_VERSION,
        "params_digest": params_digest,
        "code_ref": "git:HEAD",
    }


def _slides_data(
    *,
    title: str,
    figure_digests: tuple[str, ...],
    cifra_digests: tuple[str, ...],
    figure_count: int,
    binding: CertificateBinding | None,
) -> JSONValue:
    """`slides.typ` reads this via `json(bytes(sys.inputs.data))`. `figures`
    drives the per-figure slides (only the ones with an actual SVG payload,
    `figure_count = len(figure_svgs)` — same convention as
    `pdf.py::_report_data`); `cifras` drives the summary slide (digest + cert,
    no image — a cifra is a cited number, not a figure)."""
    figures: list[JSONValue] = []
    for index in range(figure_count):
        digest = figure_digests[index]
        figures.append(
            {
                "key": f"figure_{index}",
                "digest_short": _short_digest(digest),
                "cert": resolve_cert_id(binding, digest),
            }
        )
    cifras: list[JSONValue] = [
        {
            "digest_short": _short_digest(digest),
            "cert": resolve_cert_id(binding, digest),
        }
        for digest in cifra_digests
    ]
    return {"title": title, "figures": figures, "cifras": cifras}


def _compile_typst(
    *,
    title: str,
    figure_digests: tuple[str, ...],
    cifra_digests: tuple[str, ...],
    figure_svgs: tuple[bytes, ...] | None,
    binding: CertificateBinding | None,
) -> bytes:
    """Deterministic Typst compilation, fully in-memory — same pattern as
    `pdf.py::_compile_typst`: never a real tempfile/tempdir."""
    import typst

    figure_count = len(figure_svgs) if figure_svgs is not None else 0
    data = _slides_data(
        title=title,
        figure_digests=figure_digests,
        cifra_digests=cifra_digests,
        figure_count=figure_count,
        binding=binding,
    )
    sys_inputs: dict[str, str] = {"data": canonicalize(data).decode("utf-8")}
    if figure_svgs is not None:
        for index, svg_bytes in enumerate(figure_svgs):
            sys_inputs[f"figure_{index}"] = svg_bytes.decode("utf-8")

    return typst.compile(_template_bytes(), format="pdf", sys_inputs=sys_inputs)


def compile_slides(
    *,
    template_digest: str,
    figure_digests: tuple[str, ...],
    cifra_digests: tuple[str, ...],
    certificate_conclusions: tuple[Conclusion, ...] | None = None,
    certificate_attestations: tuple[Mapping[str, Any], ...] | None = None,
    certificate_deliverables: tuple[Deliverable, ...] | None = None,
    cert_id: str = "",
    figure_svgs: tuple[bytes, ...] | None = None,
    run_id: str = "slides",
    title: str = _DEFAULT_TITLE,
) -> CompiledSlides:
    """Compile the slide deck — itself a `DerivationProvenance`
    (`recipe.capability = "blite.report.compile_slides"`), reusing the R2
    recipe shape verbatim exactly like `compile_report`.

    Leaving `certificate_conclusions`/`certificate_attestations`/
    `certificate_deliverables` ALL as `None` skips the binding check
    (recompilation/determinism mode). Passing ANY of them — including `()` —
    enforces that EVERY digest in `figure_digests`/`cifra_digests` resolves
    against their UNION (C3, `blite_cap_report.binding.build_binding`),
    fail-closed (`UncitableFigureError` from `binding.py`). `cert_id` is the
    certificate that binding resolves against — it also stamps the
    `cert:<id>` footer on every resolved figure/cifra.

    `template_digest` is the CALLER-supplied digest of the versioned
    `slides.typ` template (pin it via `slides_template_digest()` — same
    pattern as `compile_report`'s `template_digest` parameter): it enters
    `provenance.inputs` as `{ref: "template", digest: ...}` but does NOT
    select which bytes actually compile — the bundled template is always
    used, exactly like `compile_report`.
    """
    binding = build_full_binding(
        cert_id=cert_id,
        certificate_conclusions=certificate_conclusions,
        certificate_attestations=certificate_attestations,
        certificate_deliverables=certificate_deliverables,
    )
    if binding is not None:
        enforce_binding(figure_digests + cifra_digests, binding)

    inputs = _build_inputs(template_digest, figure_digests, cifra_digests)
    recipe = _build_recipe(
        _params_digest(
            title=title,
            template_digest_value=template_digest,
            figure_digests=figure_digests,
            cifra_digests=cifra_digests,
            cert_id=cert_id,
            binding_active=binding is not None,
        )
    )
    provenance = DerivationProvenance(
        kind="derivation", inputs=inputs, recipe=recipe, run_id=run_id, assertions=()
    )

    pdf_bytes = _compile_typst(
        title=title,
        figure_digests=figure_digests,
        cifra_digests=cifra_digests,
        figure_svgs=figure_svgs,
        binding=binding,
    )
    slide_count = count_pdf_pages(pdf_bytes)

    digest = _SHA256_PREFIX + hashlib.sha256(pdf_bytes).hexdigest()
    return CompiledSlides(
        digest=digest,
        pdf_bytes=pdf_bytes,
        provenance=provenance,
        slide_count=slide_count,
    )
