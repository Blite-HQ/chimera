"""Endpoint SSE del walking skeleton — spec confianza-api-sse (freeze §9).

Catch-up por `Last-Event-ID`, aislamiento por stream (el Studio jamás ve
eventos de otros runs), cabeceras anti-buffering, y tail vivo con corte por
desconexión. El store se inyecta por el puerto (in-memory hoy; PG detrás del
mismo puerto — nota 01 §1.5).

Los tests HTTP usan `?live=0` (snapshot finito): el TestClient httpx
bufferea la respuesta completa, así que el tail infinito se testea directo
sobre `event_stream` con desconexión controlable.
"""

from __future__ import annotations

import json
from typing import cast

import httpx
from chimera_api.app import create_app, event_stream
from fastapi.testclient import TestClient

from blite.events import create_event_store
from blite.events.store import EventStore


def _seed(store: EventStore) -> list[int]:
    """Dos streams: r1 con 3 eventos, r2 con 1 (ruido). Devuelve global_seqs de r1."""
    seqs: list[int] = []
    first = store.append(
        stream_id="r1",
        type="run.created",
        actor_id="user:dylan",
        domain_id="d-default",
        payload={"run_id": "r1"},
    )
    seqs.append(first.global_seq)
    store.append(
        stream_id="r2",
        type="run.created",
        actor_id="user:dylan",
        domain_id="d-default",
        payload={"run_id": "r2"},
    )
    second = store.append(
        stream_id="r1",
        type="verification.completed",
        actor_id="service:verifier",
        domain_id="d-default",
        payload={"verification": {"verdict": "pass"}},
        expected_seq=1,
    )
    seqs.append(second.global_seq)
    third = store.append(
        stream_id="r1",
        type="run.completed",
        actor_id="service:runtime",
        domain_id="d-default",
        payload={},
        expected_seq=2,
    )
    seqs.append(third.global_seq)
    return seqs


def _parse_frames(body: str) -> list[dict[str, str]]:
    frames: list[dict[str, str]] = []
    for chunk in body.split("\n\n"):
        if not chunk:
            continue
        frame: dict[str, str] = {}
        for line in chunk.split("\n"):
            key, _, value = line.partition(": ")
            frame[key] = value
        frames.append(frame)
    return frames


# starlette.testclient.TestClient anota su `.get()` contra el paquete
# `httpx2` (bajo TYPE_CHECKING) que este repo no instala — el fallback en
# runtime es el `httpx` real (con warning de deprecación), así que el
# `cast` de abajo es fiel al tipo efectivo en ejecución; pyright solo
# necesita el ignore puntual sobre la llamada en sí, ya que `httpx2` no
# está resoluble estáticamente (equivalente a "librería sin stubs").
def _get(
    client: TestClient, url: str, *, headers: dict[str, str] | None = None
) -> httpx.Response:
    return cast(
        httpx.Response,
        client.get(url, headers=headers),
    )


class TestHealth:
    def test_health_responde_ok(self) -> None:
        client = TestClient(create_app(create_event_store()))
        response = _get(client, "/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestRunEventsSse:
    def test_catchup_completo_sin_cursor(self) -> None:
        # Arrange
        store = create_event_store()
        seqs = _seed(store)
        client = TestClient(create_app(store))

        # Act — snapshot: catch-up y cerrar
        response = _get(client, "/runs/r1/events?live=0")

        # Assert — los 3 de r1, en orden, con id = global_seq y event = type
        frames = _parse_frames(response.text)
        assert [int(f["id"]) for f in frames] == seqs
        assert [f["event"] for f in frames] == [
            "run.created",
            "verification.completed",
            "run.completed",
        ]

    def test_reanudacion_con_last_event_id(self) -> None:
        # Arrange
        store = create_event_store()
        seqs = _seed(store)
        client = TestClient(create_app(store))

        # Act — el cursor es el global_seq del primero: llegan solo 2.º y 3.º
        response = _get(
            client,
            "/runs/r1/events?live=0",
            headers={"Last-Event-ID": str(seqs[0])},
        )

        # Assert
        frames = _parse_frames(response.text)
        assert [int(f["id"]) for f in frames] == seqs[1:]

    def test_last_event_id_invalido_degrada_a_catchup_completo(self) -> None:
        # freeze §9: F5 + catch-up ES la feature — jamás matar el stream.
        store = create_event_store()
        seqs = _seed(store)
        client = TestClient(create_app(store))
        response = _get(
            client,
            "/runs/r1/events?live=0",
            headers={"Last-Event-ID": "not-a-number"},
        )
        assert [int(f["id"]) for f in _parse_frames(response.text)] == seqs

    def test_aislamiento_por_stream(self) -> None:
        # Arrange
        store = create_event_store()
        _seed(store)
        client = TestClient(create_app(store))

        # Act
        frames = _parse_frames(_get(client, "/runs/r1/events?live=0").text)

        # Assert — jamás un evento de r2 (proyección, no fuente)
        payloads = [json.loads(f["data"]) for f in frames]
        assert len(payloads) == 3
        assert all(p["payload"].get("run_id") != "r2" for p in payloads)

    def test_data_es_la_proyeccion_sin_hashes(self) -> None:
        store = create_event_store()
        _seed(store)
        client = TestClient(create_app(store))
        frames = _parse_frames(_get(client, "/runs/r1/events?live=0").text)
        data = json.loads(frames[0]["data"])
        assert data["global_seq"] == int(frames[0]["id"])
        assert "hash" not in data
        assert "prev_hash" not in data

    def test_cabeceras_anti_buffering(self) -> None:
        store = create_event_store()
        _seed(store)
        client = TestClient(create_app(store))
        response = _get(client, "/runs/r1/events?live=0")
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["x-accel-buffering"] == "no"


class TestEventStreamTail:
    async def test_tail_entrega_lo_nuevo_y_corta_al_desconectar(self) -> None:
        # Arrange
        store = create_event_store()
        seqs = _seed(store)
        polls = 0

        async def is_disconnected() -> bool:
            nonlocal polls
            polls += 1
            if polls == 1:
                # Un evento nuevo aparece DESPUÉS del catch-up inicial.
                store.append(
                    stream_id="r1",
                    type="run.metrics.recorded",
                    actor_id="service:runtime",
                    domain_id="d-default",
                    payload={},
                    expected_seq=3,
                )
                return False
            return True  # segunda pasada: el cliente se fue

        # Act
        frames: list[str] = []
        stream = event_stream(
            store,
            "r1",
            cursor=seqs[-1],
            poll_interval=0.001,
            is_disconnected=is_disconnected,
        )
        async for frame in stream:
            frames.append(frame)

        # Assert — solo el evento post-cursor, y el generador TERMINÓ solo.
        assert len(frames) == 1
        assert "event: run.metrics.recorded" in frames[0]
