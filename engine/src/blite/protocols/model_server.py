"""
`ModelServer` — el adapter que implementa `ModelPort` (freeze §15.7, execution/09).
[S-G · A2]

Vive en `blite.protocols` (nunca en `blite.serving`, AX3): hereda el contrato de
layers INV-6 (protocols exige authz) sin gate nuevo, y es el ÚNICO módulo
autorizado a importar un SDK de modelo (AX3-b). Tres backends seleccionables
por construcción (`ModelBackend`):

- **`replay`**: fail-closed por diseño — busca la clave (`replay_key_digest`,
  Regla 2 del anexo, prefijo `REPLAY_DIGEST_PREFIX`) en el `ReplayManifest`
  inyectado. MISS ⇒ `ReplayMissError`, JAMÁS passthrough a red (freeze §15.7
  punto 1). Nunca invoca al `live_caller` — no hay ruta desde `replay` hacia
  la red, ni siquiera en el fallo.
- **`record`**: llama al modelo vivo (vía `live_caller` inyectado), graba la
  respuesta content-addressed en el `ContentStore` (hash-first) y ADEMÁS
  apunta la clave del request al `response_digest` en el `ReplayManifest` —
  el único backend que escribe el manifest (freeze §15.7 punto 5: modo
  grabación separado y explícito).
- **`live`**: mismo camino que `record` MENOS la escritura del manifest — una
  llamada real sin dejar fixture de replay.

**Por qué un `ReplayManifest` separado del `ContentStore`:** el `ContentStore`
(`blite.content`) es puramente content-addressed — su digest es
`sha256(bytes)`, decidido por el store, no inyectable por el caller. La CLAVE
de replay (`replay_key_digest`) es un digest DISTINTO — calculado sobre la
FORMA del request, no sobre la respuesta — por lo que no existe un `data` que,
hasheado, produzca simultáneamente esa clave Y cargue el `response_digest`
(dependerían de bytes distintos). El freeze §15.7 punto 4 ya nombra esta pieza
como "manifest de replay" (el SET de fixtures pinneado por digest) — un
mapeo `replay_key -> response_digest`, conceptualmente distinto del
`ContentStore` que solo direcciona bytes por su propio hash. `ReplayManifest`
formaliza esa pieza; `InMemoryReplayManifest` es su respaldo mínimo (mismo
rol que `InMemoryContentStore` para el puerto `ContentStore`) — el respaldo
pinneado/versionado del día D (freeze: "el modo grabación no puede mutar la
config del demo en silencio") es trabajo posterior, no de este adapter.

**Inyección del caller vivo:** `LiveModelCaller = Callable[[ModelRequest],
bytes]` — testeable sin red/API key/litellm instalado (el fake de test es una
función local explícita). El default de producción (`_default_live_caller`)
envuelve `litellm.completion`; el `import litellm` vive DENTRO del closure
retornado, nunca a nivel de módulo, para que `blite.protocols.model_server`
importe aun si `litellm` no está instalado (solo se paga el import si de
verdad se invoca la ruta vivo/record sin caller inyectado).
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, cast, runtime_checkable

from blite.certificate.canonical import JSONValue, canonicalize
from blite.content import ContentStore
from blite.serving.model_port import (
    REPLAY_DIGEST_PREFIX,
    ModelRequest,
    ModelResponse,
    ReplayMissError,
)

_REPLAY_KEY_PREFIX = REPLAY_DIGEST_PREFIX.encode("ascii") + b"\n"
_RESPONSE_MEDIA_TYPE = "application/octet-stream"

ModelBackend = Literal["replay", "record", "live"]
LiveModelCaller = Callable[[ModelRequest], bytes]


def replay_key_digest(request: ModelRequest) -> str:
    """`SHA-256(REPLAY_DIGEST_PREFIX ‖ "\\n" ‖ C({backend_id, local,
    prompt_digest}))` — freeze §15.7 punto 2: la clave incluye `backend_id`
    EXPLÍCITAMENTE (dos backends con el mismo prompt no colisionan). Mismo
    estilo que `claim_view_digest`/`provenance_hash` (§7, `bundle_check.py`):
    prefijo de dominio versionado ‖ forma canónica (Regla 2 del anexo)."""
    view: dict[str, JSONValue] = {
        "backend_id": request.backend_id,
        "local": request.local,
        "prompt_digest": request.prompt_digest,
    }
    return hashlib.sha256(_REPLAY_KEY_PREFIX + canonicalize(view)).hexdigest()


@runtime_checkable
class ReplayManifest(Protocol):
    """El mapeo `replay_key -> response_digest` (freeze §15.7 punto 4, "manifest
    de replay") — pieza distinta del `ContentStore`, ver docstring del módulo."""

    def lookup(self, replay_key: str) -> str | None:
        """`None` ⇒ miss — el caller (`ModelServer`) decide fail-closed."""
        ...

    def record(self, replay_key: str, response_digest: str) -> None:
        """Ata la clave al digest de la respuesta ya grabada en el
        `ContentStore` — nunca los bytes en sí (los bytes viven por su propio
        digest, hash-first)."""
        ...


class InMemoryReplayManifest:
    """Respaldo mínimo de `ReplayManifest` — mismo rol que
    `InMemoryContentStore` para `ContentStore` (freeze: el respaldo
    pinneado/versionado del día D es trabajo posterior, no de este adapter)."""

    def __init__(self) -> None:
        self._entries: dict[str, str] = {}

    def lookup(self, replay_key: str) -> str | None:
        return self._entries.get(replay_key)

    def record(self, replay_key: str, response_digest: str) -> None:
        self._entries[replay_key] = response_digest


def _default_live_caller(content_store: ContentStore, ctx: object) -> LiveModelCaller:
    """El caller de producción — envuelve `litellm.completion`. El `import
    litellm` vive DENTRO de `_call` (perezoso): construir este closure, o
    incluso importar este módulo, no requiere que `litellm` esté instalado —
    solo invocarlo de verdad lo requiere."""

    def _call(request: ModelRequest) -> bytes:
        import litellm  # noqa: PLC0415 - perezoso a propósito, ver docstring

        # litellm no publica stubs completos para pyright --strict (varios
        # parámetros/atributos internos quedan "Unknown") — se aísla el `Any`
        # de terceros a este único cast documentado en vez de sembrar
        # `# type: ignore` por cada línea de la ruta de llamada.
        litellm_client = cast("Any", litellm)
        prompt_bytes = content_store.get(request.prompt_digest, ctx)
        prompt_text = prompt_bytes.decode("utf-8")
        completion = litellm_client.completion(
            model=request.backend_id,
            messages=[{"role": "user", "content": prompt_text}],
        )
        response_text = completion.choices[0].message.content
        return (response_text or "").encode("utf-8")

    return _call


@dataclass(frozen=True)
class ModelServer:
    """El adapter `ModelPort` (freeze §15.7) — `mode` selecciona el backend
    por construcción; `live_caller` se inyecta para test sin red (default =
    `_default_live_caller`, litellm perezoso). `content_store`/`ctx` quedan
    fijos por instancia (el gateway construye un `ModelServer` por dominio —
    `ModelRequest` no carga `domain_id`, SO2 lo resuelve el caller)."""

    mode: ModelBackend
    content_store: ContentStore
    ctx: object
    manifest: ReplayManifest = field(default_factory=InMemoryReplayManifest)
    live_caller: LiveModelCaller | None = None

    def call(self, request: ModelRequest) -> ModelResponse:
        """Despacha por `mode` — `replay` jamás toca `live_caller` (fail-closed
        por construcción, no por chequeo posterior)."""
        if self.mode == "replay":
            return self._call_replay(request)
        if self.mode in ("record", "live"):
            return self._call_live_or_record(request)
        msg = f"ModelServer.mode desconocido: {self.mode!r}"
        raise ValueError(msg)

    def _call_replay(self, request: ModelRequest) -> ModelResponse:
        key = replay_key_digest(request)
        response_digest = self.manifest.lookup(key)
        if response_digest is None:
            msg = (
                f"replay miss (backend_id={request.backend_id!r}, "
                f"prompt_digest={request.prompt_digest!r}) — freeze §15.7: "
                "jamás passthrough a red"
            )
            raise ReplayMissError(msg)
        return ModelResponse(response_digest=response_digest)

    def _call_live_or_record(self, request: ModelRequest) -> ModelResponse:
        caller = self.live_caller or _default_live_caller(self.content_store, self.ctx)
        response_bytes = caller(request)
        artifact = self.content_store.put(
            response_bytes, _RESPONSE_MEDIA_TYPE, self.ctx
        )
        if self.mode == "record":
            self.manifest.record(replay_key_digest(request), artifact.digest)
        return ModelResponse(response_digest=artifact.digest)
