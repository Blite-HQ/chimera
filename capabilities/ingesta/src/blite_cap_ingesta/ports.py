"""Puertos locales, duck-typed — ADR-008: este paquete JAMÁS importa `blite.*`.

`ArtifactLike`/`ContentSink` son espejos ESTRUCTURALES de
`blite.content.{Artifact, ContentStore}` (mismo shape, misma firma de
método) sin ningún acoplamiento de import: el `InMemoryContentStore`/
`Artifact` real del engine los satisface hoy sin cambios, y cualquier otro
almacén estructuralmente compatible lo hará mañana. `blite.ingesta.snapshot.fetch`
recibe su `ContentSink` inyectado en tiempo de invocación (vía la clave
`content_store` del dict de `invoke()`) — no es representable en el
`input_schema` genérico (no es JSON), ver `snapshot_fetch.py`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class ArtifactLike(Protocol):
    """Espejo estructural de `blite.content.Artifact` — solo atributos."""

    digest: str
    domain_id: str
    media_type: str
    size_bytes: int
    storage_ref: str
    created_at: datetime


@runtime_checkable
class ContentSink(Protocol):
    """Espejo estructural de `blite.content.ContentStore.put` — el único
    método que `blite.ingesta.snapshot.fetch` necesita."""

    def put(self, data: bytes, media_type: str, ctx: object) -> ArtifactLike: ...
