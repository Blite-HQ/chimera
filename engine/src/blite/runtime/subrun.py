"""Sub-runs elegidos por el agente — freeze §13 (Las 3 reglas del run
jerárquico) + docs/specs/harness-agentico.md §Contrato-4. [S-G · A4]

El criterio de qué CALIFICA como sub-run NO cambia (§13 [S-F]): es sub-run
SOLO la unidad que produce claims propios que el certificado citará — todo
lo demás son steps del loop plano de A3 (`_run_agentic_turn`). Este módulo
NO decide ese criterio (eso vive en el agente/proposer que ELIGE lanzar un
sub-run); ofrece los TRES mecanismos que el freeze exige alrededor de esa
decisión, una vez tomada:

1. **`spawn_sub_run`** — corre el hijo (`execute_run` con `parent_run_id`)
   tras comprobar la **herencia fail-closed de `policy_digest`** (regla 3):
   sin valor explícito, hereda el del raíz; con un valor que DIVERGE, la
   llamada explota ANTES de escribir un solo evento del sub-run
   (`PolicyInheritanceError`) — "un certificado jamás se compone de claims
   verificados bajo policies distintas".
2. **`contribute_sub_run_claims`** — tras terminar el sub-run (regla 2):
   computa su `sub_run_provenance_hash` (el hash ENCADENA, Merkle-style, la
   porción de procedencia del sub-run) y aporta cada `claim.emitted` de su
   propio stream al stream del RAÍZ, con `sub_run_id` (CORRELACIONA) + el
   hash estampados — así el `provenance_hash` del raíz ampara
   transitivamente el trabajo del sub-run.
3. **`cancel_run_with_cascade`** — cancela un run y, en cascada, cada
   sub-run DIRECTO que siga activo (regla 1) con
   `run.cancelled {reason: "parent_cancelled"}`; uno ya terminal se SALTA
   (append-only, sin transición entre terminales). El rechazo de appends
   post-terminales de `run.step.*`/`capability.job.*` a un sub-run ya
   cancelado lo garantiza el `EventStore` mismo (freeze §2, `events/rules.py`
   vía `events/writer.py`) — este módulo no lo reimplementa, solo lo hereda
   por construcción.

Import-linter (AX3-b/INV-5): este módulo, como `runtime/loop.py`, jamás
importa litellm/openai/anthropic ni `events.writer`/`postgres`. Tampoco
importa `blite.verification` — el mismo patrón de delegación por callback
que `PostInvokeDelegate` (A3): `contribute_sub_run_claims` journaliza los
payloads de `claim.emitted` que YA existen en el stream del sub-run (los
puso ahí, en su momento, el delegate de verificación de quien invocó el
sub-run) — este módulo solo re-estampa los DOS campos que él sí conoce
(`sub_run_id`, `sub_run_provenance_hash`), nunca construye ni valida la
forma completa de `ClaimEmittedPayload`.

Sin árboles profundos (freeze §13 [S-F], lista NO-va, §15.4): la cascada
alcanza sub-runs DIRECTOS del run cancelado — un sub-run de un sub-run
queda fuera de alcance de Fase 1.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from blite.content import ContentStore
from blite.events.event import Event
from blite.events.rules import provenance_slice
from blite.events.store import EventStore
from blite.runtime.dispatch import Dispatcher
from blite.runtime.loop import (
    PostInvokeDelegate,
    Proposer,
    RunBudget,
    execute_run,
)
from blite.runtime.plan import PlanItem
from blite.runtime.projection import TERMINAL_RUN_STATUSES, RunRow, project_runs
from blite.runtime.registry import Registry

_RUNTIME_ACTOR = "service:runtime"
_DEFAULT_MAX_TURNS = 30

CLAIM_EMITTED_TYPE = "claim.emitted"
RUN_CANCELLED_TYPE = "run.cancelled"
PARENT_CANCELLED_REASON = "parent_cancelled"
"""freeze §13 regla 1: la ÚNICA `reason` que la cascada estampa — la razón
propia de la cancelación del run que la disparó es asunto del caller."""

SUB_RUN_PROVENANCE_PREFIX = b"blite/sub-run-provenance/v1\n"
"""Prefijo del hash de §13 regla 2 ("el hash encadena"). Nota de scope: esto
NO es el `provenance_hash` del certificado DSSE — esa fórmula exacta (vistas
canónicas + `PROVENANCE_PREFIX`) es de `blite.certificate` (frontera Dylan/
Steven, freeze §7); `blite.runtime` no la importa (mantiene la separación de
capas: certificate consume el log del runtime, no al revés). Este hash es un
encadenado propio y suficiente para lo que §13 regla 2 exige: que el
`sub_run_id` no viaje "sin integridad" — cualquier evento del sub-run que
cambie, cambia este hash."""


class PolicyInheritanceError(ValueError):
    """freeze §13 regla 3: herencia fail-closed de `policy_digest`.

    Un sub-run que intente un `policy_digest` que DIVERGE del de su raíz es
    un error de contrato — se levanta ANTES de invocar `execute_run`, así
    que el sub-run NO llega a tener ni su propio `run.created`."""


def _canonical_json(obj: object) -> bytes:
    """Misma forma canónica mínima que `runtime/loop.py::_canonical_json`
    (claves ordenadas, sin espacios) — duplicada a propósito: es una utilidad
    de tres líneas, no una regla de negocio a compartir entre módulos."""
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def compute_sub_run_provenance_hash(events: tuple[Event, ...]) -> str:
    """El hash que ENCADENA la porción de procedencia de un sub-run (§13
    regla 2) — mismo corte que `events.rules.provenance_slice` (freeze §2
    [stress-final]: desde `run.created` hasta el terminal, INCLUSIVE).

    Determinista sobre `(type, seq, payload)` de cada evento del corte —
    cualquier evento del sub-run que cambie, cambia este hash. Sin terminal
    aún ⇒ `ValueError` (propagada de `provenance_slice`): no se puede
    encadenar un sub-run que sigue vivo."""
    sliced = provenance_slice(events)
    body = b"".join(
        _canonical_json({"type": e.type, "seq": e.seq, "payload": e.payload}) + b"\n"
        for e in sliced
    )
    return hashlib.sha256(SUB_RUN_PROVENANCE_PREFIX + body).hexdigest()


def spawn_sub_run(  # noqa: PLR0913 — misma superficie que execute_run (que envuelve) + el trío propio del sub-run (parent_run_id/parent_policy_digest/sub_run_id)
    store: EventStore,
    registry: Registry,
    dispatcher: Dispatcher,
    content: ContentStore,
    *,
    parent_run_id: str,
    parent_policy_digest: str,
    sub_run_id: str,
    actor_id: str,
    domain_id: str,
    max_steps: int,
    capability_id: str,
    inputs: dict[str, Any],
    policy_digest: str | None = None,
    post_invoke: PostInvokeDelegate | None = None,
    max_turns: int = _DEFAULT_MAX_TURNS,
    budget: RunBudget | None = None,
    proposer: Proposer | None = None,
    plan_id: str | None = None,
    plan_items: tuple[PlanItem, ...] = (),
) -> RunRow:
    """Lanza el sub-run hijo de `parent_run_id` (§Contrato-4) y lo corre
    hasta su propio terminal — `execute_run` ya garantiza eso.

    `policy_digest`: `None` ⇒ HEREDA el del raíz (el caso común: el agente
    elige QUÉ sub-run correr, no bajo qué policy). Un valor explícito que
    DIFIERE del raíz es un error fail-closed (`PolicyInheritanceError`) — la
    ÚNICA forma válida de pasarlo explícito es repetir el mismo valor del
    raíz (p.ej. un caller que ya lo tiene a mano y quiere ser explícito).
    """
    effective_policy_digest = (
        parent_policy_digest if policy_digest is None else policy_digest
    )
    if effective_policy_digest != parent_policy_digest:
        msg = (
            f"sub-run {sub_run_id!r} declaró policy_digest="
            f"{effective_policy_digest!r}, diverge del raíz {parent_run_id!r} "
            f"({parent_policy_digest!r}) — herencia fail-closed (freeze §13 regla 3)"
        )
        raise PolicyInheritanceError(msg)

    return execute_run(
        store,
        registry,
        dispatcher,
        content,
        run_id=sub_run_id,
        actor_id=actor_id,
        domain_id=domain_id,
        max_steps=max_steps,
        policy_digest=effective_policy_digest,
        capability_id=capability_id,
        inputs=inputs,
        parent_run_id=parent_run_id,
        post_invoke=post_invoke,
        max_turns=max_turns,
        budget=budget,
        proposer=proposer,
        plan_id=plan_id,
        plan_items=plan_items,
    )


def contribute_sub_run_claims(
    store: EventStore,
    *,
    root_run_id: str,
    sub_run_id: str,
    domain_id: str,
    actor_id: str = _RUNTIME_ACTOR,
) -> str:
    """Tras terminar el sub-run (§13 regla 2): aporta cada `claim.emitted`
    de SU propio stream al stream del RAÍZ, con `sub_run_id`/
    `sub_run_provenance_hash` estampados — retorna el hash computado.

    Fail-closed: el sub-run DEBE estar `completed` (nunca `failed`/
    `cancelled`) — un certificado no ampara transitivamente el trabajo de un
    sub-run que no llegó a un terminal exitoso propio.
    """
    rows = project_runs(store.read_all())
    sub_run_row = rows.get(sub_run_id)
    if sub_run_row is None or sub_run_row.status != "completed":
        status = sub_run_row.status if sub_run_row is not None else "unknown"
        msg = (
            f"sub-run {sub_run_id!r} no está 'completed' (status={status!r}) — "
            "solo un sub-run completado aporta claims al raíz (§13 regla 2)"
        )
        raise ValueError(msg)

    sub_run_events = store.read_stream(sub_run_id)
    sub_run_hash = compute_sub_run_provenance_hash(sub_run_events)
    sliced = provenance_slice(sub_run_events)

    for event in sliced:
        if event.type != CLAIM_EMITTED_TYPE:
            continue
        payload = dict(event.payload)
        payload["sub_run_id"] = sub_run_id
        payload["sub_run_provenance_hash"] = sub_run_hash
        store.append(
            stream_id=root_run_id,
            type=CLAIM_EMITTED_TYPE,
            actor_id=actor_id,
            domain_id=domain_id,
            payload=payload,
        )

    return sub_run_hash


def cancel_run_with_cascade(
    store: EventStore,
    *,
    run_id: str,
    domain_id: str,
    reason: str,
    actor_id: str = _RUNTIME_ACTOR,
) -> tuple[str, ...]:
    """Cancela `run_id` (con `reason` propio del caller) y cascada
    `run.cancelled {reason: "parent_cancelled"}` a cada sub-run DIRECTO que
    siga activo (§13 regla 1).

    No-op sobre `run_id` si ya estaba terminal (jamás doble terminal — freeze
    §2/§3, "sin transición entre terminales"); un sub-run ya terminal se
    SALTA de la cascada por la misma razón. Retorna los `run_id`
    efectivamente cancelados por ESTA llamada, en orden: `run_id` primero (si
    aplicó) y luego los sub-runs cascadeados, orden determinista por id."""
    rows = project_runs(store.read_all())
    cancelled: list[str] = []

    root_row = rows.get(run_id)
    if root_row is not None and root_row.status not in TERMINAL_RUN_STATUSES:
        store.append(
            stream_id=run_id,
            type=RUN_CANCELLED_TYPE,
            actor_id=actor_id,
            domain_id=domain_id,
            payload={"reason": reason},
        )
        cancelled.append(run_id)

    children = sorted(rid for rid, row in rows.items() if row.parent_run_id == run_id)
    for child_id in children:
        child_row = rows[child_id]
        if child_row.status in TERMINAL_RUN_STATUSES:
            continue
        store.append(
            stream_id=child_id,
            type=RUN_CANCELLED_TYPE,
            actor_id=actor_id,
            domain_id=domain_id,
            payload={"reason": PARENT_CANCELLED_REASON},
        )
        cancelled.append(child_id)

    return tuple(cancelled)


__all__ = [
    "CLAIM_EMITTED_TYPE",
    "PARENT_CANCELLED_REASON",
    "PolicyInheritanceError",
    "RUN_CANCELLED_TYPE",
    "cancel_run_with_cascade",
    "compute_sub_run_provenance_hash",
    "contribute_sub_run_claims",
    "spawn_sub_run",
]
