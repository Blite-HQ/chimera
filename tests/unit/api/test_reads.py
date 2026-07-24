"""Tests de las 6 rutas de lectura del Studio (`chimera_api/reads.py`) —
`docs/specs/endpoints-studio.md` (costura E↔D). Cubre: `/runs` con un run
sembrado directo (sin ticket, defaults honestos) y con un run REAL vía
`POST /runs` (golden path 4bus, enriquecido desde el certificado);
`/artifacts`/`/knowledge` sin certificado (`[]`) y con certificado real;
`/steps/{id}/evidence` con y sin `verification.completed` para el step;
`/ablation` sin y con `run.metrics.recorded`; `/topology` con y sin
partición; y 404 fail-closed para las 5 rutas parametrizadas por `run_id`
sobre un run inexistente.

Reusa el patrón hermético de `test_certificate.py`/`test_runs.py`: capability
echo + `EntryPointRegistry` inyectada en `create_app(store, registry=...)`.
"""

from __future__ import annotations

from typing import Any, cast

import httpx
import pytest
from chimera_api.app import create_app
from fastapi.testclient import TestClient

from blite.events import create_event_store
from blite.events.store import EventStore
from blite.runtime.registry import EntryPointRegistry
from blite_capability.manifest import CapabilityManifest

_STATEMENT_4BUS = "la partición propuesta es óptima y electricamente factible"
_SCOPE_4BUS: dict[str, Any] = {"instancia": "sintetica-4bus"}
_EDGES_4BUS = ((0, 1, 0), (2, 3, 0), (1, 2, 5))

_RUN_CREATED_PAYLOAD: dict[str, Any] = {
    "run_id": "r1",
    "max_steps": 8,
    "policy_digest": "sha256:pp",
}


class _EchoCapability:
    """Capability hermética de test — mismo patrón que `test_certificate.py`."""

    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id="cap.echo",
            description="generic test capability",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return {"echoed": inputs["x"]}


def _make_registry() -> EntryPointRegistry:
    return EntryPointRegistry({"cap.echo": _EchoCapability()})


def _make_client(store: EventStore | None = None) -> TestClient:
    event_store = store if store is not None else create_event_store()
    return TestClient(create_app(event_store, registry=_make_registry()))


# Mismo pyright-ignore puntual que `test_certificate.py`/`test_runs.py`:
# `TestClient.get`/`.post` anotan contra `httpx2` (bajo TYPE_CHECKING), que
# este repo no instala — el fallback real en runtime es `httpx`.
def _get(client: TestClient, url: str) -> httpx.Response:
    return cast(
        httpx.Response,
        client.get(url),  # pyright: ignore[reportUnknownMemberType]
    )


def _post(client: TestClient, url: str, *, json_body: dict[str, Any]) -> httpx.Response:
    return cast(
        httpx.Response,
        client.post(url, json=json_body),  # pyright: ignore[reportUnknownMemberType]
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
    corren y TERMINAN dentro del ciclo de la request (mismo comentario que
    `test_certificate.py`)."""
    response = _post(client, "/runs", json_body=body)
    assert response.status_code == 202
    run_id: str = response.json()["run_id"]
    return run_id


def _seed_terminal_run(store: EventStore, run_id: str = "r1") -> None:
    """Un run terminado sembrado DIRECTO en el store — sin ticket, así que
    `/runs`/`/artifacts`/`/knowledge` no encuentran certificado (defaults
    honestos, no un 404: el run existe, solo no tiene certificado emitido)."""
    store.append(
        stream_id=run_id,
        type="run.created",
        actor_id="user:dylan",
        domain_id="d-default",
        payload={**_RUN_CREATED_PAYLOAD, "run_id": run_id},
    )
    store.append(
        stream_id=run_id,
        type="run.completed",
        actor_id="service:runtime",
        domain_id="d-default",
        payload={},
        expected_seq=1,
    )


class TestListRunsSinCertificado:
    def test_run_sembrado_directo_sin_ticket_da_defaults(self) -> None:
        # Arrange
        store = create_event_store()
        _seed_terminal_run(store)
        client = _make_client(store)

        # Act
        response = _get(client, "/runs")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        row = body[0]
        assert row["run_id"] == "r1"
        assert row["status"] == "completado"
        assert row["conclusion"] == "Sin conclusión registrada"
        assert row["verdict"] == "inconclusive"
        assert row["titular_level"] == "AL0"
        assert row["titular_class"] == "formal_exact"
        assert row["events_count"] == 2
        assert row["actor"] == "user:dylan"
        assert "completed_at" in row

    def test_run_vivo_sin_ticket_da_en_curso_y_omite_completed_at(self) -> None:
        # Arrange — solo `run.created`, sin terminal: el enum wire congelado
        # (`completado`/`en_curso`) no distingue "vivo" de "failed/cancelled".
        store = create_event_store()
        store.append(
            stream_id="r-vivo",
            type="run.created",
            actor_id="user:dylan",
            domain_id="d-default",
            payload={**_RUN_CREATED_PAYLOAD, "run_id": "r-vivo"},
        )
        client = _make_client(store)

        # Act
        response = _get(client, "/runs")

        # Assert
        assert response.status_code == 200
        row = response.json()[0]
        assert row["status"] == "en_curso"
        assert "completed_at" not in row


class TestListRunsConCertificado:
    def test_run_golden_path_aparece_enriquecido(self) -> None:
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
        response = _get(client, "/runs")

        # Assert
        assert response.status_code == 200
        rows = {row["run_id"]: row for row in response.json()}
        row = rows[run_id]
        assert row["status"] == "completado"
        assert row["conclusion"] == _STATEMENT_4BUS
        assert row["verdict"] == "verified"
        assert row["titular_level"] == "AL3"
        assert row["actor"] == "user:api"
        assert "completed_at" in row


class TestArtifactsYKnowledge:
    def test_artifacts_sin_certificado_da_lista_vacia(self) -> None:
        # Arrange
        store = create_event_store()
        _seed_terminal_run(store)
        client = _make_client(store)

        # Act
        response = _get(client, "/runs/r1/artifacts")

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    def test_knowledge_sin_certificado_da_lista_vacia(self) -> None:
        # Arrange
        store = create_event_store()
        _seed_terminal_run(store)
        client = _make_client(store)

        # Act
        response = _get(client, "/runs/r1/knowledge")

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    def test_knowledge_con_certificado_real_trae_la_conclusion(self) -> None:
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
        response = _get(client, f"/runs/{run_id}/knowledge")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["statement"] == _STATEMENT_4BUS
        assert body[0]["verdict"] == "verified"
        assert body[0]["run_id"] == run_id

    def test_artifacts_con_certificado_real_no_revienta(self) -> None:
        # Arrange — `POST /runs` (Task B) todavía no declara `deliverables`
        # en el `RunTicket`: `assemble_bundle` cae a su default `()`, así
        # que un golden path real hoy da `[]` — igual que sin certificado,
        # pero por una ruta de código distinta (predicate SÍ existe, la
        # ruta itera `predicate["deliverables"]` vacío). Se documenta en el
        # reporte como costura fuera de alcance de E1.
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
        response = _get(client, f"/runs/{run_id}/artifacts")

        # Assert
        assert response.status_code == 200
        assert response.json() == []


class TestStepEvidence:
    def test_step_con_submitted_y_verification_da_capability_y_attestations(
        self,
    ) -> None:
        # Arrange
        store = create_event_store()
        store.append(
            stream_id="r1",
            type="run.created",
            actor_id="user:dylan",
            domain_id="d-default",
            payload=_RUN_CREATED_PAYLOAD,
        )
        store.append(
            stream_id="r1",
            type="capability.job.submitted",
            actor_id="service:runtime",
            domain_id="d-default",
            payload={
                "step_id": "s1",
                "capability_id": "cap.echo",
                "input_digest": "sha256:in",
            },
            expected_seq=1,
        )
        store.append(
            stream_id="r1",
            type="verification.completed",
            actor_id="service:verifier",
            domain_id="d-default",
            payload={
                "step_id": "s1",
                "attestation": {
                    "verdict": "pass",
                    "verifier_class": "execution",
                    "level": "AL3",
                    "claim_digest": "sha256:c1",
                },
            },
            expected_seq=2,
        )
        store.append(
            stream_id="r1",
            type="run.completed",
            actor_id="service:runtime",
            domain_id="d-default",
            payload={},
            expected_seq=3,
        )
        client = _make_client(store)

        # Act
        response = _get(client, "/runs/r1/steps/s1/evidence")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["step_id"] == "s1"
        assert body["capability_id"] == "cap.echo"
        assert body["input_digest"] == "sha256:in"
        assert len(body["attestations"]) == 1
        assert body["attestations"][0]["verifier_class"] == "execution"

    def test_step_sin_verificacion_da_attestations_vacio(self) -> None:
        # Arrange — el paso corrió (run terminó) pero nunca se sembró
        # `verification.completed` para este step_id.
        store = create_event_store()
        _seed_terminal_run(store)
        client = _make_client(store)

        # Act
        response = _get(client, "/runs/r1/steps/s-sin-verificar/evidence")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["step_id"] == "s-sin-verificar"
        assert body["capability_id"] == ""
        assert body["attestations"] == []


class TestAblation:
    def test_run_sin_metricas_da_lista_vacia(self) -> None:
        # Arrange
        store = create_event_store()
        _seed_terminal_run(store)
        client = _make_client(store)

        # Act
        response = _get(client, "/runs/r1/ablation")

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    def test_run_con_metrics_recorded_da_fila_por_variante(self) -> None:
        # Arrange
        store = create_event_store()
        store.append(
            stream_id="r1",
            type="run.created",
            actor_id="user:dylan",
            domain_id="d-default",
            payload=_RUN_CREATED_PAYLOAD,
        )
        store.append(
            stream_id="r1",
            type="run.metrics.recorded",
            actor_id="service:runtime",
            domain_id="d-default",
            payload={
                "variant": "quantum",
                "cut_cost": 12.5,
                "wall_ms": 340,
                "verification_latency_ms": 80,
            },
            expected_seq=1,
        )
        client = _make_client(store)

        # Act
        response = _get(client, "/runs/r1/ablation")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["variant"] == "quantum"
        assert body[0]["cut_cost"] == 12.5
        assert body[0]["wall_ms"] == 340
        assert body[0]["verification_latency_ms"] == 80

    def test_evento_de_metrics_sin_variant_se_ignora(self) -> None:
        # Arrange
        store = create_event_store()
        store.append(
            stream_id="r1",
            type="run.created",
            actor_id="user:dylan",
            domain_id="d-default",
            payload=_RUN_CREATED_PAYLOAD,
        )
        store.append(
            stream_id="r1",
            type="run.metrics.recorded",
            actor_id="service:runtime",
            domain_id="d-default",
            payload={"wall_ms": 340},
            expected_seq=1,
        )
        client = _make_client(store)

        # Act
        response = _get(client, "/runs/r1/ablation")

        # Assert
        assert response.status_code == 200
        assert response.json() == []


class TestTopology:
    def test_run_con_particion_da_payload_intacto(self) -> None:
        # Arrange
        store = create_event_store()
        store.append(
            stream_id="r1",
            type="run.created",
            actor_id="user:dylan",
            domain_id="d-default",
            payload=_RUN_CREATED_PAYLOAD,
        )
        store.append(
            stream_id="r1",
            type="verification.completed",
            actor_id="service:verifier",
            domain_id="d-default",
            payload={
                "topology_ref": "topo-1",
                "islands": [
                    {
                        "id": "isla-1",
                        "name": "Norte",
                        "bus_ids": [0, 1],
                        "verification": {"verdict": "pass"},
                    }
                ],
                "cut_branch_ids": ["b1"],
                "cut_cost": 5,
            },
            expected_seq=1,
        )
        client = _make_client(store)

        # Act
        response = _get(client, "/runs/r1/topology")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["topology_ref"] == "topo-1"
        assert len(body["islands"]) == 1
        assert body["islands"][0]["verification"] == {"verdict": "pass"}
        assert body["cut_branch_ids"] == ["b1"]
        assert body["cut_cost"] == 5

    def test_run_sin_particion_da_envelope_vacio(self) -> None:
        # Arrange
        store = create_event_store()
        _seed_terminal_run(store)
        client = _make_client(store)

        # Act
        response = _get(client, "/runs/r1/topology")

        # Assert
        assert response.status_code == 200
        assert response.json() == {
            "topology_ref": "",
            "islands": [],
            "cut_branch_ids": [],
            "cut_cost": 0,
        }


class TestRunDesconocido:
    """Fail-closed (mismo patrón que `certificate.py::get_certificate`): un
    `run_id` desconocido es 404 en las 5 rutas por-run, jamás una lista
    vacía disfrazada de éxito silencioso."""

    @pytest.mark.parametrize(
        "path",
        [
            "/runs/no-existe/artifacts",
            "/runs/no-existe/knowledge",
            "/runs/no-existe/steps/s1/evidence",
            "/runs/no-existe/ablation",
            "/runs/no-existe/topology",
        ],
    )
    def test_run_id_inexistente_da_404(self, path: str) -> None:
        # Arrange
        client = _make_client()

        # Act
        response = _get(client, path)

        # Assert
        assert response.status_code == 404
