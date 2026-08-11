"""Sesión JWT en cookie (freeze §9 P1-9) + actor real en el cruce — C2/M2.

F1.2 — flip a 401-obligatorio APLICADO: `POST /auth/session` emite el JWT
del operador del despliegue (doctrina §7: la identidad del actor es dato
del despliegue) y lo deja en cookie HttpOnly. `POST /runs` deriva su
Identity de esa cookie: cookie AUSENTE o INVÁLIDA ⇒ 401 fail-closed — mismo
trato para las dos, jamás un fallback que fabrique una Identity. `_API_ACTOR`
murió: el actor de `run.created` y de los `capability.job.*` es el del
cruce (AX1).
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


def test_run_sin_cookie_es_401_fail_closed_jamas_fallback() -> None:
    """F1.2 — flip a 401-obligatorio: `POST /runs` sin cookie de sesión ya
    NO degrada al operador default. El fallback murió; sin sesión, el
    mismo fail-closed que una cookie inválida — y nada se journaliza."""
    store = create_event_store()
    client = _make_client(store)
    response = _post(client, "/runs", json=_claim_run_body())
    assert response.status_code == 401
    assert store.read_all() == ()


def test_cookie_invalida_es_401_fail_closed_jamas_fallback() -> None:
    client = _make_client()
    # mismo patrón httpx/httpx2 que _post
    client.cookies.set(SESSION_COOKIE, "token.manipulado.xyz")
    response = _post(client, "/runs", json=_claim_run_body())
    assert response.status_code == 401


def test_operador_configurable_no_evita_401_sin_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Doctrina §7: quién actúa es dato del despliegue — env, no hardcode.
    Pero configurar el operador NO abre una puerta trasera al
    401-obligatorio (F1.2): sin cookie, fail-closed pase lo que diga el
    env."""
    monkeypatch.setenv("CHIMERA_OPERATOR_ID", "user:dylan")
    store = create_event_store()
    client = _make_client(store)
    response = _post(client, "/runs", json=_claim_run_body())
    assert response.status_code == 401
    assert store.read_all() == ()


def test_operador_configurable_por_despliegue_con_sesion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """La contraparte viva del test de arriba: CON sesión, el operador SÍ
    gobierna la Identity emitida — la configurabilidad (doctrina §7) sigue
    siendo real, solo que ahora pasa siempre por `POST /auth/session`."""
    monkeypatch.setenv("CHIMERA_OPERATOR_ID", "user:dylan")
    store = create_event_store()
    client = _make_client(store)
    assert _post(client, "/auth/session").status_code == 200
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


def test_me_sin_cookie_es_401_fail_closed() -> None:
    """`GET /me` — quién está operando (P6/M15, bloque de usuario del Studio).

    F1.2 — flip a 401-obligatorio: sin cookie ya no hay "identidad del
    operador local" que mostrar — 401, mismo trato que las rutas de
    escritura. El Studio pide sesión ANTES de pintar el bloque de usuario."""
    client = _make_client()
    response = _get(client, "/me")

    assert response.status_code == 401


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
