"""
PostgresProjectRepository — el MISMO puerto `ProjectRepository`, durable
sobre `domains`/`projects` (`docs/esquema-datos-v2.md` §2, init_v2.sql).

Mismo criterio que `blite.events.postgres` (docstring líneas 4-6): SOLO
`blite.organization.*` puede importar este módulo; el resto recibe el
repositorio vía `blite.organization.create_project_repository()` (contrato
import-linter "organization: only blite.organization writes projects via
postgres"). `ensure_domain` es un upsert idempotente (`ON CONFLICT (id) DO
NOTHING`) porque el bootstrap del wiring (F1.1 ítem 2) corre en cada
arranque del API — jamás debe fallar por correr dos veces.
"""

from __future__ import annotations

from typing import Any

from psycopg import errors
from psycopg_pool import ConnectionPool

from blite.organization import Project, ProjectAlreadyExistsError

_ENSURE_DOMAIN = """
INSERT INTO domains (id, owner_id) VALUES (%(id)s, %(owner_id)s)
ON CONFLICT (id) DO NOTHING
"""

_INSERT_PROJECT = """
INSERT INTO projects (id, domain_id, name, created_at)
VALUES (%(id)s, %(domain_id)s, %(name)s, %(created_at)s)
RETURNING id, domain_id, name, created_at
"""

_GET_PROJECT = "SELECT id, domain_id, name, created_at FROM projects WHERE id = %(id)s"

_LIST_PROJECTS = (
    "SELECT id, domain_id, name, created_at FROM projects "
    "WHERE domain_id = %(domain_id)s ORDER BY created_at, id"
)


def _row_to_project(row: tuple[Any, ...]) -> Project:
    return Project(id=row[0], domain_id=row[1], name=row[2], created_at=row[3])


class PostgresProjectRepository:
    """`ProjectRepository` durable sobre `domains`/`projects` de init_v2.sql."""

    def __init__(self, conninfo: str, *, min_size: int = 1, max_size: int = 4) -> None:
        self._pool = ConnectionPool(
            conninfo, min_size=min_size, max_size=max_size, open=True
        )

    def close(self) -> None:
        self._pool.close()

    def ensure_domain(self, domain_id: str, owner_id: str) -> None:
        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_ENSURE_DOMAIN, {"id": domain_id, "owner_id": owner_id})

    def create(self, project: Project) -> Project:
        with self._pool.connection() as conn, conn.cursor() as cur:
            try:
                cur.execute(
                    _INSERT_PROJECT,
                    {
                        "id": project.id,
                        "domain_id": project.domain_id,
                        "name": project.name,
                        "created_at": project.created_at,
                    },
                )
            except errors.UniqueViolation as exc:
                raise ProjectAlreadyExistsError(
                    f"project {project.id!r} ya existe"
                ) from exc
            inserted = cur.fetchone()
            if (
                inserted is None
            ):  # pragma: no cover — INSERT…RETURNING siempre trae fila
                raise ProjectAlreadyExistsError(
                    f"el INSERT sobre {project.id!r} no devolvió fila"
                )
            return _row_to_project(inserted)

    def get(self, project_id: str) -> Project | None:
        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_GET_PROJECT, {"id": project_id})
            row = cur.fetchone()
            return None if row is None else _row_to_project(row)

    def list_projects(self, domain_id: str) -> tuple[Project, ...]:
        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_LIST_PROJECTS, {"domain_id": domain_id})
            return tuple(_row_to_project(row) for row in cur.fetchall())


__all__ = ["PostgresProjectRepository"]
