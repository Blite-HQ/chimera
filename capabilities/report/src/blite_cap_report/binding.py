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
