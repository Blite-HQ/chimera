"""
ModelPort + doctrina del backend `replay` — freeze §3 / §15.7. [S-G Etapa 0]

AX3: un modelo nunca toca el mundo directo — `blite.serving` no importa
`protocols`, `gateway`, `runtime`, `authz` ni clientes de red (gate de
import). Este módulo define SOLO el puerto; los SDKs de modelo viven en el
adapter de `blite.protocols` (AX3-b).

Contrato `replay` (freeze §15.7 [S-F], la red de seguridad del air-gap del
día D):
1. Miss ⇒ `model.call.failed {error_kind: "replay_miss"}` — JAMÁS passthrough
   a red.
2. Clave = digest (Regla 2 del anexo) sobre el request canónico, incluyendo
   `backend_id`, con el prefijo `blite/model-replay/v1`.
3. Fixtures content-addressed en el ContentStore, con `domain_id` (SO2).
4. Manifest de replay pinneado por digest.
5. Modo grabación (`record`) es separado y explícito (infra/03
   `compose.record.yml`) — jamás grabar en modo replay.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

REPLAY_MISS_ERROR_KIND = "replay_miss"
REPLAY_DIGEST_PREFIX = "blite/model-replay/v1"


class ReplayMissError(Exception):
    """Miss del backend replay — se reporta como `model.call.failed
    {error_kind: "replay_miss"}`; el passthrough a red está PROHIBIDO."""


class ModelRequest(BaseModel):
    """El request que viaja al puerto — espejo del evento `model.call.requested`
    (freeze §3): `{backend_id, local, prompt_digest}`. El prompt completo vive
    como `Artifact` por digest (hash-first, freeze §2)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    backend_id: str
    local: bool
    prompt_digest: str


class ModelResponse(BaseModel):
    """Espejo de `model.call.completed {response_digest}` (freeze §3)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    response_digest: str


@runtime_checkable
class ModelPort(Protocol):
    """El único camino a un modelo (AX3) — generativo o de embeddings
    (frontera RAG, freeze §7 [nota 10]): sin excepción para embeddings."""

    def call(self, request: ModelRequest) -> ModelResponse:
        """Despacha al backend elegido; en `replay`, un miss levanta
        `ReplayMissError` — nunca red."""
        ...
