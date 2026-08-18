"""P11 — la ESPERA de la respuesta humana (`chimera_api.runs`).

Lo que F1.3 (#183) dejó declarado como imposible sin cola durable: cerrar EN
VIVO el par `approval.requested` → `approval.responded`. El gate síncrono
decidía con lo que tenía (negar, fail-closed) porque bloquear bajo
`BackgroundTasks` clava un hilo del servidor; con la cola, el run corre en un
worker y ahí esperar es lo normal.

Este archivo cubre la espera en sí (veredicto, vencimiento, muerte del run
mientras espera) y —el test que cierra el ítem— el ciclo COMPLETO contra el
endpoint real: el run se queda vivo pidiendo permiso, un humano responde por
`POST /runs/{id}/approvals/{id}` con 202, y el turno sigue e invoca la
capability de verdad. Sin fixtures y sin aflojar el 409 post-terminal: el
stream está ABIERTO cuando la respuesta entra, así que `approval.responded`
cae DENTRO del corte de procedencia (freeze §2), que era justo el punto.
"""

from __future__ import annotations

import threading
import time
from typing import Any, cast

import httpx
import pytest
from chimera_api.app import create_app
from chimera_api.jobs import MissionJob
from chimera_api.runs import (
    _APPROVAL_DENIED_CAUSE,  # pyright: ignore[reportPrivateUsage]
    _APPROVAL_SIDE_EFFECTS_ENV,  # pyright: ignore[reportPrivateUsage]
    _APPROVAL_TIMEOUT_CAUSE,  # pyright: ignore[reportPrivateUsage]
    RunTerminatedWhileWaitingError,
    _build_approval_gate,  # pyright: ignore[reportPrivateUsage]
    _wait_for_approval_response,  # pyright: ignore[reportPrivateUsage]
    build_run_resources,
    execute_mission_job,
)
from fastapi.testclient import TestClient

from blite.events import create_event_store
from blite.events.store import EventStore
from blite.identity.identity import Identity
from blite.runtime.loop import ProposedStep, TurnContext, execute_run
from blite.runtime.mission import ApprovalRequest
from blite.runtime.registry import EntryPointRegistry
from blite_capability.manifest import CapabilityManifest
from tests.conftest import authenticated

_RUN_ID = "run-espera"
_APPROVAL_ID = "approval-1"
_DOMAIN = "domain-chimera"


class _CapabilityConEfecto:
    """Doble genérico (ADR-029) con un side_effect que el despliegue puede
    poner en la lista de aprobación — y que SÍ se invoca cuando la aprueban:
    la mitad que el gate síncrono nunca podía alcanzar."""

    def __init__(self) -> None:
        self.invocaciones = 0

    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id="cap.con-efecto",
            description="generic test capability with an external effect",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            side_effects="reversible-external",
            required_permission="capability:invoke",
            interaction="request_response",
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        self.invocaciones += 1
        return {"efecto": "aplicado"}


def _proponer_la_capability(_ctx: TurnContext) -> ProposedStep:
    """Proposer determinista (etiquetado, jamás "el agente"): la misión de
    este test es invocar la capability que exige aprobación."""
    return ProposedStep(capability_id="cap.con-efecto", inputs={})


def _sembrar_run(store: EventStore, *, run_id: str = _RUN_ID) -> None:
    """Un stream vivo con su `approval.requested` ya publicado — el estado
    exacto en el que el loop llama a la espera."""
    store.append(
        stream_id=run_id,
        type="run.created",
        actor_id="user:operador",
        domain_id=_DOMAIN,
        payload={
            "run_id": run_id,
            "actor_id": "user:operador",
            "domain_id": _DOMAIN,
            "max_steps": 4,
            "policy_digest": "pol-1",
        },
    )
    store.append(
        stream_id=run_id,
        type="approval.requested",
        actor_id="service:runtime",
        domain_id=_DOMAIN,
        payload={
            "run_id": run_id,
            "approval_id": _APPROVAL_ID,
            "json_schema": {"type": "object"},
            "prompt": "¿autorizás?",
            "step_id": None,
        },
    )


def _responder(store: EventStore, response: Any, *, run_id: str = _RUN_ID) -> None:
    store.append(
        stream_id=run_id,
        type="approval.responded",
        actor_id="user:operador",
        domain_id=_DOMAIN,
        payload={
            "run_id": run_id,
            "approval_id": _APPROVAL_ID,
            "response": response,
            "authorized_by": "user:operador",
        },
    )


def _esperar(resources: Any, *, timeout_s: float = 0.5) -> Any:
    return _wait_for_approval_response(
        resources,
        run_id=_RUN_ID,
        approval_id=_APPROVAL_ID,
        timeout_s=timeout_s,
        poll_interval_s=0.01,
    )


class TestLaEspera:
    def test_concede_cuando_la_respuesta_dice_que_si(self) -> None:
        store = create_event_store()
        resources = build_run_resources(store)
        _sembrar_run(store)
        _responder(store, {"approved": True})

        outcome = _esperar(resources)

        assert outcome.granted is True

    def test_niega_con_causa_humana_cuando_la_respuesta_dice_que_no(self) -> None:
        """Negar es una decisión REGISTRADA, no un error del sistema — y su
        causa la distingue del vencimiento."""
        store = create_event_store()
        resources = build_run_resources(store)
        _sembrar_run(store)
        _responder(store, {"approved": False})

        outcome = _esperar(resources)

        assert outcome.granted is False
        assert outcome.cause == _APPROVAL_DENIED_CAUSE

    def test_acepta_el_booleano_pelado_que_el_studio_puede_mandar(self) -> None:
        """#184: un `json_schema` booleano produce un `response` que es
        `true` a secas. La espera lee las dos formas — el wire manda, no una
        suposición del lector."""
        store = create_event_store()
        resources = build_run_resources(store)
        _sembrar_run(store)
        _responder(store, True)

        assert _esperar(resources).granted is True

    def test_una_respuesta_de_forma_inesperada_jamas_concede(self) -> None:
        """Fail-closed: lo que no se entiende NO autoriza. Un `response` con
        otra forma es una respuesta que nadie sabe leer, y leerla como "sí"
        sería fabricar la aprobación que este sistema promete no fabricar."""
        store = create_event_store()
        resources = build_run_resources(store)
        _sembrar_run(store)
        _responder(store, {"otra_cosa": 1})

        outcome = _esperar(resources)

        assert outcome.granted is False
        assert outcome.cause == _APPROVAL_DENIED_CAUSE

    def test_vence_fail_closed_si_nadie_responde(self) -> None:
        """Un worker no espera para siempre: el vencimiento es su propio
        hecho (`approval_timeout`), distinguible de un "no" humano."""
        store = create_event_store()
        resources = build_run_resources(store)
        _sembrar_run(store)

        outcome = _esperar(resources, timeout_s=0.05)

        assert outcome.granted is False
        assert outcome.cause == _APPROVAL_TIMEOUT_CAUSE

    def test_se_rinde_si_el_run_muere_mientras_espera(self) -> None:
        """Cancelar en vez de responder es legítimo — y entonces el terminal
        del run YA existe. La espera no puede devolver un veredicto ahí: si
        lo hiciera, el loop journalizaría un SEGUNDO terminal sobre un stream
        ya cerrado. Se rinde con excepción propia, que el arranque de la
        tarea distingue de una falla real."""
        store = create_event_store()
        resources = build_run_resources(store)
        _sembrar_run(store)
        store.append(
            stream_id=_RUN_ID,
            type="run.cancelled",
            actor_id="user:operador",
            domain_id=_DOMAIN,
            payload={"reason": "user_requested"},
        )

        with pytest.raises(RunTerminatedWhileWaitingError):
            _esperar(resources)

    def test_ignora_la_respuesta_de_otro_approval(self) -> None:
        """El par es 1:1 por `approval_id` — una respuesta ajena no autoriza
        nada, ni siquiera dentro del mismo run."""
        store = create_event_store()
        resources = build_run_resources(store)
        _sembrar_run(store)
        store.append(
            stream_id=_RUN_ID,
            type="approval.responded",
            actor_id="user:operador",
            domain_id=_DOMAIN,
            payload={
                "run_id": _RUN_ID,
                "approval_id": "approval-de-otro",
                "response": {"approved": True},
                "authorized_by": "user:operador",
            },
        )

        outcome = _esperar(resources, timeout_s=0.05)

        assert outcome.granted is False
        assert outcome.cause == _APPROVAL_TIMEOUT_CAUSE


class TestGateQueEspera:
    def test_sin_espera_el_gate_sigue_negando_como_en_f1_3(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Regresión: el camino `BackgroundTasks` no cambia — ahí bloquear
        seguiría clavando un hilo del servidor."""
        monkeypatch.setenv(_APPROVAL_SIDE_EFFECTS_ENV, "reversible-external")
        resources = build_run_resources(
            create_event_store(),
            registry=EntryPointRegistry({"cap.con-efecto": _CapabilityConEfecto()}),
        )
        gate = _build_approval_gate(resources)
        assert gate is not None

        decision = gate(
            ApprovalRequest(
                run_id=_RUN_ID, turn=1, capability_id="cap.con-efecto", inputs={}
            )
        )

        assert decision.required is True
        assert decision.granted is False
        assert decision.wait is None

    def test_con_espera_el_gate_declara_como_esperar(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(_APPROVAL_SIDE_EFFECTS_ENV, "reversible-external")
        resources = build_run_resources(
            create_event_store(),
            registry=EntryPointRegistry({"cap.con-efecto": _CapabilityConEfecto()}),
        )
        gate = _build_approval_gate(resources, wait_for_human=True)
        assert gate is not None

        decision = gate(
            ApprovalRequest(
                run_id=_RUN_ID, turn=1, capability_id="cap.con-efecto", inputs={}
            )
        )

        # `granted=False` SIGUE siendo el valor de la decisión: la espera es
        # lo único que puede conceder (fail-closed intacto, `mission.py`).
        assert decision.required is True
        assert decision.granted is False
        assert decision.wait is not None


class TestCicloVivoCompleto:
    """El ítem entero, sin Docker: run vivo → card → 202 → el turno sigue.

    Es el mismo mecanismo que la corrida en compose ejercita; lo que ese test
    vivo agrega es el worker de procrastinate como PROCESO. Acá el run corre
    en un hilo (que es lo que el worker hace con una tarea sync) y el humano
    responde por el endpoint REAL, con su chequeo de permiso incluido."""

    def test_el_humano_aprueba_en_vivo_y_el_turno_sigue(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(_APPROVAL_SIDE_EFFECTS_ENV, "reversible-external")
        monkeypatch.setenv("CHIMERA_OPERATOR_PERMISSIONS", "override:apply:run")

        capability = _CapabilityConEfecto()
        store = create_event_store()
        registry = EntryPointRegistry({"cap.con-efecto": capability})
        resources = build_run_resources(store, registry=registry)
        client = authenticated(TestClient(create_app(store, registry=registry)))
        gate = _build_approval_gate(resources, wait_for_human=True)
        assert gate is not None

        def _correr() -> None:
            execute_run(
                store,
                registry,
                resources.dispatcher,
                resources.content,
                run_id=_RUN_ID,
                actor_id="user:operador",
                domain_id=_DOMAIN,
                max_steps=4,
                policy_digest="pol-1",
                capability_id="cap.con-efecto",
                inputs={},
                max_turns=1,
                proposer=_proponer_la_capability,
                approval_gate=gate,
            )

        hilo = threading.Thread(target=_correr, daemon=True)
        hilo.start()

        # El run se queda VIVO pidiendo permiso — eso es lo nuevo.
        approval_id = _esperar_evento(store, "approval.requested")
        assert not [
            e
            for e in store.read_stream(_RUN_ID)
            if e.type in {"run.completed", "run.failed", "run.cancelled"}
        ], "el run no puede ser terminal mientras espera a un humano"
        assert capability.invocaciones == 0, "no se ejecuta nada antes de aprobar"

        # El humano responde por la MISMA ruta que usa la card del Studio.
        respuesta = cast(
            httpx.Response,
            client.post(
                f"/runs/{_RUN_ID}/approvals/{approval_id}",
                json={"response": {"approved": True}},
            ),
        )
        assert respuesta.status_code == 202, respuesta.text

        hilo.join(timeout=10)
        assert not hilo.is_alive()

        eventos = store.read_stream(_RUN_ID)
        tipos = [e.type for e in eventos]
        # `approval.responded` cae ANTES del terminal ⇒ dentro del corte de
        # procedencia (freeze §2): el certificado ampara el gobierno.
        terminal = next(
            i
            for i, t in enumerate(tipos)
            if t in {"run.completed", "run.failed", "run.cancelled"}
        )
        assert tipos.index("approval.responded") < terminal
        # Y el turno SIGUIÓ: la capability se invocó de verdad.
        assert capability.invocaciones == 1
        assert "capability.job.completed" in tipos


def _esperar_evento(store: EventStore, tipo: str, *, timeout_s: float = 10.0) -> str:
    limite = time.monotonic() + timeout_s
    while time.monotonic() < limite:
        for event in store.read_stream(_RUN_ID):
            if event.type == tipo:
                return str(event.payload["approval_id"])
        time.sleep(0.01)
    raise AssertionError(f"el evento {tipo!r} nunca llegó en {timeout_s}s")


class TestElCaminoDelWorker:
    """`execute_mission_job` es el armado del run EN EL WORKER. Casi todo lo
    que hace ya está cubierto pieza por pieza; lo que NO puede quedar sin
    trinquete es la única línea que distingue este camino del anterior."""

    def test_el_worker_arma_la_compuerta_que_espera(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Si alguien borrara `wait_for_human=True` de `execute_mission_job`,
        P11 se revertiría EN SILENCIO: los runs seguirían corriendo en el
        worker, pero el gate volvería a negar en el mismo turno y la
        aprobación humana viva desaparecería sin que un solo test se pusiera
        rojo (el e2e vivo no corre en CI). Este test es ese trinquete.

        Se ejercita por la señal observable —que la decisión traiga `wait`—
        en vez de leer el código fuente: lo que importa no es que la llamada
        tenga ese literal, sino que el run del worker pueda esperar."""
        monkeypatch.setenv(_APPROVAL_SIDE_EFFECTS_ENV, "reversible-external")
        capability = _CapabilityConEfecto()
        store = create_event_store()
        registry = EntryPointRegistry({"cap.con-efecto": capability})
        resources = build_run_resources(store, registry=registry)

        decisiones: list[Any] = []

        def _espiar_gate(recursos: Any, *, wait_for_human: bool = False) -> Any:
            gate = _build_approval_gate(recursos, wait_for_human=wait_for_human)
            assert gate is not None

            def _envuelto(request: ApprovalRequest) -> Any:
                decision = gate(request)
                decisiones.append(decision)
                return decision

            return _envuelto

        monkeypatch.setattr("chimera_api.runs._worker_resources", lambda: resources)
        monkeypatch.setattr("chimera_api.runs._build_approval_gate", _espiar_gate)
        monkeypatch.setenv("CHIMERA_APPROVAL_WAIT_TIMEOUT_S", "0.05")
        monkeypatch.setenv("CHIMERA_APPROVAL_POLL_INTERVAL_S", "0.01")

        execute_mission_job(
            MissionJob(
                run_id="run-worker-1",
                identity=Identity(
                    id="user:operador",
                    kind="human",
                    domain_id=_DOMAIN,
                    permissions=frozenset({"capability:invoke"}),
                ).model_dump(mode="json"),
                mission="una misión que pide permiso",
                capability_id="cap.con-efecto",
                inputs={},
                max_turns=1,
                max_steps=4,
            )
        )

        # La compuerta que el worker armó SABE esperar…
        assert decisiones and decisiones[0].wait is not None
        # …y como nadie respondió, venció fail-closed en vez de ejecutar.
        eventos = store.read_stream("run-worker-1")
        tipos = [e.type for e in eventos]
        assert "approval.requested" in tipos
        assert capability.invocaciones == 0
        terminal = next(e for e in eventos if e.type == "run.failed")
        assert terminal.payload["error_kind"] == _APPROVAL_TIMEOUT_CAUSE
