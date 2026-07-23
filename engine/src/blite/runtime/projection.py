"""
Proyección `runs` — replay puro del log de eventos. [S-G Etapa 0 · Steven]

docs/contract-freeze.md §3 [stress-final]: el payload de `run.created` carga
TODO lo que la fila necesita (`max_steps`, `policy_digest`, `parent_run_id?`,
digests de definición) — "un replay de events regenera la proyección" es
verdad ejecutable: `project_runs(store.read_all())` reconstruye cada fila
desde el log solo, sin estado lateral.

Máquina de estados (freeze §3): CREATED → RUNNING → {COMPLETED | FAILED |
CANCELLED}, sin transición entre terminales — un evento de ciclo de vida
posterior al terminal no muta la fila.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from blite.events.event import Event
from blite.events.rules import is_system_stream

RunStatus = Literal["created", "running", "completed", "failed", "cancelled"]

TERMINAL_RUN_STATUSES: frozenset[str] = frozenset({"completed", "failed", "cancelled"})


class RunRow(BaseModel):
    """Una fila de `runs_projection` — íntegramente regenerable por replay."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    status: RunStatus
    actor_id: str
    domain_id: str
    max_steps: int
    policy_digest: str
    parent_run_id: str | None = None
    output_digest: str | None = None
    error_kind: str | None = None
    cancel_reason: str | None = None


def _row_from_created(event: Event) -> RunRow:
    """La fila nace del payload de `run.created` — `max_steps` y `policy_digest`
    son obligatorios en ese payload (freeze §3); su ausencia explota, no se
    rellena con defaults."""
    payload = event.payload
    return RunRow(
        run_id=payload.get("run_id", event.stream_id),
        status="created",
        actor_id=payload.get("actor_id", event.actor_id),
        domain_id=payload.get("domain_id", event.domain_id),
        max_steps=payload["max_steps"],
        policy_digest=payload["policy_digest"],
        parent_run_id=payload.get("parent_run_id"),
    )


def project_runs(events: tuple[Event, ...]) -> dict[str, RunRow]:
    """Fold puro sobre el log: `{run_id: RunRow}` a partir de `read_all()`.

    Ignora streams de sistema (`system:*` — freeze §2 [S-F · N2]) y eventos
    que no son ciclo de vida `run.*`; la clave es el `stream_id`, que ES el
    `run_id` (freeze §2/§13, un stream por run).
    """
    rows: dict[str, RunRow] = {}
    for event in events:
        if is_system_stream(event.stream_id):
            continue
        if event.type == "run.created":
            # El fundacional abre la fila; un duplicado no la reescribe
            # (el EventStore ya garantiza seq por stream — primero gana).
            if event.stream_id not in rows:
                rows[event.stream_id] = _row_from_created(event)
            continue
        row = rows.get(event.stream_id)
        if row is None or row.status in TERMINAL_RUN_STATUSES:
            continue
        if event.type == "run.started":
            rows[event.stream_id] = row.model_copy(update={"status": "running"})
        elif event.type == "run.completed":
            rows[event.stream_id] = row.model_copy(
                update={
                    "status": "completed",
                    "output_digest": event.payload.get("output_digest"),
                }
            )
        elif event.type == "run.failed":
            rows[event.stream_id] = row.model_copy(
                update={
                    "status": "failed",
                    "error_kind": event.payload.get("error_kind"),
                }
            )
        elif event.type == "run.cancelled":
            rows[event.stream_id] = row.model_copy(
                update={
                    "status": "cancelled",
                    "cancel_reason": event.payload.get("reason"),
                }
            )
    return rows
