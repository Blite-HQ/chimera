"""SEED · ejecución/confianza (frontera) — palanca EX-5.

freeze §6 [S-F · EX-5]: al aplicar un `○PolicyChanged` que ENDURECE, el runtime
abre `●EscalationOpened` sobre los cases en vuelo cuyo `policy_digest` pinneado
quedó por debajo de la nueva exigencia. El pin no cambia (R-Pol1): la palanca
es alarma, jamás revocación. Verde cuando exista el handler.
"""

from __future__ import annotations

import pytest

from blite.events import create_event_store

pytestmark = [
    pytest.mark.seed,
    pytest.mark.xfail(
        strict=False,
        reason="SEED S-G (frontera Dylan/Steven): handler de ○PolicyChanged aún no existe",
    ),
]


def test_a_hardened_policy_opens_escalations_over_in_flight_cases() -> None:
    # Arrange — un run en vuelo pinneado a la policy vieja
    store = create_event_store()
    store.append(
        stream_id="r1",
        type="run.created",
        actor_id="user:test",
        domain_id="d1",
        payload={"run_id": "r1", "max_steps": 5, "policy_digest": "sha256:old"},
    )

    # Act — API a fijar; el seed fija la CONDUCTA (freeze §6 EX-5)
    from blite.runtime.policy_watch import (  # pyright: ignore[reportMissingImports]
        on_policy_changed,  # pyright: ignore[reportUnknownVariableType]
    )

    on_policy_changed(
        store,
        old_digest="sha256:old",
        new_digest="sha256:new",
        hardened=True,
    )

    # Assert — alarma sobre el case en vuelo; el pin NO cambia
    types = [e.type for e in store.read_stream("r1")]
    assert "escalation.opened" in types or any("Escalation" in t for t in types)
    created = store.read_stream("r1")[0]
    assert created.payload["policy_digest"] == "sha256:old"
