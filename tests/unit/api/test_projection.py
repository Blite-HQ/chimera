"""Proyección para UI + frame SSE — spec confianza-api-sse (freeze §9).

`data:` = JSON del evento proyectado (subset del Event: SIN hashes), con
`id:` = global_seq y `event:` = type. La proyección jamás recorta el payload
(regla de forma: ningún resultado sin su bloque `verification`).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from chimera_api.projection import project_event, sse_frame

from blite.events.event import Event


def _event(**overrides: Any) -> Event:
    base: dict[str, Any] = {
        "id": uuid4(),
        "stream_id": "8f2c1a9b",
        "seq": 1,
        "global_seq": 41,
        "type": "run.created",
        "actor_id": "user:dylan",
        "domain_id": "d-default",
        "payload": {"run_id": "8f2c1a9b"},
        "occurred_at": datetime(2026, 7, 22, 12, 0, 1, tzinfo=UTC),
        "prev_hash": None,
        "hash": "deadbeef" * 8,
    }
    base.update(overrides)
    return Event(**base)


class TestProjectEvent:
    def test_incluye_los_minimos_de_trust07_y_excluye_hashes(self) -> None:
        # Arrange
        event = _event()

        # Act
        projected = project_event(event)

        # Assert — mínimos del timeline (trust/07 §1.3) + payload íntegro
        assert projected["global_seq"] == 41
        assert projected["type"] == "run.created"
        assert projected["actor_id"] == "user:dylan"
        assert projected["payload"] == {"run_id": "8f2c1a9b"}
        # subset del Event: sin prev_hash/hash (freeze §9)
        assert "hash" not in projected
        assert "prev_hash" not in projected
        assert "id" not in projected

    def test_occurred_at_es_rfc3339_con_z(self) -> None:
        projected = project_event(_event())
        assert projected["occurred_at"] == "2026-07-22T12:00:01Z"

    def test_step_id_aflora_cuando_el_payload_lo_trae(self) -> None:
        with_step = project_event(_event(payload={"step_id": "s1"}))
        without_step = project_event(_event())
        assert with_step["step_id"] == "s1"
        assert "step_id" not in without_step

    def test_resumen_pasa_del_payload_o_degrada_al_type(self) -> None:
        explicit = project_event(_event(payload={"resumen": "Corte óptimo confirmado"}))
        fallback = project_event(_event(type="verification.completed"))
        assert explicit["resumen"] == "Corte óptimo confirmado"
        assert fallback["resumen"] == "verification.completed"

    def test_el_bloque_verification_sobrevive_integro(self) -> None:
        # freeze §9: ningún payload de resultado sin su bloque verification —
        # la proyección no lo recorta ni lo reescribe.
        verification = {
            "verdict": "pass",
            "verifier_class": "execution",
            "level": "AL3",
        }
        projected = project_event(
            _event(
                type="verification.completed", payload={"verification": verification}
            )
        )
        assert projected["payload"]["verification"] == verification


class TestSseFrame:
    def test_forma_exacta_del_frame(self) -> None:
        # Arrange
        event = _event(global_seq=7, type="run.completed", payload={})

        # Act
        frame = sse_frame(event)

        # Assert — id = global_seq · event = type · data = proyección JSON
        lines = frame.split("\n")
        assert lines[0] == "id: 7"
        assert lines[1] == "event: run.completed"
        assert lines[2].startswith("data: ")
        assert frame.endswith("\n\n")
        data = json.loads(lines[2].removeprefix("data: "))
        assert data == project_event(event)

    def test_data_es_una_sola_linea(self) -> None:
        # JSON compacto: un payload multilínea rompería el framing SSE.
        frame = sse_frame(_event(payload={"a": "x\ny", "b": [1, 2]}))
        body = frame.removesuffix("\n\n")
        assert len(body.split("\n")) == 3
