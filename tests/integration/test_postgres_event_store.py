"""PostgresEventStore — el MISMO contrato del puerto, contra Postgres real.

Env-gated como el probe del esquema (`CHIMERA_TEST_DATABASE_URL`): sin DSN se
salta, con DSN corre el contrato completo sobre un schema efímero al que se
aplica `engine/sql/init_v2.sql` tal cual (la letra ejecutable — cero DDL
paralelo en tests). La concurrencia optimista vive en el UNIQUE
(stream_id, seq) del esquema; el rechazo post-terminal reusa las MISMAS
reglas de `blite.events.rules` que el store in-memory.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest

from blite.events.event import Event
from blite.events.postgres import PostgresEventStore
from blite.events.rules import PostTerminalAppendError
from blite.events.store import ConcurrentAppendError

pytestmark = pytest.mark.skipif(
    not os.environ.get("CHIMERA_TEST_DATABASE_URL"),
    reason="contrato con Postgres real: exportá CHIMERA_TEST_DATABASE_URL",
)

ROOT = Path(__file__).resolve().parents[2]
INIT_SQL = ROOT / "engine" / "sql" / "init_v2.sql"


@pytest.fixture()
def pg_store() -> Iterator[PostgresEventStore]:
    """Schema efímero + init_v2.sql aplicado + store con search_path fijado."""
    psycopg = pytest.importorskip("psycopg")
    from psycopg.conninfo import make_conninfo

    base = os.environ["CHIMERA_TEST_DATABASE_URL"]
    schema = f"t_{uuid4().hex[:12]}"
    with psycopg.connect(base, autocommit=True) as conn:
        conn.execute(f'CREATE SCHEMA "{schema}"')
    conninfo = make_conninfo(base, options=f"-c search_path={schema}")
    try:
        with psycopg.connect(conninfo) as conn:
            conn.execute(INIT_SQL.read_text(encoding="utf-8"))
            conn.commit()
        store = PostgresEventStore(conninfo)
        try:
            yield store
        finally:
            store.close()
    finally:
        with psycopg.connect(base, autocommit=True) as conn:
            conn.execute(f'DROP SCHEMA "{schema}" CASCADE')


def _append(
    store: PostgresEventStore,
    stream_id: str,
    type_: str,
    expected_seq: int | None = None,
) -> Event:
    return store.append(
        stream_id=stream_id,
        type=type_,
        actor_id="user:test",
        domain_id="d-default",
        payload={"k": "v"},
        expected_seq=expected_seq,
    )


class TestPortContract:
    def test_append_asigna_seq_y_global_seq_y_roundtrip_del_payload(
        self, pg_store: PostgresEventStore
    ) -> None:
        event = _append(pg_store, "r1", "run.created")
        assert event.seq == 1
        assert event.global_seq >= 1
        assert event.payload == {"k": "v"}
        assert event.occurred_at.tzinfo is not None

    def test_seq_por_stream_y_global_seq_cruzado_creciente(
        self, pg_store: PostgresEventStore
    ) -> None:
        first = _append(pg_store, "r1", "run.created")
        other = _append(pg_store, "r2", "run.created")
        second = _append(pg_store, "r1", "run.step.started", expected_seq=1)
        assert (first.seq, second.seq, other.seq) == (1, 2, 1)
        assert first.global_seq < other.global_seq < second.global_seq

    def test_read_stream_ordenado_y_con_cursor(
        self, pg_store: PostgresEventStore
    ) -> None:
        _append(pg_store, "r1", "run.created")
        _append(pg_store, "r2", "run.created")
        _append(pg_store, "r1", "run.step.started", expected_seq=1)
        assert [e.type for e in pg_store.read_stream("r1")] == [
            "run.created",
            "run.step.started",
        ]
        assert [e.seq for e in pg_store.read_stream("r1", from_seq=1)] == [2]

    def test_read_all_es_el_cursor_global_para_sse(
        self, pg_store: PostgresEventStore
    ) -> None:
        first = _append(pg_store, "r1", "run.created")
        _append(pg_store, "r2", "run.created")
        tail = pg_store.read_all(from_global_seq=first.global_seq)
        assert [e.stream_id for e in tail] == ["r2"]

    def test_conflicto_de_expected_seq_explota_y_no_apendea(
        self, pg_store: PostgresEventStore
    ) -> None:
        _append(pg_store, "r1", "run.created")
        with pytest.raises(ConcurrentAppendError):
            _append(pg_store, "r1", "run.step.started", expected_seq=0)
        assert len(pg_store.read_stream("r1")) == 1

    def test_expected_seq_adelantado_explota_sin_dejar_hueco(
        self, pg_store: PostgresEventStore
    ) -> None:
        _append(pg_store, "r1", "run.created")
        with pytest.raises(ConcurrentAppendError):
            _append(pg_store, "r1", "run.step.started", expected_seq=5)
        assert [e.seq for e in pg_store.read_stream("r1")] == [1]

    def test_rechazo_post_terminal(self, pg_store: PostgresEventStore) -> None:
        _append(pg_store, "r1", "run.created")
        _append(pg_store, "r1", "run.completed", expected_seq=1)
        with pytest.raises(PostTerminalAppendError):
            _append(pg_store, "r1", "run.step.started", expected_seq=2)

    def test_familias_de_cierre_pasan_post_terminal(
        self, pg_store: PostgresEventStore
    ) -> None:
        # freeze §2: métricas/familias de cierre quedan FUERA del corte del
        # hash y NO se rechazan tras el terminal.
        _append(pg_store, "r1", "run.created")
        _append(pg_store, "r1", "run.completed", expected_seq=1)
        event = _append(pg_store, "r1", "run.metrics.recorded", expected_seq=2)
        assert event.seq == 3
