"""E2 — el contrato SSE aditivo (plan/aprobación/mapa) sobre el endpoint REAL.

`docs/specs/superficie-visual.md` §1 (decisión #66 fija el wire) + freeze §9
(extensión ADITIVA, sin tocar los payloads congelados). El seed
`tests/seeds/test_seed_superficie_plan_aprobacion.py` ya prueba que
`project_event`/`sse_frame` no degradan estos payloads; ESTE test cierra el
lazo end-to-end: los mismos payloads atraviesan `GET /runs/{id}/events`
(catch-up `?live=0`) intactos, framing §9 exacto (`id: global_seq`,
`event: <type>`, `data: <proyección>`). El endpoint SSE NO filtra por tipo:
los cuatro eventos nuevos fluyen igual que los congelados — eso ES la
aditividad, verificada contra la superficie HTTP, no solo la función pura.
"""

from __future__ import annotations

import json
from typing import Any, cast

import httpx
from chimera_api.app import create_app
from chimera_api.projection import project_event
from fastapi.testclient import TestClient

from blite.events import create_event_store
from blite.events.event import Event
from blite.events.store import EventStore

_RUN_ID = "run-superficie"

_PLAN_CREATED: dict[str, Any] = {
    "plan_id": "plan-1",
    "run_id": _RUN_ID,
    "items": [
        {
            "id": "item-1",
            "description": "Formular el QUBO Max-Cut",
            "verification": "formal_exact",
            "status": "pending",
        },
        {
            "id": "item-2",
            "description": "Correr QAOA",
            "verification": "execution",
            "status": "pending",
        },
    ],
}
_APPROVAL_REQUESTED: dict[str, Any] = {
    "run_id": _RUN_ID,
    "approval_id": "approval-1",
    "json_schema": {"type": "object", "properties": {"ok": {"type": "boolean"}}},
    "prompt": "¿Autorizar la relajación de PR2 para esta corrida?",
    "step_id": "item-2",
}
_PARTITION: dict[str, Any] = {
    "topology_ref": "ieee14-topology@v1",
    "islands": [
        {
            "id": "island-a",
            "name": "Isla A",
            "bus_ids": ["1", "2", "3"],
            "verification": {
                "verdict": "pass",
                "verifier_class": "execution",
                "level": "AL3",
                "anchor_kind": "execution",
                "method": "pandapower-powerflow",
                "summary": "Flujo de potencia converge",
            },
        },
        {
            "id": "island-b",
            "name": "Isla B",
            "bus_ids": ["4", "5"],
            "verification": {
                "verdict": "pass",
                "verifier_class": "execution",
                "level": "AL3",
                "anchor_kind": "execution",
                "method": "pandapower-powerflow",
                "summary": "Flujo de potencia converge",
            },
        },
    ],
    "cut_branch_ids": ["L3-4"],
    "cut_cost": 1,
}


def _append(store: EventStore, type_: str, payload: dict[str, Any], seq: int) -> Event:
    return store.append(
        stream_id=_RUN_ID,
        type=type_,
        actor_id="agent:planner-7",
        domain_id="d-default",
        payload=payload,
        expected_seq=seq if seq > 0 else None,
    )


def _seed_superficie_run(store: EventStore) -> None:
    """Un run que emite los cuatro tipos aditivos + una partición por-isla,
    entre los eventos de ciclo de vida congelados."""
    _append(store, "run.created", {"run_id": _RUN_ID}, 0)
    _append(store, "plan.created", _PLAN_CREATED, 1)
    _append(
        store,
        "plan.item_updated",
        {"plan_id": "plan-1", "run_id": _RUN_ID, "item_id": "item-1", "status": "ok"},
        2,
    )
    _append(store, "approval.requested", _APPROVAL_REQUESTED, 3)
    _append(
        store,
        "approval.responded",
        {
            "run_id": _RUN_ID,
            "approval_id": "approval-1",
            "response": {"ok": True},
            "authorized_by": "user:dylan",
        },
        4,
    )
    _append(store, "verification.completed", _PARTITION, 5)
    _append(store, "run.completed", {}, 6)


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


def _get(client: TestClient, url: str) -> httpx.Response:
    # Mismo pyright-ignore que test_app_sse.py: TestClient.get anota contra
    # httpx2 (no instalado); el runtime real es httpx.
    return cast(
        httpx.Response,
        client.get(url),  # pyright: ignore[reportUnknownMemberType]
    )


def _frames_by_type(store: EventStore) -> dict[str, dict[str, str]]:
    client = TestClient(create_app(store))
    response = _get(client, f"/runs/{_RUN_ID}/events?live=0")
    assert response.status_code == 200
    return {f["event"]: f for f in _parse_frames(response.text)}


class TestAditividadSobreElStreamReal:
    def test_los_cuatro_tipos_nuevos_no_se_filtran_del_stream(self) -> None:
        # Arrange
        store = create_event_store()
        _seed_superficie_run(store)

        # Act
        client = TestClient(create_app(store))
        response = _get(client, f"/runs/{_RUN_ID}/events?live=0")

        # Assert — los aditivos VIAJAN junto a los congelados (endpoint no
        # filtra por type); aditividad = cero eventos perdidos.
        types = [f["event"] for f in _parse_frames(response.text)]
        assert types == [
            "run.created",
            "plan.created",
            "plan.item_updated",
            "approval.requested",
            "approval.responded",
            "verification.completed",
            "run.completed",
        ]

    def test_plan_created_viaja_con_items_y_status_intactos(self) -> None:
        # Arrange / Act
        store = create_event_store()
        _seed_superficie_run(store)
        frame = _frames_by_type(store)["plan.created"]

        # Assert — payload íntegro, cero recorte de items/status/verification
        data = json.loads(frame["data"])
        assert data["payload"] == _PLAN_CREATED
        assert data["payload"]["items"][0]["status"] == "pending"
        assert data["payload"]["items"][1]["verification"] == "execution"

    def test_approval_requested_conserva_schema_prompt_y_step_id(self) -> None:
        # Arrange / Act
        store = create_event_store()
        _seed_superficie_run(store)
        frame = _frames_by_type(store)["approval.requested"]

        # Assert — json_schema y prompt intactos; step_id promovido a
        # top-level (regla project_event) Y preservado en el payload.
        data = json.loads(frame["data"])
        assert data["payload"] == _APPROVAL_REQUESTED
        assert data["step_id"] == "item-2"
        assert data["payload"]["json_schema"]["properties"]["ok"]["type"] == "boolean"

    def test_particion_lleva_verification_por_isla_intacta(self) -> None:
        # Arrange / Act — freeze §9: verification POR ISLA, nunca solo global.
        store = create_event_store()
        _seed_superficie_run(store)
        frame = _frames_by_type(store)["verification.completed"]

        # Assert
        data = json.loads(frame["data"])
        islands = data["payload"]["islands"]
        assert len(islands) == 2
        assert all("verification" in island for island in islands)
        assert islands[0]["verification"]["level"] == "AL3"
        assert data["payload"] == _PARTITION

    def test_framing_exacto_para_plan_created(self) -> None:
        # Arrange
        store = create_event_store()
        _seed_superficie_run(store)
        plan_event = next(
            e for e in store.read_stream(_RUN_ID) if e.type == "plan.created"
        )

        # Act
        frame = _frames_by_type(store)["plan.created"]

        # Assert — id = global_seq, data = proyección exacta (framing §9).
        assert int(frame["id"]) == plan_event.global_seq
        assert json.loads(frame["data"]) == project_event(plan_event)
