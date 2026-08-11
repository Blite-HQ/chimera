"""Seed de la costura chat/conversación (S-A, decisión #123).

Contrato: docs/specs/chat-conversacion.md. Cada test fija una pieza del
contrato que P3/P6 (Fase 1) implementan; el xfail se retira pieza por pieza,
jamás se borra el test (mismo ciclo SPEC→SEED→VERDE del README de specs).
Collection-safe: los imports de `blite`/`chimera_api` viven DENTRO de cada
función. Nota de mecánica: bajo TestClient los BackgroundTasks corren a
término antes de volver, así que un run de misión ya es TERMINAL al volver el
POST — los casos pre-terminales siembran el stream a mano (run sin terminal).

**VERDE desde P3 (#144, 2026-08-02)**: el xfail se retiró — las 8 piezas
pasan contra la implementación real (`blite.runtime.mission`,
`chimera_api.chat`, `TurnContext.pending_messages`, `PROMPT_PROTOCOL` v2 y
los aditivos de `run.created`). El test NO se borra: queda como la regresión
del contrato S-A (ciclo SPEC→SEED→VERDE del README de specs).

Directiva pyright per-file: se conserva el silencio de tipos porque el seed
usa `Any` a propósito (los imports viven dentro de cada función para ser
collection-safe), no porque falten módulos.
"""

# pyright: reportMissingImports=false, reportUnknownVariableType=false
# pyright: reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from typing import Any

import pytest

pytestmark = [pytest.mark.seed]

_RUN_ABIERTO = "run-chat-abierto"


def _store_con_run_abierto() -> Any:
    """Stream con run.created + run.started y SIN terminal (mensajes entran)."""
    from blite.events import create_event_store

    store = create_event_store()
    store.append(
        stream_id=_RUN_ABIERTO,
        type="run.created",
        actor_id="user:dylan",
        domain_id="domain-default",
        payload={
            "run_id": _RUN_ABIERTO,
            "actor_id": "user:dylan",
            "domain_id": "domain-default",
            "max_steps": 4,
            "policy_digest": "d" * 64,
        },
        expected_seq=0,
    )
    store.append(
        stream_id=_RUN_ABIERTO,
        type="run.started",
        actor_id="service:runtime",
        domain_id="domain-default",
        payload={},
        expected_seq=1,
    )
    return store


def _client(store: Any) -> Any:
    from chimera_api.app import create_app
    from fastapi.testclient import TestClient
    from tests.conftest import authenticated

    return authenticated(TestClient(create_app(store)))


def test_mission_message_payload_forma() -> None:
    """§Contrato-1: payload de 4 campos, frozen, extra=forbid."""
    from blite.runtime.mission import MissionMessagePayload

    payload = MissionMessagePayload(
        run_id="run-1",
        message_id="msg-1",
        author="user:dylan",
        text="ajustá el presupuesto y seguí",
    )
    assert payload.model_dump() == {
        "run_id": "run-1",
        "message_id": "msg-1",
        "author": "user:dylan",
        "text": "ajustá el presupuesto y seguí",
    }
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        # El campo de más es EL punto del test (`extra="forbid"` en runtime);
        # ahora que el modelo EXISTE, pyright también lo rechaza estáticamente.
        MissionMessagePayload(
            run_id="run-1",
            message_id="msg-1",
            author="user:dylan",
            text="x",
            extra_campo="no",  # pyright: ignore[reportCallIssue]
        )


def test_turn_context_pending_messages_default_vacio() -> None:
    """§Contrato-5: aditivo con default () — compat total con el loop actual."""
    from blite.runtime.loop import TurnContext

    ctx = TurnContext(
        run_id="run-1",
        domain_id="domain-default",
        turn=1,
        goal_capability_id="blite.solvers.qubo",
        goal_inputs={},
    )
    assert ctx.pending_messages == ()


def test_prompt_protocol_v2_con_historial() -> None:
    """§Contrato-6: la constante avanza a v2 (`messages` entra a la vista)."""
    from chimera_api.model_proposer import PROMPT_PROTOCOL

    assert PROMPT_PROTOCOL == "chimera/mission-proposer-prompt/v2"


def test_post_messages_202_y_evento_en_stream() -> None:
    """§Contrato-2: 202 {message_id} + mission.message journalizado."""
    store = _store_con_run_abierto()
    respuesta = _client(store).post(
        f"/runs/{_RUN_ABIERTO}/messages", json={"text": "hola"}
    )
    assert respuesta.status_code == 202
    assert respuesta.json()["message_id"]
    tipos = [evento.type for evento in store.read_stream(_RUN_ABIERTO)]
    assert "mission.message" in tipos


def test_post_messages_409_post_terminal() -> None:
    """§Contrato-2: la cara HTTP del rechazo post-terminal del §2 del freeze."""
    store = _store_con_run_abierto()
    store.append(
        stream_id=_RUN_ABIERTO,
        type="run.failed",
        actor_id="service:runtime",
        domain_id="domain-default",
        payload={"error_kind": "exhausted"},
        expected_seq=2,
    )
    respuesta = _client(store).post(
        f"/runs/{_RUN_ABIERTO}/messages", json={"text": "tarde"}
    )
    assert respuesta.status_code == 409


def test_post_cancel_202_y_run_cancelled() -> None:
    """§Contrato-3: emisor HTTP de run.cancelled (N1); reason default."""
    store = _store_con_run_abierto()
    respuesta = _client(store).post(f"/runs/{_RUN_ABIERTO}/cancel", json={})
    assert respuesta.status_code == 202
    cancelados = [
        evento
        for evento in store.read_stream(_RUN_ABIERTO)
        if evento.type == "run.cancelled"
    ]
    assert cancelados and cancelados[0].payload["reason"] == "user_requested"


def test_post_cancel_rechaza_parent_cancelled() -> None:
    """§Contrato-3: 'parent_cancelled' queda reservado a la cascada §13 — 422."""
    store = _store_con_run_abierto()
    respuesta = _client(store).post(
        f"/runs/{_RUN_ABIERTO}/cancel", json={"reason": "parent_cancelled"}
    )
    assert respuesta.status_code == 422


def test_run_created_porta_thread_y_project() -> None:
    """§Contrato-4: los aditivos del body de misión llegan al payload fundacional.

    `project_id="default"` — F1.1 materializó la FK que este seed dejaba
    opaca: `create_app()` siembra ese proyecto en cada arranque
    (`chimera_api.projects.ensure_default_project`), así que sigue siendo
    la referencia MÁS simple que el API valida de verdad antes de agendar."""
    from blite.events import create_event_store

    store = create_event_store()
    client = _client(store)
    respuesta = client.post(
        "/runs",
        json={
            "mission": "particioná la red",
            "max_turns": 1,
            "thread_id": "run-raiz",
            "project_id": "default",
        },
    )
    assert respuesta.status_code == 202
    run_id = respuesta.json()["run_id"]
    creado = next(
        evento for evento in store.read_stream(run_id) if evento.type == "run.created"
    )
    assert creado.payload["thread_id"] == "run-raiz"
    assert creado.payload["project_id"] == "default"
