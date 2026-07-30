"""Tests de `chimera_api.model_proposer` — el adapter `Proposer ← ModelServer`
(carril P4, mandato Dylan 2026-07-29). El agente real entra por el MISMO seam
`Proposer` (decisión #92, `loop.py`) — este módulo arma el request del modelo
desde `TurnContext` (determinista: mismos bytes ⇒ mismo `replay_key`), llama
`ModelPort.call`, y parsea la respuesta con un protocolo JSON ESTRICTO
(reusa `ProposedStep` como el wire — `extra="forbid"` ya lo hace estricto).

Frontera declarada (ver `docs/specs/harness-agentico.md` sección aditiva):
`_run_agentic_turn` (`engine/src/blite/runtime/loop.py`, fuera de mi carril)
NO envuelve la llamada al `proposer` en try/except — un `raise` ahí tumba el
turno ANTES de journalizar nada (verificado empíricamente: `execute_run`
propaga la excepción sin emitir `run.failed`). Por eso este adapter JAMÁS deja
escapar una excepción cruda: toda falla del seam modelo (miss de replay,
respuesta no parseable, digest no visible) se traduce a un `ProposedStep` con
una capability CENTINELA que el registry real nunca registrará — el turno
sigue su curso normal por `_run_resolve_and_invoke`, que SÍ está protegido
(KeyError del registry ⇒ `run.step.failed` + `run.failed` fail-loud, MISMO
contrato que una capability desconocida cualquiera, `TestCapabilityDesconocida`
en `test_runs.py`). No es tolerancia: es canalizar el error por el ÚNICO paso
del loop que ya es fail-loud por contrato.
"""

from __future__ import annotations

import pytest
from chimera_api.model_proposer import (
    PROTOCOL_VIOLATION_CAPABILITY_ID,
    ModelResponseProtocolError,
    make_model_proposer,
    parse_proposed_step,
)

from blite.protocols.model_server import InMemoryReplayManifest, ModelServer
from blite.runtime.content_store import InMemoryContentStore
from blite.runtime.loop import ProposedStep, TurnContext
from blite.runtime.registry import EntryPointRegistry
from blite_capability.manifest import CapabilityManifest

_CTX = {"domain_id": "domain-default"}
_BACKEND_ID = "anthropic/claude-sonnet-test"


def _turn(*, turn: int = 1, previous_output_digest: str | None = None) -> TurnContext:
    return TurnContext(
        run_id="run-" + "a" * 32,
        domain_id="domain-default",
        turn=turn,
        goal_capability_id="blite.solvers.qubo",
        goal_inputs={"mission": "particionar la red"},
        plan_item_id="mission-1",
        previous_output_digest=previous_output_digest,
    )


def _registry() -> EntryPointRegistry:
    manifest = CapabilityManifest(
        id="cap.mission-echo",
        description="mission-tolerant test capability",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
    )

    class _FakeCapability:
        @property
        def manifest(self) -> CapabilityManifest:
            return manifest

        def invoke(self, inputs: dict[str, object]) -> dict[str, object]:
            return {}

    return EntryPointRegistry({"cap.mission-echo": _FakeCapability()})


class TestParseProposedStep:
    def test_json_valido_devuelve_proposed_step(self) -> None:
        # Arrange
        payload = (
            b'{"capability_id": "cap.mission-echo", '
            b'"inputs": {"x": 1}, "tokens": 128, "cost_usd": 0.01}'
        )

        # Act
        step = parse_proposed_step(payload)

        # Assert
        assert step == ProposedStep(
            capability_id="cap.mission-echo",
            inputs={"x": 1},
            tokens=128,
            cost_usd=0.01,
        )

    def test_json_sin_campos_opcionales_devuelve_proposed_step_honesto(self) -> None:
        # Arrange — tokens/cost_usd ausentes ⇒ None, no cero fingido (#92).
        payload = b'{"capability_id": "cap.mission-echo", "inputs": {}}'

        # Act
        step = parse_proposed_step(payload)

        # Assert
        assert step.tokens is None
        assert step.cost_usd is None

    def test_json_malformado_levanta_excepcion_clara(self) -> None:
        with pytest.raises(ModelResponseProtocolError):
            parse_proposed_step(b"esto no es json")

    def test_campo_requerido_ausente_levanta_excepcion_clara(self) -> None:
        with pytest.raises(ModelResponseProtocolError):
            parse_proposed_step(b'{"inputs": {}}')

    def test_campo_extra_viola_el_protocolo_estricto(self) -> None:
        # `extra="forbid"` en `ProposedStep` (loop.py) es el protocolo estricto
        # que este parser reusa como wire — no inventa una segunda forma.
        payload = b'{"capability_id": "cap.x", "inputs": {}, "sneaky": true}'
        with pytest.raises(ModelResponseProtocolError):
            parse_proposed_step(payload)


class TestMakeModelProposerReplay:
    def test_replay_hit_devuelve_el_proposed_step_grabado(self) -> None:
        # Arrange — graba una respuesta válida en el manifest/content store,
        # exactamente como haría el backend `record` (round-trip A2).
        store = InMemoryContentStore()
        manifest = InMemoryReplayManifest()
        recorder = ModelServer(
            mode="record",
            content_store=store,
            ctx=_CTX,
            manifest=manifest,
            live_caller=lambda _req: (
                b'{"capability_id": "cap.mission-echo", '
                b'"inputs": {"matrix": [[1]]}, "tokens": 64, "cost_usd": 0.002}'
            ),
        )
        record_proposer = make_model_proposer(
            model_server=recorder,
            registry=_registry(),
            content_store=store,
            ctx=_CTX,
            backend_id=_BACKEND_ID,
        )
        replay_proposer = make_model_proposer(
            model_server=ModelServer(
                mode="replay", content_store=store, ctx=_CTX, manifest=manifest
            ),
            registry=_registry(),
            content_store=store,
            ctx=_CTX,
            backend_id=_BACKEND_ID,
        )
        turn = _turn()
        # El proposer arma el MISMO request que grabamos: debe hacer HIT (el
        # replay_key coincide por construcción — determinismo, no coincidencia).
        recorded_step = record_proposer(turn)

        # Act
        replayed_step = replay_proposer(turn)

        # Assert
        assert replayed_step == recorded_step
        assert replayed_step.capability_id == "cap.mission-echo"
        assert replayed_step.inputs == {"matrix": [[1]]}
        assert replayed_step.tokens == 64
        assert replayed_step.cost_usd == 0.002

    def test_mismo_turn_context_produce_el_mismo_replay_key_dos_veces(self) -> None:
        # Arrange — determinismo: el MISMO TurnContext armado dos veces con
        # el mismo registry/backend_id pega el mismo fixture ambas veces.
        store = InMemoryContentStore()
        manifest = InMemoryReplayManifest()
        recorder = ModelServer(
            mode="record",
            content_store=store,
            ctx=_CTX,
            manifest=manifest,
            live_caller=lambda _req: (
                b'{"capability_id": "cap.mission-echo", "inputs": {}}'
            ),
        )
        record_proposer = make_model_proposer(
            model_server=recorder,
            registry=_registry(),
            content_store=store,
            ctx=_CTX,
            backend_id=_BACKEND_ID,
        )
        replay_proposer = make_model_proposer(
            model_server=ModelServer(
                mode="replay", content_store=store, ctx=_CTX, manifest=manifest
            ),
            registry=_registry(),
            content_store=store,
            ctx=_CTX,
            backend_id=_BACKEND_ID,
        )
        turn = _turn(turn=3, previous_output_digest="d" * 64)
        record_proposer(turn)

        # Act — dos llamadas de replay sobre el MISMO turno
        first = replay_proposer(turn)
        second = replay_proposer(turn)

        # Assert
        assert (
            first == second == ProposedStep(capability_id="cap.mission-echo", inputs={})
        )

    def test_replay_miss_no_levanta_deja_un_proposed_step_centinela(self) -> None:
        # Arrange — manifest vacío: CUALQUIER request es un miss.
        store = InMemoryContentStore()
        proposer = make_model_proposer(
            model_server=ModelServer(
                mode="replay",
                content_store=store,
                ctx=_CTX,
                manifest=InMemoryReplayManifest(),
            ),
            registry=_registry(),
            content_store=store,
            ctx=_CTX,
            backend_id=_BACKEND_ID,
        )

        # Act — NO debe lanzar (ver docstring del módulo: el seam del
        # proposer no está protegido por loop.py).
        step = proposer(_turn())

        # Assert — capability centinela, jamás registrada de verdad.
        assert step.capability_id == PROTOCOL_VIOLATION_CAPABILITY_ID
        assert step.inputs["error_kind"] == "ReplayMissError"

    def test_respuesta_grabada_corrupta_deja_un_proposed_step_centinela(self) -> None:
        # Arrange — el backend `record` graba BYTES que no son el protocolo
        # JSON estricto (p.ej. el modelo devolvió prosa, no un ProposedStep).
        store = InMemoryContentStore()
        manifest = InMemoryReplayManifest()
        recorder = ModelServer(
            mode="record",
            content_store=store,
            ctx=_CTX,
            manifest=manifest,
            live_caller=lambda _req: b"lo siento, no puedo ayudar con eso",
        )
        record_proposer = make_model_proposer(
            model_server=recorder,
            registry=_registry(),
            content_store=store,
            ctx=_CTX,
            backend_id=_BACKEND_ID,
        )
        replay_proposer = make_model_proposer(
            model_server=ModelServer(
                mode="replay", content_store=store, ctx=_CTX, manifest=manifest
            ),
            registry=_registry(),
            content_store=store,
            ctx=_CTX,
            backend_id=_BACKEND_ID,
        )
        turn = _turn()
        record_proposer(turn)

        # Act
        step = replay_proposer(turn)

        # Assert
        assert step.capability_id == PROTOCOL_VIOLATION_CAPABILITY_ID
        assert step.inputs["error_kind"] == "ModelResponseProtocolError"


class TestMakeModelProposerLive:
    def test_backend_live_con_caller_inyectado_parsea_la_respuesta(self) -> None:
        # Arrange — sin red real (freeze §15.7): el caller vivo es un fake
        # local explícito (mismo patrón que test_model_server.py).
        store = InMemoryContentStore()
        proposer = make_model_proposer(
            model_server=ModelServer(
                mode="live",
                content_store=store,
                ctx=_CTX,
                live_caller=lambda _req: (
                    b'{"capability_id": "cap.mission-echo", "inputs": {"n": 2}}'
                ),
            ),
            registry=_registry(),
            content_store=store,
            ctx=_CTX,
            backend_id=_BACKEND_ID,
        )

        # Act
        step = proposer(_turn())

        # Assert
        assert step == ProposedStep(capability_id="cap.mission-echo", inputs={"n": 2})
