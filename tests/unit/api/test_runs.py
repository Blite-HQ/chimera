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
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
from chimera_api.app import create_app
from chimera_api.model_proposer import make_model_proposer
from chimera_api.model_session import write_session
from fastapi.testclient import TestClient

from blite.events import create_event_store
from blite.events.store import EventStore
from blite.protocols.model_server import InMemoryReplayManifest, ModelServer
from blite.runtime.content_store import InMemoryContentStore
from blite.runtime.loop import TurnContext
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
            side_effects="pure",
            required_permission="capability:invoke",
            interaction="request_response",
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
            side_effects="pure",
            required_permission="capability:invoke",
            interaction="request_response",
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
        client.get(url),
    )


def _post(client: TestClient, url: str, *, json_body: dict[str, Any]) -> httpx.Response:
    return cast(
        httpx.Response,
        client.post(url, json=json_body),
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
    """Frames del stream del run — INCLUIDA la familia de cierre.

    [V2/M19] `run.metrics.recorded` se emite DESPUÉS del terminal (freeze §2
    [stress-final]: familia de cierre, fuera del hash), así que el último
    frame del stream ya no es el terminal. Los tests que preguntan «¿cómo
    cerró este run?» usan `_events_hasta_el_terminal`, que corta donde corta
    el provenance_hash — preguntar por `frames[-1]` sería preguntar por el
    cierre métrico, no por el desenlace."""
    response = _get(client, f"/runs/{run_id}/events?live=0")
    return _parse_frames(response.text)


_CLOSING_EVENT_TYPES = frozenset({"run.metrics.recorded"})


def _events_hasta_el_terminal(client: TestClient, run_id: str) -> list[dict[str, str]]:
    """El mismo corte que `provenance_slice`: hasta el terminal, inclusive."""
    frames = _events_of(client, run_id)
    return [f for f in frames if f["event"] not in _CLOSING_EVENT_TYPES]


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

        frames = _events_hasta_el_terminal(client, run_id)
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
    def test_instancia_sin_dato_electrico_suma_la_pata_estructural(self) -> None:
        """[V1/M18] El run de una instancia sin modelo eléctrico emite DOS
        `verification.completed`: la formal (CP-SAT) y la estructural (AL2),
        que es la que aporta los checks por isla que el mapa necesita. Antes
        emitía una sola y la superficie se quedaba sin nada que pintar."""
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
        frames = _events_hasta_el_terminal(client, run_id)
        assert frames[-1]["event"] == "run.completed"
        assert [f["event"] for f in frames].count("verification.completed") == 2


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
        frames = _events_hasta_el_terminal(client, run_id)
        assert frames[-1]["event"] == "run.failed"


class TestModoMision:
    """`POST /runs` modo misión — docs/specs/endpoints-studio.md
    §"POST /runs — modo misión" (decisión #91, costura A↔E↔D).

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

        frames = _events_hasta_el_terminal(client, run_id)
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
        frames = _events_hasta_el_terminal(client, run_id)
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


_MODEL_CTX = {"domain_id": "domain-default"}
_MODEL_BACKEND_ID = "anthropic/claude-sonnet-test"


_LOCAL_OPERATOR = "user:local-operator"
"""La identidad que `SessionAuth.identity_from` resuelve sin cookie
(`chimera_api.auth`) — la MISMA que estampa el `author` de la misión en el
historial v2, así que una sesión grabada tiene que usarla o la clave de
replay no coincide."""


def _write_fake_session(
    session_dir: Path,
    *,
    turn_contexts_and_responses: list[tuple[TurnContext, bytes]],
    mission: str | None = None,
    mission_author: str | None = None,
) -> None:
    """Graba una sesión fake — mismo camino de producción (`make_model_proposer`
    sobre un `ModelServer(mode="record")`) que `scripts/record_session.py`
    usaría de verdad, solo que con un `live_caller` fake determinista en vez
    de litellm (freeze §15.7: testeable sin red/API key).

    `mission`/`mission_author` son los del historial v2 (P3,
    `chat-conversacion.md` §Contrato-6): la vista del prompt los incluye, así
    que grabar con OTRA misión produce otro `prompt_digest` y el replay hace
    miss — propiedad correcta, no un detalle del test: la sesión grabada es
    de UNA conversación concreta."""
    store = InMemoryContentStore()
    manifest = InMemoryReplayManifest()

    # Un `ModelServer(mode="record")` nuevo por turno (mismo manifest/
    # content_store compartido) — cada uno con el `live_caller` fake que le
    # corresponde a ESE turno.
    for turn_ctx, response_bytes in turn_contexts_and_responses:
        recorder = ModelServer(
            mode="record",
            content_store=store,
            ctx=_MODEL_CTX,
            manifest=manifest,
            live_caller=lambda _req, _b=response_bytes: _b,
        )
        proposer = make_model_proposer(
            model_server=recorder,
            registry=_make_registry(),
            content_store=store,
            ctx=_MODEL_CTX,
            backend_id=_MODEL_BACKEND_ID,
            mission=mission,
            mission_author=mission_author,
        )
        proposer(turn_ctx)

    write_session(
        session_dir,
        backend_id=_MODEL_BACKEND_ID,
        local=False,
        manifest=manifest,
        content_store=store,
        ctx=_MODEL_CTX,
    )


class TestModoMisionProposerReal:
    """`CHIMERA_MODEL_BACKEND`/`CHIMERA_MODEL_SESSION_DIR` — el agente real
    (P4, decisión #92) entra por el MISMO seam `Proposer`; ausente ⇒ el
    placeholder determinista actual, default INTACTO (cubierto por
    `TestModoMision` de arriba, que no toca estas env vars)."""

    def test_replay_progresa_con_la_capability_que_dicta_la_sesion(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange — el goal_capability_id del body ("cap.goal-no-registrada")
        # NO existe en el registry hermético: si el placeholder determinista
        # corriera (regresión), el turno propondría ESE id verbatim y el run
        # fallaría KeyError en el turno 1. La sesión grabada dicta OTRA
        # capability (real, registrada) — solo el proposer real puede llegar
        # a `capability.job.completed`.
        mission = "particionar la red y certificar el corte"
        goal_inputs = {"mission": mission}
        turn_ctx = TurnContext(
            run_id="run-precomputo-no-viaja-en-la-vista",
            domain_id="domain-default",
            turn=1,
            goal_capability_id="cap.goal-no-registrada",
            goal_inputs=goal_inputs,
            plan_item_id="mission-1",
            previous_output_digest=None,
        )
        session_dir = tmp_path / "sesion-fake"
        _write_fake_session(
            session_dir,
            turn_contexts_and_responses=[
                (
                    turn_ctx,
                    b'{"capability_id": "cap.mission-echo", '
                    b'"inputs": {"mission": "dictado por la sesion"}}',
                )
            ],
            mission=mission,
            mission_author=_LOCAL_OPERATOR,
        )
        monkeypatch.setenv("CHIMERA_MODEL_BACKEND", "replay")
        monkeypatch.setenv("CHIMERA_MODEL_SESSION_DIR", str(session_dir))
        client = _make_client()

        # Act
        response = _post(
            client,
            "/runs",
            json_body={
                "mission": mission,
                "capability_id": "cap.goal-no-registrada",
                "max_turns": 1,
            },
        )

        # Assert — 202 + progresa de VERDAD (la sesión decidió, no el goal).
        assert response.status_code == 202
        run_id = response.json()["run_id"]
        frames = _events_hasta_el_terminal(client, run_id)
        types = [f["event"] for f in frames]
        assert types.count("capability.job.completed") == 1
        assert "capability.job.failed" not in types
        # Sin gate de verificación cableado, max_turns=1 agotado cierra
        # exhausted — jamás completed implícito (mismo contrato que siempre).
        assert frames[-1]["event"] == "run.failed"
        assert json.loads(frames[-1]["data"])["payload"]["error_kind"] == "exhausted"

    def test_replay_miss_falla_fail_loud_en_el_primer_turno(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange — sesión VACÍA (sin entradas): cualquier request es un miss.
        # `capability_id="cap.mission-echo"` SÍ está registrada a propósito:
        # si el placeholder determinista corriera (regresión — sin wiring
        # real), completaría los 5 turnos sin fallar, agotando `max_turns`
        # SOLO tras 5 turnos (>=5 `run.step.started`). El proposer real debe
        # fallar YA en el turno 1 — esto es lo que discrimina el test.
        session_dir = tmp_path / "sesion-vacia"
        write_session(
            session_dir,
            backend_id=_MODEL_BACKEND_ID,
            local=False,
            manifest=InMemoryReplayManifest(),
            content_store=InMemoryContentStore(),
            ctx=_MODEL_CTX,
        )
        monkeypatch.setenv("CHIMERA_MODEL_BACKEND", "replay")
        monkeypatch.setenv("CHIMERA_MODEL_SESSION_DIR", str(session_dir))
        client = _make_client()

        # Act
        response = _post(
            client,
            "/runs",
            json_body={
                "mission": "una misión cualquiera",
                "capability_id": "cap.mission-echo",
                "max_turns": 5,
            },
        )

        # Assert — falla YA en el turno 1 (nunca agota los 5 turnos), y desde
        # P1/M32 lo hace SIN fabricar rastro: el guard del proposer en
        # `loop.py` journaliza el terminal con la causa REAL antes de que
        # ningún step arranque. Cero `run.step.*` (el centinela que provocaba
        # un resolve inventado murió con P1) y `error_kind` = la excepción
        # verdadera del seam del modelo, no un `KeyError` prestado.
        assert response.status_code == 202
        run_id = response.json()["run_id"]
        frames = _events_hasta_el_terminal(client, run_id)
        types = [f["event"] for f in frames]
        assert types.count("run.step.started") == 0
        assert types[-2:] == ["plan.item_updated", "run.failed"]
        assert (
            json.loads(frames[-1]["data"])["payload"]["error_kind"] == "ReplayMissError"
        )

    def test_backend_invalido_levanta_value_error_al_construir_la_app(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CHIMERA_MODEL_BACKEND", "no-es-un-backend-valido")
        with pytest.raises(ValueError, match="CHIMERA_MODEL_BACKEND"):
            _make_client()

    def test_replay_sin_session_dir_levanta_value_error_al_construir_la_app(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CHIMERA_MODEL_BACKEND", "replay")
        monkeypatch.delenv("CHIMERA_MODEL_SESSION_DIR", raising=False)
        with pytest.raises(ValueError, match="CHIMERA_MODEL_SESSION_DIR"):
            _make_client()


class TestContratoFixtureStudio:
    """El body EXACTO que el Studio produce (fixture de costura single-origin,
    `tests/fixtures/contract/endpoints/post-runs-mission.json`) responde 202 —
    el 422 que ese body provocaba en vivo (pre-#91) está muerto por contrato,
    no por casualidad."""

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
        frames = _events_hasta_el_terminal(client, run_id)
        assert "plan.created" in [f["event"] for f in frames]


class TestModoMisionInstanciaReal:
    """`POST /runs` modo misión sobre el registry REAL (`load_registry`,
    entry points instalados del venv — decisiones #95-#98,
    `docs/mvp/decisiones.md` §"Análisis para discusión" punto 1): una misión
    con `instance_id` del corpus real progresa de VERDAD contra
    `blite.solvers.qubo` (default), no la capability tolerante inventada
    `cap.mission-echo` que usan los demás tests de esta clase.

    `cr6-uniforme` (`knowledge/islanding/corpus/cr6-uniforme.json`, óptimo
    congelado 5) resuelve a una QUBO 6×6 simétrica que CP-SAT resuelve en
    milisegundos — cada turno completa resolve+invoke de verdad (2 jobs por
    turno, `max_turns=2` ⇒ 4 steps); sin gate de verificación cableado el
    run SIEMPRE cierra `run.failed {error_kind: "exhausted"}` tras agotar
    `max_turns` — nunca un `run.completed` implícito (§Contrato-3)."""

    def test_cr6_uniforme_completa_turnos_reales_y_cierra_exhausted(self) -> None:
        # Arrange — SIN override de registry: `RunResources.registry()` carga
        # perezosamente `load_registry(store)` sobre los entry points
        # REALES `blite.capabilities` instalados en el venv (no un doble).
        store = create_event_store()
        client = TestClient(create_app(store))
        body = {
            "mission": "particionar cr6-uniforme y certificar el corte",
            "instance_id": "cr6-uniforme",
            "max_turns": 2,
        }

        # Act
        response = _post(client, "/runs", json_body=body)

        # Assert — arranque HTTP intacto
        assert response.status_code == 202
        run_id = response.json()["run_id"]

        frames = _events_hasta_el_terminal(client, run_id)
        types = [f["event"] for f in frames]

        # El plan viaja como eventos, mismo contrato que el resto de la clase
        assert "plan.created" in types

        # Cada turno resolvió e invocó de verdad — CERO fallo de capability:
        # `blite.solvers.qubo` recibe una matrix real (nunca placeholder
        # {mission, instance_id} que el solver rechaza fail-loud).
        assert types.count("capability.job.completed") == 2
        assert "capability.job.failed" not in types

        # Sin gate de verificación cableado, `max_turns` agotado cierra
        # exhausted — jamás completed implícito.
        assert frames[-1]["event"] == "run.failed"
        last_payload = json.loads(frames[-1]["data"])["payload"]
        assert last_payload["error_kind"] == "exhausted"


class TestEndpointsExistentesSiguenVerdes:
    def test_health_sigue_respondiendo_ok(self) -> None:
        client = _make_client()
        response = _get(client, "/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestMissionInstancePathGuard:
    """`instance_id` viaja en el body HTTP y se interpola en una ruta de
    archivo — un id con forma de traversal jamás debe llegar al filesystem
    (validación en la frontera, no solo el fallback benigno)."""

    def test_instance_id_con_traversal_levanta_value_error_sin_tocar_disco(
        self,
    ) -> None:
        from chimera_api.runs import (
            _load_corpus_matrix,  # pyright: ignore[reportPrivateUsage] — el guard es interno a propósito; el test lo ejercita directo
        )

        with pytest.raises(ValueError, match="instance_id"):
            _load_corpus_matrix("../cr6-uniforme")


class TestGuardDeNivelTask:
    """P1/M32 — el guard de nivel TASK de `BackgroundTasks`.

    `starlette.background.BackgroundTask.__call__` no atrapa nada: una
    excepción que escape de `execute_run` (por una frontera que el loop
    todavía no cubra, o por el propio store) dejaría el run COLGADO en el
    stream, sin terminal, para siempre. Este guard es el último recurso:
    cierra el run con `run.failed {error_kind}` — y jamás duplica un
    terminal que la tarea ya haya journalizado.
    """

    def test_excepcion_que_escapa_de_la_tarea_cierra_el_run(self) -> None:
        from chimera_api.runs import run_in_background

        store = create_event_store()
        store.append(
            stream_id="run-colgado",
            type="run.created",
            actor_id="user:dylan",
            domain_id="domain-default",
            payload={
                "run_id": "run-colgado",
                "actor_id": "user:dylan",
                "domain_id": "domain-default",
                "max_steps": 4,
                "policy_digest": "d" * 64,
            },
            expected_seq=0,
        )

        def _tarea_que_explota() -> None:
            msg = "frontera no cubierta por el loop"
            raise RuntimeError(msg)

        # Act — el guard NO relanza: la tarea de fondo jamás tumba el worker.
        run_in_background(store, "run-colgado", _tarea_que_explota)

        # Assert — el terminal de último recurso, y solo después el cierre
        # métrico (V2/M19: familia de cierre post-terminal, fuera del hash).
        eventos = store.read_stream("run-colgado")
        assert [e.type for e in eventos] == [
            "run.created",
            "run.failed",
            "run.metrics.recorded",
        ]
        terminal = next(e for e in eventos if e.type == "run.failed")
        assert terminal.payload["error_kind"] == "RuntimeError"

    def test_no_duplica_el_terminal_que_la_tarea_ya_journalizo(self) -> None:
        from chimera_api.runs import run_in_background

        store = create_event_store()
        store.append(
            stream_id="run-ya-terminal",
            type="run.created",
            actor_id="user:dylan",
            domain_id="domain-default",
            payload={
                "run_id": "run-ya-terminal",
                "actor_id": "user:dylan",
                "domain_id": "domain-default",
                "max_steps": 4,
                "policy_digest": "d" * 64,
            },
            expected_seq=0,
        )

        def _tarea_que_cierra_y_luego_explota() -> None:
            store.append(
                stream_id="run-ya-terminal",
                type="run.failed",
                actor_id="service:runtime",
                domain_id="domain-default",
                payload={"error_kind": "ValueError"},
                expected_seq=1,
            )
            msg = "explota DESPUÉS del terminal"
            raise RuntimeError(msg)

        run_in_background(store, "run-ya-terminal", _tarea_que_cierra_y_luego_explota)

        tipos = [e.type for e in store.read_stream("run-ya-terminal")]
        assert tipos.count("run.failed") == 1
        assert tipos == ["run.created", "run.failed", "run.metrics.recorded"]

    def test_tarea_que_termina_bien_no_agrega_nada(self) -> None:
        from chimera_api.runs import run_in_background

        store = create_event_store()
        corridas: list[int] = []
        run_in_background(store, "run-inexistente", lambda: corridas.append(1))
        assert corridas == [1]
        # Un run que el log jamás vio tampoco recibe cierre métrico: no hay
        # terminal que cerrar (V2/M19).
        assert store.read_stream("run-inexistente") == ()


class TestModelCallEmitido:
    """P4/M31 — `model.call.*` (freeze §3) dejan de ser vocabulario muerto.

    La llamada de modelo era el ÚNICO efecto del sistema sin rastro propio, y
    por eso `extract_effects`/`find_replay_divergences` (`blite.runtime.replay`)
    eran infraestructura sin uso. Vive acá y no en `test_model_call_events.py`
    porque necesita los helpers de sesión/cliente de ESTE módulo."""

    def test_un_run_de_mision_con_agente_real_deja_rastro_de_la_llamada(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mission = "una misión con rastro de modelo"
        turn_ctx = TurnContext(
            run_id="run-no-viaja",
            domain_id="domain-default",
            turn=1,
            goal_capability_id="cap.mission-echo",
            goal_inputs={"mission": mission},
            plan_item_id="mission-1",
        )
        session_dir = tmp_path / "sesion"
        _write_fake_session(
            session_dir,
            turn_contexts_and_responses=[
                (turn_ctx, b'{"capability_id": "cap.mission-echo", "inputs": {}}')
            ],
            mission=mission,
            mission_author=_LOCAL_OPERATOR,
        )
        monkeypatch.setenv("CHIMERA_MODEL_BACKEND", "replay")
        monkeypatch.setenv("CHIMERA_MODEL_SESSION_DIR", str(session_dir))
        client = _make_client()

        response = _post(
            client,
            "/runs",
            json_body={
                "mission": mission,
                "capability_id": "cap.mission-echo",
                "max_turns": 1,
            },
        )

        assert response.status_code == 202
        run_id = response.json()["run_id"]
        types = [f["event"] for f in _events_hasta_el_terminal(client, run_id)]
        assert "model.call.requested" in types
        assert "model.call.completed" in types
        # El rastro del modelo precede al paso que su propuesta disparó — el
        # orden real de los hechos, que es lo que `extract_effects` empareja.
        assert types.index("model.call.requested") < types.index("run.step.started")
