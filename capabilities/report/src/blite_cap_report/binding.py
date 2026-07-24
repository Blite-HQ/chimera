"""binding.py — cifra→certificado como valor de primera clase
(docs/specs/informe-derivado.md §Binding cifra→certificado (C3)).

Toda cifra citada en el informe DEBE resolver, por su digest, a una entrada
real en `conclusions[]`/`attestations[]`/`deliverables[]` del certificado
EMITIDO para el run que la produjo — la regla dura de C3. Este módulo la
modela como datos: un `CertificateBinding` es el conjunto resoluble completo
de UN certificado; `resolve()` es la única forma de consultarlo. Normaliza el
prefijo `sha256:` en ambos lados — los digests de `conclusions`/`deliverables`
viajan como hex bare (freeze §7) mientras que `figure_digests`/`cifra_digests`
viajan prefijados (`pdf.py`), y ambos deben comparar igual.

También vive aquí el contrato fail-closed COMPARTIDO por cada capability de
derivación que cita digests (`pdf.py::compile_report`,
`slides.py::compile_slides`): `build_full_binding` (tri-state — `None` opta
OUT del check por completo; cualquier otra cosa, incluido `()`, lo activa),
`enforce_binding` (falla-fuerte con `UncitableFigureError` si algo no
resuelve) y `resolve_cert_id` (el `cert:<id>`/`"unbound"` visible). Una sola
implementación — ningún derivador la reimplementa.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from blite.certificate.predicate import Conclusion, Deliverable

_SHA256_PREFIX = "sha256:"

CitationKind = Literal["conclusion", "attestation", "deliverable"]


def _normalize(digest: str) -> str:
    """Strip the `sha256:` prefix so bare-hex predicate digests and prefixed
    figure/cifra digests compare equal."""
    return digest.removeprefix(_SHA256_PREFIX)


@dataclass(frozen=True)
class Citation:
    """One resolved entry: the normalized digest, what kind of claim it came
    from, and which certificate it belongs to."""

    digest: str
    kind: CitationKind
    cert_id: str


@dataclass(frozen=True)
class CertificateBinding:
    """The full resolvable set for one emitted certificate — `resolve()` is
    the only way to query it (informe-derivado.md §Binding)."""

    cert_id: str
    citations: Mapping[str, Citation]
    """Normalized digest -> Citation."""

    def resolve(self, digest: str) -> Citation | None:
        """Normalizes `digest` and looks it up — `None` means the cifra does
        NOT resolve against this certificate (fail-closed territory)."""
        return self.citations.get(_normalize(digest))

    @property
    def resolvable(self) -> frozenset[str]:
        """The normalized digest keys — the resolvable set itself."""
        return frozenset(self.citations.keys())


def build_binding(
    *,
    cert_id: str,
    conclusions: tuple[Conclusion, ...] = (),
    attestations: tuple[Mapping[str, Any], ...] = (),
    deliverables: tuple[Deliverable, ...] = (),
) -> CertificateBinding:
    """Unites conclusions ∪ attestations ∪ deliverables of the EMITTED
    certificate into one resolvable `CertificateBinding` (informe-derivado.md
    §Binding: a cifra resolves to conclusions[]/attestations[]/deliverables[]
    of the certificate). `conclusions` map by `.claim_digest` (kind=
    "conclusion"); `attestations` (raw predicate dicts — same shape as
    `scripts/gen-example-bundle.py`) map by `["claim_digest"]` (kind=
    "attestation"); `deliverables` map by `.digest` (kind="deliverable"). All
    three sources normalize the `sha256:` prefix identically."""
    citations: dict[str, Citation] = {}
    for conclusion in conclusions:
        normalized = _normalize(conclusion.claim_digest)
        citations[normalized] = Citation(
            digest=normalized, kind="conclusion", cert_id=cert_id
        )
    for attestation in attestations:
        normalized = _normalize(str(attestation["claim_digest"]))
        citations[normalized] = Citation(
            digest=normalized, kind="attestation", cert_id=cert_id
        )
    for deliverable in deliverables:
        normalized = _normalize(deliverable.digest)
        citations[normalized] = Citation(
            digest=normalized, kind="deliverable", cert_id=cert_id
        )
    return CertificateBinding(cert_id=cert_id, citations=citations)


_UNBOUND_CERT = "unbound"


class UncitableFigureError(Exception):
    """Fail-closed (informe-derivado.md §Binding cifra→certificado): a cited
    figure/cifra whose digest does NOT resolve against the certificate makes
    the derivation fail — never a report/slide deck with an unsupported
    claim."""


def build_full_binding(
    *,
    cert_id: str,
    certificate_conclusions: tuple[Conclusion, ...] | None,
    certificate_attestations: tuple[Mapping[str, Any], ...] | None,
    certificate_deliverables: tuple[Deliverable, ...] | None,
) -> CertificateBinding | None:
    """`None` only when the caller opted OUT of the binding check entirely
    (all three left as `None` — recompilation/determinism mode). Otherwise
    builds the UNION binding via `build_binding`, even if some parts are
    empty (an explicit `()` still enforces — fail-closed on an empty set).
    Shared by `pdf.py::compile_report` and `slides.py::compile_slides` — the
    tri-state binding-or-skip decision is ONE contract, never reimplemented
    per derivation capability."""
    if (
        certificate_conclusions is None
        and certificate_attestations is None
        and certificate_deliverables is None
    ):
        return None
    return build_binding(
        cert_id=cert_id,
        conclusions=certificate_conclusions or (),
        attestations=certificate_attestations or (),
        deliverables=certificate_deliverables or (),
    )


def enforce_binding(
    cited_digests: tuple[str, ...],
    binding: CertificateBinding,
) -> None:
    """Fail-closed check shared by every derivation capability that cites
    digests against a certificate binding: every digest in `cited_digests`
    MUST resolve, or the derivation never compiles."""
    for digest in cited_digests:
        if binding.resolve(digest) is None:
            msg = (
                f"cited digest {digest!r} does not resolve against any "
                "certificate conclusion/attestation/deliverable "
                "(informe-derivado.md §Binding cifra→certificado — "
                "fail-closed: never an unsupported claim)"
            )
            raise UncitableFigureError(msg)


def resolve_cert_id(binding: CertificateBinding | None, digest: str) -> str:
    """`cert_id` if `binding` resolves `digest`, `"unbound"` otherwise (no
    binding at all, or a digest that does not resolve) — the visible
    `cert:<id>` footer shared by `pdf.py` and `slides.py`."""
    if binding is None:
        return _UNBOUND_CERT
    citation = binding.resolve(digest)
    return citation.cert_id if citation is not None else _UNBOUND_CERT
