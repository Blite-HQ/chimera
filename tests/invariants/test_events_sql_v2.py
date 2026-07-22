"""
events SQL v2 — structural checks (ficha B2 piece 6).

docs/contract-freeze.md SS2 / knowledge/trust/01-event-sourcing-postgres.md
SS1.2-SS1.5: 3 changes over the seed schema (docs/esquema-datos.md SS1) —
global_seq as a monotonic cursor, REVOKE+trigger instead of silent rules,
and expected_seq concurrency semantics documented at the writer. No live
Postgres in this ficha (B2 explicitly excludes it — session 9's job); this
asserts the DDL text carries the required pieces rather than executing it.
"""

from __future__ import annotations

import re
from pathlib import Path

# [S-G Etapa 0] events_v2.sql superseded por init_v2.sql (único SQL ejecutable;
# el viejo conservaba el índice duplicado que [S-F · N6] eliminó). Los asserts
# de este archivo se sostienen sin cambio: son sobre la letra, no sobre nombres.
SQL_PATH = Path(__file__).resolve().parents[2] / "engine" / "sql" / "init_v2.sql"


def test_events_sql_file_exists() -> None:
    assert SQL_PATH.exists(), f"{SQL_PATH} is missing"


def test_events_table_has_a_monotonic_global_seq_cursor() -> None:
    sql = SQL_PATH.read_text(encoding="utf-8")
    assert re.search(r"global_seq\s+BIGINT\s+GENERATED\s+ALWAYS\s+AS\s+IDENTITY", sql)


def test_events_table_keeps_the_seed_stream_ordering_constraint() -> None:
    sql = SQL_PATH.read_text(encoding="utf-8")
    assert re.search(r"UNIQUE\s*\(\s*stream_id\s*,\s*seq\s*\)", sql)


def test_append_only_fails_loud_via_revoke_and_trigger_not_silent_rules() -> None:
    sql = SQL_PATH.read_text(encoding="utf-8")
    # [S-G] el chequeo es sobre SQL ejecutable: la letra v2 menciona la regla
    # vieja en un COMENTARIO ("las reglas silenciosas ... se reemplazan").
    executable = re.sub(r"--[^\n]*", "", sql)
    assert "DO INSTEAD NOTHING" not in executable, (
        "silent rules are exactly what note 01 SS1.2 replaces"
    )
    assert re.search(r"REVOKE\s+UPDATE\s*,\s*DELETE\s+ON\s+events", sql)
    assert "RAISE EXCEPTION" in sql
    assert re.search(r"BEFORE\s+UPDATE\s+OR\s+DELETE\s+ON\s+events", sql)


def test_actor_id_and_domain_id_remain_not_null() -> None:
    sql = SQL_PATH.read_text(encoding="utf-8")
    assert re.search(r"actor_id\s+TEXT\s+NOT\s+NULL", sql)
    assert re.search(r"domain_id\s+TEXT\s+NOT\s+NULL", sql)
