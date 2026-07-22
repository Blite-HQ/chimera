"""
`Artifact` + `ContentStore` — freeze §12 (ADOPTADO, convergencia §4.1). [S-G Etapa 0]

El contenido se direcciona por identidad (digest de la forma canónica), no por
ubicación. `put()` devuelve el digest: el contenido define su identidad (O3/L3).
SO2: particionado por dominio — un digest es visible solo dentro de su dominio
salvo Channel con 'read'; la dedup física es optimización interna, jamás canal
de visibilidad. Sustrato de Evidence, deliverables, prompts/respuestas de
modelo (hash-first, freeze §2) y del corpus RAG (nota 10 de ejecución).
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


class Artifact(BaseModel):
    """Espejo de la tabla `artifacts` (esquema v2 §4.b / freeze §12)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    digest: str
    domain_id: str
    media_type: str
    size_bytes: int
    storage_ref: str
    created_at: datetime


@runtime_checkable
class ContentStore(Protocol):
    """`put(bytes, media_type, ctx) -> Artifact / get(digest, ctx) / stat(digest, ctx)`
    (freeze §12). `ctx` porta el `domain_id` del caller (SO2) — sin dominio no
    hay visibilidad; el tipo concreto del contexto lo fija el gateway (§8)."""

    def put(self, data: bytes, media_type: str, ctx: object) -> Artifact:
        """Escribe y devuelve el Artifact — el digest ES la identidad (O3)."""
        ...

    def get(self, digest: str, ctx: object) -> bytes:
        """Bytes exactos, recuperables byte a byte — o falla fuerte."""
        ...

    def stat(self, digest: str, ctx: object) -> Artifact | None:
        """Metadata sin bytes; None si no es visible en el dominio del ctx."""
        ...
