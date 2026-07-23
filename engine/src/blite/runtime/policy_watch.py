"""
Palanca compensatoria de R-Pol1 — freeze §6 [S-F · EX-5]. [S-G · frontera Dylan/Steven]

Al aplicar un `○PolicyChanged` que ENDURECE, el runtime abre
`●EscalationOpened` (`escalation.opened`, catálogo §14) sobre los runs en
vuelo cuyo `policy_digest` pinneado quedó por debajo de la nueva exigencia.
El pin NO cambia (R-Pol1): la palanca es alarma, jamás revocación ni re-pin —
el `run.created` original queda intacto; solo se apila un evento nuevo en el
stream del run. Un softening (`hardened=False`) no es condición de alarma.

El payload de `escalation.opened` lo cierra Steven (visto bueno de Dylan)
al estilo del catálogo §14: referencias trazables por digest, sin texto libre.
"""

from __future__ import annotations

from blite.events.event import Event
from blite.events.store import EventStore
from blite.runtime.projection import TERMINAL_RUN_STATUSES, project_runs

ESCALATION_OPENED = "escalation.opened"

_RUNTIME_ACTOR = "service:runtime"


def on_policy_changed(
    store: EventStore,
    *,
    old_digest: str,
    new_digest: str,
    hardened: bool,
) -> tuple[Event, ...]:
    """Reacción del runtime a `○PolicyChanged` — retorna las escalaciones abiertas.

    Los runs en vuelo se descubren por replay (`project_runs` — misma
    proyección del seed 1, no un fold paralelo): status no terminal y
    `policy_digest` pinneado == `old_digest`.
    """
    if not hardened:
        return ()
    rows = project_runs(store.read_all())
    opened: list[Event] = []
    for run_id, row in rows.items():
        if row.status in TERMINAL_RUN_STATUSES:
            continue
        if row.policy_digest != old_digest:
            continue
        opened.append(
            store.append(
                stream_id=run_id,
                type=ESCALATION_OPENED,
                actor_id=_RUNTIME_ACTOR,
                domain_id=row.domain_id,
                payload={
                    "run_id": run_id,
                    "pinned_policy_digest": old_digest,
                    "superseding_policy_digest": new_digest,
                    "reason_kind": "policy_hardened",
                },
            )
        )
    return tuple(opened)
