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


def _get(client: TestClient, url: str) -> httpx.Response:
    """Mismo motivo que `_post`: el TestClient de starlette devuelve
    `Unknown` bajo pyright estricto, y castear en cada llamada esconde el
    ruido en vez de resolverlo una vez."""
    return cast(
        httpx.Response,
        client.get(url),
    )


def _post(client: TestClient, url: str, **kwargs: Any) -> httpx.Response:
    return cast(
        httpx.Response,
        client.post(url, **kwargs),
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
    # mismo patrón httpx/httpx2 que _post
    client.cookies.set(SESSION_COOKIE, "token.manipulado.xyz")
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


def test_cookie_secure_por_env_para_despliegues_tls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Revisión C-1: `Secure` es dato del despliegue — el walking skeleton
    local corre http://localhost (curl/navegador DESCARTAN cookies Secure en
    http plano ⇒ degradación silenciosa al default); un despliegue TLS
    (Fargate) DEBE encender CHIMERA_SESSION_COOKIE_SECURE=1."""
    client = _make_client()
    plain = _post(client, "/auth/session").headers["set-cookie"]
    assert "Secure" not in plain

    monkeypatch.setenv("CHIMERA_SESSION_COOKIE_SECURE", "1")
    secured = _post(_make_client(), "/auth/session").headers["set-cookie"]
    assert "Secure" in secured


def test_me_devuelve_la_identidad_del_operador_sin_cookie() -> None:
    """`GET /me` — quién está operando (P6/M15, bloque de usuario del Studio).

    Sin cookie la identidad es la del operador local, la MISMA que estampan
    los eventos: el Studio no puede mostrar un usuario distinto del que va a
    quedar journalizado en `actor_id`, o el bloque mentiría sobre quién
    firma."""
    client = _make_client()
    if True:
        response = _get(client, "/me")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == _OPERATOR
        assert body["kind"] in {"human", "agent", "service"}
        assert isinstance(body["permissions"], list)


def test_me_refleja_la_identidad_de_la_cookie() -> None:
    """Con sesión, `GET /me` reporta la identidad de ESA sesión — no el
    default. Es la misma resolución que usa cualquier ruta de escritura."""
    client = _make_client()
    if True:
        _post(client, "/auth/session")

        response = _get(client, "/me")

        assert response.status_code == 200
        assert response.json()["id"] == _OPERATOR


def test_me_con_cookie_rota_falla_cerrado() -> None:
    """Una cookie inválida NO degrada al default: 401. Si `GET /me`
    degradara, el Studio mostraría 'operador local' mientras las rutas de
    escritura rechazan con 401 — dos versiones de quién sos."""
    client = _make_client()
    if True:
        cookies = cast(httpx.Cookies, client.cookies)
        cookies.set(SESSION_COOKIE, "no-es-un-jwt")

        assert _get(client, "/me").status_code == 401
