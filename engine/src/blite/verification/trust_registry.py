"""
Registro de confianza — `●VerifierRegistered` / `●AnchorRegistered` (freeze
§14) sobre el stream de sistema `system:trust-registry` (freeze §2 [S-F·N2]).
Cierre del ítem C3/M3 (#103): «registro en trust-registry».

**Qué problema resuelve.** El punto 5 del checklist exige que todo `pass`
traiga un `anchor_digest` *que resuelva contra un descriptor empaquetado en
el Bundle* — endurecimiento SF-P0-1, porque la sola presencia del campo
dejaba pasar un ancla fabricada. Pero hasta hoy esos descriptores se
escribían a mano en el generador del Bundle: el certificado afirmaba anclas
que ningún registro respaldaba, y el punto 5 comparaba una lista contra otra
lista del mismo autor. Con el registro, los descriptores son **proyección
del log** — la misma doctrina de todo lo demás: si no está en el log, no
entra al certificado.

**Streams de sistema (freeze §2).** Estos eventos no pertenecen a ningún run
y JAMÁS entran al `provenance_hash`: registrar un verificador no puede
cambiar los bytes del stream de un run ya certificado. La proyección lee
SOLO `system:trust-registry` — un evento homónimo en el stream de un run no
puede inyectar un descriptor.

**Alcance declarado.** Se implementan los dos eventos de ALTA. El resto del
catálogo (`●Verifier/AnchorSuperseded|Deprecated|Revoked`) queda declarado
sin código: el ciclo de vida exige decidir qué pasa con los certificados ya
emitidos que citan un ancla retirada, y esa pregunta la responde la
StatusList (ítem C7), no este módulo.
"""

from __future__ import annotations

import re
from typing import Any, Protocol, runtime_checkable

from blite.events.store import EventStore
from blite.verification.anchor import AnchorKind
from blite.verification.rule_set import RuleSet

TRUST_REGISTRY_STREAM = "system:trust-registry"
VERIFIER_REGISTERED = "verifier.registered"
ANCHOR_REGISTERED = "anchor.registered"

_REGISTRY_ACTOR = "service:trust-registry"
_SYSTEM_DOMAIN = "system"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@runtime_checkable
class RegistrableVerifier(Protocol):
    """Lo que un adapter debe exponer para ser registrable.

    NO es el puerto `Verifier` (freeze §4, congelado): es la convención que
    todos los adapters ya siguen para poder llenar los 4 digests del binding
    de la `Attestation`. Se declara como tipo para que el registro no dependa
    de un `getattr` optimista."""

    @property
    def verifier_id(self) -> str: ...

    @property
    def verifier_class(self) -> str: ...

    @property
    def anchor_kind(self) -> str: ...

    @property
    def verifier_binary_digest(self) -> str: ...

    @property
    def verifier_params_digest(self) -> str: ...


def _require_digest(value: str, field: str) -> str:
    if not _SHA256.match(value):
        msg = (
            f"{field}={value!r} no es un sha256 hex de 64 caracteres — un "
            "descriptor con digest mal formado convierte el punto 5 del "
            "checklist en comparar basura contra basura (fail-closed)"
        )
        raise ValueError(msg)
    return value


def register_verifier(store: EventStore, verifier: RegistrableVerifier) -> None:
    """Da de alta un verificador: quién es, de qué clase, con qué binario y
    con qué parámetros — lo que un tercero necesita para saber si dos
    constancias salieron del mismo verificador."""
    store.append(
        stream_id=TRUST_REGISTRY_STREAM,
        type=VERIFIER_REGISTERED,
        actor_id=_REGISTRY_ACTOR,
        domain_id=_SYSTEM_DOMAIN,
        payload={
            "verifier_id": verifier.verifier_id,
            "verifier_class": verifier.verifier_class,
            "anchor_kind": verifier.anchor_kind,
            "binary_digest": _require_digest(
                verifier.verifier_binary_digest, "binary_digest"
            ),
            "params_digest": _require_digest(
                verifier.verifier_params_digest, "params_digest"
            ),
        },
    )


def register_anchor(
    store: EventStore, *, anchor_digest: str, kind: AnchorKind, provenance: str
) -> None:
    """Da de alta un ancla por su digest + su procedencia legible."""
    store.append(
        stream_id=TRUST_REGISTRY_STREAM,
        type=ANCHOR_REGISTERED,
        actor_id=_REGISTRY_ACTOR,
        domain_id=_SYSTEM_DOMAIN,
        payload={
            "anchor_digest": _require_digest(anchor_digest, "anchor_digest"),
            "kind": kind,
            "provenance": provenance,
        },
    )


def register_rule_set(store: EventStore, rule_set: RuleSet) -> None:
    """El ancla de un `RuleVerifier` ES su artefacto de reglas: se registra
    por el digest de sus BYTES y se cita por su `rule_set_id`."""
    register_anchor(
        store,
        anchor_digest=rule_set.rule_digest,
        kind="rule",
        provenance=rule_set.rule_set_id,
    )


def _registry_events(store: EventStore, event_type: str) -> tuple[dict[str, Any], ...]:
    return tuple(
        event.payload
        for event in store.read_stream(TRUST_REGISTRY_STREAM)
        if event.type == event_type
    )


def anchor_descriptors(store: EventStore) -> tuple[dict[str, Any], ...]:
    """Los `anchor_descriptors` que el Bundle empaqueta (freeze §7), en
    orden de registro y SIN duplicados: el log es append-only (registrar dos
    veces deja dos eventos), pero el descriptor duplicado no aporta nada y
    ensucia lo que un auditor tiene que leer."""
    seen: dict[str, dict[str, Any]] = {}
    for payload in _registry_events(store, ANCHOR_REGISTERED):
        seen.setdefault(
            payload["anchor_digest"],
            {
                "anchor_digest": payload["anchor_digest"],
                "kind": payload["kind"],
                "provenance": payload["provenance"],
            },
        )
    return tuple(seen.values())


def verifier_descriptors(store: EventStore) -> tuple[dict[str, Any], ...]:
    """Los `verifier_descriptors` del Bundle — misma regla de deduplicación."""
    seen: dict[str, dict[str, Any]] = {}
    for payload in _registry_events(store, VERIFIER_REGISTERED):
        seen.setdefault(
            payload["verifier_id"],
            {
                "verifier_id": payload["verifier_id"],
                "binary_digest": payload["binary_digest"],
            },
        )
    return tuple(seen.values())


__all__ = [
    "ANCHOR_REGISTERED",
    "TRUST_REGISTRY_STREAM",
    "VERIFIER_REGISTERED",
    "RegistrableVerifier",
    "anchor_descriptors",
    "register_anchor",
    "register_rule_set",
    "register_verifier",
    "verifier_descriptors",
]
