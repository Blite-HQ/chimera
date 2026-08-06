"""Hash-chain por evento en el writer único — anexo de canonicalización §4
(CONGELADO), ítem C5/M8 pieza 1.

`hash_i = SHA-256("blite/event/v1\\n" ‖ hash_{i-1}^hex ‖ "\\n" ‖ C(view(e_i)))`,
génesis `hash_0^hex = ""`.

Qué compra la cadena por encima del `provenance_hash` que ya existía: el
`provenance_hash` cubre el corte del run (hasta el terminal) y se computa
cuando se emite el certificado. La cadena cubre CADA evento en el momento de
escribirlo — incluidas las familias de cierre post-terminales, que quedan
FUERA del hash del certificado por diseño y hasta hoy no las amparaba nada.
Y el head en el terminal es exactamente el valor que la Fase 2 promueve a
`provenance_hash` «sin cambiar forma»: emitirlo ya deja el sustrato puesto.
"""

from __future__ import annotations

import hashlib

from blite.certificate.canonical import canonicalize
from blite.events import create_event_store
from blite.events.chain import (
    EVENT_CHAIN_PREFIX,
    GENESIS_PREV_HASH,
    chain_head_of_views,
    event_view,
)
from blite.events.event import Event
from blite.events.rules import provenance_slice
from blite.events.store import EventStore


def _append(store: EventStore, stream_id: str, type_: str, **payload: object) -> Event:
    return store.append(
        stream_id=stream_id,
        type=type_,
        actor_id="service:runtime",
        domain_id="d-default",
        payload=dict(payload),
    )


def test_el_primer_evento_de_un_stream_encadena_desde_la_genesis() -> None:
    """Génesis `""` — elección EXPLÍCITA del anexo §4 (el AGT tiene `""` en
    Python y `"0"*64` en TypeScript por no elegir, y sus implementaciones no
    se verifican entre sí)."""
    # Arrange
    store = create_event_store()

    # Act
    evento = _append(store, "run-chain", "run.created", run_id="run-chain")

    # Assert
    assert evento.prev_hash == GENESIS_PREV_HASH
    esperado = hashlib.sha256(
        EVENT_CHAIN_PREFIX + b"" + b"\n" + canonicalize(event_view(evento))
    ).hexdigest()
    assert evento.hash == esperado


def test_cada_evento_encadena_al_anterior_de_su_propio_stream() -> None:
    """La cadena es por stream: dos runs concurrentes no se entrelazan (si lo
    hicieran, el orden de escritura de OTRO run cambiaría los hashes de este
    y el replay dejaría de ser determinista)."""
    # Arrange
    store = create_event_store()

    # Act — se intercalan a propósito
    a1 = _append(store, "run-a", "run.created", run_id="run-a")
    b1 = _append(store, "run-b", "run.created", run_id="run-b")
    a2 = _append(store, "run-a", "run.started")

    # Assert
    assert a2.prev_hash == a1.hash
    assert b1.prev_hash == GENESIS_PREV_HASH
    assert a1.hash != b1.hash


def test_la_cadena_se_recomputa_entera_desde_las_vistas() -> None:
    """LA propiedad que hace la cadena verificable offline: quien audite NO
    necesita un hash por evento empaquetado — con las vistas canónicas
    reconstruye la cadena completa y llega al mismo head."""
    # Arrange
    store = create_event_store()
    _append(store, "run-c", "run.created", run_id="run-c")
    _append(store, "run-c", "run.started")
    _append(store, "run-c", "run.completed")

    # Act
    eventos = store.read_stream("run-c")
    head = chain_head_of_views([event_view(e) for e in eventos])

    # Assert
    assert head == eventos[-1].hash


def test_el_head_del_certificado_es_el_del_evento_terminal() -> None:
    """Corte [stress-final] (freeze §2): las familias de cierre
    post-terminales (`run.metrics.recorded`, los ● del case) siguen
    encadenadas en el log —nadie las puede reescribir— pero el head que el
    certificado ampara es el del terminal, o `●CertificateIssued` se
    auto-referenciaría."""
    # Arrange
    store = create_event_store()
    _append(store, "run-d", "run.created", run_id="run-d")
    _append(store, "run-d", "run.completed")
    metricas = _append(store, "run-d", "run.metrics.recorded", attestations_total=2)

    # Act
    eventos = store.read_stream("run-d")
    corte = provenance_slice(eventos)

    # Assert
    assert len(corte) == 2  # el terminal cierra el corte
    assert chain_head_of_views([event_view(e) for e in corte]) == corte[-1].hash
    # y la métrica post-terminal SÍ sigue encadenada en el log
    assert metricas.prev_hash == corte[-1].hash


def test_reescribir_un_payload_rompe_el_recompute_de_la_cadena() -> None:
    """La cadena es tamper-evident por evento, no solo por corte: cambiar un
    payload viejo cambia su hash y el de TODOS los posteriores."""
    # Arrange
    store = create_event_store()
    _append(store, "run-e", "run.created", run_id="run-e")
    _append(store, "run-e", "run.started")
    eventos = store.read_stream("run-e")
    vistas = [event_view(e) for e in eventos]

    # Act — la historia reescrita post-hoc
    vistas[0]["payload"] = {"run_id": "run-FORJADO"}

    # Assert
    assert chain_head_of_views(vistas) != eventos[-1].hash


def test_el_encadenado_no_entra_a_la_vista_canonica() -> None:
    """El anexo §3 excluye `prev_hash`/`hash` de `view(e)` — si entraran, el
    hash de un evento dependería de sí mismo."""
    store = create_event_store()
    evento = _append(store, "run-f", "run.created", run_id="run-f")

    assert set(event_view(evento)) == {
        "id",
        "stream_id",
        "seq",
        "type",
        "actor_id",
        "domain_id",
        "payload",
        "occurred_at",
    }
