"""
`GET /projects`, `POST /projects` — el sistema organizacional del Studio
(F1.1, ítem 1 de `docs/mejorado/09-cierre.md` §2·F1).

Cada `create_app()` bootstrapea el dominio `domain-default` y el proyecto
neutro `default` (F1.1 ítem 2) — por eso el listado de un cliente recién
creado NUNCA es `[]`: ya trae la semilla.
"""

from __future__ import annotations

from typing import Any, cast

import httpx
import pytest
from chimera_api.app import create_app
from fastapi.testclient import TestClient

from blite.events import create_event_store
from blite.runtime.registry import EntryPointRegistry
from tests.conftest import authenticated


@pytest.fixture()
def client() -> TestClient:
    return authenticated(
        TestClient(create_app(create_event_store(), registry=EntryPointRegistry({})))
    )


def _get(client: TestClient, url: str) -> httpx.Response:
    return cast(httpx.Response, client.get(url))


def _post(client: TestClient, url: str, *, json_body: dict[str, Any]) -> httpx.Response:
    return cast(httpx.Response, client.post(url, json=json_body))


def test_el_listado_recien_arrancado_ya_trae_la_semilla_neutra(
    client: TestClient,
) -> None:
    response = _get(client, "/projects")

    assert response.status_code == 200
    body: list[dict[str, Any]] = response.json()
    assert [p["id"] for p in body] == ["default"]
    assert body[0]["domain_id"] == "domain-default"
    # Decisión #173.1 — la semilla es NEUTRA: jamás nombra el caso ICE.
    assert "ice" not in body[0]["name"].lower()
    assert "islanding" not in body[0]["name"].lower()
    assert "ieee" not in body[0]["name"].lower()


def test_el_listado_expone_id_domain_id_name_created_at_en_snake_case(
    client: TestClient,
) -> None:
    fila = _get(client, "/projects").json()[0]

    assert set(fila) == {"id", "domain_id", "name", "created_at"}
    # ISO-8601 UTC — `datetime.fromisoformat` lo parsea sin ayuda.
    from datetime import datetime

    parsed = datetime.fromisoformat(fila["created_at"])
    assert parsed.tzinfo is not None


def test_crear_un_proyecto_devuelve_201_y_la_fila_creada(client: TestClient) -> None:
    response = _post(client, "/projects", json_body={"id": "reto-1", "name": "Reto 1"})

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == "reto-1"
    assert body["name"] == "Reto 1"
    assert body["domain_id"] == "domain-default"


def test_el_proyecto_creado_aparece_despues_en_el_listado(client: TestClient) -> None:
    _post(client, "/projects", json_body={"id": "reto-1", "name": "Reto 1"})

    ids = [p["id"] for p in _get(client, "/projects").json()]

    assert ids == ["default", "reto-1"]


def test_crear_con_un_id_ya_existente_da_409(client: TestClient) -> None:
    response = _post(client, "/projects", json_body={"id": "default", "name": "Otro"})

    assert response.status_code == 409


def test_crear_dos_veces_el_mismo_id_la_segunda_da_409_y_no_duplica(
    client: TestClient,
) -> None:
    _post(client, "/projects", json_body={"id": "reto-1", "name": "Reto 1"})

    segunda = _post(
        client, "/projects", json_body={"id": "reto-1", "name": "Reto 1 bis"}
    )

    assert segunda.status_code == 409
    ids = [p["id"] for p in _get(client, "/projects").json()]
    assert ids.count("reto-1") == 1


@pytest.mark.parametrize(
    "project_id",
    [
        "",
        "Mayúscula",
        "con espacio",
        "-empieza-con-guion",
        "_guion-bajo",
        "a" * 64,
    ],
)
def test_un_id_fuera_del_slug_da_422(client: TestClient, project_id: str) -> None:
    response = _post(client, "/projects", json_body={"id": project_id, "name": "X"})

    assert response.status_code == 422


def test_un_body_con_campo_extra_da_422(client: TestClient) -> None:
    response = _post(
        client,
        "/projects",
        json_body={"id": "reto-1", "name": "Reto 1", "domain_id": "otro-dominio"},
    )

    assert response.status_code == 422


def test_un_nombre_vacio_da_422(client: TestClient) -> None:
    response = _post(client, "/projects", json_body={"id": "reto-1", "name": ""})

    assert response.status_code == 422
