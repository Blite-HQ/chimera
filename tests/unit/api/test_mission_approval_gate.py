"""F1.3 — cableado del `ApprovalGate` en el camino de misión (`chimera_api.runs`).

Diagnóstico previo a esta sesión (tres bloqueos independientes, ver el ledger):
(a) nadie construía ni pasaba un `ApprovalGate` a `execute_run` en el camino de
misión — `approval.requested` solo existía en tests de `blite.runtime.loop`,
jamás en un run real disparado por HTTP; (b) el espejo Zod del Studio
descartaba el evento real en silencio (`step_id: null`, cubierto en
`schemas.test.ts`/`RunThread.chat.test.tsx`); (c) responder daba 403 sin el
permiso `override:apply:run` (cubierto en `test_chat.py::TestPostApprovals`).

Este archivo cubre (a): el MECANISMO, no la política — `mission.py:130-138`
("El default del despliegue es SIN gate — cero aprobaciones fingidas") sigue
intacto: sin `CHIMERA_APPROVAL_REQUIRED_SIDE_EFFECTS` configurada,
`_build_approval_gate` devuelve `None` y `execute_run` no cablea nada, byte-
idéntico al comportamiento previo. Configurada, una capability cuyo manifest
declare uno de esos `side_effects` pide aprobación — la política de CUÁLES
side_effects la fija el despliegue (env var), no este código.

El test que cierra el ítem es `TestApprovalMechanismoSinCierreEnVivo` — el
gate NO puede bloquear esperando una respuesta humana (`mission.py:132-141`:
con `BackgroundTasks` un gate bloqueante clava un hilo), así que decide con
lo que tiene: niega (`granted=False`, fail-closed, mismo comportamiento que
`_GateQueAprueba` en `test_agentic_loop.py`) y deja el `approval.requested`
REAL journalizado. El run termina `run.failed` en el mismo turno.

**Revisión de control (declarada, no rodeada):** ese `approval.requested`
real es el mecanismo demostrado — pero responderlo NO da 202. Freeze §2 deja
los eventos post-terminales fuera del `provenance_hash` (solo entran
familias de CIERRE ahí — `run.metrics.recorded`, `●CaseClosed`,
`●CertificateIssued`); una respuesta de aprobación es GOBIERNO, no cierre, y
el run ya falló, así que un 202 ahí mentiría que hubo gobierno cuando no lo
hubo. `POST .../approvals/{id}` sigue con `_require_open_stream` — MISMA
guardia que `messages`/`cancel` — y da 409 (ver
`test_chat.py::test_responder_un_approval_de_un_run_ya_terminal_es_409_fail_closed_a_proposito`).
Un par request→response que cierre EN VIVO (202 legítimo, `approval.
responded` dentro del hash) exige que el gate pueda esperar sin bloquear un
hilo — eso es la cola durable de P11, no este ítem. Sin P11, "aprobación
humana en el lazo" es un mecanismo demostrado, no una política de cierre en
vivo — y esta suite lo prueba honestamente en vez de aflojar el contrato
para que un test pase.
"""

from __future__ import annotations

from typing import Any, cast

import httpx
import pytest
from chimera_api.app import create_app
from chimera_api.runs import (
    _APPROVAL_REQUIRED_CAUSE,  # pyright: ignore[reportPrivateUsage]
    _APPROVAL_SIDE_EFFECTS_ENV,  # pyright: ignore[reportPrivateUsage]
    _approval_required_side_effects,  # pyright: ignore[reportPrivateUsage]
    _build_approval_gate,  # pyright: ignore[reportPrivateUsage]
    build_run_resources,
)
from fastapi.testclient import TestClient

from blite.events import create_event_store
from blite.gateway.approval import ApprovalRequestedPayload
from blite.runtime.mission import ApprovalRequest
from blite.runtime.registry import EntryPointRegistry
from blite_cap_mcp import McpToolInvoker
from blite_capability.manifest import CapabilityManifest
from tests.conftest import authenticated

_CAP_ID = "blite.mcp.invoke_tool"


def _registry() -> EntryPointRegistry:
    """El blanco REAL declarado `irreversible-external` (diagnóstico #1) —
    el gate nunca llega a invocarlo (niega antes de `_run_resolve_and_invoke`),
    así que no hace falta un dispatcher MCP vivo detrás."""
    return EntryPointRegistry({_CAP_ID: McpToolInvoker()})


def _pure_registry() -> EntryPointRegistry:
    class _Pure:
        @property
        def manifest(self) -> CapabilityManifest:
            return CapabilityManifest(
                id="cap.pure",
                description="test capability sin side effects",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                side_effects="pure",
                required_permission="capability:invoke",
                interaction="request_response",
            )

        def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
            return {}

    return EntryPointRegistry({"cap.pure": _Pure()})


def _post(client: TestClient, url: str, body: dict[str, Any]) -> httpx.Response:
    return cast(httpx.Response, client.post(url, json=body))


class TestApprovalRequiredSideEffects:
    def test_env_ausente_da_conjunto_vacio(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(_APPROVAL_SIDE_EFFECTS_ENV, raising=False)
        assert _approval_required_side_effects() == frozenset()

    def test_env_con_espacios_y_comas_se_normaliza(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(
            _APPROVAL_SIDE_EFFECTS_ENV, " irreversible-external ,reversible-external,"
        )
        assert _approval_required_side_effects() == frozenset(
            {"irreversible-external", "reversible-external"}
        )


class TestBuildApprovalGate:
    def test_sin_env_configurada_no_hay_gate(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Doctrina intacta (`mission.py:130`): default del despliegue SIN
        gate — `execute_run` ni se entera de que este puerto existe."""
        monkeypatch.delenv(_APPROVAL_SIDE_EFFECTS_ENV, raising=False)
        resources = build_run_resources(create_event_store(), registry=_registry())
        assert _build_approval_gate(resources) is None

    def test_capability_con_side_effects_fuera_de_la_lista_no_requiere(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(_APPROVAL_SIDE_EFFECTS_ENV, "irreversible-external")
        resources = build_run_resources(create_event_store(), registry=_pure_registry())
        gate = _build_approval_gate(resources)
        assert gate is not None
        decision = gate(
            ApprovalRequest(run_id="run-1", turn=1, capability_id="cap.pure", inputs={})
        )
        assert decision.required is False

    def test_capability_desconocida_no_explota_y_no_requiere(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """El gate corre ANTES del resolve real — una capability que no
        existe en el registry es un problema del paso de invocación, no del
        gate: `KeyError` se degrada a "no requiere", jamás a una excepción
        que tumbe el turno entero."""
        monkeypatch.setenv(_APPROVAL_SIDE_EFFECTS_ENV, "irreversible-external")
        resources = build_run_resources(create_event_store(), registry=_registry())
        gate = _build_approval_gate(resources)
        assert gate is not None
        decision = gate(
            ApprovalRequest(
                run_id="run-1", turn=1, capability_id="cap.fantasma", inputs={}
            )
        )
        assert decision.required is False

    def test_capability_con_side_effects_configurado_requiere_y_niega(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(_APPROVAL_SIDE_EFFECTS_ENV, "irreversible-external")
        resources = build_run_resources(create_event_store(), registry=_registry())
        gate = _build_approval_gate(resources)
        assert gate is not None
        decision = gate(
            ApprovalRequest(
                run_id="run-1",
                turn=1,
                capability_id=_CAP_ID,
                inputs={"server": "x", "tool": "y"},
            )
        )
        # required + NO granted: el gate no puede bloquear esperando a un
        # humano (mission.py:132-141) — decide con lo que tiene, fail-closed.
        assert decision.required is True
        assert decision.granted is False
        assert decision.approval_id != ""
        assert decision.prompt != ""
        # json_schema: booleano-en-objeto, el caso que `booleanDecisionField`
        # (RunThread.tsx) ya sabe renderizar como Aprobar/Rechazar.
        assert decision.json_schema["type"] == "object"
        assert decision.json_schema["required"] == ["approved"]
        assert decision.cause == _APPROVAL_REQUIRED_CAUSE


class TestApprovalMechanismoSinCierreEnVivo:
    """El corazón del ítem: run en modo misión con el gate activo ⇒
    `approval.requested` REAL en el stream — el mecanismo que faltaba
    (diagnóstico (a)). Lo que este item NO entrega (y declara en vez de
    rodear): un cierre EN VIVO del par request→response. Con el gate
    síncrono de hoy, el único `approval.requested` posible nace de un turno
    que ya terminó el run — así que responderlo es, correctamente, un 409
    post-terminal (freeze §2: gobierno post-terminal queda fuera del hash).
    Ese cierre en vivo es P11 (cola durable), no este ítem."""

    def test_gate_activo_emite_approval_requested_real_y_responderlo_es_409_post_terminal(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(_APPROVAL_SIDE_EFFECTS_ENV, "irreversible-external")
        # F1.3 §3: sin este permiso, responder da 403 fail-closed — el
        # despliegue lo declara explícito, jamás el default de código.
        monkeypatch.setenv("CHIMERA_OPERATOR_PERMISSIONS", "override:apply:run")

        store = create_event_store()
        client = authenticated(TestClient(create_app(store, registry=_registry())))

        # Arrange + Act 1 — arranca el run en modo misión contra el blanco
        # REAL irreversible-external.
        respuesta = _post(
            client,
            "/runs",
            {
                "mission": "invocar un tool MCP externo con side effect real",
                "capability_id": _CAP_ID,
                "max_turns": 1,
            },
        )
        assert respuesta.status_code == 202
        run_id = respuesta.json()["run_id"]

        # Assert 1 — `approval.requested` REAL (no un fixture, no un doble):
        # valida contra el modelo Pydantic del wire congelado, y `step_id`
        # es `None` porque lo emite el harness agéntico, no un turno con
        # `RunStep` real (loop.py:861) — jamás "step-1" inventado.
        eventos = store.read_stream(run_id)
        tipos = [e.type for e in eventos]
        assert "approval.requested" in tipos
        solicitud = next(e for e in eventos if e.type == "approval.requested")
        ApprovalRequestedPayload.model_validate(solicitud.payload)
        assert solicitud.payload["step_id"] is None
        approval_id = str(solicitud.payload["approval_id"])

        # Honesto: el gate negó (no puede esperar a un humano) — el run YA
        # es terminal en este punto, con causa humana, no un error del
        # sistema. (`run.metrics.recorded` puede seguir — familia de cierre
        # FUERA del corte de `provenance_slice`, freeze §2.)
        assert "run.failed" in tipos
        terminal = next(e for e in eventos if e.type == "run.failed")
        assert terminal.payload["error_kind"] == _APPROVAL_REQUIRED_CAUSE

        # Act 2 — el humano responde DESPUÉS, contra el run ya terminal
        # (única secuencia posible con un gate síncrono — ver docstring del
        # módulo).
        aprobacion = _post(
            client,
            f"/runs/{run_id}/approvals/{approval_id}",
            {"response": {"approved": True}},
        )

        # Assert 2 — 409 fail-closed A PROPÓSITO (revisión de control): el
        # run ya es terminal, y freeze §2 deja el gobierno post-terminal
        # fuera del `provenance_hash` — un `approval.responded` acá sería
        # una decisión que el certificado no puede demostrar, y aprobar un
        # run ya fallido no cambia nada de todos modos. MISMA guardia que
        # `messages`/`cancel` (`_require_open_stream`), sin excepción.
        assert aprobacion.status_code == 409
        eventos_finales = store.read_stream(run_id)
        assert not [e for e in eventos_finales if e.type == "approval.responded"]

    def test_sin_env_configurada_el_mismo_run_no_emite_ningun_approval(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Byte-idéntico al comportamiento previo a esta sesión cuando el
        despliegue no opta por el gate — mismo capability_id, mismo modo
        misión, cero eventos `approval.*`."""
        monkeypatch.delenv(_APPROVAL_SIDE_EFFECTS_ENV, raising=False)
        store = create_event_store()
        client = authenticated(TestClient(create_app(store, registry=_registry())))

        respuesta = _post(
            client,
            "/runs",
            {
                "mission": "invocar un tool MCP externo sin gate configurado",
                "capability_id": _CAP_ID,
                "max_turns": 1,
            },
        )
        assert respuesta.status_code == 202
        run_id = respuesta.json()["run_id"]

        tipos = [e.type for e in store.read_stream(run_id)]
        assert not [t for t in tipos if t.startswith("approval.")]
