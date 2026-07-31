"""
Esquema v2 — el doc es la letra; init_v2.sql es la traducción ejecutable. [S-G Etapa 0]

docs/esquema-datos-v2.md (SEMILLA v2, gobernada por contract-freeze.md) cierra con:
"La traducción a SQL real la gobierna contract-freeze.md". Este test hace esa regla
ejecutable en AMBAS direcciones: cada statement SQL de los bloques ```sql del doc
debe aparecer normalizado en engine/sql/init_v2.sql, y el init no puede cargar
statements sin respaldo en el doc (la dirección que produjo el índice duplicado
[S-F · N6] en el viejo events_v2.sql). El drift explota aquí, no en el
camino dorado.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = ROOT / "docs" / "esquema-datos-v2.md"
INIT_PATH = ROOT / "engine" / "sql" / "init_v2.sql"


def _normalized_statements(sql: str) -> set[str]:
    sql = re.sub(r"--[^\n]*", "", sql)
    sql = re.sub(r"\s+", " ", sql)
    return {s.strip() for s in sql.split(";") if s.strip()}


def _doc_sql() -> str:
    blocks = re.findall(
        r"```sql\n(.*?)```", DOC_PATH.read_text(encoding="utf-8"), re.DOTALL
    )
    return "\n".join(blocks)


def test_init_sql_exists() -> None:
    assert INIT_PATH.exists(), f"{INIT_PATH} is missing"


def test_every_doc_statement_lands_in_init_sql() -> None:
    missing = _normalized_statements(_doc_sql()) - _normalized_statements(
        INIT_PATH.read_text(encoding="utf-8")
    )
    assert not missing, (
        f"statements del doc ausentes en init_v2.sql: {sorted(missing)[:3]}"
    )


def test_init_sql_has_no_statements_outside_the_doc() -> None:
    extra = _normalized_statements(
        INIT_PATH.read_text(encoding="utf-8")
    ) - _normalized_statements(_doc_sql())
    assert not extra, (
        f"statements en init_v2.sql sin respaldo en el doc: {sorted(extra)[:3]}"
    )


@pytest.mark.skipif(
    not os.environ.get("CHIMERA_TEST_DATABASE_URL"),
    reason="probe con Postgres real: exportá CHIMERA_TEST_DATABASE_URL",
)
def test_init_sql_applies_and_events_fails_loud_on_update() -> None:
    """Aplica el init en una transacción (DDL transaccional en PG) y prueba el
    invariante conductual central: UPDATE sobre events EXPLOTA (INV-5), jamás
    no-op silencioso. Todo se revierte — cero residuo en la base."""
    psycopg = pytest.importorskip("psycopg")
    with psycopg.connect(os.environ["CHIMERA_TEST_DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute(INIT_PATH.read_text(encoding="utf-8"))
            cur.execute("INSERT INTO domains (id, owner_id) VALUES ('d1', 'user:test')")
            cur.execute(
                "INSERT INTO events (stream_id, seq, type, actor_id, domain_id, payload)"
                " VALUES ('r1', 1, 'run.created', 'user:test', 'd1', '{}')"
            )
            with pytest.raises(psycopg.errors.RaiseException):
                cur.execute("UPDATE events SET type = 'x' WHERE stream_id = 'r1'")
        conn.rollback()
