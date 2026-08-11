"""
`GET /projects`, `POST /projects` — el sistema organizacional del Studio
(F1.1, ítem 1 de `docs/mejorado/09-cierre.md` §2·F1, ceremonia #176 sobre el
esquema). La fila relacional YA existe (`docs/esquema-datos-v2.md` §2); este
módulo la sirve y siembra el proyecto neutro que todo despliegue necesita
ANTES de que exista ningún otro.

**Por qué la semilla es neutra:** decisión #173.1 — los datos de un caso de
uso concreto son material de prueba y validación, jamás un activo del
producto. El proyecto por defecto no puede nombrar ninguno.
"""

# pyright: reportUnusedFunction=false
# ^ Los handlers de FastAPI se registran por DECORADOR, no por llamada
#   (mismo motivo que el resto de los routers de este paquete).

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from blite.organization import Project, ProjectAlreadyExistsError, ProjectRepository
from chimera_api.auth import SessionAuth

_PROJECT_ID_PATTERN = r"^[a-z0-9][a-z0-9-]{0,62}$"

DEFAULT_DOMAIN_ID = "domain-default"
"""Coincide con `chimera_api.runs._DEFAULT_DOMAIN` — Fase 1 tiene un solo
dominio. Se repite el literal en vez de importar el privado del otro módulo
de wiring para no acoplar entre sí dos módulos que ya son independientes."""

DEFAULT_PROJECT_ID = "default"
DEFAULT_PROJECT_NAME = "Proyecto por defecto"
"""Semilla NEUTRA (decisión #173.1): el proyecto por defecto NO puede nombrar
un caso de uso concreto — esos datos son material de prueba, jamás un activo
del producto."""

_BOOTSTRAP_OWNER_ID_ENV = "CHIMERA_OPERATOR_ID"
_BOOTSTRAP_DEFAULT_OWNER_ID = "user:local-operator"
"""Mismo default que `chimera_api.auth._DEFAULT_OPERATOR_ID` — el dueño que
`ensure_domain` declara cuando el despliegue no fijó un operador propio."""


def ensure_default_project(repo: ProjectRepository) -> None:
    """Bootstrap idempotente del wiring (F1.1 ítem 2) — se llama desde
    `chimera_api.runs.build_run_resources`, NUNCA en import time: dos
    corridas seguidas no duplican ni fallan, `get` decide antes de `create`."""
    owner_id = os.environ.get(_BOOTSTRAP_OWNER_ID_ENV, _BOOTSTRAP_DEFAULT_OWNER_ID)
    repo.ensure_domain(DEFAULT_DOMAIN_ID, owner_id)
    if repo.get(DEFAULT_PROJECT_ID) is not None:
        return
    repo.create(
        Project(
            id=DEFAULT_PROJECT_ID,
            domain_id=DEFAULT_DOMAIN_ID,
            name=DEFAULT_PROJECT_NAME,
            created_at=datetime.now(UTC),
        )
    )


class CreateProjectRequest(BaseModel):
    """Body de `POST /projects` — `extra="forbid"`, mismo patrón que el
    resto de los bodies de `chimera_api` (p.ej. `MissionBudgetRequest`)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=_PROJECT_ID_PATTERN)
    name: str = Field(min_length=1)


def _fila(project: Project) -> dict[str, Any]:
    return {
        "id": project.id,
        "domain_id": project.domain_id,
        "name": project.name,
        "created_at": project.created_at.isoformat(),
    }


def create_projects_router(
    session_auth: SessionAuth, repo: ProjectRepository
) -> APIRouter:
    """Router de `/projects` — mismo patrón que `create_files_router`: el
    dominio sale de la IDENTIDAD de quien pregunta, jamás de una constante."""
    router = APIRouter()

    @router.get("/projects")
    def list_projects(request: Request) -> list[dict[str, Any]]:
        identity = session_auth.identity_from(request)
        return [_fila(p) for p in repo.list_projects(identity.domain_id)]

    @router.post("/projects", status_code=201)
    def create_project(body: CreateProjectRequest, request: Request) -> dict[str, Any]:
        identity = session_auth.identity_from(request)
        project = Project(
            id=body.id,
            domain_id=identity.domain_id,
            name=body.name,
            created_at=datetime.now(UTC),
        )
        try:
            created = repo.create(project)
        except ProjectAlreadyExistsError as exc:
            raise HTTPException(
                status_code=409, detail=f"project_id ya existe: {body.id}"
            ) from exc
        return _fila(created)

    return router


__all__ = [
    "DEFAULT_DOMAIN_ID",
    "DEFAULT_PROJECT_ID",
    "DEFAULT_PROJECT_NAME",
    "create_projects_router",
    "ensure_default_project",
]
