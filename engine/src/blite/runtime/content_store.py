"""
ContentStore in-memory de Fase 1 — freeze §12, alcance P0-3. [S-G · Steven]

Implementación mínima del puerto `blite.content.ContentStore` (put/get/stat,
NADA más — GC/tiering/S3 están en la lista NO-va, freeze §15.4). El digest es
sha256 de los bytes recibidos: la canonicalización (RFC 8785 JCS + NFC) es
responsabilidad del CALLER cuando el contenido es JSON — este store direcciona
bytes, no interpreta formas.

SO2 (particionado por dominio): los bytes se deduplican físicamente UNA vez
por digest, pero la visibilidad es por fila `(digest, domain_id)` — la dedup
jamás es canal de visibilidad (AX1b/Inv-E). El `ctx` porta el `domain_id` del
caller; el tipo concreto del contexto lo fija el gateway (§8) y HOY es el
Context no congelado del pipeline (dict) — por eso aquí se extrae de forma
estructural y fail-closed: sin dominio no hay visibilidad.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import cast

from blite.content import Artifact


def _domain_of(ctx: object) -> str:
    """Extrae el `domain_id` del ctx o EXPLOTA — sin dominio no hay visibilidad
    (SO2, freeze §12); jamás un default de dominio implícito."""
    if isinstance(ctx, Mapping):
        domain = cast("Mapping[str, object]", ctx).get("domain_id")
        if isinstance(domain, str) and domain:
            return domain
    msg = (
        "ctx sin domain_id: el ContentStore exige el dominio del caller "
        "(SO2, freeze §12) — sin dominio no hay visibilidad"
    )
    raise TypeError(msg)


class InMemoryContentStore:
    """`ContentStore` de Fase 1 — mismo rol que `create_event_store()` para el
    log: el puerto es el contrato, el respaldo (Postgres/disco) llega después
    detrás de la misma firma."""

    def __init__(self) -> None:
        self._blobs: dict[str, bytes] = {}
        self._rows: dict[tuple[str, str], Artifact] = {}

    def put(self, data: bytes, media_type: str, ctx: object) -> Artifact:
        domain_id = _domain_of(ctx)
        digest = hashlib.sha256(data).hexdigest()
        existing = self._rows.get((digest, domain_id))
        if existing is not None:
            # El contenido define su identidad (O3): re-put es idempotente.
            return existing
        artifact = Artifact(
            digest=digest,
            domain_id=domain_id,
            media_type=media_type,
            size_bytes=len(data),
            storage_ref=f"memory:{digest}",
            created_at=datetime.now(tz=UTC),
        )
        self._blobs[digest] = data
        self._rows[(digest, domain_id)] = artifact
        return artifact

    def get(self, digest: str, ctx: object) -> bytes:
        domain_id = _domain_of(ctx)
        if (digest, domain_id) not in self._rows:
            msg = (
                f"digest {digest!r} no es visible en el dominio {domain_id!r} "
                "(SO2, freeze §12) — la dedup física jamás es canal de visibilidad"
            )
            raise KeyError(msg)
        return self._blobs[digest]

    def stat(self, digest: str, ctx: object) -> Artifact | None:
        return self._rows.get((digest, _domain_of(ctx)))
