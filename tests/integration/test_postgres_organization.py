"""PostgresProjectRepository — el MISMO contrato del puerto, contra Postgres real.

Env-gated como el resto de los probes contra Postgres (`CHIMERA_TEST_DATABASE_URL`,
mismo patrón que `test_postgres_event_store.py` / `test_esquema_migration.py`):
sin DSN se salta, con DSN corre el contrato completo sobre un schema efímero al
que se aplica `engine/sql/init_v2.sql` tal cual — cero DDL paralelo en tests.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from blite.organization import Project, ProjectAlreadyExistsError
from blite.organization.postgres import PostgresProjectRepository

pytestmark = pytest.mark.skipif(
    not os.environ.get("CHIMERA_TEST_DATABASE_URL"),
    reason="contrato con Postgres real: exportá CHIMERA_TEST_DATABASE_URL",
)

ROOT = Path(__file__).resolve().parents[2]
INIT_SQL = ROOT / "engine" / "sql" / "init_v2.sql"

_NOW = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)


@pytest.fixture()
def pg_repo() -> Iterator[PostgresProjectRepository]:
    """Schema efímero + init_v2.sql aplicado + repo con search_path fijado."""
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
        repo = PostgresProjectRepository(conninfo)
        try:
            yield repo
        finally:
            repo.close()
    finally:
        with psycopg.connect(base, autocommit=True) as conn:
            conn.execute(f'DROP SCHEMA "{schema}" CASCADE')


def _project(
    project_id: str = "p1", domain_id: str = "d1", name: str = "Uno"
) -> Project:
    return Project(id=project_id, domain_id=domain_id, name=name, created_at=_NOW)


class TestPortContract:
    def test_ensure_domain_es_idempotente(
        self, pg_repo: PostgresProjectRepository
    ) -> None:
        pg_repo.ensure_domain("d1", "user:test")
        pg_repo.ensure_domain("d1", "user:test")  # segunda corrida — no explota

    def test_create_devuelve_la_fila_y_get_la_encuentra_despues(
        self, pg_repo: PostgresProjectRepository
    ) -> None:
        pg_repo.ensure_domain("d1", "user:test")

        created = pg_repo.create(_project())

        assert created.id == "p1"
        assert created.domain_id == "d1"
        assert created.name == "Uno"
        assert pg_repo.get("p1") == created

    def test_get_de_un_id_desconocido_es_none(
        self, pg_repo: PostgresProjectRepository
    ) -> None:
        assert pg_repo.get("desconocido") is None

    def test_create_con_id_repetido_explota_y_no_pisa_la_fila(
        self, pg_repo: PostgresProjectRepository
    ) -> None:
        pg_repo.ensure_domain("d1", "user:test")
        pg_repo.create(_project(name="original"))

        with pytest.raises(ProjectAlreadyExistsError):
            pg_repo.create(_project(name="pisador"))

        row = pg_repo.get("p1")
        assert row is not None
        assert row.name == "original"

    def test_create_sin_dominio_previo_explota_por_la_fk(
        self, pg_repo: PostgresProjectRepository
    ) -> None:
        """`projects.domain_id REFERENCES domains(id)` (init_v2.sql) — sin
        `ensure_domain` antes, el INSERT viola la FK del esquema congelado."""
        psycopg = pytest.importorskip("psycopg")

        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            pg_repo.create(_project(domain_id="dominio-inexistente"))

    def test_list_projects_aisla_por_dominio_y_ordena_por_creacion(
        self, pg_repo: PostgresProjectRepository
    ) -> None:
        pg_repo.ensure_domain("d1", "user:test")
        pg_repo.ensure_domain("d2", "user:test")
        pg_repo.create(_project(project_id="p2", domain_id="d1"))
        pg_repo.create(
            Project(
                id="p1", domain_id="d1", name="Uno", created_at=_NOW.replace(hour=1)
            )
        )
        pg_repo.create(_project(project_id="otro", domain_id="d2"))

        del_d1 = pg_repo.list_projects("d1")

        assert [p.id for p in del_d1] == ["p1", "p2"]
