"""`ModelServer` — el adapter de `ModelPort` (freeze §15.7, A2). [S-G]

TDD: replay HIT/MISS fail-closed, round-trip record→replay (comparten el
mismo `ReplayManifest` inyectado — dos instancias de `ModelServer` distintas,
como haría el gateway al cablear un modo por invocación), live con caller
inyectado, y que `backend_id` participa de la clave (freeze §15.7 punto 2:
"dos backends con el mismo prompt no colisionan"). Cero mocks silenciosos —
el caller vivo fake es una función local explícita.
"""

from __future__ import annotations

import hashlib

import pytest

from blite.protocols.model_server import (
    InMemoryReplayManifest,
    ModelServer,
    replay_key_digest,
)
from blite.runtime.content_store import InMemoryContentStore
from blite.serving.model_port import (
    ModelPort,
    ModelRequest,
    ModelResponse,
    ReplayMissError,
)

_CTX = {"domain_id": "domain-a"}


def _request(
    backend_id: str = "anthropic/claude", prompt_digest: str = "p" * 64
) -> ModelRequest:
    return ModelRequest(backend_id=backend_id, local=False, prompt_digest=prompt_digest)


def _fake_caller(response_bytes: bytes) -> object:
    """Caller vivo determinista y explícito — NADA de mocks mágicos."""

    def _call(request: ModelRequest) -> bytes:  # noqa: ARG001 - firma del puerto
        return response_bytes

    return _call


def test_isinstance_model_port_holds_for_every_mode() -> None:
    store = InMemoryContentStore()

    for mode in ("replay", "record", "live"):
        server = ModelServer(mode=mode, content_store=store, ctx=_CTX)
        assert isinstance(server, ModelPort)


def test_replay_miss_raises_replay_miss_error_never_touches_the_network() -> None:
    store = InMemoryContentStore()

    def _exploding_caller(request: ModelRequest) -> bytes:  # noqa: ARG001
        message = "replay JAMÁS debe invocar al caller vivo (fail-closed)"
        raise AssertionError(message)

    server = ModelServer(
        mode="replay",
        content_store=store,
        ctx=_CTX,
        manifest=InMemoryReplayManifest(),
        live_caller=_exploding_caller,
    )

    with pytest.raises(ReplayMissError):
        server.call(_request())


def test_record_then_replay_round_trip_same_request_finds_the_fixture() -> None:
    store = InMemoryContentStore()
    manifest = InMemoryReplayManifest()
    request = _request()
    response_bytes = b"la respuesta grabada en el ensayo"

    recorder = ModelServer(
        mode="record",
        content_store=store,
        ctx=_CTX,
        manifest=manifest,
        live_caller=_fake_caller(response_bytes),  # type: ignore[arg-type]
    )
    recorded = recorder.call(request)

    replayer = ModelServer(
        mode="replay", content_store=store, ctx=_CTX, manifest=manifest
    )
    replayed = replayer.call(request)

    assert isinstance(recorded, ModelResponse)
    assert replayed.response_digest == recorded.response_digest
    assert recorded.response_digest == hashlib.sha256(response_bytes).hexdigest()
    # El fixture vive hash-first en el ContentStore (freeze §15.7 punto 3).
    assert store.get(recorded.response_digest, _CTX) == response_bytes


def test_record_writes_the_manifest_but_live_does_not() -> None:
    store = InMemoryContentStore()
    manifest = InMemoryReplayManifest()
    request = _request()
    key = replay_key_digest(request)

    live_server = ModelServer(
        mode="live",
        content_store=store,
        ctx=_CTX,
        manifest=manifest,
        live_caller=_fake_caller(b"respuesta vivo, no grabada"),  # type: ignore[arg-type]
    )
    live_server.call(request)

    assert manifest.lookup(key) is None

    record_server = ModelServer(
        mode="record",
        content_store=store,
        ctx=_CTX,
        manifest=manifest,
        live_caller=_fake_caller(b"respuesta grabada"),  # type: ignore[arg-type]
    )
    recorded = record_server.call(request)

    assert manifest.lookup(key) == recorded.response_digest


def test_live_backend_returns_the_hash_first_digest_of_the_caller_response() -> None:
    store = InMemoryContentStore()
    response_bytes = b"contenido de la respuesta vivo"

    server = ModelServer(
        mode="live",
        content_store=store,
        ctx=_CTX,
        live_caller=_fake_caller(response_bytes),  # type: ignore[arg-type]
    )

    response = server.call(_request())

    assert response.response_digest == hashlib.sha256(response_bytes).hexdigest()
    assert store.get(response.response_digest, _CTX) == response_bytes


def test_replay_key_includes_backend_id_two_backends_never_collide() -> None:
    request_a = _request(backend_id="anthropic/claude")
    request_b = _request(backend_id="ollama_chat/gpt-oss")

    assert replay_key_digest(request_a) != replay_key_digest(request_b)


def test_replay_key_is_deterministic_for_the_same_request_shape() -> None:
    first = _request(backend_id="anthropic/claude", prompt_digest="a" * 64)
    second = _request(backend_id="anthropic/claude", prompt_digest="a" * 64)

    assert replay_key_digest(first) == replay_key_digest(second)


def test_replay_miss_for_an_unseen_backend_even_if_another_backend_was_recorded() -> (
    None
):
    store = InMemoryContentStore()
    manifest = InMemoryReplayManifest()
    prompt_digest = "d" * 64

    recorder = ModelServer(
        mode="record",
        content_store=store,
        ctx=_CTX,
        manifest=manifest,
        live_caller=_fake_caller(b"respuesta de anthropic"),  # type: ignore[arg-type]
    )
    recorder.call(_request(backend_id="anthropic/claude", prompt_digest=prompt_digest))

    replayer = ModelServer(
        mode="replay", content_store=store, ctx=_CTX, manifest=manifest
    )
    with pytest.raises(ReplayMissError):
        replayer.call(
            _request(backend_id="ollama_chat/gpt-oss", prompt_digest=prompt_digest)
        )
