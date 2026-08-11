"""
In-memory `ProjectRepository` — house style de `blite.events.writer`: un
proceso, no durable, Fase 1. El estado interno (dicts protegidos por lock)
se muta en sitio como el resto de los stores in-memory de este repo; lo que
NUNCA se muta es el `Project` que sale por el puerto — `create` devuelve la
misma instancia inmutable que recibió, jamás una copia parcheada.
"""

from __future__ import annotations

import threading

from blite.organization import Project, ProjectAlreadyExistsError


class InMemoryProjectRepository:
    """In-memory `ProjectRepository` — vive y muere con el proceso."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._projects: dict[str, Project] = {}
        self._domain_owners: dict[str, str] = {}

    def ensure_domain(self, domain_id: str, owner_id: str) -> None:
        with self._lock:
            self._domain_owners.setdefault(domain_id, owner_id)

    def create(self, project: Project) -> Project:
        with self._lock:
            if project.id in self._projects:
                raise ProjectAlreadyExistsError(f"project {project.id!r} ya existe")
            self._projects[project.id] = project
            return project

    def get(self, project_id: str) -> Project | None:
        with self._lock:
            return self._projects.get(project_id)

    def list_projects(self, domain_id: str) -> tuple[Project, ...]:
        with self._lock:
            matches = tuple(
                p for p in self._projects.values() if p.domain_id == domain_id
            )
        return tuple(sorted(matches, key=lambda p: (p.created_at, p.id)))


__all__ = ["InMemoryProjectRepository"]
