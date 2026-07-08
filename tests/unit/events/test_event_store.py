"""
EventStore port + in-memory implementation (ficha B2 piece 6).

docs/contract-freeze.md SS2 / knowledge/trust/01-event-sourcing-postgres.md
SS1.5: append/read_stream/read_all, optimistic concurrency via expected_seq,
global_seq as a monotonic cross-stream cursor. INV-5 stays intact: only
blite.events.* may import blite.events.writer — everything else goes through
create_event_store()/EventStore (blite.events.__init__ / .store).
"""

from __future__ import annotations

import pytest

from blite.events import ConcurrentAppendError, EventStore, create_event_store


def _store() -> EventStore:
    return create_event_store()


def test_append_returns_an_event_with_seq_one_and_global_seq_one_for_a_fresh_stream() -> (
    None
):
    store = _store()
    event = store.append(
        stream_id="run:1",
        type="run.started",
        actor_id="user:dylan",
        domain_id="d-default",
        payload={},
    )
    assert event.seq == 1
    assert event.global_seq == 1
    assert event.stream_id == "run:1"
    assert event.actor_id == "user:dylan"


def test_append_increments_seq_within_a_stream_and_global_seq_across_streams() -> None:
    store = _store()
    store.append(
        stream_id="run:1",
        type="run.started",
        actor_id="user:dylan",
        domain_id="d-default",
        payload={},
    )
    second_same_stream = store.append(
        stream_id="run:1",
        type="tool.invoked",
        actor_id="user:dylan",
        domain_id="d-default",
        payload={},
    )
    first_other_stream = store.append(
        stream_id="run:2",
        type="run.started",
        actor_id="user:dylan",
        domain_id="d-default",
        payload={},
    )

    assert second_same_stream.seq == 2
    assert second_same_stream.global_seq == 2
    assert first_other_stream.seq == 1
    assert first_other_stream.global_seq == 3


def test_read_stream_returns_only_that_streams_events_in_seq_order() -> None:
    store = _store()
    store.append(
        stream_id="run:1",
        type="run.started",
        actor_id="user:dylan",
        domain_id="d-default",
        payload={},
    )
    store.append(
        stream_id="run:2",
        type="run.started",
        actor_id="user:dylan",
        domain_id="d-default",
        payload={},
    )
    store.append(
        stream_id="run:1",
        type="run.completed",
        actor_id="user:dylan",
        domain_id="d-default",
        payload={},
    )

    events = store.read_stream("run:1")
    assert [e.type for e in events] == ["run.started", "run.completed"]
    assert all(e.stream_id == "run:1" for e in events)


def test_read_stream_from_seq_excludes_already_seen_events() -> None:
    store = _store()
    store.append(
        stream_id="run:1",
        type="run.started",
        actor_id="user:dylan",
        domain_id="d-default",
        payload={},
    )
    store.append(
        stream_id="run:1",
        type="run.completed",
        actor_id="user:dylan",
        domain_id="d-default",
        payload={},
    )

    events = store.read_stream("run:1", from_seq=1)
    assert [e.type for e in events] == ["run.completed"]


def test_read_all_is_the_cross_stream_cursor_for_sse_catchup() -> None:
    store = _store()
    store.append(
        stream_id="run:1",
        type="run.started",
        actor_id="user:dylan",
        domain_id="d-default",
        payload={},
    )
    store.append(
        stream_id="run:2",
        type="run.started",
        actor_id="user:dylan",
        domain_id="d-default",
        payload={},
    )

    caught_up = store.read_all(from_global_seq=1)
    assert len(caught_up) == 1
    assert caught_up[0].global_seq == 2
    assert caught_up[0].stream_id == "run:2"


def test_expected_seq_conflict_raises_and_does_not_append() -> None:
    store = _store()
    store.append(
        stream_id="run:1",
        type="run.started",
        actor_id="user:dylan",
        domain_id="d-default",
        payload={},
    )

    with pytest.raises(ConcurrentAppendError):
        store.append(
            stream_id="run:1",
            type="tool.invoked",
            actor_id="user:dylan",
            domain_id="d-default",
            payload={},
            expected_seq=0,
        )

    assert len(store.read_stream("run:1")) == 1


def test_expected_seq_matching_current_position_succeeds() -> None:
    store = _store()
    store.append(
        stream_id="run:1",
        type="run.started",
        actor_id="user:dylan",
        domain_id="d-default",
        payload={},
    )
    event = store.append(
        stream_id="run:1",
        type="tool.invoked",
        actor_id="user:dylan",
        domain_id="d-default",
        payload={},
        expected_seq=1,
    )
    assert event.seq == 2


def test_appended_event_is_frozen() -> None:
    from pydantic import ValidationError

    store = _store()
    event = store.append(
        stream_id="run:1",
        type="run.started",
        actor_id="user:dylan",
        domain_id="d-default",
        payload={},
    )
    with pytest.raises(ValidationError):
        event.type = "mutated"
