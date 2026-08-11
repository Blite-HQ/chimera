"""Tests de `GET /runs/{run_id}/certificate` — plan `docs/mvp/01-runtime-api.md`
§2 (decisiones `docs/mvp/decisiones.md` #9 llave efímera, #10 verbo GET, #12
409 si no-terminal).

Cubre: golden 7/7 (dos patas reales sobre `sintetica-4bus`), refutación 7/7
(titular AL0 — refutar es un veredicto de primera clase), run desconocido
(404), run vivo sin evento terminal (409) y run fallido — `AssembleError`
mapeado a 409 honesto: no hay certificado que emitir.

Reusa el patrón hermético de `test_runs.py`: capability echo +
`EntryPointRegistry` inyectada en `create_app(store, registry=...)`.
"""

from __future__ import annotations

import base64
import json
from typing import Any, cast

import httpx
from chimera_api.app import create_app
from chimera_api.certificate import create_certificate_router
from chimera_api.runs import RunTicket, build_run_resources
from fastapi import FastAPI
from fastapi.testclient import TestClient

from blite.certificate.assemble import ConclusionDeclaration
from blite.certificate.bundle_check import check_bundle
from blite.events import create_event_store
from blite.events.store import EventStore
from blite.runtime.registry import EntryPointRegistry
from blite_capability.manifest import CapabilityManifest

_STATEMENT_4BUS = "la partición propuesta es óptima y electricamente factible"
_SCOPE_4BUS: dict[str, Any] = {"instancia": "sintetica-4bus"}
_EDGES_4BUS = ((0, 1, 0), (2, 3, 0), (1, 2, 5))

_STATEMENT_K3 = "la asignación propuesta es el corte máximo exacto"
_SCOPE_DESCONOCIDA: dict[str, Any] = {"instancia": "desconocida"}
_EDGES_K3 = ((0, 1, 1), (1, 2, 1), (0, 2, 1))


class _EchoCapability:
    """Capability hermética de test — mismo patrón que `test_runs.py`."""

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


def _make_registry() -> EntryPointRegistry:
    return EntryPointRegistry({"cap.echo": _EchoCapability()})


def _make_client(store: EventStore | None = None) -> TestClient:
    event_store = store if store is not None else create_event_store()
    return TestClient(create_app(event_store, registry=_make_registry()))


# Mismo patrón de pyright-ignore puntual que `test_runs.py`/`test_app_sse.py`:
# `TestClient.get`/`.post` anotan contra `httpx2` (bajo TYPE_CHECKING), que
# este repo no instala — el fallback real en runtime es `httpx`.
def _get(client: TestClient, url: str) -> httpx.Response:
    return cast(
        httpx.Response,
        client.get(url),
    )


def _post(client: TestClient, url: str, *, json_body: dict[str, Any]) -> httpx.Response:
    return cast(
        httpx.Response,
        client.post(url, json=json_body),
    )


def _claim_body(
    *,
    n_nodes: int,
    edges: tuple[tuple[int, int, int], ...],
    assignment: tuple[int, ...],
    canonical_statement: str,
    scope: dict[str, Any],
    claim_type: str = "solution",
) -> dict[str, Any]:
    return {
        "instance": {"n_nodes": n_nodes, "edges": edges},
        "assignment": assignment,
        "canonical_statement": canonical_statement,
        "scope": scope,
        "claim_type": claim_type,
    }


def _run_body(
    *,
    claim: dict[str, Any],
    capability_id: str = "cap.echo",
    inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "capability_id": capability_id,
        "inputs": inputs if inputs is not None else {"x": 21},
        "claim": claim,
    }


def _create_run(client: TestClient, body: dict[str, Any]) -> str:
    """POST /runs y devuelve el run_id — bajo TestClient los BackgroundTasks
    corren y TERMINAN dentro del ciclo de la request (freeze de Starlette,
    mismo comentario que `test_runs.py`)."""
    response = _post(client, "/runs", json_body=body)
    assert response.status_code == 202
    run_id: str = response.json()["run_id"]
    return run_id


def _predicate_of(bundle: dict[str, Any]) -> dict[str, Any]:
    """Mismo helper que `test_assemble.py::_predicate_of` — decodifica
    `envelope.payload` base64→json→`["predicate"]`."""
    payload = base64.b64decode(bundle["envelope"]["payload"])
    statement: dict[str, Any] = json.loads(payload)
    return statement["predicate"]


class TestGoldenPath:
    def test_certificado_de_run_optimo_da_7_de_7_con_titular_al3(self) -> None:
        # Arrange
        client = _make_client()
        run_id = _create_run(
            client,
            _run_body(
                claim=_claim_body(
                    n_nodes=4,
                    edges=_EDGES_4BUS,
                    assignment=(0, 0, 1, 1),
                    canonical_statement=_STATEMENT_4BUS,
                    scope=_SCOPE_4BUS,
                )
            ),
        )

        # Act
        response = _get(client, f"/runs/{run_id}/certificate")

        # Assert
        assert response.status_code == 200
        bundle = response.json()
        results = check_bundle(bundle)
        assert all(r.ok for r in results), [
            (r.number, r.failures) for r in results if not r.ok
        ]
        predicate = _predicate_of(bundle)
        assert predicate["titular_level"] == "AL3"
        assert {a["anchor_kind"] for a in predicate["attestations"]} == {
            "solver",
            "execution",
        }


class TestRefutacion:
    def test_certificado_de_run_suboptimo_da_7_de_7_con_titular_al0(self) -> None:
        # Arrange — assignment (0,0,0,1) aísla el bus 3 (sin slack): refuta
        # LIMPIO en las dos patas — formal (no es óptimo, corte 0 < 5) Y
        # execution (isla sin fuente, hard-fail antes de correr el flujo).
        #
        # Desviación documentada del brief: (0,0,0,0) NO sirve aquí — deja
        # los dos slacks (bus 0 y bus 2) dentro de la MISMA isla conectada,
        # así que pandapower converge y la pata execution da "pass"; con
        # solo la pata formal en "fail" el punto 7 exige 2 patas por
        # independence_group y encuentra 1 (falla). Verificado empíricamente
        # invocando `ExecutionVerifier.verify` directo antes de fijar el
        # assignment de este test.
        client = _make_client()
        run_id = _create_run(
            client,
            _run_body(
                claim=_claim_body(
                    n_nodes=4,
                    edges=_EDGES_4BUS,
                    assignment=(0, 0, 0, 1),
                    canonical_statement=_STATEMENT_4BUS,
                    scope=_SCOPE_4BUS,
                )
            ),
        )

        # Act
        response = _get(client, f"/runs/{run_id}/certificate")

        # Assert
        assert response.status_code == 200
        bundle = response.json()
        results = check_bundle(bundle)
        assert all(r.ok for r in results), [
            (r.number, r.failures) for r in results if not r.ok
        ]
        predicate = _predicate_of(bundle)
        assert predicate["conclusions"][0]["verdict"] == "refuted"
        assert predicate["titular_level"] == "AL0"


class TestRunDesconocido:
    def test_run_id_inexistente_da_404(self) -> None:
        # Arrange
        client = _make_client()

        # Act
        response = _get(client, "/runs/run-inexistente/certificate")

        # Assert
        assert response.status_code == 404


class TestRunNoTerminal:
    def test_run_vivo_sin_evento_terminal_da_409(self) -> None:
        # Arrange — recursos y router aislados: un stream con SOLO
        # `run.created`, sin terminal — un run vivo jamás se certifica
        # (decisión #12).
        resources = build_run_resources(create_event_store())
        resources.store.append(
            stream_id="run-parcial",
            type="run.created",
            actor_id="user:api",
            domain_id="domain-default",
            payload={"run_id": "run-parcial", "actor_id": "user:api"},
        )
        resources.run_tickets["run-parcial"] = RunTicket(
            conclusions=(
                ConclusionDeclaration(
                    canonical_statement=_STATEMENT_4BUS,
                    scope=_SCOPE_4BUS,
                    claim_type="solution",
                ),
            ),
            anchor_descriptors=(),
        )
        app = FastAPI()
        app.include_router(create_certificate_router(resources))
        client = TestClient(app)

        # Act
        response = _get(client, "/runs/run-parcial/certificate")

        # Assert
        assert response.status_code == 409


class TestRunFallido:
    def test_capability_inexistente_deja_run_failed_y_certificate_da_409(
        self,
    ) -> None:
        # Arrange
        client = _make_client()
        run_id = _create_run(
            client,
            _run_body(
                claim=_claim_body(
                    n_nodes=3,
                    edges=_EDGES_K3,
                    assignment=(0, 0, 1),
                    canonical_statement=_STATEMENT_K3,
                    scope=_SCOPE_DESCONOCIDA,
                ),
                capability_id="cap.inexistente",
            ),
        )

        # Act
        response = _get(client, f"/runs/{run_id}/certificate")

        # Assert — el run terminó (run.failed es terminal) pero
        # `assemble_bundle` no encuentra evidencia amparando la conclusión
        # (fail-closed) — 409 honesto, jamás un certificado fabricado.
        assert response.status_code == 409
