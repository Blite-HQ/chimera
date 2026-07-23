"""
Loop del runtime — pipeline fijo de Fase 1. [S-G · Steven]

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
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from blite.content import ContentStore
from blite.events.rules import validate_run_id
from blite.events.store import EventStore
from blite.runtime.dispatch import Dispatcher
from blite.runtime.projection import RunRow, project_runs
from blite.runtime.registry import Registry

MAX_STEPS_EXCEEDED = "MaxStepsExceeded"

_RUNTIME_ACTOR = "service:runtime"
_JSON_MEDIA_TYPE = "application/json"
_DEFAULT_PROFILE = "in-process"

StepStatus = Literal["pending", "running", "completed", "failed"]


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
) -> RunRow:
    """Ejecuta el pipeline fijo de Fase 1 y retorna la fila proyectada.

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

    # ── step "resolve": elegir la capability vía Registry (ADR-008) ──
    resolve_step = _start_step(
        "resolve", recorder.digest_of({"capability_id": capability_id})
    )
    if resolve_step is None:
        return _projected_row()
    try:
        capability = registry.get(capability_id)
    except KeyError as exc:
        recorder.step_event(
            "failed", resolve_step.model_copy(update={"status": "failed"})
        )
        recorder.fail_run(type(exc).__name__)
        return _projected_row()
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
    invoke_step = _start_step("invoke", input_digest)
    if invoke_step is None:
        return _projected_row()
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
        return _projected_row()
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

    recorder.append("run.completed", {"output_digest": output_digest})
    return _projected_row()
