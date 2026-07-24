"""
Loop del runtime — pipeline fijo de Fase 1 + loop agéntico plano (A3).
[S-G · Steven, evolución Sonnet/A3]

nota execution/02 §11 (recomendación de POC, ratificada en freeze §13 "el
runtime es dueño del loop"): NO ReAct, NO plan-execute, NO jerárquico — una
secuencia fija de pasos discretos y nombrados ("resolver qué capability
invocar" → "invocarla"), cada uno serializable como payload de evento. El
loop SOLO secuencia pasos y registra eventos: no verifica (INV-2), no decide
egreso — cualquier "¿este resultado es válido?" se delega.

freeze §3: `run.created {run_id, actor_id, domain_id, max_steps,
policy_digest, parent_run_id?}` carga TODO lo que la proyección necesita;
step↔job 1:1; `capability.job.submitted` se emite ANTES de ejecutar (PR1);
`max_steps` es contrato, no cortesía — el guard corta el loop con
`run.failed`, jamás un cuelgue. Despacho EXCLUSIVAMENTE vía Registry +
Dispatcher (ADR-008 — mitiga el "unlogged tool call", nota 02 §6).

docs/specs/harness-agentico.md (decisión #66, PENDIENTE-Steven — esta
implementación es el material que ratifica o rechaza, no se auto-ratifica):
`execute_run` gana un loop agéntico OPCIONAL, activado por un `proposer`
inyectable. Sin `proposer` (default), el comportamiento es BYTE-IDÉNTICO al
pipeline fijo original (un turno resolve→invoke) — la superficie que ya
consume la API y los tests existentes no cambia. Con `proposer`, el loop
repite `proponer → gobernar → ejecutar → journalizar → verificar` por turno:
el MODELO (vía el proposer, que envuelve `ModelPort.call`) SOLO propone el
próximo `RunStep` candidato — el harness sigue siendo el ÚNICO ejecutor
(INV-2 intacto). Replanificar = un turno nuevo, con sus propios `run.step.*`
apendeados — jamás una segunda pasada de un step en curso.

Terminación triple (§Contrato-3): la primera condición en dispararse corta
el run — (a) `max_turns` (cota de iteraciones del loop agéntico); (b)
`budget` (tokens/costo acumulado, declarado por el propio proposer en cada
turno); (c) el gate de verificación (`post_invoke` devuelve un valor
truthy ⟺ el verifier pasa ⟺ `done`). Agotar (a) o (b) ⇒ terminal
`run.failed {error_kind: EXHAUSTED_ERROR_KIND}` — jamás un `run.completed`
implícito. `max_steps` (guard estructural sobre cada `RunStep`) sigue
vigente sin cambios: por construcción `max_turns <= max_steps` es
responsabilidad del caller, pero AMBOS guards conviven — el que se agote
primero corta.

Decisiones de carril avisadas (no congeladas): `error_kind` del guard =
"MaxStepsExceeded" (misma convención type-name que el registry); eventos
emitidos por el runtime (started/step/job/terminal) llevan
`actor_id: service:runtime` (§13 cascada) — `run.created` estampa el actor
del caller (AX1). El perfil de despacho es el default "in-process"
(trust/06 §4) hasta que el manifest exponga `execution_profile` (carril de
Dylan). El cruce por el gateway completo por step (§13) se cablea cuando el
ctx del pipeline se congele con Dylan.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from blite.content import ContentStore
from blite.events.rules import validate_run_id
from blite.events.store import EventStore
from blite.runtime.dispatch import Dispatcher
from blite.runtime.plan import (
    PlanCreatedPayload,
    PlanItem,
    PlanItemStatus,
    PlanItemUpdatedPayload,
)
from blite.runtime.projection import RunRow, project_runs
from blite.runtime.registry import Registry

MAX_STEPS_EXCEEDED = "MaxStepsExceeded"
EXHAUSTED_ERROR_KIND = "exhausted"
"""Agotar `max_turns` o `budget` en el loop agéntico (§Contrato-3) — convive
con `MAX_STEPS_EXCEEDED`: dos guards distintos, dos `error_kind` distintos,
mismo campo `str` libre (freeze §3)."""

_DEFAULT_MAX_TURNS = 30

_RUNTIME_ACTOR = "service:runtime"
_JSON_MEDIA_TYPE = "application/json"
_DEFAULT_PROFILE = "in-process"

StepStatus = Literal["pending", "running", "completed", "failed"]


AppendEvent = Callable[[str, dict[str, Any]], None]
"""Firma con la que un delegate agrega eventos al rastro (type, payload)."""


class PostInvokeContext(BaseModel):
    """Lo que el loop le entrega al delegate post-invoke — datos, no poderes.

    Decisión de carril (avisada, no congelada): el loop NO verifica (INV-2) —
    ofrece esta costura ANTES del terminal para que un delegado (p.ej. el
    orquestador de `blite.verification`) emita sus eventos DENTRO del corte
    de procedencia. Si el delegate levanta, el run falla fail-loud con el
    tipo de la excepción como `error_kind` (misma convención del registry).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    domain_id: str
    step_id: str
    output_digest: str


PostInvokeDelegate = Callable[[PostInvokeContext, AppendEvent], "bool | None"]
"""El delegate post-invoke puede devolver `None` (modo pipeline fijo — el
valor se ignora, el run siempre completa tras el único turno, igual que
antes de A3) o `bool` (modo agéntico — el gate de verificación: un valor
truthy es `done`, freeze §Contrato-3 de docs/specs/harness-agentico.md)."""


class RunStep(BaseModel):
    """Unidad mínima del loop (nota 02 §1.3) — viaja COMO payload de eventos
    `run.step.*`, jamás en un almacén propio. `status` es conjunto cerrado."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    step_id: str
    run_id: str
    kind: str
    input_digest: str
    output_digest: str | None = None
    status: StepStatus


class RunBudget(BaseModel):
    """Presupuesto tokens/costo del run — freeze §3 aditivo en `run.created`
    (decisión #66, PENDIENTE-Steven). Ambos ejes opcionales e independientes:
    `None` en un eje ⇒ ese eje no tiene tope (freeze §Contrato-3)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tokens: int | None = None
    cost_usd: float | None = None


class ProposedStep(BaseModel):
    """Lo que el `Proposer` devuelve: un candidato de turno — el MODELO
    propone `capability_id`/`inputs`, JAMÁS los ejecuta (INV-2 intacto); el
    harness es el único que corre el par resolve→invoke sobre esta propuesta.

    `tokens`/`cost_usd` son el auto-reporte de gasto de ESTE turno — el
    harness los acumula contra `RunBudget` ANTES de ejecutar el turno
    (gobernar antes de ejecutar, fail-closed como el guard de `max_steps`)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    capability_id: str
    inputs: dict[str, Any]
    tokens: int | None = None
    cost_usd: float | None = None


class TurnContext(BaseModel):
    """Lo que el harness le entrega al `Proposer` en cada turno — datos, no
    poderes (mismo patrón que `PostInvokeContext`). `goal_capability_id`/
    `goal_inputs` son el encargo original de `execute_run`; el proposer es
    libre de proponer algo distinto en cada turno (sub-runs elegidos por el
    agente, §Contrato-4 — fuera de alcance de A3, el campo queda disponible
    para cuando A4 lo consuma)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    domain_id: str
    turn: int
    goal_capability_id: str
    goal_inputs: dict[str, Any]
    plan_item_id: str | None = None
    previous_output_digest: str | None = None


Proposer = Callable[[TurnContext], ProposedStep]
"""El puerto inyectable que envuelve `ModelPort.call` (freeze §15.7) — en
tests, un fake determinista local; jamás litellm/red importado aquí
(AX3-b: `blite.runtime` no puede importar SDKs de modelo)."""


class _TurnOutcome(BaseModel):
    """Resultado interno de un par resolve→invoke — `error_kind` no-`None`
    ⇒ el run YA quedó terminal (el helper ya llamó `fail_run`), el caller
    solo debe cortar y retornar la fila proyectada."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    output_digest: str | None
    error_kind: str | None
    step_id: str | None


def _canonical_json(obj: object) -> bytes:
    """Forma canónica mínima de Fase 1 (claves ordenadas, sin espacios) — la
    canonicalización RFC 8785 completa llega con la vista canónica del anexo."""
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


class _RunRecorder:
    """Escritura del rastro de un run — cada helper es un evento del freeze §3."""

    def __init__(
        self, store: EventStore, content: ContentStore, *, run_id: str, domain_id: str
    ) -> None:
        self._store = store
        self._content = content
        self._run_id = run_id
        self._domain_id = domain_id
        self._ctx = {"domain_id": domain_id}

    def digest_of(self, obj: object) -> str:
        artifact = self._content.put(_canonical_json(obj), _JSON_MEDIA_TYPE, self._ctx)
        return artifact.digest

    def append(
        self, type_: str, payload: dict[str, Any], *, actor_id: str = _RUNTIME_ACTOR
    ) -> None:
        self._store.append(
            stream_id=self._run_id,
            type=type_,
            actor_id=actor_id,
            domain_id=self._domain_id,
            payload=payload,
        )

    def step_event(self, suffix: str, step: RunStep) -> None:
        self.append(f"run.step.{suffix}", step.model_dump())

    def fail_run(self, error_kind: str) -> None:
        self.append("run.failed", {"error_kind": error_kind})


def _run_resolve_and_invoke(
    recorder: _RunRecorder,
    start_step: Callable[[str, str], RunStep | None],
    registry: Registry,
    dispatcher: Dispatcher,
    *,
    capability_id: str,
    inputs: dict[str, Any],
) -> _TurnOutcome:
    """Corre el par resolve→invoke de UN turno (nota 02 §11) — compartido por
    el pipeline fijo (un solo turno) y el loop agéntico (N turnos, cada uno
    con SUS propios `run.step.*` apendeados, jamás reutilizando step_ids).

    `error_kind` no-`None` en el resultado ⇒ el run YA quedó terminal
    (`fail_run` ya corrió dentro de este helper o de `start_step`) — el
    caller solo debe cortar."""
    # ── step "resolve": elegir la capability vía Registry (ADR-008) ──
    resolve_step = start_step(
        "resolve", recorder.digest_of({"capability_id": capability_id})
    )
    if resolve_step is None:
        return _TurnOutcome(
            output_digest=None, error_kind=MAX_STEPS_EXCEEDED, step_id=None
        )
    try:
        capability = registry.get(capability_id)
    except KeyError as exc:
        recorder.step_event(
            "failed", resolve_step.model_copy(update={"status": "failed"})
        )
        recorder.fail_run(type(exc).__name__)
        return _TurnOutcome(
            output_digest=None,
            error_kind=type(exc).__name__,
            step_id=resolve_step.step_id,
        )
    resolve_output = recorder.digest_of(
        {"capability_id": capability_id, "version": capability.manifest.version}
    )
    recorder.step_event(
        "completed",
        resolve_step.model_copy(
            update={"status": "completed", "output_digest": resolve_output}
        ),
    )

    # ── step "invoke": 1:1 con su capability.job (freeze §3) ──
    input_digest = recorder.digest_of(inputs)
    invoke_step = start_step("invoke", input_digest)
    if invoke_step is None:
        return _TurnOutcome(
            output_digest=None, error_kind=MAX_STEPS_EXCEEDED, step_id=None
        )
    job_id = f"{invoke_step.step_id}:job"
    # PR1 (provenance:pre): el submitted existe ANTES de ejecutar — el rastro
    # sobrevive aunque la ejecución explote.
    recorder.append(
        "capability.job.submitted",
        {
            "job_id": job_id,
            "step_id": invoke_step.step_id,
            "capability_id": capability_id,
            "input_digest": input_digest,
        },
    )
    try:
        strategy = dispatcher.resolve(_DEFAULT_PROFILE)
        outputs = strategy.execute(capability, inputs)
    except Exception as exc:  # noqa: BLE001 — frontera de capability: el fallo se registra como eventos, jamás tumba el runtime
        error_kind = type(exc).__name__
        recorder.append(
            "capability.job.failed",
            {
                "job_id": job_id,
                "step_id": invoke_step.step_id,
                "error_kind": error_kind,
            },
        )
        recorder.step_event(
            "failed", invoke_step.model_copy(update={"status": "failed"})
        )
        recorder.fail_run(error_kind)
        return _TurnOutcome(
            output_digest=None, error_kind=error_kind, step_id=invoke_step.step_id
        )
    output_digest = recorder.digest_of(outputs)
    recorder.append(
        "capability.job.completed",
        {
            "job_id": job_id,
            "step_id": invoke_step.step_id,
            "output_digest": output_digest,
        },
    )
    recorder.step_event(
        "completed",
        invoke_step.model_copy(
            update={"status": "completed", "output_digest": output_digest}
        ),
    )
    return _TurnOutcome(
        output_digest=output_digest, error_kind=None, step_id=invoke_step.step_id
    )


def _budget_after(
    budget: RunBudget | None,
    *,
    spent_tokens: int,
    spent_cost_usd: float,
    proposal: ProposedStep,
) -> tuple[int, float, bool]:
    """Gobernar el gasto ANTES de ejecutar (mismo espíritu fail-closed que el
    guard de `max_steps`): acumula lo que el proposer auto-reportó y dice si
    el turno agotaría `budget` — en cuyo caso el turno NUNCA se ejecuta."""
    would_spend_tokens = spent_tokens + (proposal.tokens or 0)
    would_spend_cost = spent_cost_usd + (proposal.cost_usd or 0.0)
    if budget is None:
        return would_spend_tokens, would_spend_cost, False
    exhausted = (budget.tokens is not None and would_spend_tokens > budget.tokens) or (
        budget.cost_usd is not None and would_spend_cost > budget.cost_usd
    )
    return would_spend_tokens, would_spend_cost, exhausted


def execute_run(
    store: EventStore,
    registry: Registry,
    dispatcher: Dispatcher,
    content: ContentStore,
    *,
    run_id: str,
    actor_id: str,
    domain_id: str,
    max_steps: int,
    policy_digest: str,
    capability_id: str,
    inputs: dict[str, Any],
    parent_run_id: str | None = None,
    post_invoke: PostInvokeDelegate | None = None,
    max_turns: int = _DEFAULT_MAX_TURNS,
    budget: RunBudget | None = None,
    proposer: Proposer | None = None,
    plan_id: str | None = None,
    plan_items: tuple[PlanItem, ...] = (),
) -> RunRow:
    """Ejecuta el run y retorna la fila proyectada.

    Sin `proposer` (default): el pipeline fijo de Fase 1 — un turno
    resolve→invoke, byte-idéntico al comportamiento previo a A3 (la
    superficie que ya consume la API y los tests existentes no cambia).

    Con `proposer`: el loop agéntico plano de A3 (docs/specs/harness-
    agentico.md §Contrato-1/3) — N turnos hasta que el gate de verificación
    (`post_invoke` devuelve truthy) dé `done`, o hasta agotar `max_turns`/
    `budget` (terminal `run.failed {error_kind: EXHAUSTED_ERROR_KIND}`).

    La fila retornada se REGENERA por replay del log (`project_runs`) — la
    doctrina "los eventos son la única fuente de verdad" es ejecutable, no
    prosa (freeze §3 [stress-final]).
    """
    validate_run_id(run_id)

    created_payload: dict[str, Any] = {
        "run_id": run_id,
        "actor_id": actor_id,
        "domain_id": domain_id,
        "max_steps": max_steps,
        "policy_digest": policy_digest,
        "max_turns": max_turns,
        "budget": budget.model_dump() if budget is not None else None,
    }
    if parent_run_id is not None:
        created_payload["parent_run_id"] = parent_run_id

    recorder = _RunRecorder(store, content, run_id=run_id, domain_id=domain_id)
    recorder.append("run.created", created_payload, actor_id=actor_id)
    recorder.append("run.started", {})

    steps_started = 0

    def _start_step(kind: str, input_digest: str) -> RunStep | None:
        """Abre el step o corta el loop — el guard de max_steps corre ANTES
        de cada step (nota 02 §6: el límite es contrato, no cortesía)."""
        nonlocal steps_started
        if steps_started >= max_steps:
            recorder.fail_run(MAX_STEPS_EXCEEDED)
            return None
        steps_started += 1
        step = RunStep(
            step_id=f"step-{steps_started}",
            run_id=run_id,
            kind=kind,
            input_digest=input_digest,
            status="running",
        )
        recorder.step_event("started", step)
        return step

    def _projected_row() -> RunRow:
        return project_runs(store.read_all())[run_id]

    if proposer is None:
        return _execute_single_turn(
            recorder,
            _start_step,
            _projected_row,
            registry,
            dispatcher,
            run_id=run_id,
            domain_id=domain_id,
            capability_id=capability_id,
            inputs=inputs,
            post_invoke=post_invoke,
        )

    return _execute_agentic_loop(
        recorder,
        _start_step,
        _projected_row,
        registry,
        dispatcher,
        run_id=run_id,
        domain_id=domain_id,
        capability_id=capability_id,
        inputs=inputs,
        post_invoke=post_invoke,
        max_turns=max_turns,
        budget=budget,
        proposer=proposer,
        plan_id=plan_id if plan_id is not None else f"plan-{run_id}",
        plan_items=plan_items,
    )


def _execute_single_turn(
    recorder: _RunRecorder,
    start_step: Callable[[str, str], RunStep | None],
    projected_row: Callable[[], RunRow],
    registry: Registry,
    dispatcher: Dispatcher,
    *,
    run_id: str,
    domain_id: str,
    capability_id: str,
    inputs: dict[str, Any],
    post_invoke: PostInvokeDelegate | None,
) -> RunRow:
    """El pipeline fijo de Fase 1 — comportamiento PREVIO a A3, sin cambios:
    el retorno de `post_invoke` se ignora (el run completa tras el único
    turno pase lo que pase adentro — un veredicto "fail" del verificador es
    un hecho registrado, no una falla del run)."""
    outcome = _run_resolve_and_invoke(
        recorder,
        start_step,
        registry,
        dispatcher,
        capability_id=capability_id,
        inputs=inputs,
    )
    if outcome.error_kind is not None:
        return projected_row()

    # Costura post-invoke, ANTES del terminal: lo que el delegate emita entra
    # al corte de procedencia. El loop sigue sin verificar (INV-2) — delega.
    if post_invoke is not None:
        try:
            post_invoke(
                PostInvokeContext(
                    run_id=run_id,
                    domain_id=domain_id,
                    step_id=outcome.step_id or "",
                    output_digest=outcome.output_digest or "",
                ),
                recorder.append,
            )
        except Exception as exc:  # noqa: BLE001 — frontera delegada: el fallo se registra como eventos, jamás tumba el runtime
            recorder.fail_run(type(exc).__name__)
            return projected_row()

    recorder.append("run.completed", {"output_digest": outcome.output_digest})
    return projected_row()


def _emit_plan_item_update(
    recorder: _RunRecorder,
    plan_item: PlanItem | None,
    *,
    plan_id: str,
    run_id: str,
    status: PlanItemStatus,
    cause: str | None = None,
) -> None:
    """Una transición de ítem del plan — append-only (INV-5), jamás una
    reescritura. Sin ítem para este turno (plan agotado), no-op explícito."""
    if plan_item is None:
        return
    recorder.append(
        "plan.item_updated",
        PlanItemUpdatedPayload(
            plan_id=plan_id,
            run_id=run_id,
            item_id=plan_item.id,
            status=status,
            cause=cause,
        ).model_dump(),
    )


class _TurnResult(BaseModel):
    """Lo que decide UN turno agéntico completo — le dice al driver del loop
    qué hacer después: `terminal` ya journalizó su propio `run.failed` (solo
    cortar), `done` pide emitir `run.completed`, ninguno de los dos pide
    seguir al próximo turno."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    terminal: bool
    done: bool
    spent_tokens: int
    spent_cost_usd: float
    output_digest: str | None


def _run_agentic_turn(  # noqa: PLR0913 — un turno completo (proponer→gobernar→ejecutar→journalizar→verificar) necesita los 5 componentes como parámetros
    recorder: _RunRecorder,
    start_step: Callable[[str, str], RunStep | None],
    registry: Registry,
    dispatcher: Dispatcher,
    proposer: Proposer,
    post_invoke: PostInvokeDelegate | None,
    *,
    run_id: str,
    domain_id: str,
    turn: int,
    plan_id: str,
    plan_item: PlanItem | None,
    spent_tokens: int,
    spent_cost_usd: float,
    budget: RunBudget | None,
    goal_capability_id: str,
    goal_inputs: dict[str, Any],
    previous_output_digest: str | None,
) -> _TurnResult:
    """UN turno del loop agéntico plano (§Contrato-1): `proponer → gobernar →
    ejecutar → journalizar → verificar`. El MODELO (vía `proposer`) SOLO
    propone; este helper es el único que ejecuta y journaliza (INV-2)."""
    # ── proponer: el MODELO (vía el proposer) propone el candidato ──
    proposal = proposer(
        TurnContext(
            run_id=run_id,
            domain_id=domain_id,
            turn=turn,
            goal_capability_id=goal_capability_id,
            goal_inputs=goal_inputs,
            plan_item_id=plan_item.id if plan_item is not None else None,
            previous_output_digest=previous_output_digest,
        )
    )

    # ── gobernar: el budget se chequea ANTES de ejecutar (fail-closed, mismo
    # espíritu que el guard de max_steps) ──
    spent_tokens, spent_cost_usd, budget_exhausted = _budget_after(
        budget,
        spent_tokens=spent_tokens,
        spent_cost_usd=spent_cost_usd,
        proposal=proposal,
    )
    if budget_exhausted:
        _emit_plan_item_update(
            recorder,
            plan_item,
            plan_id=plan_id,
            run_id=run_id,
            status="failed",
            cause=EXHAUSTED_ERROR_KIND,
        )
        recorder.fail_run(EXHAUSTED_ERROR_KIND)
        return _TurnResult(
            terminal=True,
            done=False,
            spent_tokens=spent_tokens,
            spent_cost_usd=spent_cost_usd,
            output_digest=previous_output_digest,
        )

    _emit_plan_item_update(
        recorder, plan_item, plan_id=plan_id, run_id=run_id, status="running"
    )

    # ── ejecutar + journalizar: el harness es el ÚNICO ejecutor (INV-2) ──
    outcome = _run_resolve_and_invoke(
        recorder,
        start_step,
        registry,
        dispatcher,
        capability_id=proposal.capability_id,
        inputs=proposal.inputs,
    )
    if outcome.error_kind is not None:
        _emit_plan_item_update(
            recorder,
            plan_item,
            plan_id=plan_id,
            run_id=run_id,
            status="failed",
            cause=outcome.error_kind,
        )
        return _TurnResult(
            terminal=True,
            done=False,
            spent_tokens=spent_tokens,
            spent_cost_usd=spent_cost_usd,
            output_digest=previous_output_digest,
        )

    _emit_plan_item_update(
        recorder, plan_item, plan_id=plan_id, run_id=run_id, status="ok"
    )

    # ── verificar: done ⟺ el verifier pasa (post_invoke devuelve truthy) ──
    done = False
    if post_invoke is not None:
        try:
            gate_result = post_invoke(
                PostInvokeContext(
                    run_id=run_id,
                    domain_id=domain_id,
                    step_id=outcome.step_id or "",
                    output_digest=outcome.output_digest or "",
                ),
                recorder.append,
            )
        except Exception as exc:  # noqa: BLE001 — frontera delegada: el fallo se registra como eventos, jamás tumba el runtime
            recorder.fail_run(type(exc).__name__)
            return _TurnResult(
                terminal=True,
                done=False,
                spent_tokens=spent_tokens,
                spent_cost_usd=spent_cost_usd,
                output_digest=outcome.output_digest,
            )
        done = bool(gate_result)

    return _TurnResult(
        terminal=False,
        done=done,
        spent_tokens=spent_tokens,
        spent_cost_usd=spent_cost_usd,
        output_digest=outcome.output_digest,
    )


def _execute_agentic_loop(  # noqa: PLR0913 — misma superficie que _execute_single_turn + los 6 parámetros propios del loop agéntico
    recorder: _RunRecorder,
    start_step: Callable[[str, str], RunStep | None],
    projected_row: Callable[[], RunRow],
    registry: Registry,
    dispatcher: Dispatcher,
    *,
    run_id: str,
    domain_id: str,
    capability_id: str,
    inputs: dict[str, Any],
    post_invoke: PostInvokeDelegate | None,
    max_turns: int,
    budget: RunBudget | None,
    proposer: Proposer,
    plan_id: str,
    plan_items: tuple[PlanItem, ...],
) -> RunRow:
    """El driver del loop agéntico plano de A3 — repite `_run_agentic_turn`
    hasta la terminación triple (docs/specs/harness-agentico.md
    §Contrato-1/2/3): el gate de verificación dice `done`, o `max_turns`/
    `budget` se agotan primero (`run.failed {error_kind: EXHAUSTED_ERROR_KIND}`,
    jamás un `run.completed` implícito).

    Replanificar = un turno NUEVO con sus propios `run.step.*` apendeados —
    jamás una segunda pasada de un step ya en curso."""
    items = plan_items or (
        PlanItem(
            id="item-1",
            description=f"agentic run — {capability_id}",
            verification="delegate",
            status="pending",
        ),
    )
    recorder.append(
        "plan.created",
        PlanCreatedPayload(plan_id=plan_id, run_id=run_id, items=items).model_dump(),
    )

    spent_tokens = 0
    spent_cost_usd = 0.0
    previous_output_digest: str | None = None

    for turn in range(1, max_turns + 1):
        plan_item = items[turn - 1] if turn - 1 < len(items) else None
        result = _run_agentic_turn(
            recorder,
            start_step,
            registry,
            dispatcher,
            proposer,
            post_invoke,
            run_id=run_id,
            domain_id=domain_id,
            turn=turn,
            plan_id=plan_id,
            plan_item=plan_item,
            spent_tokens=spent_tokens,
            spent_cost_usd=spent_cost_usd,
            budget=budget,
            goal_capability_id=capability_id,
            goal_inputs=inputs,
            previous_output_digest=previous_output_digest,
        )
        spent_tokens, spent_cost_usd = result.spent_tokens, result.spent_cost_usd
        previous_output_digest = result.output_digest

        if result.terminal:
            return projected_row()
        if result.done:
            recorder.append("run.completed", {"output_digest": result.output_digest})
            return projected_row()

    # Terminación triple, rama (a): max_turns agotado sin que el gate dijera
    # "done" — jamás un run.completed implícito por "se acabaron los turnos".
    recorder.fail_run(EXHAUSTED_ERROR_KIND)
    return projected_row()
