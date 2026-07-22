"""Reglas S-F/stress-final del log (freeze §2): streams de sistema, reserva de
namespace, rechazo post-terminal y corte del provenance_hash."""

from __future__ import annotations

import pytest

from blite.events import create_event_store
from blite.events.rules import (
    PostTerminalAppendError,
    is_system_stream,
    provenance_slice,
    validate_run_id,
)


def _append(store, stream_id: str, type: str):  # noqa: ANN001, ANN202 - helper local
    return store.append(
        stream_id=stream_id,
        type=type,
        actor_id="service:runtime",
        domain_id="d1",
        payload={},
    )


def test_post_terminal_step_append_is_rejected_loud() -> None:
    # Arrange
    store = create_event_store()
    _append(store, "r1", "run.created")
    _append(store, "r1", "run.completed")

    # Act / Assert — freeze §2 [S-F]: jamás "aceptar marcado late"
    with pytest.raises(PostTerminalAppendError):
        _append(store, "r1", "run.step.started")
    with pytest.raises(PostTerminalAppendError):
        _append(store, "r1", "capability.job.submitted")


def test_closure_families_are_accepted_after_the_terminal() -> None:
    # Arrange
    store = create_event_store()
    _append(store, "r1", "run.created")
    _append(store, "r1", "run.failed")

    # Act — familia de cierre (freeze §2 [stress-final])
    event = _append(store, "r1", "run.metrics.recorded")

    # Assert
    assert event.seq == 3


def test_provenance_slice_cuts_at_the_terminal_inclusive() -> None:
    # Arrange — cierre post-terminal FUERA del hash
    store = create_event_store()
    _append(store, "r1", "run.created")
    _append(store, "r1", "run.step.started")
    _append(store, "r1", "run.completed")
    _append(store, "r1", "run.metrics.recorded")

    # Act
    sliced = provenance_slice(store.read_stream("r1"))

    # Assert
    assert [e.type for e in sliced] == [
        "run.created",
        "run.step.started",
        "run.completed",
    ]


def test_provenance_slice_refuses_a_live_run() -> None:
    # Arrange
    store = create_event_store()
    _append(store, "r1", "run.created")

    # Act / Assert — sin terminal no hay corte definido
    with pytest.raises(ValueError, match="terminal"):
        provenance_slice(store.read_stream("r1"))


def test_system_streams_never_enter_the_provenance_hash() -> None:
    # Arrange
    store = create_event_store()
    _append(store, "system:registry", "registry.loaded")

    # Act / Assert
    assert is_system_stream("system:registry")
    with pytest.raises(ValueError, match="sistema"):
        provenance_slice(store.read_stream("system:registry"))


def test_run_id_cannot_invade_the_system_namespace() -> None:
    # Act / Assert — reserva de namespace (freeze §2 [stress-final])
    assert validate_run_id("8f2c1a9b") == "8f2c1a9b"
    with pytest.raises(ValueError, match="system:"):
        validate_run_id("system:sneaky")
