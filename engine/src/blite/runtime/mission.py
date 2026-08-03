"""
Conversación del run — `mission.message` ↔ `●MissionMessage` (spec
`docs/specs/chat-conversacion.md` §Contrato-1/5, decisión #123). [A · P3]

**El chat NO es un almacén paralelo.** El mensaje del usuario es un evento del
MISMO stream del run (patrón OpenHands/AG-UI validado en el research R2), lo
que le da a Chimera una propiedad que ningún producto estudiado ofrece: la
conversación que dirigió el run queda DENTRO del `provenance_hash` — el
certificado ampara también lo que se pidió, no solo lo que se hizo. Por eso
acá no hay tabla `messages` ni buffer: la cola de mensajes pendientes se
DERIVA del stream (`pending_messages_for`), fuente única (INV-5 append-only).

Queue-to-next-turn (§Contrato-5): un mensaje journalizado a mitad del turno N
se drena al `TurnContext` del turno N+1 — jamás interrumpe el turno en curso.
Es la traducción del «safe boundary» del estado del arte (Devin/Claude Code)
a la frontera que Chimera ya tenía: el límite de turno. Steer intra-turno
queda vetado por doctrina propia (freeze §8: reautorizar a mitad de step es
error fail-closed).
"""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field

from blite.events.event import Event

MISSION_MESSAGE_EVENT = "mission.message"
"""Nombre de wire congelado (catálogo §14 [MEJORADO #102] — la reserva
`●MissionMessage` que esta implementación materializa)."""

DEFAULT_CANCEL_REASON = "user_requested"
"""Default del emisor HTTP de `run.cancelled` (spec §Contrato-3)."""

CASCADE_CANCEL_REASON = "parent_cancelled"
"""RESERVADO a la cascada del runtime (§13 regla (i)) — el endpoint de cancel
lo rechaza con 422: un humano jamás declara que su run murió por su padre."""


class MissionMessagePayload(BaseModel):
    """Payload de `mission.message` (§Contrato-1) — 4 campos, misma disciplina
    que `PlanCreatedPayload` (`frozen`, `extra="forbid"`).

    `author` es la URN de quien lo escribió (la estampa la identidad del
    request, jamás el body — §Contrato-2); `text` no puede ser vacía: un
    mensaje sin contenido no es evidencia de nada."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    message_id: str
    author: str
    text: str = Field(min_length=1)


class PendingMessage(BaseModel):
    """Lo que el harness le entrega al proposer en el turno siguiente
    (§Contrato-5) — datos, no poderes (mismo patrón que `TurnContext`).

    `message_id` viaja acá (el harness correlaciona) pero NO entra a la vista
    del prompt: un ID minteado por request rompería la clave de replay
    (freeze §15.7 punto 2) — ver `PROMPT_PROTOCOL` v2."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    message_id: str
    author: str
    text: str


def pending_messages_for(
    stream: tuple[Event, ...], *, already_drained: frozenset[str] = frozenset()
) -> tuple[PendingMessage, ...]:
    """Los `mission.message` del stream que TODAVÍA no se drenaron, en orden
    de log (§Contrato-5: «el harness deriva la cola del stream — fuente
    única, no de un buffer paralelo»).

    `already_drained` son los `message_id` que turnos anteriores ya
    entregaron: el harness lleva esa cuenta en memoria durante la corrida, y
    en un replay se reconstruye leyendo el mismo stream en el mismo orden —
    determinista por construcción."""
    return tuple(
        PendingMessage(
            message_id=str(event.payload["message_id"]),
            author=str(event.payload["author"]),
            text=str(event.payload["text"]),
        )
        for event in stream
        if event.type == MISSION_MESSAGE_EVENT
        and str(event.payload.get("message_id", "")) not in already_drained
    )


class ApprovalRequest(BaseModel):
    """Lo que el loop le pide a la compuerta de aprobación ANTES de ejecutar
    un turno (`harness-agentico.md` §Contrato-6) — datos, no poderes.

    El loop NO decide si algo necesita aprobación (eso es política, y el
    runtime no hace política: INV-2); solo ofrece la costura. La compuerta
    inyectada decide, y su decisión viaja como eventos tipados."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    turn: int
    capability_id: str
    inputs: dict[str, object]


class ApprovalDecision(BaseModel):
    """Lo que la compuerta responde. `required=False` ⇒ el turno sigue sin
    emitir NADA (el caso por defecto: sin compuerta cableada no hay
    aprobaciones fabricadas).

    `required=True` + `granted=False` ⇒ el turno se corta con `cause`: una
    aprobación negada NO es un error del sistema, es una decisión humana
    registrada — por eso viaja con causa propia y no como excepción."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    required: bool = False
    granted: bool = False
    approval_id: str = ""
    prompt: str = ""
    json_schema: dict[str, object] = {}
    cause: str = "approval_denied"


ApprovalGate = Callable[[ApprovalRequest], ApprovalDecision]
"""Puerto inyectable de aprobación humana — mismo patrón que `proposer` y
`crossing` (freeze §8 C-5: se INYECTA, el runtime solo conoce la firma).

**Frontera declarada:** cómo se ESPERA la respuesta humana (bloquear el
worker, suspender el run, reanudar por cola) es decisión del adapter, no del
loop; con `BackgroundTasks` un gate bloqueante retiene un hilo, y por eso la
cola durable (P11/`JobQueue`) es la casa natural del gate que espera de
verdad. El default del despliegue es SIN gate — cero aprobaciones fingidas."""


__all__ = [
    "CASCADE_CANCEL_REASON",
    "DEFAULT_CANCEL_REASON",
    "MISSION_MESSAGE_EVENT",
    "ApprovalDecision",
    "ApprovalGate",
    "ApprovalRequest",
    "MissionMessagePayload",
    "PendingMessage",
    "pending_messages_for",
]
