"""Sesión JWT en cookie (freeze §9 P1-9) + actor real en el cruce — C2/M2.

`POST /auth/session` emite el JWT del operador del despliegue (doctrina §7:
la identidad del actor es dato del despliegue) y lo deja en cookie HttpOnly.
`POST /runs` deriva su Identity de esa cookie: cookie inválida ⇒ 401
fail-closed (jamás fallback); sin cookie ⇒ la identidad default del operador
local (decisión registrada — el flip a 401-obligatorio espera el bootstrap
del Studio, frontera P-ui). `_API_ACTOR` murió: el actor de `run.created` y
de los `capability.job.*` es el del cruce (AX1).
"""

from __future__ import annotations

from typing import Any, cast

import httpx
import pytest
from chimera_api.app import create_app
from chimera_api.auth import SESSION_COOKIE
from fastapi.testclient import TestClient

from blite.events import create_event_store
from blite.events.store import EventStore
from blite.runtime.registry import EntryPointRegistry
from blite_capability.manifest import CapabilityManifest

_OPERATOR = "user:local-operator"


class _EchoCapability:
    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id="cap.echo",
            description="generic test capability",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            side_effects="pure",
            required_permission="capability:invoke",
            interaction="request_response",
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return {"echoed": inputs["x"]}


def _make_client(store: EventStore | None = None) -> TestClient:
    event_store = store if store is not None else create_event_store()
    registry = EntryPointRegistry({"cap.echo": _EchoCapability()})
    return TestClient(create_app(event_store, registry=registry))


def _post(client: TestClient, url: str, **kwargs: Any) -> httpx.Response:
    return cast(
        httpx.Response,
        client.post(url, **kwargs),  # pyright: ignore[reportUnknownMemberType]
    )


def _claim_run_body() -> dict[str, Any]:
    return {
        "capability_id": "cap.echo",
        "inputs": {"x": 21},
        "claim": {
            "instance": {"n_nodes": 4, "edges": ((0, 1, 0), (2, 3, 0), (1, 2, 5))},
            "assignment": (0, 0, 1, 1),
            "canonical_statement": (
                "la partición propuesta es óptima y electricamente factible"
            ),
            "scope": {"instancia": "sintetica-4bus"},
            "claim_type": "solution",
        },
    }


def test_auth_session_emite_cookie_httponly_con_el_actor() -> None:
    client = _make_client()
    response = _post(client, "/auth/session")
    assert response.status_code == 200
    assert response.json()["actor_id"] == _OPERATOR
    set_cookie = response.headers["set-cookie"]
    assert SESSION_COOKIE in set_cookie
    assert "HttpOnly" in set_cookie


def test_run_con_cookie_estampa_el_actor_del_jwt_en_los_eventos() -> None:
    """CP5 a nivel unidad: run.created Y capability.job.* llevan el actor del
    JWT — jamás 'user:api' (muerto) ni service:runtime en el cruce."""
    store = create_event_store()
    client = _make_client(store)
    assert _post(client, "/auth/session").status_code == 200

    response = _post(client, "/runs", json=_claim_run_body())
    assert response.status_code == 202
    run_id = response.json()["run_id"]

    events = store.read_stream(run_id)
    created = next(e for e in events if e.type == "run.created")
    assert created.actor_id == _OPERATOR
    job_events = [e for e in events if e.type.startswith("capability.job.")]
    assert job_events, "el cruce debió emitir eventos de job"
    assert all(e.actor_id == _OPERATOR for e in job_events)
    assert not any(e.actor_id == "user:api" for e in events)


def test_run_sin_cookie_usa_el_operador_default_jamas_user_api() -> None:
    store = create_event_store()
    client = _make_client(store)
    response = _post(client, "/runs", json=_claim_run_body())
    assert response.status_code == 202
    run_id = response.json()["run_id"]
    created = next(e for e in store.read_stream(run_id) if e.type == "run.created")
    assert created.actor_id == _OPERATOR


def test_cookie_invalida_es_401_fail_closed_jamas_fallback() -> None:
    client = _make_client()
    client.cookies.set(  # pyright: ignore[reportUnknownMemberType] — mismo patrón httpx/httpx2 que _post
        SESSION_COOKIE, "token.manipulado.xyz"
    )
    response = _post(client, "/runs", json=_claim_run_body())
    assert response.status_code == 401


def test_operador_configurable_por_despliegue(monkeypatch: pytest.MonkeyPatch) -> None:
    """Doctrina §7: quién actúa es dato del despliegue — env, no hardcode."""
    monkeypatch.setenv("CHIMERA_OPERATOR_ID", "user:dylan")
    store = create_event_store()
    client = _make_client(store)
    response = _post(client, "/runs", json=_claim_run_body())
    assert response.status_code == 202
    run_id = response.json()["run_id"]
    created = next(e for e in store.read_stream(run_id) if e.type == "run.created")
    assert created.actor_id == "user:dylan"
