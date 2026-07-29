"""Tests de `POST /runs` — plan `docs/mvp/01-runtime-api.md` §1.

Cubre: golden path de dos patas (formal + eléctrica) sobre `sintetica-4bus`,
fail-closed cuando `resolve_verifiers` devuelve vacío, claim inválido (400 de
validación de dominio), instancia desconocida amparada SOLO por la pata
formal, y capability desconocida como `run.failed` fail-loud — el arranque
HTTP jamás falla por un error DENTRO del run (el registro lo registra como
evento, nunca tumba el API).

Bajo `TestClient` los `BackgroundTasks` corren y TERMINAN dentro del ciclo de
la request (freeze de Starlette): tras el POST el run ya completó, así que un
`GET .../events?live=0` inmediato ve el snapshot terminal — no hace falta
sondear ni dormir.
"""

from __future__ import annotations

import json
import re
from typing import Any, cast

import httpx
from chimera_api.app import create_app
from fastapi.testclient import TestClient

from blite.events import create_event_store
from blite.events.store import EventStore
from blite.runtime.registry import EntryPointRegistry
from blite_capability.manifest import CapabilityManifest

_RUN_ID_PATTERN = re.compile(r"^run-[0-9a-f]{32}$")

_STATEMENT_4BUS = "la partición propuesta es óptima y electricamente factible"
_SCOPE_4BUS: dict[str, Any] = {"instancia": "sintetica-4bus"}
_EDGES_4BUS = ((0, 1, 0), (2, 3, 0), (1, 2, 5))

_STATEMENT_K3 = "la asignación propuesta es el corte máximo exacto"
_SCOPE_DESCONOCIDA: dict[str, Any] = {"instancia": "desconocida"}
_EDGES_K3 = ((0, 1, 1), (1, 2, 1), (0, 2, 1))


class _EchoCapability:
    """Capability hermética de test — mismo patrón que
    `tests/unit/certificate/test_assemble.py::_EchoCapability`."""

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


class _MissionCapability:
    """Capability hermética tolerante a inputs de misión (sin campos
    requeridos) — doble etiquetado, mismo patrón que `_EchoCapability`."""

    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id="cap.mission-echo",
            description="mission-tolerant test capability",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return {"echoed_mission": inputs.get("mission")}


def _make_registry() -> EntryPointRegistry:
    return EntryPointRegistry(
        {"cap.echo": _EchoCapability(), "cap.mission-echo": _MissionCapability()}
    )


def _make_client(store: EventStore | None = None) -> TestClient:
    event_store = store if store is not None else create_event_store()
    return TestClient(create_app(event_store, registry=_make_registry()))


# starlette.testclient.TestClient anota `.get()`/`.post()` contra el paquete
# `httpx2` (bajo TYPE_CHECKING) que este repo no instala — el fallback en
# runtime es el `httpx` real, así que el cast es fiel al tipo efectivo en
# ejecución; pyright solo necesita el ignore puntual sobre la llamada (mismo
# patrón que `_get` en test_app_sse.py).
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


def _parse_frames(body: str) -> list[dict[str, str]]:
    frames: list[dict[str, str]] = []
    for chunk in body.split("\n\n"):
        if not chunk:
            continue
        frame: dict[str, str] = {}
        for line in chunk.split("\n"):
            key, _, value = line.partition(": ")
            frame[key] = value
        frames.append(frame)
    return frames


def _events_of(client: TestClient, run_id: str) -> list[dict[str, str]]:
    response = _get(client, f"/runs/{run_id}/events?live=0")
    return _parse_frames(response.text)


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


class TestGoldenPathDosPatas:
    def test_run_optimo_sobre_sintetica_4bus_completa_con_dos_verifications(
        self,
    ) -> None:
        # Arrange
        client = _make_client()
        body = _run_body(
            claim=_claim_body(
                n_nodes=4,
                edges=_EDGES_4BUS,
                assignment=(0, 0, 1, 1),
                canonical_statement=_STATEMENT_4BUS,
                scope=_SCOPE_4BUS,
            )
        )

        # Act
        response = _post(client, "/runs", json_body=body)

        # Assert
        assert response.status_code == 202
        run_id = response.json()["run_id"]
        assert _RUN_ID_PATTERN.match(run_id)

        frames = _events_of(client, run_id)
        types = [f["event"] for f in frames]
        assert frames[-1]["event"] == "run.completed"
        assert types.count("claim.emitted") == 1
        assert types.count("verification.completed") == 2


class TestFailClosed:
    def test_claim_type_fuera_del_vocabulario_no_agenda_el_run(self) -> None:
        # Arrange
        store = create_event_store()
        client = _make_client(store)
        body = _run_body(
            claim=_claim_body(
                n_nodes=4,
                edges=_EDGES_4BUS,
                assignment=(0, 0, 1, 1),
                canonical_statement=_STATEMENT_4BUS,
                scope=_SCOPE_4BUS,
                claim_type="mystery",
            )
        )

        # Act
        response = _post(client, "/runs", json_body=body)

        # Assert — jamás un run sin verificación: ni se agenda, ni deja rastro
        assert response.status_code == 400
        assert "fail-closed" in response.json()["detail"]
        assert store.read_all() == ()


class TestClaimInvalido:
    def test_assignment_de_largo_incorrecto_da_400(self) -> None:
        # Arrange
        client = _make_client()
        body = _run_body(
            claim=_claim_body(
                n_nodes=3,
                edges=(),
                assignment=(0, 0),
                canonical_statement="assignment de largo incorrecto",
                scope={"instancia": "cualquiera"},
            )
        )

        # Act
        response = _post(client, "/runs", json_body=body)

        # Assert
        assert response.status_code == 400


class TestFormalOnly:
    def test_instancia_desconocida_ampara_solo_con_cpsat(self) -> None:
        # Arrange
        client = _make_client()
        body = _run_body(
            claim=_claim_body(
                n_nodes=3,
                edges=_EDGES_K3,
                assignment=(0, 0, 1),
                canonical_statement=_STATEMENT_K3,
                scope=_SCOPE_DESCONOCIDA,
            )
        )

        # Act
        response = _post(client, "/runs", json_body=body)

        # Assert
        assert response.status_code == 202
        run_id = response.json()["run_id"]
        frames = _events_of(client, run_id)
        assert frames[-1]["event"] == "run.completed"
        assert [f["event"] for f in frames].count("verification.completed") == 1


class TestCapabilityDesconocida:
    def test_capability_inexistente_falla_el_run_no_el_arranque(self) -> None:
        # Arrange
        client = _make_client()
        body = _run_body(
            claim=_claim_body(
                n_nodes=3,
                edges=_EDGES_K3,
                assignment=(0, 0, 1),
                canonical_statement=_STATEMENT_K3,
                scope=_SCOPE_DESCONOCIDA,
            ),
            capability_id="cap.inexistente",
        )

        # Act
        response = _post(client, "/runs", json_body=body)

        # Assert — el arranque HTTP no falla; el fallo vive DENTRO del stream
        assert response.status_code == 202
        run_id = response.json()["run_id"]
        frames = _events_of(client, run_id)
        assert frames[-1]["event"] == "run.failed"


class TestModoMision:
    """`POST /runs` modo misión — docs/specs/endpoints-studio.md
    §"POST /runs — modo misión" (checkpoint 5, costura A↔E↔D).

    Contrato: 202 + run_id; el plan viaja como eventos (`plan.created` /
    `plan.item_updated`) en el stream; sin gate de verificación el run
    termina `run.failed {error_kind: "exhausted"}` — jamás un
    `run.completed` implícito; 422 SOLO si ni mission ni claim válidos.
    """

    def test_mission_arranca_202_y_emite_plan_created_en_el_stream(self) -> None:
        # Arrange
        client = _make_client()
        mission = (
            "particionar sintetica-4bus en islas controladas y certificar el corte"
        )
        body = {
            "mission": mission,
            "instance_id": "sintetica-4bus",
            "capability_id": "cap.mission-echo",
            "max_turns": 2,
        }

        # Act
        response = _post(client, "/runs", json_body=body)

        # Assert — 202 + run_id, mismo envelope que el modo claim-first
        assert response.status_code == 202
        run_id = response.json()["run_id"]
        assert _RUN_ID_PATTERN.match(run_id)

        frames = _events_of(client, run_id)
        types = [f["event"] for f in frames]

        # El plan es un artefacto del stream (harness-agentico.md §Contrato-2)
        assert "plan.created" in types
        plan_frame = next(f for f in frames if f["event"] == "plan.created")
        plan_payload = json.loads(plan_frame["data"])["payload"]
        assert plan_payload["run_id"] == run_id
        # La misión queda journalizada como description del ítem fundacional
        assert plan_payload["items"][0]["description"] == mission
        assert "plan.item_updated" in types

        # Gate ausente ⇒ exhausted honesto — jamás run.completed implícito
        assert frames[-1]["event"] == "run.failed"
        last_payload = json.loads(frames[-1]["data"])["payload"]
        assert last_payload["error_kind"] == "exhausted"

    def test_mission_sin_capability_usa_default_y_falla_dentro_del_stream(
        self,
    ) -> None:
        # Arrange — el registry hermético NO registra la capability default:
        # el arranque HTTP igual responde 202 y el fallo vive en el stream
        # (fail-loud, mismo contrato que TestCapabilityDesconocida).
        client = _make_client()

        # Act
        response = _post(
            client, "/runs", json_body={"mission": "misión sin capability explícita"}
        )

        # Assert
        assert response.status_code == 202
        run_id = response.json()["run_id"]
        frames = _events_of(client, run_id)
        types = [f["event"] for f in frames]
        assert "plan.created" in types
        # FLAG (frontera Steven, no de este contrato): en el camino de error
        # del turno agéntico, `plan.item_updated {failed}` se apendea DESPUÉS
        # de `run.failed` (loop.py `_run_agentic_turn` — fail_run corre dentro
        # de `_run_resolve_and_invoke`); por eso acá se asevera presencia del
        # terminal fail-loud, no su posición final.
        assert "run.failed" in types

    def test_body_sin_mission_ni_claim_da_422(self) -> None:
        # Arrange
        store = create_event_store()
        client = _make_client(store)

        # Act
        response = _post(client, "/runs", json_body={})

        # Assert — ni se agenda, ni deja rastro
        assert response.status_code == 422
        assert store.read_all() == ()

    def test_mission_vacia_da_422(self) -> None:
        # Arrange
        store = create_event_store()
        client = _make_client(store)

        # Act
        response = _post(client, "/runs", json_body={"mission": ""})

        # Assert
        assert response.status_code == 422
        assert store.read_all() == ()

    def test_body_con_mission_y_claim_da_422(self) -> None:
        # Arrange — `extra="forbid"` en AMBOS lados de la unión: un body con
        # los dos discriminadores no valida contra ninguno.
        store = create_event_store()
        client = _make_client(store)
        body = _run_body(
            claim=_claim_body(
                n_nodes=4,
                edges=_EDGES_4BUS,
                assignment=(0, 0, 1, 1),
                canonical_statement=_STATEMENT_4BUS,
                scope=_SCOPE_4BUS,
            )
        )
        body["mission"] = "también una misión"

        # Act
        response = _post(client, "/runs", json_body=body)

        # Assert
        assert response.status_code == 422
        assert store.read_all() == ()


class TestContratoFixtureStudio:
    """El body EXACTO que el Studio produce (fixture de costura single-origin,
    `tests/fixtures/contract/endpoints/post-runs-mission.json`) responde 202 —
    el 422 vivo del checkpoint 2 está muerto por contrato, no por casualidad."""

    def test_el_body_del_fixture_responde_202_y_emite_plan_created(self) -> None:
        # Arrange
        from pathlib import Path

        fixture_path = (
            Path(__file__).resolve().parents[3]
            / "tests"
            / "fixtures"
            / "contract"
            / "endpoints"
            / "post-runs-mission.json"
        )
        body = cast(dict[str, Any], json.loads(fixture_path.read_text("utf-8")))
        client = _make_client()

        # Act
        response = _post(client, "/runs", json_body=body)

        # Assert — 202 aunque el registry hermético no conozca la capability
        # (blite.solvers.qaoa): el arranque HTTP solo falla por errores del
        # REQUEST; lo demás vive fail-loud en el stream.
        assert response.status_code == 202
        run_id = response.json()["run_id"]
        frames = _events_of(client, run_id)
        assert "plan.created" in [f["event"] for f in frames]


class TestEndpointsExistentesSiguenVerdes:
    def test_health_sigue_respondiendo_ok(self) -> None:
        client = _make_client()
        response = _get(client, "/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
