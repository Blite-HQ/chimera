"""SEED · superficie visual (Dylan) — spec `docs/specs/superficie-visual.md`.

freeze §9: ningún payload de resultado sin su bloque `verification` — la
proyección NO recorta el payload, viaja intacto tal como el emisor lo
estampó. Decisión #66 (`docs/mvp/decisiones.md`) fija el wire de
`plan.created`/`plan.item_updated`/`approval.requested`/`approval.responded`
que el harness (A, `harness-agentico.md`) emitirá — este seed NO espera a que
ese harness exista: `chimera_api.projection.project_event`/`sse_frame`
(spec `confianza-api-sse.md`) ya son type-agnostic hoy (no distinguen por
`event.type`), así que el contrato "estos payloads nuevos sobreviven
íntegros a la proyección" es verificable YA, contra el `Event` genérico.

VERDE (2026-07-24): verificado que la proyección no recorta ni reescribe
ningún campo — import a nivel de módulo, mismo patrón que
`tests/unit/api/test_projection.py`.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from chimera_api.projection import project_event, sse_frame

from blite.events.event import Event

pytestmark = [pytest.mark.seed]


def _event(**overrides: Any) -> Event:
    base: dict[str, Any] = {
        "id": uuid4(),
        "stream_id": "run-plan-demo",
        "seq": 1,
        "global_seq": 100,
        "type": "plan.created",
        "actor_id": "agent:planner-7",
        "domain_id": "d-default",
        "payload": {},
        "occurred_at": datetime(2026, 7, 24, 9, 0, 0, tzinfo=UTC),
        "prev_hash": None,
        "hash": "cafebabe" * 8,
    }
    base.update(overrides)
    return Event(**base)


class TestPlanCreatedSurvivesProjection:
    def test_plan_created_payload_survives_intact(self) -> None:
        # Arrange — el wire canónico de decisión #66 (superficie-visual §1)
        payload = {
            "plan_id": "plan-1",
            "run_id": "run-plan-demo",
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
        event = _event(type="plan.created", payload=payload)

        # Act
        projected = project_event(event)

        # Assert — payload íntegro, cero recorte de items/status
        assert projected["type"] == "plan.created"
        assert projected["payload"] == payload
        assert projected["payload"]["items"][0]["status"] == "pending"

    def test_plan_item_updated_survives_intact(self) -> None:
        payload = {
            "plan_id": "plan-1",
            "run_id": "run-plan-demo",
            "item_id": "item-1",
            "status": "ok",
        }
        projected = project_event(
            _event(type="plan.item_updated", payload=payload, global_seq=101)
        )
        assert projected["payload"] == payload

    def test_plan_item_updated_carries_cause_when_present(self) -> None:
        # replanificar = append con causa (superficie-visual §2) — jamás
        # re-entrada silenciosa: si el emisor estampa `cause`, sobrevive.
        payload = {
            "plan_id": "plan-1",
            "run_id": "run-plan-demo",
            "item_id": "item-2",
            "status": "failed",
            "cause": "capability timeout",
        }
        projected = project_event(
            _event(type="plan.item_updated", payload=payload, global_seq=102)
        )
        assert projected["payload"]["cause"] == "capability timeout"


class TestApprovalSurvivesProjection:
    def test_approval_requested_payload_survives_intact(self) -> None:
        payload = {
            "run_id": "run-plan-demo",
            "approval_id": "approval-1",
            "json_schema": {
                "type": "object",
                "properties": {"ok": {"type": "boolean"}},
            },
            "prompt": "¿Autorizar la relajación de PR2 para esta corrida?",
            "step_id": "item-2",
        }
        event = _event(type="approval.requested", payload=payload, global_seq=103)

        projected = project_event(event)

        assert projected["payload"] == payload
        # step_id promovido a top-level (regla existente de project_event) Y
        # preservado dentro del payload — ninguna de las dos formas se pierde.
        assert projected["step_id"] == "item-2"
        assert projected["payload"]["step_id"] == "item-2"

    def test_approval_responded_payload_survives_intact(self) -> None:
        payload = {
            "run_id": "run-plan-demo",
            "approval_id": "approval-1",
            "response": {"ok": True},
            "authorized_by": "user:dylan",
        }
        projected = project_event(
            _event(type="approval.responded", payload=payload, global_seq=104)
        )
        assert projected["payload"] == payload

    def test_sse_frame_forma_exacta_para_approval_requested(self) -> None:
        # freeze §9 framing: id = global_seq, event = type, data en una línea.
        event = _event(
            type="approval.requested",
            global_seq=105,
            payload={
                "run_id": "run-plan-demo",
                "approval_id": "approval-2",
                "json_schema": {"type": "object"},
                "prompt": "¿Continuar?",
            },
        )
        frame = sse_frame(event)
        lines = frame.split("\n")
        assert lines[0] == "id: 105"
        assert lines[1] == "event: approval.requested"
        data = json.loads(lines[2].removeprefix("data: "))
        assert data == project_event(event)


class TestTopologyVerificationPerIsland:
    def test_partition_result_carries_verification_per_island_intact(self) -> None:
        # freeze §9, regla de forma validada por el spike (trust/07 §1.4): el
        # resultado de partición lleva `verification` POR ISLA, no solo un
        # bloque global — superficie-visual.md §4 formaliza este shape.
        payload = {
            "topology_ref": "ieee14-topology@v1",
            "islands": [
                {
                    "id": "island-a",
                    "name": "Isla A",
                    "bus_ids": ["1", "2", "3", "4", "5"],
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
                    "bus_ids": ["6", "7", "8", "9", "10", "11", "12", "13", "14"],
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
            "cut_branch_ids": ["L4-7", "L4-9", "L5-6"],
            "cut_cost": 3,
        }
        event = _event(type="verification.completed", payload=payload, global_seq=106)

        projected = project_event(event)

        # Nada se recorta: CADA isla conserva su propio bloque verification.
        islands = projected["payload"]["islands"]
        assert len(islands) == 2
        assert all("verification" in island for island in islands)
        assert islands[0]["verification"]["verdict"] == "pass"
        assert islands[1]["verification"]["level"] == "AL3"
        assert projected["payload"] == payload
