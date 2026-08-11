"""Tests de `POST /runs` — modo ablación (ceremonia #177, spec
`docs/specs/endpoints-studio.md` §"POST /runs — modo ablación").

Tercera forma de body (`{ablation: {instance_id, layers?, seed?}}`),
discriminada por presencia de campo como `claim`/`mission` — mismo patrón que
`TestModoMision`/`TestFailClosed` de `test_runs.py`. Cubre: 202 + run_id,
discriminación excluyente contra `claim`/`mission` (422), `extra="forbid"`
sobre el body anidado (incluido un intento de elegir brazos), fail-loud de
instancia desconocida DENTRO del stream del RAÍZ (nunca un 4xx del arranque),
y los brazos como sub-runs que `GET /runs/{run_id}/ablation` agrega.

Bajo `TestClient` los `BackgroundTasks` corren y TERMINAN dentro del ciclo de
la request (mismo freeze de Starlette que `test_runs.py`) — tras el POST el
run ya completó su orquestación.
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

# knowledge/islanding/corpus/cr6-uniforme.json — óptimo congelado 5, la misma
# instancia que `TestModoMisionInstanciaReal` de `test_runs.py` ya usa contra
# el registry real.
_INSTANCE = "cr6-uniforme"


class _FakeQaoa:
    """Hermética: produce la forma que `expected_energy_of` lee."""

    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id="blite.quantum.qaoa",
            description="qaoa hermético de test",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            side_effects="pure",
            required_permission="capability:invoke",
            interaction="request_response",
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return {"energy": 6.0, "expected_energy": 6.35}


class _FakeQubo:
    """Hermética: produce la forma que `exact_energy_of` lee."""

    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id="blite.solvers.qubo",
            description="qubo hermético de test",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            side_effects="pure",
            required_permission="capability:invoke",
            interaction="request_response",
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return {"energy": 5.0}


class _FakeZne:
    """Hermética: produce la forma que `mitigated_energy_of` lee."""

    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id="blite.quantum.zne",
            description="zne hermético de test",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            side_effects="pure",
            required_permission="capability:invoke",
            interaction="request_response",
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return {"mitigated_energy": 5.5, "improvement_survives_control": True}


def _make_ablation_registry() -> EntryPointRegistry:
    """Registry hermético que SÍ resuelve los 3 `capability_id` que
    `build_arms` declara — a diferencia del registry por defecto de
    `test_runs.py` (`cap.echo`/`cap.mission-echo`), que deliberadamente no
    los conoce."""
    return EntryPointRegistry(
        {
            "blite.quantum.qaoa": _FakeQaoa(),
            "blite.solvers.qubo": _FakeQubo(),
            "blite.quantum.zne": _FakeZne(),
        }
    )


def _make_client(
    store: EventStore | None = None, *, registry: EntryPointRegistry | None = None
) -> TestClient:
    event_store = store if store is not None else create_event_store()
    return TestClient(create_app(event_store, registry=registry))


def _get(client: TestClient, url: str) -> httpx.Response:
    return cast(httpx.Response, client.get(url))


def _post(client: TestClient, url: str, *, json_body: dict[str, Any]) -> httpx.Response:
    return cast(httpx.Response, client.post(url, json=json_body))


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


_CLOSING_EVENT_TYPES = frozenset({"run.metrics.recorded"})


def _events_hasta_el_terminal(client: TestClient, run_id: str) -> list[dict[str, str]]:
    """Mismo corte que `provenance_slice` — el cierre métrico (V2/M19) se
    emite DESPUÉS del terminal, así que preguntar por el desenlace de un run
    es preguntar por esto, no por `frames[-1]`."""
    frames = _events_of(client, run_id)
    return [f for f in frames if f["event"] not in _CLOSING_EVENT_TYPES]


def _sub_run_ids_of(store: EventStore, run_id: str) -> list[str]:
    """Sub-runs DIRECTOS de `run_id` — correlación por `parent_run_id`
    (§13), no por prefijo de id ni por "cualquier stream que no sea el
    raíz" (el store también puede tener streams de sistema, p.ej.
    `system:registry`)."""
    return [
        stream_id
        for stream_id in {e.stream_id for e in store.read_all()}
        if stream_id != run_id
        and store.read_stream(stream_id)
        and store.read_stream(stream_id)[0].payload.get("parent_run_id") == run_id
    ]


class TestAblacionArrancaComoSubRuns:
    """Body válido ⇒ 202, y los brazos (`blite.runtime.ablation.build_arms`)
    corren como sub-runs del raíz."""

    def test_body_valido_arranca_202_con_run_id(self) -> None:
        # Arrange
        client = _make_client(registry=_make_ablation_registry())
        body = {"ablation": {"instance_id": _INSTANCE}}

        # Act
        response = _post(client, "/runs", json_body=body)

        # Assert
        assert response.status_code == 202
        run_id = response.json()["run_id"]
        assert _RUN_ID_PATTERN.match(run_id)

    def test_los_brazos_aparecen_como_sub_runs_del_raiz(self) -> None:
        # Arrange
        store = create_event_store()
        client = _make_client(store, registry=_make_ablation_registry())
        body = {"ablation": {"instance_id": _INSTANCE, "layers": 1, "seed": 7}}

        # Act
        response = _post(client, "/runs", json_body=body)
        run_id = response.json()["run_id"]

        # Assert — el raíz existe y CADA brazo declaró `parent_run_id`
        # apuntando a él (§13: la jerarquía viaja por `parent_run_id`, no por
        # streams anidados).
        raiz = store.read_stream(run_id)
        assert raiz[0].type == "run.created"
        assert len(_sub_run_ids_of(store, run_id)) == 3

    def test_get_ablation_del_raiz_agrega_las_filas_de_los_tres_brazos(self) -> None:
        """El set de variantes lo produce LA REGLA (`build_arms`), no el
        caller: el body no trae forma de pedir un subconjunto, y estas son
        SIEMPRE las tres declaradas con productor real."""
        # Arrange
        store = create_event_store()
        client = _make_client(store, registry=_make_ablation_registry())
        body = {"ablation": {"instance_id": _INSTANCE}}

        # Act
        response = _post(client, "/runs", json_body=body)
        run_id = response.json()["run_id"]
        panel = _get(client, f"/runs/{run_id}/ablation").json()

        # Assert
        assert sorted(fila["variant"] for fila in panel) == [
            "classical",
            "quantum",
            "zne",
        ]
        assert "mitigated" not in {fila["variant"] for fila in panel}
        for fila in panel:
            assert isinstance(fila["cut_cost"], float)


class TestDiscriminacionExcluyente:
    """`extra="forbid"` en los TRES lados de la unión (`claim`/`mission`/
    `ablation`) — un body con dos formas, o ninguna, no valida contra
    ninguna."""

    def test_ablation_y_claim_juntos_da_422(self) -> None:
        # Arrange
        store = create_event_store()
        client = _make_client(store)
        body = {
            "ablation": {"instance_id": _INSTANCE},
            "capability_id": "cap.echo",
            "inputs": {"x": 1},
            "claim": {
                "instance": {"n_nodes": 2, "edges": ((0, 1, 1),)},
                "assignment": (0, 1),
                "canonical_statement": "también un claim",
                "scope": {"instancia": "cualquiera"},
                "claim_type": "solution",
            },
        }

        # Act
        response = _post(client, "/runs", json_body=body)

        # Assert
        assert response.status_code == 422
        assert store.read_all() == ()

    def test_ablation_y_mission_juntos_da_422(self) -> None:
        # Arrange
        store = create_event_store()
        client = _make_client(store)
        body = {
            "ablation": {"instance_id": _INSTANCE},
            "mission": "también una misión",
        }

        # Act
        response = _post(client, "/runs", json_body=body)

        # Assert
        assert response.status_code == 422
        assert store.read_all() == ()

    def test_body_vacio_da_422(self) -> None:
        # Arrange
        store = create_event_store()
        client = _make_client(store)

        # Act
        response = _post(client, "/runs", json_body={})

        # Assert
        assert response.status_code == 422
        assert store.read_all() == ()

    def test_ablation_con_campo_extra_desconocido_da_422(self) -> None:
        # Arrange
        store = create_event_store()
        client = _make_client(store)
        body = {"ablation": {"instance_id": _INSTANCE, "foo": "bar"}}

        # Act
        response = _post(client, "/runs", json_body=body)

        # Assert
        assert response.status_code == 422
        assert store.read_all() == ()

    def test_el_caller_no_puede_elegir_brazos_via_un_campo_arms(self) -> None:
        """No existe campo para declarar QUÉ brazos correr — un intento de
        colarlo por `arms` (o cualquier otro nombre) es exactamente el mismo
        caso que un campo extra desconocido: `extra="forbid"` lo rechaza."""
        # Arrange
        store = create_event_store()
        client = _make_client(store)
        body = {
            "ablation": {"instance_id": _INSTANCE, "arms": ["quantum", "classical"]}
        }

        # Act
        response = _post(client, "/runs", json_body=body)

        # Assert
        assert response.status_code == 422
        assert store.read_all() == ()


class TestFailLoudInstanciaDesconocida:
    """Fail-loud intacto (spec): instancia desconocida ⇒ 202 + `run.failed`
    DENTRO del stream del RAÍZ — el arranque HTTP solo falla por errores del
    REQUEST, jamás por lo que pase al resolver la instancia."""

    def test_instance_id_desconocido_da_202_y_run_failed_en_el_stream(self) -> None:
        # Arrange
        client = _make_client(registry=_make_ablation_registry())
        body = {"ablation": {"instance_id": "no-existe-de-verdad"}}

        # Act
        response = _post(client, "/runs", json_body=body)

        # Assert — el arranque HTTP no falla
        assert response.status_code == 202
        run_id = response.json()["run_id"]
        assert _RUN_ID_PATTERN.match(run_id)

        frames = _events_hasta_el_terminal(client, run_id)
        types = [f["event"] for f in frames]
        assert types == ["run.created", "run.failed"]
        payload = json.loads(frames[-1]["data"])["payload"]
        assert payload["error_kind"] == "FileNotFoundError"

    def test_instancia_desconocida_no_deja_sub_runs_colgados(self) -> None:
        """Sin matriz no hay con qué construir brazos — cero sub-runs, no
        tres sub-runs a medio arrancar."""
        # Arrange
        store = create_event_store()
        client = _make_client(store, registry=_make_ablation_registry())
        body = {"ablation": {"instance_id": "tampoco-existe"}}

        # Act
        response = _post(client, "/runs", json_body=body)
        run_id = response.json()["run_id"]

        # Assert
        assert _sub_run_ids_of(store, run_id) == []


class TestCapabilityDelRegistryDelApi:
    """El modo ablación resuelve capabilities por el registry del API
    (`RunResources.registry()`), NUNCA por el `_registry()` explícito del
    script — si el registry del despliegue no conoce los capability_id de
    los brazos, eso es fail-loud DENTRO del stream de CADA brazo, jamás un
    500 del arranque HTTP."""

    def test_capabilities_sin_registrar_fallan_el_brazo_no_el_arranque(self) -> None:
        # Arrange — registry EXPLÍCITAMENTE vacío: sin override,
        # `RunResources.registry()` carga los entry points REALES
        # instalados en el venv (donde `blite.quantum.qaoa` SÍ existe) —
        # este test necesita garantizar la AUSENCIA, no depender de qué
        # esté instalado.
        store = create_event_store()
        client = _make_client(store, registry=EntryPointRegistry({}))
        body = {"ablation": {"instance_id": _INSTANCE}}

        # Act
        response = _post(client, "/runs", json_body=body)

        # Assert — el arranque HTTP sigue respondiendo 202
        assert response.status_code == 202
        run_id = response.json()["run_id"]
        sub_run_ids = _sub_run_ids_of(store, run_id)
        assert len(sub_run_ids) == 3
        for sub_run_id in sub_run_ids:
            tipos = [e.type for e in store.read_stream(sub_run_id)]
            assert "run.failed" in tipos
