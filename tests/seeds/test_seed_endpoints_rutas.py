"""SEED · endpoints Studio (Steven+Dylan) — spec `docs/specs/endpoints-studio.md`.

Fase 0 fijó el contrato ruta→forma (freeze §7/§9, proyecciones YA congeladas)
ANTES de que las rutas existieran. Fase 1 (Steven+Dylan) las implementó las
6 de una vez en `chimera_api.reads.create_reads_router` (montado en
`chimera_api.app.create_app` junto a `/health`, `/runs` POST,
`/runs/{id}/events` SSE y `/runs/{id}/certificate` GET) — cada test de abajo
describe la CONDUCTA esperada (código 200 + forma de la respuesta) y ya
pasa en VERDE; el `xfail` se retiró de las 6 (no quedó ninguna pendiente).

Collection-safe a propósito (import de `chimera_api`/`blite` DENTRO de cada
función, nunca a nivel de módulo): estas rutas se agregaron a `create_app`,
no a un módulo nuevo, así que el import del paquete en sí no fallaría hoy —
pero se mantiene la convención de la sesión para no divergir del patrón
pedido y para que el seed siga siendo seguro de recolectar incluso si algún
módulo intermedio cambia de forma más adelante.
"""

from __future__ import annotations

from typing import Any, cast

import httpx
import pytest
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.seed]


# starlette.testclient.TestClient anota `.get()` contra el paquete `httpx2`
# (bajo TYPE_CHECKING) que este repo no instala — el fallback real en
# runtime es `httpx`; mismo patrón de cast + ignore puntual que
# `tests/unit/api/test_runs.py::_get`/`test_certificate.py::_get`. `httpx`/
# `TestClient` no son `chimera_api`/`blite` — no rompen collection-safe.
def _get(client: TestClient, url: str) -> httpx.Response:
    return cast(
        httpx.Response,
        client.get(url),
    )


def _seed_minimal_run(store: Any, run_id: str) -> None:
    """Un run mínimo terminado — insumo común a las 6 rutas."""
    store.append(
        stream_id=run_id,
        type="run.created",
        actor_id="user:dylan",
        domain_id="d-default",
        payload={"run_id": run_id, "max_steps": 8, "policy_digest": "sha256:pp"},
    )
    store.append(
        stream_id=run_id,
        type="verification.completed",
        actor_id="service:verifier",
        domain_id="d-default",
        payload={
            "step_id": "s1",
            "verification": {
                "verdict": "pass",
                "verifier_class": "execution",
                "level": "AL3",
            },
        },
        expected_seq=1,
    )
    store.append(
        stream_id=run_id,
        type="run.completed",
        actor_id="service:runtime",
        domain_id="d-default",
        payload={},
        expected_seq=2,
    )


def test_get_runs_returns_run_summary_list() -> None:
    from chimera_api.app import create_app
    from fastapi.testclient import TestClient

    from blite.events import create_event_store

    store = create_event_store()
    _seed_minimal_run(store, "r1")
    client = TestClient(create_app(store))

    response = _get(client, "/runs")

    assert response.status_code == 200
    body: list[dict[str, Any]] = response.json()
    assert isinstance(body, list)
    row: dict[str, Any] = body[0]
    for key in (
        "run_id",
        "status",
        "conclusion",
        "verdict",
        "titular_level",
        "titular_class",
        "events_count",
        "actor",
    ):
        assert key in row


def test_get_run_artifacts_returns_project_artifact_list() -> None:
    from chimera_api.app import create_app
    from fastapi.testclient import TestClient

    from blite.events import create_event_store

    store = create_event_store()
    _seed_minimal_run(store, "r1")
    client = TestClient(create_app(store))

    response = _get(client, "/runs/r1/artifacts")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    if body:
        for key in (
            "artifact_ref",
            "digest",
            "run_id",
            "titular_level",
            "titular_class",
            "verdict",
            "issued_at",
        ):
            assert key in body[0]


def test_get_run_knowledge_returns_knowledge_claim_list() -> None:
    from chimera_api.app import create_app
    from fastapi.testclient import TestClient

    from blite.events import create_event_store

    store = create_event_store()
    _seed_minimal_run(store, "r1")
    client = TestClient(create_app(store))

    response = _get(client, "/runs/r1/knowledge")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    if body:
        for key in (
            "statement",
            "scope",
            "verdict",
            "level",
            "titular_class",
            "run_id",
            "valid_as_of",
        ):
            assert key in body[0]


def test_get_step_evidence_returns_step_detail() -> None:
    from chimera_api.app import create_app
    from fastapi.testclient import TestClient

    from blite.events import create_event_store

    store = create_event_store()
    _seed_minimal_run(store, "r1")
    client = TestClient(create_app(store))

    response = _get(client, "/runs/r1/steps/s1/evidence")

    assert response.status_code == 200
    body = response.json()
    for key in (
        "step_id",
        "capability_id",
        "input_digest",
        "output_digest",
        "attestations",
    ):
        assert key in body
    assert body["step_id"] == "s1"


def test_get_ablation_returns_ablation_metric_list() -> None:
    from chimera_api.app import create_app
    from fastapi.testclient import TestClient

    from blite.events import create_event_store

    store = create_event_store()
    _seed_minimal_run(store, "r1")
    client = TestClient(create_app(store))

    response = _get(client, "/runs/r1/ablation")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    if body:
        for key in ("variant", "cut_cost", "wall_ms", "verification_latency_ms"):
            assert key in body[0]


def test_get_topology_returns_partition_with_verification_per_island() -> None:
    from chimera_api.app import create_app
    from fastapi.testclient import TestClient

    from blite.events import create_event_store

    store = create_event_store()
    _seed_minimal_run(store, "r1")
    client = TestClient(create_app(store))

    response = _get(client, "/runs/r1/topology")

    assert response.status_code == 200
    body = response.json()
    for key in ("topology_ref", "islands", "cut_branch_ids", "cut_cost"):
        assert key in body
    # freeze §9: verification POR ISLA, nunca solo un bloque global.
    assert all("verification" in island for island in body["islands"])


def test_unknown_run_id_is_404_not_fabricated_data() -> None:
    # Fail-closed (mismo patron que certificate.py::get_certificate): un
    # run_id desconocido es 404, jamas una lista vacia disfrazada de exito
    # silencioso ni un 200 con datos inventados.
    from chimera_api.app import create_app
    from fastapi.testclient import TestClient

    from blite.events import create_event_store

    client = TestClient(create_app(create_event_store()))

    response = _get(client, "/runs/no-existe/artifacts")

    assert response.status_code == 404
