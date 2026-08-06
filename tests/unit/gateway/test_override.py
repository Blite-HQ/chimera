"""`OverrideEvent`/`OverridePayload` — ítem C10/M29 (freeze §10 completo).

Relajar una garantía no se hace con un flag: se escribe en el log
append-only quién lo autorizó, por qué y con qué alcance, y se escribe ANTES
de que surta efecto (INV-4). Estos tests fijan las cuatro reglas que hacen
que eso sea cierto y no una intención:

1. sin permiso EXACTO del alcance no se escribe NADA (fail-closed);
2. el autorizador es `user:*` — un agente no puede firmar por un humano;
3. nadie registra a OTRO como responsable;
4. AX2: desactivar el propio registro es, a su vez, un override.
"""

from __future__ import annotations

import pytest

from blite.events import create_event_store
from blite.gateway.override import (
    OVERRIDE_APPLIED,
    OVERRIDE_LOG_TARGET,
    OverrideNotAuthorizedError,
    OverridePayload,
    apply_override,
    required_permission,
)
from blite.identity.identity import Identity

DOMINIO = "d-default"
RUN = "run-override"


def _identidad(*, permisos: set[str], id_: str = "user:dylan") -> Identity:
    return Identity(
        id=id_,
        kind="human" if id_.startswith("user:") else "agent",
        domain_id=DOMINIO,
        permissions=frozenset(permisos),
    )


def _payload(**overrides: object) -> OverridePayload:
    base: dict[str, object] = {
        "target": "principle:PR2",
        "reason": "corrida de diagnóstico con el ingeniero responsable presente",
        "authorized_by": "user:dylan",
        "scope": "run",
    }
    return OverridePayload(**{**base, **overrides})  # type: ignore[arg-type]


def test_el_override_autorizado_queda_en_el_log_con_su_responsable() -> None:
    # Arrange
    store = create_event_store()
    autorizador = _identidad(permisos={"override:apply:run"})

    # Act
    evento = apply_override(
        store,
        payload=_payload(),
        authorizer=autorizador,
        domain_id=DOMINIO,
        stream_id=RUN,
    )

    # Assert
    assert evento.type == OVERRIDE_APPLIED
    assert evento.actor_id == "user:dylan"
    assert evento.payload["target"] == "principle:PR2"
    assert evento.payload["reason"]
    assert evento.payload["scope"] == "run"
    assert store.read_stream(RUN)[-1].id == evento.id


def test_sin_el_permiso_exacto_no_se_escribe_nada() -> None:
    """Fail-closed de verdad: el intento rechazado no deja rastro en `events`.
    Si lo dejara, «hay un override registrado» dejaría de significar «hubo un
    override»."""
    # Arrange
    store = create_event_store()
    sin_permiso = _identidad(permisos={"capability:invoke"})

    # Act / Assert
    with pytest.raises(OverrideNotAuthorizedError, match="override:apply:run"):
        apply_override(
            store,
            payload=_payload(),
            authorizer=sin_permiso,
            domain_id=DOMINIO,
            stream_id=RUN,
        )
    assert store.read_stream(RUN) == ()


def test_el_permiso_global_no_habilita_un_override_de_run() -> None:
    """Match EXACTO (A6, estampado): la alternativa jerárquica hace que el
    permiso más peligroso sea también el más cómodo, y convierte cada
    concesión amplia en una concesión silenciosa de todos los alcances
    menores."""
    store = create_event_store()
    global_ = _identidad(permisos={"override:apply:global"})

    with pytest.raises(OverrideNotAuthorizedError, match="match EXACTO"):
        apply_override(
            store,
            payload=_payload(scope="run"),
            authorizer=global_,
            domain_id=DOMINIO,
            stream_id=RUN,
        )


def test_el_permiso_de_run_tampoco_habilita_un_override_global() -> None:
    """La dirección que de verdad importa: nadie escala su alcance."""
    store = create_event_store()
    de_run = _identidad(permisos={"override:apply:run"})

    with pytest.raises(OverrideNotAuthorizedError):
        apply_override(
            store,
            payload=_payload(scope="global"),
            authorizer=de_run,
            domain_id=DOMINIO,
            stream_id=RUN,
        )


def test_un_agente_no_puede_autorizar_una_relajacion() -> None:
    """AX2: la relajación exige responsable HUMANO identificable. Si un
    `agent:*` pudiera, «hay un humano detrás» sería una convención."""
    with pytest.raises(ValueError, match="authorized_by"):
        _payload(authorized_by="agent:planner-7")


def test_nadie_registra_a_otro_como_responsable() -> None:
    """El autorizador que presenta el override y el que queda registrado son
    el MISMO — o el registro nombraría a alguien que no estuvo."""
    store = create_event_store()
    otro = _identidad(permisos={"override:apply:run"}, id_="user:sebas")

    with pytest.raises(OverrideNotAuthorizedError, match="nadie registra a otro"):
        apply_override(
            store,
            payload=_payload(authorized_by="user:dylan"),
            authorizer=otro,
            domain_id=DOMINIO,
            stream_id=RUN,
        )


def test_un_override_sin_razon_no_es_representable() -> None:
    """Un registro que no dice POR QUÉ documenta que pasó algo y no sirve
    para juzgarlo."""
    with pytest.raises(ValueError, match="reason"):
        _payload(reason="")


# ── AX2: la regla que se muerde la cola ─────────────────────────────────


def test_ax2_desactivar_el_registro_de_overrides_es_un_override() -> None:
    """La regla dura del §10: apagar el propio registro no tiene excepción —
    se escribe ANTES, en el mismo `events` append-only. Este test es la
    diferencia entre que la regla exista en el freeze y que exista en el
    sistema."""
    # Arrange
    store = create_event_store()
    autorizador = _identidad(permisos={"override:apply:global"})

    # Act — el caller solo puede apagar el registro DESPUÉS de que esto
    # retorne, y para entonces el evento ya está escrito
    evento = apply_override(
        store,
        payload=_payload(
            target=OVERRIDE_LOG_TARGET,
            scope="global",
            reason="mantenimiento del almacenamiento del log, ventana declarada",
        ),
        authorizer=autorizador,
        domain_id=DOMINIO,
        stream_id="system:override",
    )

    # Assert — el apagón del registro quedó registrado
    assert evento.payload["target"] == OVERRIDE_LOG_TARGET
    assert store.read_stream("system:override")[0].type == OVERRIDE_APPLIED


def test_ax2_tampoco_hay_excepcion_de_permiso_para_apagar_el_registro() -> None:
    """Si el caso del registro tuviera un camino más fácil que los demás,
    sería EL camino."""
    store = create_event_store()
    sin_permiso = _identidad(permisos=set())

    with pytest.raises(OverrideNotAuthorizedError):
        apply_override(
            store,
            payload=_payload(target=OVERRIDE_LOG_TARGET, scope="global"),
            authorizer=sin_permiso,
            domain_id=DOMINIO,
            stream_id="system:override",
        )
    assert store.read_stream("system:override") == ()


def test_el_permiso_se_nombra_en_un_solo_lugar() -> None:
    assert required_permission("domain") == "override:apply:domain"
