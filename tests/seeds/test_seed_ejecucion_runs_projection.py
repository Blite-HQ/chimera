"""SEED · ejecución (Steven) — runs_projection regenerable por replay.

freeze §3 [stress-final]: el payload de `run.created` carga TODO lo que
`runs_projection` necesita (`policy_digest`, `parent_run_id?`, digests de
definición, `max_steps`) — "un replay de events regenera la proyección" debe
ser verdad ejecutable, no doctrina. Verde cuando exista el proyector.
"""

from __future__ import annotations

from typing import Any, cast

import pytest

from blite.events import create_event_store

pytestmark = [
    pytest.mark.seed,
    pytest.mark.xfail(
        strict=False,
        reason="SEED S-G (Steven): el proyector de runs aún no existe (blite.runtime.projection)",
    ),
]


def test_replay_of_the_log_regenerates_the_full_run_row() -> None:
    # Arrange — el evento fundacional carga el payload completo (freeze §3)
    store = create_event_store()
    store.append(
        stream_id="r1",
        type="run.created",
        actor_id="user:test",
        domain_id="d1",
        payload={
            "run_id": "r1",
            "actor_id": "user:test",
            "domain_id": "d1",
            "max_steps": 10,
            "policy_digest": "sha256:pp",
            "parent_run_id": None,
        },
    )
    store.append(
        stream_id="r1",
        type="run.completed",
        actor_id="service:runtime",
        domain_id="d1",
        payload={},
    )

    # Act — API a fijar por Steven; el seed fija la CONDUCTA
    from blite.runtime.projection import (  # pyright: ignore[reportMissingImports]
        project_runs,  # pyright: ignore[reportUnknownVariableType]
    )

    rows = cast(Any, project_runs(store.read_all()))

    # Assert — la fila completa sale SOLO del log
    row = rows["r1"]
    assert row.status == "completed"
    assert row.max_steps == 10
    assert row.policy_digest == "sha256:pp"
    assert row.parent_run_id is None
