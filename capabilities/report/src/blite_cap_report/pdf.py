"""compile_report — the PDF is the final derivation (informe-derivado.md §b).

`typst-py` (no LaTeX toolchain) compiles the versioned template (`report.typ`,
hashed by its own digest via `template_digest()`) plus the cited figures and
cifras (by digest) into a byte-reproducible PDF: `set document(date: none)`
in the template drops CreationDate/ModDate, and Typst's `/ID` is
content-derived (not random) — two compilations of the same inputs produce
IDENTICAL bytes (verified same-process AND cross-process). This is the
property that makes "verify the report = recompile and compare digests"
(informe-derivado.md §b) more than a slogan.

Binding fail-closed (C3 skeleton — informe-derivado.md §Binding
cifra→certificado): when `certificate_conclusions` is given (even `()`),
every cited digest MUST resolve against it, or the PDF never gets compiled.
`certificate_conclusions=None` opts OUT of the check entirely (recompilation/
determinism mode — no certificate to bind against yet).

Data is injected into the Typst source via `sys_inputs` (see `report.typ`):
never raw string interpolation into the template (Typst-syntax injection
risk). `sys_inputs` values are strings; `data` travels as canonicalized JSON
(`blite.certificate.canonical.canonicalize` — the single gate) and figures
as UTF-8 SVG text, both decoded back inside the template with
`json(bytes(...))` / `image(bytes(...), format: "svg")`.
"""

from __future__ import annotations

# typst-py ships full stubs (py.typed + .pyi) for its public surface, but the
# `Input` TypeVar it exposes is deliberately narrow (str | Path | bytes) and
# pyright cannot always fully resolve the dict-shaped `sys_inputs` payload
# this module builds. Silenced ONLY in this module — same pattern as
# `blite_cap_report.plotting`'s matplotlib silencing, never leaked upstream.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
import hashlib
import re
from dataclasses import dataclass
from importlib import resources

from blite.certificate.canonical import JSONValue, canonicalize
from blite.certificate.predicate import Conclusion
from blite.verification.provenance import (
    DerivationProvenance,
    DerivationRecipe,
    InputRef,
)

CAPABILITY_ID = "blite.report.compile_pdf"
CAPABILITY_VERSION = "0.1.0"

# informe-derivado.md §b: "PDF <= 8 paginas".
MAX_PAGE_COUNT = 8

_SHA256_PREFIX = "sha256:"
_TEMPLATE_RESOURCE = ("template", "report.typ")

# Individual page objects, e.g. `/Type/Page/Resources ...` — the negative
# lookahead excludes `/Type/Pages` (the page TREE node) and other siblings
# like `/Type/PageLabel` (any letter right after "Page" disqualifies it, not
# just "s" — a `/PageLabel` object matched a naive `(?!s)` lookahead and
# silently double-counted pages until this was caught against a real render).
_PAGE_OBJECT_RE = re.compile(rb"/Type\s*/Page(?![A-Za-z])")


class UncitableFigureError(Exception):
    """Fail-closed (informe-derivado.md §Binding): a cited figure/cifra whose
    digest does NOT resolve against the certificate makes the PDF derivation
    fail — never a report with an unsupported figure."""


class ReportTooLongError(Exception):
    """The compiled PDF exceeds the 8-page budget (informe-derivado.md §b)."""


@dataclass(frozen=True)
class CompiledReport:
    """Result of `compile_report`: the PDF IS its `DerivationProvenance`."""

    digest: str
    pdf_bytes: bytes
    provenance: DerivationProvenance
    page_count: int


def _template_bytes() -> bytes:
    resource = resources.files("blite_cap_report").joinpath(*_TEMPLATE_RESOURCE)
    return resource.read_bytes()


def template_digest() -> str:
    """Digest of the bundled, versioned `report.typ` template — the template
    IS pinned by its own digest (informe-derivado.md §b `inputs[{ref:
    "template", ...}]`). Public so an independent verifier can recompute it
    from the same package."""
    return _SHA256_PREFIX + hashlib.sha256(_template_bytes()).hexdigest()


def _normalize(digest: str) -> str:
    """Strip the `sha256:` prefix so predicate digests (bare hex) and
    figure/cifra digests (prefixed) compare equal."""
    return digest.removeprefix(_SHA256_PREFIX)


def _resolvable_digests(
    certificate_conclusions: tuple[Conclusion, ...],
) -> frozenset[str]:
    """The set of digests a cited figure/cifra may resolve against. Structured
    as its own function so C3 can extend it to attestations/deliverables
    without touching the binding enforcement below."""
    return frozenset(_normalize(c.claim_digest) for c in certificate_conclusions)


def _enforce_binding(
    cited_digests: tuple[str, ...],
    certificate_conclusions: tuple[Conclusion, ...],
) -> None:
    resolvable = _resolvable_digests(certificate_conclusions)
    for digest in cited_digests:
        if _normalize(digest) not in resolvable:
            msg = (
                f"cited digest {digest!r} does not resolve against any "
                "certificate conclusion (informe-derivado.md §Binding "
                "cifra→certificado — fail-closed: never an unsupported claim)"
            )
            raise UncitableFigureError(msg)


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
) -> str:
    payload: JSONValue = {
        "title": title,
        "template_digest": template_digest_value,
        "figure_digests": list(figure_digests),
        "cifra_digests": list(cifra_digests),
    }
    return _SHA256_PREFIX + hashlib.sha256(canonicalize(payload)).hexdigest()


def _build_recipe(params_digest: str) -> DerivationRecipe:
    return {
        "capability": CAPABILITY_ID,
        "version": CAPABILITY_VERSION,
        "params_digest": params_digest,
        "code_ref": "git:HEAD",
    }


def _report_data(
    *,
    title: str,
    template_digest_value: str,
    figure_digests: tuple[str, ...],
    cifra_digests: tuple[str, ...],
    figure_count: int,
) -> JSONValue:
    """The verification annex data — `template.typ` reads this via
    `json(bytes(sys.inputs.data))`. Enumerates EVERY artifact (template,
    figures, cifras) -> digest (informe-derivado.md §c)."""
    artifacts: list[JSONValue] = [
        {"label": "template", "digest": template_digest_value}
    ]
    for index, digest in enumerate(figure_digests):
        artifacts.append({"label": f"figure:{index}", "digest": digest})
    for index, digest in enumerate(cifra_digests):
        artifacts.append({"label": f"cifra:{index}", "digest": digest})
    figures: list[JSONValue] = [f"figure_{index}" for index in range(figure_count)]
    return {"title": title, "artifacts": artifacts, "figures": figures}


def _count_pdf_pages(pdf_bytes: bytes) -> int:
    """Count `/Type /Page` objects (the individual pages, never the `/Pages`
    tree node) directly in the PDF bytes — robust to key ordering inside the
    `/Pages` dict (no dependency on `/Count` appearing right after
    `/Type /Pages`, which may have `/Kids` or other keys interleaved)."""
    return len(_PAGE_OBJECT_RE.findall(pdf_bytes))


def _compile_typst(
    *,
    title: str,
    template_digest_value: str,
    figure_digests: tuple[str, ...],
    cifra_digests: tuple[str, ...],
    figure_svgs: tuple[bytes, ...] | None,
) -> bytes:
    """Deterministic Typst compilation, fully in-memory: the template bytes
    plus a `sys_inputs` string map — never a real tempfile/tempdir, so no
    filesystem path can leak into the output (informe-derivado.md §b)."""
    import typst

    figure_count = len(figure_svgs) if figure_svgs is not None else 0
    data = _report_data(
        title=title,
        template_digest_value=template_digest_value,
        figure_digests=figure_digests,
        cifra_digests=cifra_digests,
        figure_count=figure_count,
    )
    sys_inputs: dict[str, str] = {"data": canonicalize(data).decode("utf-8")}
    if figure_svgs is not None:
        for index, svg_bytes in enumerate(figure_svgs):
            sys_inputs[f"figure_{index}"] = svg_bytes.decode("utf-8")

    return typst.compile(_template_bytes(), format="pdf", sys_inputs=sys_inputs)


def compile_report(
    *,
    template_digest: str,
    figure_digests: tuple[str, ...],
    cifra_digests: tuple[str, ...],
    certificate_conclusions: tuple[Conclusion, ...] | None = None,
    figure_svgs: tuple[bytes, ...] | None = None,
    run_id: str = "report",
    title: str = "Informe de derivación certificada",
) -> CompiledReport:
    """Compile the final report PDF — itself a `DerivationProvenance`
    (informe-derivado.md §b), reusing the R2 recipe shape verbatim.

    `certificate_conclusions=None` skips the binding check (recompilation/
    determinism mode). Any other value — including `()` — enforces that
    EVERY digest in `figure_digests`/`cifra_digests` resolves against it,
    fail-closed (`UncitableFigureError`).
    """
    if certificate_conclusions is not None:
        _enforce_binding(figure_digests + cifra_digests, certificate_conclusions)

    inputs = _build_inputs(template_digest, figure_digests, cifra_digests)
    recipe = _build_recipe(
        _params_digest(
            title=title,
            template_digest_value=template_digest,
            figure_digests=figure_digests,
            cifra_digests=cifra_digests,
        )
    )
    provenance = DerivationProvenance(
        kind="derivation", inputs=inputs, recipe=recipe, run_id=run_id, assertions=()
    )

    pdf_bytes = _compile_typst(
        title=title,
        template_digest_value=template_digest,
        figure_digests=figure_digests,
        cifra_digests=cifra_digests,
        figure_svgs=figure_svgs,
    )
    page_count = _count_pdf_pages(pdf_bytes)
    if page_count > MAX_PAGE_COUNT:
        msg = (
            f"report exceeds the {MAX_PAGE_COUNT}-page budget "
            f"(informe-derivado.md §b): got {page_count} pages"
        )
        raise ReportTooLongError(msg)

    digest = _SHA256_PREFIX + hashlib.sha256(pdf_bytes).hexdigest()
    return CompiledReport(
        digest=digest,
        pdf_bytes=pdf_bytes,
        provenance=provenance,
        page_count=page_count,
    )
