"""
Rutas de conversación del run — `POST /runs/{id}/messages` y
`POST /runs/{id}/cancel` (spec `docs/specs/chat-conversacion.md`
§Contrato-2/3). [E · P3]

Ambas rutas son EMISORES: su efecto vive en el stream, jamás en la respuesta
HTTP (mismo principio que `POST /runs` → 202). Ninguna inventa vocabulario —
`mission.message` materializa la reserva del catálogo §14 y `run.cancelled`
ya estaba congelado (§3) desde antes, solo le faltaba quién lo emitiera (N1).

**El 409 es la cara HTTP del freeze §2.** Un stream con evento terminal no
acepta más appends de ciclo de vida: mandar un mensaje o cancelar un run ya
muerto no es un error del servidor ni se traga en silencio — es un conflicto
declarado, y el cliente continúa la conversación abriendo un run NUEVO que
cita al raíz por `thread_id` (§Contrato-4).
"""

# pyright: reportUnusedFunction=false
# ^ Los handlers de FastAPI se registran por DECORADOR (`@router.get/post`), no
#   por llamada: pyright los ve como funciones locales que nadie usa. Silenciar
#   la regla acá —y solo acá— evita 15 falsos positivos sin apagar la
#   comprobación en el resto del proyecto, donde una función sin usar SÍ es
#   señal de código muerto.

from __future__ import annotations

from typing import Any
from uuid import uuid4

import jsonschema
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from blite.events.event import Event
from blite.events.rules import TERMINAL_RUN_EVENTS
from blite.gateway.approval import (
    ApprovalRespondedPayload,
    OverrideScope,
    authorize_approval_response,
)
from blite.runtime.mission import (
    CASCADE_CANCEL_REASON,
    DEFAULT_CANCEL_REASON,
    MISSION_MESSAGE_EVENT,
    MissionMessagePayload,
)
from chimera_api.runs import RunResources


class PostMessageRequest(BaseModel):
    """Body de `POST /runs/{id}/messages` (§Contrato-2).

    `author` NO viaja acá A PROPÓSITO: lo estampa la identidad del request
    (la sesión JWT en cookie, C2/M2) — un cliente no puede decir «este
    mensaje lo escribió otro». Mismo patrón del flip AX1."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str = Field(min_length=1)


class PostMessageResponse(BaseModel):
    """202 — el `message_id` con el que el mensaje quedó journalizado."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    message_id: str


class PostCancelRequest(BaseModel):
    """Body de `POST /runs/{id}/cancel` (§Contrato-3) — `reason` opcional."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reason: str = Field(default=DEFAULT_CANCEL_REASON, min_length=1)


class PostApprovalRequest(BaseModel):
    """Body de `POST /runs/{id}/approvals/{approval_id}` (§Contrato-7).

    `authorized_by` NO viaja: lo estampa la identidad del request, igual que
    `author` en los mensajes. `response` es el valor libre que el humano
    llenó — se valida contra el `json_schema` que el request DECLARÓ, no
    contra un esquema inventado por el endpoint."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    response: Any


def _require_open_stream(resources: RunResources, run_id: str) -> tuple[Event, ...]:
    """404 si el log jamás vio el run; 409 si ya es terminal (§2).

    El orden importa: «desconocido» y «terminado» son respuestas distintas —
    un 409 sobre un run inexistente mentiría diciendo que existió."""
    stream = resources.store.read_stream(run_id)
    if not stream:
        raise HTTPException(status_code=404, detail="run desconocido")
    if any(event.type in TERMINAL_RUN_EVENTS for event in stream):
        raise HTTPException(
            status_code=409,
            detail=(
                "el run ya es terminal — el stream no acepta más appends "
                "(freeze §2); continuá el hilo con un run nuevo (thread_id)"
            ),
        )
    return stream


def create_chat_router(resources: RunResources) -> APIRouter:
    """Router de conversación, cerrado sobre la MISMA infra de vida-de-app
    que `/runs` (un `RunResources` por app — mismo `store`)."""
    router = APIRouter()

    @router.post("/runs/{run_id}/messages", status_code=202)
    def post_message(
        run_id: str, body: PostMessageRequest, request: Request
    ) -> PostMessageResponse:
        """202: el mensaje entra al stream del run — DENTRO del
        `provenance_hash` (§Contrato-1: la conversación que dirigió el run es
        parte de lo que el certificado ampara). El harness lo drena al turno
        SIGUIENTE (§Contrato-5); jamás interrumpe el turno en curso."""
        identity = resources.session_auth.identity_from(request)
        _require_open_stream(resources, run_id)
        payload = MissionMessagePayload(
            run_id=run_id,
            message_id=f"msg-{uuid4().hex}",
            author=identity.id,
            text=body.text,
        )
        resources.store.append(
            stream_id=run_id,
            type=MISSION_MESSAGE_EVENT,
            actor_id=identity.id,
            domain_id=_domain_of(resources, run_id),
            payload=payload.model_dump(),
        )
        return PostMessageResponse(message_id=payload.message_id)

    @router.post("/runs/{run_id}/cancel", status_code=202)
    def post_cancel(
        run_id: str, body: PostCancelRequest, request: Request
    ) -> dict[str, str]:
        """202: emisor de `run.cancelled` (evento YA congelado — N1 solo le
        da ruta). La cascada a sub-runs activos y el barrido de jobs son del
        runtime (§13), no de este endpoint."""
        identity = resources.session_auth.identity_from(request)
        if body.reason == CASCADE_CANCEL_REASON:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"{CASCADE_CANCEL_REASON!r} está reservado a la cascada "
                    "del runtime (freeze §13 regla i) — un humano no declara "
                    "que su run murió por el padre"
                ),
            )
        _require_open_stream(resources, run_id)
        resources.store.append(
            stream_id=run_id,
            type="run.cancelled",
            actor_id=identity.id,
            domain_id=_domain_of(resources, run_id),
            payload={"reason": body.reason},
        )
        return {}

    @router.post("/runs/{run_id}/approvals/{approval_id}", status_code=202)
    def post_approval_response(
        run_id: str,
        approval_id: str,
        body: PostApprovalRequest,
        request: Request,
    ) -> dict[str, str]:
        """202: la mitad `response` del par elicitation (§Contrato-7).

        Tres compuertas, todas fail-closed y en este orden:
        1. **existe el request** — un `approval.responded` sin su
           `approval.requested` sería una respuesta a una pregunta que nadie
           hizo (404 si el run ni existe, 409 si ya es terminal —
           `_require_open_stream`, sin excepción para esta ruta);
        2. **no fue respondido ya** — el par es 1:1 (409);
        3. **el valor valida contra el `json_schema` que el request declaró**
           (422) y **la identidad porta `override:apply:<scope>`** (403,
           `authorize_approval_response` — maquinaria §8/§10 ya congelada,
           que esta ruta REUSA sin reabrir).

        **Por qué el 409 post-terminal aplica ACÁ también, a propósito
        (F1.3, revisión de control):** freeze §2 deja los eventos
        post-terminales FUERA del `provenance_hash` (el corte va de
        `run.created` al terminal, inclusive; solo las familias de CIERRE —
        `run.metrics.recorded`, `●CaseClosed`, `●CertificateIssued` —
        se admiten después). Responder una aprobación es una decisión de
        GOBIERNO, no una familia de cierre: dejarla entrar post-terminal la
        journalizaría FUERA de lo que el certificado ampara — una aprobación
        que el bundle no puede demostrar. Y es un hueco semántico además de
        uno criptográfico: aprobar un run que ya falló no revive nada, así
        que el 202 mentiría que hubo gobierno cuando no lo hubo.

        Consecuencia honesta: con el gate SÍNCRONO de hoy
        (`chimera_api.runs._build_approval_gate`, `mission.py:132-141` — «tu
        gate NO debe bloquear esperando respuesta humana»), el ÚNICO
        `approval.requested` que puede existir nace de un turno que YA negó
        y cerró el run (`run.failed`) en el mismo turno que lo pidió. Contra
        ese run, esta ruta da 409 — correcto, no un defecto. Un par
        request→response que de verdad se cierre EN VIVO (stream abierto,
        202 legítimo, `approval.responded` dentro del hash) exige que el
        gate pueda esperar sin bloquear un hilo — eso es la cola durable de
        P11 (`JobQueue`), no esta ruta. Hasta que P11 exista, "aprobación
        humana en el lazo" es un mecanismo demostrado (el `approval.
        requested` real, ver `tests/unit/api/test_mission_approval_gate.
        py::TestApprovalMechanismoSinCierreEnVivo`) sin política de cierre
        en vivo — declarado, no rodeado.
        """
        identity = resources.session_auth.identity_from(request)
        stream = _require_open_stream(resources, run_id)
        solicitud = _find_approval_request(stream, approval_id)
        if solicitud is None:
            raise HTTPException(
                status_code=404,
                detail=f"approval {approval_id!r} desconocido en este run",
            )
        if _already_responded(stream, approval_id):
            raise HTTPException(
                status_code=409,
                detail=f"approval {approval_id!r} ya fue respondido (par 1:1)",
            )

        json_schema = solicitud.payload.get("json_schema", {})
        try:
            jsonschema.validate(body.response, json_schema)
        except jsonschema.ValidationError as exc:
            raise HTTPException(
                status_code=422,
                detail=(
                    "la respuesta no valida contra el json_schema declarado "
                    f"por el approval: {exc.message}"
                ),
            ) from exc

        payload = ApprovalRespondedPayload(
            run_id=run_id,
            approval_id=approval_id,
            response=body.response,
            authorized_by=identity.id,
        )
        decision = authorize_approval_response(payload, identity, scope=_APPROVAL_SCOPE)
        if not decision.allowed:
            raise HTTPException(status_code=403, detail=decision.reason)

        resources.store.append(
            stream_id=run_id,
            type="approval.responded",
            actor_id=identity.id,
            domain_id=_domain_of(resources, run_id),
            payload=payload.model_dump(),
        )
        return {}

    return router


_APPROVAL_SCOPE: OverrideScope = "run"
"""Scope sobre el que se exige `override:apply:<scope>` para responder un
approval — el conjunto es CERRADO (`{run, domain, global}`, freeze §10) y
`run` es el más angosto que aplica: un approval autoriza una acción DENTRO de
esta corrida, no una excepción de dominio ni global. El menor privilegio que
alcanza, jamás el más cómodo.

Consecuencia honesta y buscada: el operador local por defecto NO trae
`override:apply:run` en sus permisos (`chimera_api.auth`), así que responder
un approval sin una identidad que lo porte devuelve **403** — fail-closed. El
despliegue que quiera aprobar desde el Studio otorga el permiso explícito;
nadie aprueba por accidente."""


def _find_approval_request(stream: tuple[Event, ...], approval_id: str) -> Event | None:
    for event in stream:
        if (
            event.type == "approval.requested"
            and str(event.payload.get("approval_id")) == approval_id
        ):
            return event
    return None


def _already_responded(stream: tuple[Event, ...], approval_id: str) -> bool:
    return any(
        event.type == "approval.responded"
        and str(event.payload.get("approval_id")) == approval_id
        for event in stream
    )


def _domain_of(resources: RunResources, run_id: str) -> str:
    """El `domain_id` del propio run — se lee del `run.created` en vez de
    asumir el default del proceso: un evento del stream jamás cambia de
    dominio a mitad de camino."""
    stream = resources.store.read_stream(run_id)
    for event in stream:
        if event.type == "run.created":
            return str(event.payload.get("domain_id", event.domain_id))
    return stream[0].domain_id if stream else _FALLBACK_DOMAIN


_FALLBACK_DOMAIN = "domain-default"
"""Solo alcanzable con un stream vacío — `_require_open_stream` ya cortó con
404 antes de llegar acá; existe para que la función sea total."""


__all__ = [
    "PostCancelRequest",
    "PostMessageRequest",
    "PostMessageResponse",
    "create_chat_router",
]
