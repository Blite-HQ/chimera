"""Organization — projects within a domain (public read/write interface).

Espejo de `blite.events` (docstring `events/__init__.py:1`): el Protocol del
puerto (`ProjectRepository`) y el modelo inmutable (`Project`) viven acá; los
DOS adapters (`memory.py`, `postgres.py`) están detrás del mismo puerto —
nadie fuera de este paquete elige uno directamente, siempre vía
`create_project_repository()` (mismo criterio que `create_event_store`).

`docs/esquema-datos-v2.md` §2 (ceremonia #176): `projects` agrupa runs
dentro de un dominio; `run.created.project_id` es una referencia OPACA — el
EVENTO no valida esa FK, la valida quien construye el run contra ESTE
puerto (F1.1, `chimera_api.runs._start_mission_run`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Project:
    """Una fila de `projects` (`docs/esquema-datos-v2.md` §2) — inmutable:
    nada la muta en sitio; `ProjectRepository.create` devuelve una instancia
    persistida, jamás modifica la que recibió."""

    id: str
    domain_id: str
    name: str
    created_at: datetime


class ProjectAlreadyExistsError(Exception):
    """`ProjectRepository.create` sobre un `id` ya tomado — explícito, jamás
    un upsert silencioso (mismo espíritu que `ConcurrentAppendError` de
    `blite.events.store`)."""


@runtime_checkable
class ProjectRepository(Protocol):
    """El único puerto de lectura/escritura de `projects` — espejo de
    `EventStore`."""

    def list_projects(self, domain_id: str) -> tuple[Project, ...]:
        """Los projects de un dominio, orden estable (creación, luego id)."""
        ...

    def get(self, project_id: str) -> Project | None:
        """`None` si `project_id` no existe — jamás una excepción por leer."""
        ...

    def create(self, project: Project) -> Project:
        """Persiste `project`; `ProjectAlreadyExistsError` si el `id` ya existe."""
        ...

    def ensure_domain(self, domain_id: str, owner_id: str) -> None:
        """Idempotente: crea la fila de `domains` si faltaba, no-op si ya
        estaba (el wiring del API la llama en cada arranque, ítem F1.1 #2)."""
        ...


def create_project_repository(dsn: str | None = None) -> ProjectRepository:
    """Construye un `ProjectRepository` detrás del único puerto (mismo
    criterio que `blite.events.create_event_store`).

    Con DSN (argumento o `CHIMERA_DATABASE_URL`) devuelve el adapter Postgres
    durable; sin DSN, el in-memory de Fase 1. Only `blite.organization.*` may
    import `memory`/`postgres` directamente (contrato import-linter
    "organization: ...") — todo el mundo pasa por acá."""
    resolved = dsn or os.environ.get("CHIMERA_DATABASE_URL")
    if resolved:
        from blite.organization.postgres import PostgresProjectRepository

        return PostgresProjectRepository(resolved)
    from blite.organization.memory import InMemoryProjectRepository

    return InMemoryProjectRepository()


__all__ = [
    "Project",
    "ProjectAlreadyExistsError",
    "ProjectRepository",
    "create_project_repository",
]
