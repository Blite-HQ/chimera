"""Loop agéntico plano — A3 (docs/specs/harness-agentico.md).

Contrato bajo prueba: `execute_run` con `proposer` gana un loop de N turnos
(`proponer → gobernar → ejecutar → journalizar → verificar`); el plan viaja
como eventos (`plan.created`/`plan.item_updated`, INV-5 append-only); la
terminación triple corta en la PRIMERA condición que se agote —
`max_turns` | `budget` | el gate de verificación (`post_invoke` truthy).
Sin `proposer` (default), el comportamiento sigue siendo el pipeline fijo
de Fase 1 — ver `tests/unit/runtime/test_run_loop.py` (sin cambios, intacto).
"""

from __future__ import annotations

from typing import Any

from blite.events import create_event_store
from blite.runtime.content_store import InMemoryContentStore
from blite.runtime.dispatch import ProfileDispatcher
from blite.runtime.loop import (
    EXHAUSTED_ERROR_KIND,
    PostInvokeContext,
    ProposedStep,
    RunBudget,
    TurnContext,
    execute_run,
)
from blite.runtime.plan import PlanItem
from blite.runtime.registry import EntryPointRegistry
from blite_capability.capability import Capability
from blite_capability.manifest import CapabilityManifest


class _EchoCapability:
    """Doble genérico (ADR-029) — duplica el valor de entrada, sin efectos."""

    def __init__(self, capability_id: str = "cap.echo") -> None:
        self._id = capability_id
        self.invocations = 0

    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id=self._id,
            description="generic test capability",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            side_effects="pure",
            required_permission="capability:invoke",
            interaction="request_response",
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        self.invocations += 1
        return {"doubled": inputs["x"] * 2}


class _FixedProposer:
    """Fake determinista y explícito (cero mocks silenciosos): propone
    SIEMPRE el mismo par capability_id/inputs, con un costo declarado fijo
    por turno."""

    def __init__(
        self,
        *,
        capability_id: str = "cap.echo",
        tokens: int | None = None,
        cost_usd: float | None = None,
    ) -> None:
        self.capability_id = capability_id
        self.tokens = tokens
        self.cost_usd = cost_usd
        self.calls: list[TurnContext] = []

    def __call__(self, ctx: TurnContext) -> ProposedStep:
        self.calls.append(ctx)
        return ProposedStep(
            capability_id=self.capability_id,
            inputs={"x": ctx.turn},
            tokens=self.tokens,
            cost_usd=self.cost_usd,
        )


class _SequenceProposer:
    """Fake que propone una capability DISTINTA por turno — para probar que
    replanificar apendea steps nuevos, jamás reutiliza los de un turno previo."""

    def __init__(self, capability_ids: list[str]) -> None:
        self._ids = capability_ids

    def __call__(self, ctx: TurnContext) -> ProposedStep:
        capability_id = self._ids[min(ctx.turn - 1, len(self._ids) - 1)]
        return ProposedStep(capability_id=capability_id, inputs={"x": ctx.turn})


class _GateAtTurn:
    """Delegate post-invoke fake: el gate de verificación devuelve `done`
    (True) recién a partir de `turn_done` — antes, `False` (nunca implícito)."""

    def __init__(self, turn_done: int) -> None:
        self.turn_done = turn_done
        self.calls = 0

    def __call__(self, ctx: PostInvokeContext, append: Any) -> bool:
        self.calls += 1
        return self.calls >= self.turn_done


class _NeverDoneGate:
    """El gate que jamás verifica — fuerza el agotamiento de max_turns/budget."""

    def __call__(self, ctx: PostInvokeContext, append: Any) -> bool:
        return False


class _ExplodingCapability:
    """Doble genérico (ADR-029) — siempre explota al invocar (nunca al
    resolver) para ejercitar el camino de excepción del invoke dentro de
    `_run_resolve_and_invoke` en modo agéntico."""

    def __init__(self, capability_id: str = "cap.explode") -> None:
        self._id = capability_id

    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id=self._id,
            description="generic test capability that always fails",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            side_effects="pure",
            required_permission="capability:invoke",
            interaction="request_response",
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        msg = "simulated capability failure"
        raise RuntimeError(msg)


def _registry(*capabilities: Capability) -> EntryPointRegistry:
    return EntryPointRegistry({cap.manifest.id: cap for cap in capabilities})


def _run(
    *,
    proposer: Any,
    post_invoke: Any = None,
    max_turns: int = 30,
    budget: RunBudget | None = None,
    plan_items: tuple[PlanItem, ...] = (),
    registry: EntryPointRegistry | None = None,
    run_id: str = "run-agentic",
) -> tuple[Any, Any]:
    store = create_event_store()
    row = execute_run(
        store,
        registry if registry is not None else _registry(_EchoCapability()),
        ProfileDispatcher(),
        InMemoryContentStore(),
        run_id=run_id,
        actor_id="user:steven",
        domain_id="domain-a",
        max_steps=64,
        policy_digest="pol-digest-1",
        capability_id="cap.echo",
        inputs={"x": 1},
        post_invoke=post_invoke,
        max_turns=max_turns,
        budget=budget,
        proposer=proposer,
        plan_items=plan_items,
    )
    return row, store


def test_max_turns_exhausted_terminates_with_exhausted_error_kind() -> None:
    proposer = _FixedProposer()
    row, store = _run(proposer=proposer, post_invoke=_NeverDoneGate(), max_turns=2)

    assert row.status == "failed"
    assert row.error_kind == EXHAUSTED_ERROR_KIND
    events = store.read_stream("run-agentic")
    assert events[-1].type == "run.failed"
    assert events[-1].payload["error_kind"] == EXHAUSTED_ERROR_KIND
    assert len(proposer.calls) == 2
    # exactamente 2 turnos * 2 steps (resolve+invoke) — el guard cortó ANTES
    # de un 3er turno, jamás un cuelgue silencioso.
    started = [e for e in events if e.type == "run.step.started"]
    assert [e.payload["step_id"] for e in started] == [
        "step-1",
        "step-2",
        "step-3",
        "step-4",
    ]


def test_budget_exhausted_terminates_before_running_the_over_budget_turn() -> None:
    proposer = _FixedProposer(tokens=100)
    row, store = _run(
        proposer=proposer,
        post_invoke=_NeverDoneGate(),
        max_turns=10,
        budget=RunBudget(tokens=150),
    )

    assert row.status == "failed"
    assert row.error_kind == EXHAUSTED_ERROR_KIND
    events = store.read_stream("run-agentic")
    # Turno 1 (100 <= 150) corrió completo; turno 2 hubiera gastado 200 > 150
    # — el harness NUNCA lo ejecuta (gobernar antes de ejecutar).
    assert len(proposer.calls) == 2
    completed_jobs = [e for e in events if e.type == "capability.job.completed"]
    assert len(completed_jobs) == 1
    assert events[-1].type == "run.failed"


def test_verification_gate_terminates_the_loop_before_max_turns() -> None:
    row, store = _run(
        proposer=_FixedProposer(), post_invoke=_GateAtTurn(turn_done=2), max_turns=30
    )

    assert row.status == "completed"
    events = store.read_stream("run-agentic")
    assert events[-1].type == "run.completed"
    # Se detuvo en el turno 2 — jamás llegó a 30 (done ⟺ el verifier pasa).
    completed_jobs = [e for e in events if e.type == "capability.job.completed"]
    assert len(completed_jobs) == 2


def test_plan_created_and_item_updated_emitted_in_correct_order() -> None:
    item = PlanItem(
        id="item-1",
        description="turno único",
        verification="delegate",
        status="pending",
    )
    row, store = _run(
        proposer=_FixedProposer(),
        post_invoke=_GateAtTurn(turn_done=1),
        plan_items=(item,),
    )

    assert row.status == "completed"
    types = [e.type for e in store.read_stream("run-agentic")]
    assert types == [
        "run.created",
        "run.started",
        "plan.created",
        "plan.item_updated",
        "run.step.started",
        "run.step.completed",
        "run.step.started",
        "capability.job.submitted",
        "capability.job.completed",
        "run.step.completed",
        "plan.item_updated",
        "run.completed",
    ]

    plan_created = next(
        e for e in store.read_stream("run-agentic") if e.type == "plan.created"
    )
    assert plan_created.payload["run_id"] == "run-agentic"
    assert plan_created.payload["items"][0]["status"] == "pending"

    item_updates = [
        e for e in store.read_stream("run-agentic") if e.type == "plan.item_updated"
    ]
    assert [u.payload["status"] for u in item_updates] == ["running", "ok"]
    assert all(u.payload["item_id"] == "item-1" for u in item_updates)


def test_capability_failure_in_agentic_mode_emits_plan_item_updated_before_run_failed() -> (
    None
):
    """Bug confirmado en vivo (flag decisión #91, análisis #95-#98): el orden
    viejo apendeaba `plan.item_updated {failed}` DESPUÉS de `run.failed` —
    post-terminal, fuera del corte de `provenance_slice` (freeze §2). El
    orden corregido journaliza el plan ANTES del terminal; el terminal es
    SIEMPRE el último evento del stream, cero `run.failed` dobles."""
    item = PlanItem(
        id="item-1",
        description="turno que falla",
        verification="delegate",
        status="pending",
    )
    row, store = _run(
        proposer=_FixedProposer(capability_id="cap.explode"),
        post_invoke=_NeverDoneGate(),
        plan_items=(item,),
        registry=_registry(_ExplodingCapability()),
    )

    assert row.status == "failed"
    assert row.error_kind == "RuntimeError"
    events = store.read_stream("run-agentic")
    types = [e.type for e in events]
    assert types == [
        "run.created",
        "run.started",
        "plan.created",
        "plan.item_updated",
        "run.step.started",
        "run.step.completed",
        "run.step.started",
        "capability.job.submitted",
        "capability.job.failed",
        "run.step.failed",
        "plan.item_updated",
        "run.failed",
    ]
    # El terminal SIEMPRE de último — jamás post-terminal (freeze §2).
    assert types[-1] == "run.failed"
    assert types[-2] == "plan.item_updated"

    failed_update = events[-2]
    assert failed_update.payload["item_id"] == "item-1"
    assert failed_update.payload["status"] == "failed"
    assert failed_update.payload["cause"] == "RuntimeError"


def test_replan_appends_new_steps_never_reuses_a_step_in_progress() -> None:
    registry = _registry(_EchoCapability("cap.echo"), _EchoCapability("cap.double"))
    row, store = _run(
        proposer=_SequenceProposer(["cap.echo", "cap.double"]),
        post_invoke=_GateAtTurn(turn_done=2),
        max_turns=5,
        registry=registry,
    )

    assert row.status == "completed"
    events = store.read_stream("run-agentic")
    submitted = [e for e in events if e.type == "capability.job.submitted"]
    assert [s.payload["capability_id"] for s in submitted] == ["cap.echo", "cap.double"]
    # job_id (derivado del step_id) NUNCA se repite entre turnos — cada
    # replan es un turno nuevo con eventos apendeados, no una reescritura.
    assert len({s.payload["job_id"] for s in submitted}) == 2
    started = [e for e in events if e.type == "run.step.started"]
    assert [e.payload["step_id"] for e in started] == [
        "step-1",
        "step-2",
        "step-3",
        "step-4",
    ]


def test_run_created_carries_max_turns_and_budget_fields() -> None:
    _, store = _run(
        proposer=_FixedProposer(),
        post_invoke=_GateAtTurn(turn_done=1),
        max_turns=7,
        budget=RunBudget(tokens=500, cost_usd=1.5),
    )

    created = store.read_stream("run-agentic")[0]
    assert created.payload["max_turns"] == 7
    assert created.payload["budget"] == {"tokens": 500, "cost_usd": 1.5}


def test_default_execute_run_without_proposer_ignores_max_turns_and_budget() -> None:
    """Compatibilidad (§Contrato-3, "el comportamiento por defecto ... debe
    seguir produciendo el mismo run terminal que hoy"): sin `proposer`, los
    parámetros `max_turns`/`budget` NO alteran el pipeline fijo de un turno,
    aunque se les pase un valor imposible de cumplir en modo agéntico."""
    store = create_event_store()
    row = execute_run(
        store,
        _registry(_EchoCapability()),
        ProfileDispatcher(),
        InMemoryContentStore(),
        run_id="run-legacy",
        actor_id="user:steven",
        domain_id="domain-a",
        max_steps=8,
        policy_digest="pol-digest-1",
        capability_id="cap.echo",
        inputs={"x": 21},
        max_turns=1,
        budget=RunBudget(tokens=0),
    )

    assert row.status == "completed"
    types = [e.type for e in store.read_stream("run-legacy")]
    assert types == [
        "run.created",
        "run.started",
        "run.step.started",
        "run.step.completed",
        "run.step.started",
        "capability.job.submitted",
        "capability.job.completed",
        "run.step.completed",
        "run.completed",
    ]
