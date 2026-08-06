"""
StatusList — revocación comprobable SIN romper la verificación offline.
Ítem C7/M8 pieza 3 (research R3 §4).

**El hueco que cierra.** El certificado autodeclaraba `revocation: "none"`:
el único campo que decía «no hay forma de saber si esto fue retirado». Un
certificado que no puede ser retirado no es más confiable, es menos — porque
el día que una policy se endurece o un ancla se descubre rota, lo emitido
sigue afirmando lo mismo para siempre.

**Se adopta la FORMA de W3C Bitstring Status List v1.0 (Recommendation
may-2025), no su stack.** El bitstring comprimido con un bit por certificado
es la parte que resuelve el problema (y la que da privacidad de rebaño: quien
consulta la lista no revela QUÉ certificado le interesa). El stack de
Verifiable Credentials alrededor no aporta nada aquí y traería un modelo de
identidad ajeno. Así que la lista es **un artefacto estático firmado con el
mismo DSSE de todo lo demás**, distribuible por cualquier medio — incluido un
USB en un sitio sin red.

**Cómo convive con el air-gap (la resolución del choque).** La verificación
offline sigue siendo completa sin la lista: `verify-bundle` sin `--status-list`
dice «válido a `valid_as_of`, revocación NO comprobada» — que es exactamente
la semántica ya congelada de `VALID_AS_OF` (P1-2), dicha en voz alta en vez de
escondida. Con la lista, el mismo comando gana frescura. Opt-in, jamás una
llamada de red obligatoria.

Detalles de forma (W3C §Bitstring):
- índice 0 = bit MÁS SIGNIFICATIVO del primer byte;
- la lista tiene un mínimo de 131 072 entradas (16 KB sin comprimir) — no es
  capacidad, es privacidad: una lista corta delata a quién pertenece;
- `encoded_list` = base64 de GZIP del bitstring. Una lista vacía comprime a
  unas decenas de bytes.
"""

from __future__ import annotations

import base64
import gzip
from typing import Any, Literal

from cryptography.hazmat.primitives.asymmetric import ed25519
from pydantic import BaseModel, ConfigDict, Field

from blite.certificate.canonical import canonicalize
from blite.certificate.dsse import DSSEEnvelope, DSSESignature, sign
from blite.certificate.dsse import verify as dsse_verify
from blite.events.store import EventStore

STATUS_LIST_PAYLOAD_TYPE = "application/vnd.blite.status-list+json"
STATUS_LIST_PREDICATE_TYPE = "https://blite.dev/BitstringStatusList/v1"
STATEMENT_TYPE = "https://blite.dev/Statement/v1"

MIN_ENTRIES = 131_072
"""16 KB sin comprimir (W3C §Bitstring): mínimo por PRIVACIDAD, no por
capacidad — una lista del tamaño justo delata cuántos certificados hay y, con
un índice, a cuál pertenece."""

CERTIFICATE_REVOKED = "certificate.revoked"
"""`●CertificateRevoked` (freeze §14) — el evento que retira un certificado
emitido. Va en el stream del run, POST-terminal: fuera del corte del
`provenance_hash` (§2), como el resto de las familias de cierre — o revocar
cambiaría los bytes del stream que el propio certificado ampara."""

StatusPurpose = Literal["revocation", "suspension"]


class StatusListEntry(BaseModel):
    """La posición de UN certificado en la lista — lo que el certificado
    estampa para que un verificador sepa DÓNDE mirar."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status_list_id: str
    status_list_index: int = Field(ge=0)
    status_purpose: StatusPurpose = "revocation"


class StatusList(BaseModel):
    """El artefacto estático: el bitstring + su identidad y su instante."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status_list_id: str
    status_purpose: StatusPurpose = "revocation"
    encoded_list: str
    """base64(gzip(bitstring)) — la forma de W3C."""
    issued_at: str
    """RFC 3339: la lista dice DE CUÁNDO es. Sin esto, «no revocado» no tiene
    fecha y una lista vieja pasaría por fresca."""


def _bitstring_bytes(entries: int) -> int:
    return max(entries, MIN_ENTRIES) // 8


def build_status_list(
    *,
    status_list_id: str,
    revoked_indices: set[int],
    issued_at: str,
    entries: int = MIN_ENTRIES,
    status_purpose: StatusPurpose = "revocation",
) -> StatusList:
    """Construye la lista con los índices dados en 1 (W3C: bit 1 = el estado
    del `statusPurpose` APLICA — aquí, revocado)."""
    tamano = _bitstring_bytes(entries)
    crudo = bytearray(tamano)
    for index in sorted(revoked_indices):
        if index < 0 or index >= tamano * 8:
            msg = (
                f"índice {index} fuera de la lista ({tamano * 8} entradas) — "
                "una revocación que no cabe es una revocación que se pierde"
            )
            raise ValueError(msg)
        crudo[index // 8] |= 0x80 >> (index % 8)
    return StatusList(
        status_list_id=status_list_id,
        status_purpose=status_purpose,
        # mtime=0 para que la MISMA lista comprima a los MISMOS bytes: el
        # gzip por defecto estampa la hora y volvería el artefacto distinto
        # en cada emisión, rompiendo cualquier digest sobre él.
        encoded_list=base64.b64encode(gzip.compress(bytes(crudo), mtime=0)).decode(
            "ascii"
        ),
        issued_at=issued_at,
    )


def is_revoked(status_list: StatusList, index: int) -> bool:
    """¿El bit `index` está en 1? Fuera de rango ⇒ error, jamás «no revocado»
    por defecto: un índice que la lista no cubre es una pregunta sin
    respuesta, y responderla que no sería inventar."""
    crudo = gzip.decompress(base64.b64decode(status_list.encoded_list))
    if index < 0 or index >= len(crudo) * 8:
        msg = (
            f"índice {index} fuera de la lista {status_list.status_list_id!r} "
            f"({len(crudo) * 8} entradas) — sin respuesta, no «no revocado»"
        )
        raise ValueError(msg)
    return bool(crudo[index // 8] & (0x80 >> (index % 8)))


def revoke_certificate(
    store: EventStore,
    *,
    run_id: str,
    domain_id: str,
    entry: StatusListEntry,
    reason: str,
    actor_id: str,
) -> None:
    """Emite `●CertificateRevoked` en el stream del run.

    La revocación es un HECHO DEL LOG antes que un bit en un archivo: quién
    la pidió, cuándo y por qué quedan en el mismo registro append-only que
    todo lo demás. El bit se DERIVA de ahí (`revoked_indices_for`), nunca al
    revés — una lista mantenida a mano sería un estado paralelo sin
    procedencia, y la pregunta «¿por qué está revocado esto?» no tendría
    respuesta auditable.

    `actor_id` es obligatorio y sin default de servicio: retirar un
    certificado emitido es una decisión con responsable (mismo principio que
    `authorizedBy` en los overrides, freeze §10)."""
    store.append(
        stream_id=run_id,
        type=CERTIFICATE_REVOKED,
        actor_id=actor_id,
        domain_id=domain_id,
        payload={
            "status_list_id": entry.status_list_id,
            "status_list_index": entry.status_list_index,
            "status_purpose": entry.status_purpose,
            "reason": reason,
        },
    )


def revoked_indices_for(store: EventStore, status_list_id: str) -> set[int]:
    """Los índices revocados de una lista, PROYECTADOS del log."""
    return {
        int(event.payload["status_list_index"])
        for event in store.read_all()
        if event.type == CERTIFICATE_REVOKED
        and event.payload.get("status_list_id") == status_list_id
    }


def status_list_statement(status_list: StatusList) -> dict[str, Any]:
    """Statement in-toto de la lista — el `subject` es la lista misma."""
    return {
        "_type": STATEMENT_TYPE,
        "subject": [{"name": f"status-list:{status_list.status_list_id}"}],
        "predicateType": STATUS_LIST_PREDICATE_TYPE,
        "predicate": status_list.model_dump(),
    }


def sign_status_list(
    status_list: StatusList,
    *,
    private_key: ed25519.Ed25519PrivateKey,
    keyid: str,
) -> dict[str, Any]:
    """Firma la lista y devuelve el artefacto listo para distribuir."""
    envelope = sign(
        payload_type=STATUS_LIST_PAYLOAD_TYPE,
        payload=canonicalize(status_list_statement(status_list)),
        private_key=private_key,
        keyid=keyid,
    )
    return {
        "envelope": {
            "payloadType": envelope.payload_type,
            "payload": envelope.payload_b64,
            "signatures": [
                {"keyid": s.keyid, "sig": s.sig} for s in envelope.signatures
            ],
        }
    }


def verify_status_list(artifact: dict[str, Any], public_key_b64: str) -> StatusList:
    """Verifica la firma y devuelve la lista de sus BYTES FIRMADOS.

    Una lista sin verificar es peor que ninguna: cualquiera podría producir
    una donde el certificado que le molesta aparece revocado — o donde el que
    le conviene aparece vigente."""
    import json  # noqa: PLC0415 — import local, el resto del módulo no usa json

    sobre = artifact["envelope"]
    envelope = DSSEEnvelope(
        payload_type=sobre["payloadType"],
        payload_b64=sobre["payload"],
        signatures=tuple(
            DSSESignature(keyid=s["keyid"], sig=s["sig"]) for s in sobre["signatures"]
        ),
    )
    payload = dsse_verify(
        envelope,
        ed25519.Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64)),
    )
    statement = json.loads(payload)
    return StatusList.model_validate(statement["predicate"])


__all__ = [
    "CERTIFICATE_REVOKED",
    "MIN_ENTRIES",
    "STATUS_LIST_PAYLOAD_TYPE",
    "STATUS_LIST_PREDICATE_TYPE",
    "StatusList",
    "StatusListEntry",
    "build_status_list",
    "is_revoked",
    "revoke_certificate",
    "revoked_indices_for",
    "sign_status_list",
    "status_list_statement",
    "verify_status_list",
]
