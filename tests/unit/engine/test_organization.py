"""
`ProjectRepository` — contrato del puerto sobre el adapter in-memory (F1.1,
ítem 1 de `docs/mejorado/09-cierre.md` §2·F1).

Espejo de `tests/unit/events/test_event_store.py`: el contrato se prueba
UNA vez contra `create_project_repository()` (sin DSN ⇒ in-memory, Fase 1);
el mismo contrato corre contra Postgres real en
`tests/integration/test_postgres_organization.py` (env-gated, mismo patrón
que `test_postgres_event_store.py`).

`docs/esquema-datos-v2.md` §2 (ceremonia #176): `projects` agrupa runs
dentro de un dominio; `run.created.project_id` es una referencia OPACA — el
evento no valida la FK, la valida quien construye el run contra ESTE puerto.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime

import pytest

from blite.organization import (
    Project,
    ProjectAlreadyExistsError,
    ProjectRepository,
    create_project_repository,
)

_NOW = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)


def _repo() -> ProjectRepository:
    return create_project_repository()


def _project(
    project_id: str = "p1", domain_id: str = "d1", name: str = "Uno"
) -> Project:
    return Project(id=project_id, domain_id=domain_id, name=name, created_at=_NOW)


def test_factory_sin_dsn_devuelve_un_repositorio_que_cumple_el_puerto() -> None:
    repo = _repo()

    assert isinstance(repo, ProjectRepository)


def test_list_projects_de_un_dominio_sin_proyectos_es_vacio_no_error() -> None:
    repo = _repo()

    assert repo.list_projects("d1") == ()


def test_get_de_un_id_desconocido_es_none_no_excepcion() -> None:
    repo = _repo()

    assert repo.get("desconocido") is None


def test_create_devuelve_el_project_y_get_lo_encuentra_despues() -> None:
    repo = _repo()
    project = _project()

    created = repo.create(project)

    assert created == project
    assert repo.get("p1") == project


def test_create_no_muta_el_project_original_ni_devuelve_otro_objeto_mutado() -> None:
    # Arrange
    repo = _repo()
    project = _project()

    # Act
    created = repo.create(project)

    # Assert — inmutabilidad: el dataclass es frozen, `create` no reasigna
    # ningún campo del que se le pasó.
    with pytest.raises(dataclasses.FrozenInstanceError):
        created.name = "otro"  # type: ignore[misc]


def test_create_con_un_id_ya_tomado_explota_y_no_pisa_la_fila_existente() -> None:
    # Arrange
    repo = _repo()
    repo.create(_project(name="original"))

    # Act / Assert
    with pytest.raises(ProjectAlreadyExistsError):
        repo.create(_project(name="pisador"))

    assert repo.get("p1") is not None
    assert repo.get("p1").name == "original"  # type: ignore[union-attr]


def test_list_projects_aisla_por_dominio() -> None:
    # Arrange
    repo = _repo()
    repo.create(_project(project_id="p1", domain_id="d1"))
    repo.create(_project(project_id="p2", domain_id="d2"))

    # Act
    del_d1 = repo.list_projects("d1")

    # Assert
    assert [p.id for p in del_d1] == ["p1"]


def test_list_projects_ordena_por_fecha_de_creacion() -> None:
    # Arrange
    repo = _repo()
    primero = Project(id="a", domain_id="d1", name="A", created_at=_NOW)
    segundo = Project(
        id="b", domain_id="d1", name="B", created_at=_NOW.replace(hour=13)
    )
    repo.create(segundo)
    repo.create(primero)

    # Act
    projects = repo.list_projects("d1")

    # Assert
    assert [p.id for p in projects] == ["a", "b"]


def test_ensure_domain_es_idempotente() -> None:
    repo = _repo()

    repo.ensure_domain("d1", "user:test")
    repo.ensure_domain("d1", "user:test")  # segunda corrida — no explota


def test_bootstrap_seguido_dos_veces_no_duplica_ni_falla() -> None:
    """Simula el patrón de `chimera_api.projects.ensure_default_project`:
    `ensure_domain` + crear-si-falta, corrido dos veces seguidas."""

    def _bootstrap(repo: ProjectRepository) -> None:
        repo.ensure_domain("domain-default", "user:local-operator")
        if repo.get("default") is None:
            repo.create(
                Project(
                    id="default",
                    domain_id="domain-default",
                    name="Proyecto por defecto",
                    created_at=_NOW,
                )
            )

    repo = _repo()

    _bootstrap(repo)
    _bootstrap(repo)

    assert [p.id for p in repo.list_projects("domain-default")] == ["default"]
