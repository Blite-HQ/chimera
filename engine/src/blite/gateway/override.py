"""
`OverrideEvent` / `OverridePayload` — la relajación con responsable.
Ítem C10/M29 (freeze §10 completo → código).

**Qué es un override y por qué no es un flag.** Relajar una garantía del
sistema (un principio, un guardrail, el propio registro) no se hace con una
variable de entorno ni con un `if` piadoso: se hace escribiendo en el log
append-only QUIÉN lo autorizó, POR QUÉ y CON QUÉ ALCANCE — y se escribe
**antes** de que surta efecto (INV-4). Un override que se registra después es
un override que, si el proceso muere en el medio, nunca ocurrió para el
auditor y sí ocurrió para el sistema.

**Autoridad graduada (P1-5).** No basta con ser `user:*`: el autorizador debe
portar el permiso `override:apply:<scope>` en su intersección efectiva (§8).
Un usuario cualquiera ya no relaja PR2 con alcance global.

**Match EXACTO del permiso (A6, se estampa por escrito).** `override:apply:
global` NO habilita un override de alcance `run`, ni al revés. La alternativa
—jerárquica, «global incluye lo demás»— hace que el permiso más peligroso sea
también el más cómodo, y convierte cada concesión de alcance amplio en una
concesión silenciosa de todos los alcances menores. Con match exacto, cada
alcance se concede a propósito. El costo (un operador con `global` que
necesite un override de `run` pide también ese permiso) es visible y barato;
el de la alternativa es invisible.

**AX2 — la regla que se muerde la cola:** desactivar el propio registro de
overrides ES un override. No hay excepción para ese caso: se escribe primero,
en el mismo `events` append-only, o no ocurre.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from blite.events.event import Event
from blite.events.store import EventStore
from blite.identity.identity import Identity

OVERRIDE_APPLIED = "override.applied"
"""`●HumanOverrideRecorded` del catálogo §14, en el wire dotted-lowercase que
usa el resto de los eventos. No es tabla nueva: es una fila más de `events`
(freeze §10)."""

OVERRIDE_LOG_TARGET = "subsystem:override-log"
"""El target de AX2: apagar el registro de overrides. Nombrarlo como
constante evita que alguien lo escriba distinto y se salte, sin querer, la
regla que existe para que ese caso NO tenga excepción."""

OverrideScope = Literal["run", "domain", "global"]

_USER_URN = r"^user:[a-z0-9-]+$"


class OverrideNotAuthorizedError(PermissionError):
    """Fail-closed: sin el permiso EXACTO del alcance, no se escribe el
    evento ni se aplica nada. El intento fallido no deja rastro en `events`
    a propósito — el log de confianza registra lo que OCURRIÓ; un intento
    rechazado es asunto del log operativo, y mezclarlos haría que «hay un
    override registrado» dejara de significar «hubo un override»."""


class OverridePayload(BaseModel):
    """La forma confirmada del payload (freeze §10)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    target: str
    """`principle:PR2` · `guardrail:<name>` · `subsystem:logging` — QUÉ se
    relaja."""
    reason: str = Field(min_length=1)
    """Sin razón no hay override: un registro que no dice POR QUÉ documenta
    que pasó algo y no sirve para juzgarlo."""
    authorized_by: str = Field(pattern=_USER_URN)
    """URN restringido a `user:*` (AX2): la relajación exige un responsable
    humano identificable. Un `agent:*` o un `service:*` no pueden autorizar —
    si pudieran, «hay un humano detrás» sería una convención, no un hecho.

    Nombre en snake_case como todos los payloads del log (§3); el
    `authorizedBy` del §10 es prosa con sabor TS, no forma del wire."""
    scope: OverrideScope
    policy_id: str | None = None
    """Enlaza el override con la regla de Policy relajada (cruza con el
    estampado de §6)."""


def required_permission(scope: OverrideScope) -> str:
    """`override:apply:<scope>` — el permiso EXACTO que ese alcance exige."""
    return f"override:apply:{scope}"


def apply_override(
    store: EventStore,
    *,
    payload: OverridePayload,
    authorizer: Identity,
    domain_id: str,
    stream_id: str,
) -> Event:
    """Autoriza y REGISTRA el override; devuelve el evento escrito.

    El orden es el contrato (INV-4): esta función se llama ANTES de aplicar
    la relajación, y el caller solo aplica si esta retornó. Por eso no recibe
    ni ejecuta la acción relajada — mezclarlas permitiría que un caller
    aplicara primero «y de paso» registrara."""
    if authorizer.id != payload.authorized_by:
        msg = (
            f"el override declara autorizador {payload.authorized_by!r} pero lo "
            f"presenta {authorizer.id!r} — nadie registra a otro como responsable"
        )
        raise OverrideNotAuthorizedError(msg)
    permiso = required_permission(payload.scope)
    if permiso not in authorizer.permissions:
        msg = (
            f"{authorizer.id!r} no porta {permiso!r} en su intersección efectiva "
            f"(match EXACTO, A6): tiene {sorted(authorizer.permissions)!r}"
        )
        raise OverrideNotAuthorizedError(msg)
    return store.append(
        stream_id=stream_id,
        type=OVERRIDE_APPLIED,
        actor_id=authorizer.id,
        domain_id=domain_id,
        payload=payload.model_dump(),
    )


__all__ = [
    "OVERRIDE_APPLIED",
    "OVERRIDE_LOG_TARGET",
    "OverrideNotAuthorizedError",
    "OverridePayload",
    "OverrideScope",
    "apply_override",
    "required_permission",
]
