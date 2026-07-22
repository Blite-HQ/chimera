"""
Reglas del log de eventos — la letra S-F/stress-final del freeze §2 como código.

docs/contract-freeze.md §2 [S-F · N2] + [stress-final · 2026-07-22]:
- Streams de sistema: eventos sin run usan `stream_id = "system:<componente>"`;
  jamás entran al provenance_hash. Reserva: ningún run_id empieza con "system:".
- Escritura post-terminal = RECHAZO para `run.step.*`/`capability.job.*` — un
  append post-terminal cambia los bytes del stream y rompe el recompute del
  provenance_hash de un certificado ya emitido.
- Corte del hash: desde `run.created` hasta el evento terminal del run,
  inclusive — nada después. Las familias de cierre (`run.metrics.recorded`,
  ● de cierre del case) quedan FUERA del hash.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blite.events.event import Event

SYSTEM_STREAM_PREFIX = "system:"

TERMINAL_RUN_EVENTS = frozenset({"run.completed", "run.failed", "run.cancelled"})

# freeze §2 [stress-final]: el rechazo post-terminal aplica a estas familias.
REJECTED_POST_TERMINAL_PREFIXES = ("run.step.", "capability.job.")


class PostTerminalAppendError(Exception):
    """freeze §2 [S-F]: tras el terminal de un run, `run.step.*`/`capability.job.*`
    se RECHAZAN — jamás "aceptar marcado late"."""


def is_system_stream(stream_id: str) -> bool:
    """`system:<componente>` — registry/policy/trust-registry (freeze §2 [S-F · N2])."""
    return stream_id.startswith(SYSTEM_STREAM_PREFIX)


def validate_run_id(run_id: str) -> str:
    """Reserva de namespace (freeze §2 [stress-final]): ningún run_id puede
    empezar con "system:" — los streams de sistema son disjuntos por construcción."""
    if run_id.startswith(SYSTEM_STREAM_PREFIX):
        msg = (
            f"run_id {run_id!r} invade el namespace reservado {SYSTEM_STREAM_PREFIX!r}"
        )
        raise ValueError(msg)
    return run_id


def rejects_post_terminal(event_type: str) -> bool:
    """¿Este tipo se rechaza si el stream ya tiene su evento terminal?"""
    return event_type.startswith(REJECTED_POST_TERMINAL_PREFIXES)


def provenance_slice(stream_events: tuple[Event, ...]) -> tuple[Event, ...]:
    """El corte exacto del provenance_hash (freeze §2 [stress-final]): desde
    `run.created` hasta el terminal del run, INCLUSIVE — nada después (las
    familias de cierre post-terminales quedan fuera; así `●CertificateIssued`
    no se auto-referencia). Sin terminal aún ⇒ ValueError (el certificado no
    puede emitirse sobre un run vivo)."""
    if not stream_events:
        msg = "stream vacío: no hay run.created que abra el corte"
        raise ValueError(msg)
    if is_system_stream(stream_events[0].stream_id):
        msg = "los streams de sistema jamás entran al provenance_hash (freeze §2)"
        raise ValueError(msg)
    for i, event in enumerate(stream_events):
        if event.type in TERMINAL_RUN_EVENTS:
            return tuple(stream_events[: i + 1])
    msg = "el run no tiene evento terminal: el corte del hash no está definido aún"
    raise ValueError(msg)
