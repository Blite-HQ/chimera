"""Frontera de contenido recuperado — freeze §7 nota 10, vuelta ejecutable.
[S-G · P12 tramo 1, handoff P-rt docs/mvp/decisiones.md:2434-2437]

`docs/contract-freeze.md` §7 dice, textual: contenido recuperado (RAG) jamás
es evidencia — si un claim depende de un fragmento recuperado de una base de
conocimiento, ese fragmento entra al certificado como
`assumptions[{statement, ref{name, digest}}]`, **jamás** como `Attestation`
ni dentro de `conclusions`. Antes de este módulo la regla vivía SOLO en
prosa: ningún `grep` de `assumptions` en el código encontraba un chequeo.

**La marca — por qué este tipo y no otro.** `RetrievedRef` copia el shape de
`AssumptionRef` (`name`, `digest`) pero es una clase DISTINTA a propósito: la
frontera queda expresada en el sistema de tipos, no en una convención de
nombres. `Attestation` (`blite.verification.attestation`) declara sus propios
campos de digest (`claim_digest`, `evidence_digests`, `anchor_digest`) como
`str` sueltos — no hay forma de que un `RetrievedRef` encaje ahí por
construcción de tipos de Pydantic (asignarlo donde se espera `str` falla la
validación). El único conversor que este módulo ofrece es
`RetrievedRef.as_assumption()`, que solo sabe producir un `Assumption`; no
existe un `.as_conclusion()` ni un `.as_attestation()` — la frontera es
estructuralmente imposible de cruzar por ese camino.
`assert_retrieved_not_in_evidence` es el fusible fail-loud para el camino que
SÍ es posible: un caller que reutiliza el mismo `str` de digest (correcto o
por error) al construir una `Conclusion` o una `Attestation` por fuera de
este tipo — ahí la única defensa que queda es un chequeo en tiempo de
ensamblado, y por eso existe.

**[S-G · trinquete sin productor]** Hoy no existe NINGÚN productor de
contenido recuperado en `engine/src` ni `api/src` — el retrieval en sí
(embeddings, índice, ingesta de la base de conocimiento) es una decisión
posterior y NO es alcance de este módulo (ver handoff P-rt). Este guard se
instala ANTES que exista ese productor, a propósito: la frontera queda
ejecutable desde el primer caller real, en vez de descubrirse — o violarse
en silencio — el día en que aparezca uno. Sin productor, este guard se
ejercita SOLO por sus propios tests (`test_retrieval_boundary.py` + la
integración en `test_assemble.py`); eso se declara aquí en vez de
disimularse con un mock que finja un productor que no existe.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from pydantic import BaseModel, ConfigDict

from blite.certificate.predicate import Assumption, AssumptionRef, Conclusion

_ATTESTATION_DIGEST_FIELDS: tuple[str, ...] = ("claim_digest", "anchor_digest")
_ATTESTATION_DIGEST_SET_FIELDS: tuple[str, ...] = ("evidence_digests",)


class RetrievedRef(BaseModel):
    """Un digest marcado como CONTENIDO RECUPERADO (RAG) — freeze §7 nota 10.

    Mismo shape que `AssumptionRef` (`name`, `digest`); tipo distinto para
    que la frontera viva en el sistema de tipos. Ver el docstring del módulo
    para la justificación completa del diseño.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    digest: str

    def as_assumption(self, statement: str) -> Assumption:
        """Único camino tipado de un `RetrievedRef` hacia el predicate —
        siempre `assumptions[]`, nunca otra cosa (freeze §7)."""
        return Assumption(
            statement=statement,
            ref=AssumptionRef(name=self.name, digest=self.digest),
        )


class RetrievedContentInEvidenceError(RuntimeError):
    """Fail-loud: un `RetrievedRef` se coló en `conclusions` o en una
    `Attestation` (freeze §7 nota 10) — contenido recuperado jamás es
    evidencia. Nunca se degrada en silencio."""


def assert_retrieved_not_in_evidence(
    retrieved_refs: Sequence[RetrievedRef],
    conclusions: Sequence[Conclusion],
    attestations: Sequence[Mapping[str, object]],
) -> None:
    """Guard de la frontera (freeze §7 nota 10): revienta si algún digest
    marcado `RetrievedRef` aparece como `claim_digest` de una `Conclusion`,
    o dentro de una `Attestation` (`claim_digest`, `anchor_digest`,
    `evidence_digests` — el shape de `Attestation.model_dump(mode="json")`,
    el mismo que viaja en el evento `verification.completed`).

    `retrieved_refs` vacío (el default de todo caller hoy, sin productor de
    retrieval) es un no-op — no cambia el comportamiento de ningún bundle ya
    emitido.
    """
    retrieved_digests = frozenset(ref.digest for ref in retrieved_refs)
    if not retrieved_digests:
        return

    conclusion_hits = {c.claim_digest for c in conclusions} & retrieved_digests
    attestation_hits = _digests_of(attestations) & retrieved_digests
    hits = conclusion_hits | attestation_hits
    if not hits:
        return

    msg = (
        "contenido recuperado (RAG) jamás es evidencia (freeze §7 nota 10): "
        f"digest(s) {sorted(hits)} marcados RetrievedRef aparecen en "
        "conclusions o como Attestation — deben viajar SOLO en "
        "assumptions[{statement, ref{name, digest}}]"
    )
    raise RetrievedContentInEvidenceError(msg)


def _digests_of(attestations: Sequence[Mapping[str, object]]) -> frozenset[str]:
    """Los digests que una `Attestation` serializada expone como evidencia."""
    digests: set[str] = set()
    for attestation in attestations:
        for field in _ATTESTATION_DIGEST_FIELDS:
            value = attestation.get(field)
            if isinstance(value, str):
                digests.add(value)
        for field in _ATTESTATION_DIGEST_SET_FIELDS:
            values = attestation.get(field)
            if isinstance(values, Sequence) and not isinstance(values, str):
                # `values` es un `Sequence[Unknown]` recién narrowed — el cast
                # documenta el shape real (JSON: lista de digests `str`) sin
                # perder la comprobación `isinstance` de abajo.
                for item in cast("Sequence[object]", values):
                    if isinstance(item, str):
                        digests.add(item)
    return frozenset(digests)
