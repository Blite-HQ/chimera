"""Registro de confianza — `●VerifierRegistered`/`●AnchorRegistered` sobre el
stream `system:trust-registry` (freeze §2 [S-F·N2] + §14). Cierre del ítem
C3/M3: «registro en trust-registry».

Por qué existe: el punto 5 del checklist exige que todo `pass` traiga un
`anchor_digest` **que resuelva contra un descriptor empaquetado en el
Bundle** (SF-P0-1 — sin eso, un `pass` con ancla fabricada pasaba). Hasta
hoy esos descriptores se escribían a mano en el generador del bundle: el
Bundle afirmaba anclas que ningún registro respaldaba. El registro los
convierte en proyección de eventos — la misma doctrina que todo lo demás
(«si no está en el log, no entra al certificado»).
"""

from __future__ import annotations

import hashlib

import pytest

from blite.events import create_event_store
from blite.verification.rule import RuleVerifier
from blite.verification.rule_set import RuleSet
from blite.verification.rule_z3 import Z3RuleBackend
from blite.verification.trust_registry import (
    ANCHOR_REGISTERED,
    TRUST_REGISTRY_STREAM,
    VERIFIER_REGISTERED,
    anchor_descriptors,
    register_anchor,
    register_rule_set,
    register_verifier,
    verifier_descriptors,
)

SOURCE = b"""; rule-set-id: registro-rules@0.1.0
(declare-fun quantity () Int)
(assert (! (>= quantity 2) :named at_least_two))
"""


def _verifier() -> RuleVerifier:
    return RuleVerifier(
        verifier_id="z3-rules",
        independence_group="leg-rule",
        rule_set=RuleSet.parse(SOURCE),
        backend=Z3RuleBackend(),
    )


def test_registrar_un_verificador_escribe_en_el_stream_de_sistema() -> None:
    """Los eventos sin run viven en `system:<componente>` y JAMÁS entran al
    `provenance_hash` (freeze §2) — registrar un verificador no puede
    cambiar los bytes del stream de ningún run."""
    # Arrange
    store = create_event_store()
    verificador = _verifier()

    # Act
    register_verifier(store, verificador)

    # Assert
    (event,) = store.read_stream(TRUST_REGISTRY_STREAM)
    assert event.type == VERIFIER_REGISTERED
    assert event.actor_id.startswith("service:")
    assert event.payload["verifier_id"] == "z3-rules"
    assert event.payload["verifier_class"] == "property_rule"
    assert event.payload["binary_digest"] == verificador.verifier_binary_digest
    assert event.payload["params_digest"] == verificador.verifier_params_digest


def test_registrar_un_rule_set_lo_ancla_por_su_digest_de_artefacto() -> None:
    """El ancla del `RuleVerifier` ES el artefacto de reglas: el descriptor
    dice contra QUÉ bytes se verificó, no «contra unas reglas»."""
    # Arrange
    store = create_event_store()
    rule_set = RuleSet.parse(SOURCE)

    # Act
    register_rule_set(store, rule_set)

    # Assert
    (event,) = store.read_stream(TRUST_REGISTRY_STREAM)
    assert event.type == ANCHOR_REGISTERED
    assert event.payload["anchor_digest"] == rule_set.rule_digest
    assert event.payload["kind"] == "rule"
    assert event.payload["provenance"] == "registro-rules@0.1.0"


def test_los_descriptores_del_bundle_salen_del_log_no_de_la_mano() -> None:
    """La forma exacta que el punto 5 del checklist resuelve
    (`anchor_descriptors` del Bundle)."""
    # Arrange
    store = create_event_store()
    rule_set = RuleSet.parse(SOURCE)
    otro = hashlib.sha256(b"anchor:corpus-x").hexdigest()

    # Act
    register_rule_set(store, rule_set)
    register_anchor(store, anchor_digest=otro, kind="dataset", provenance="corpus-x@v1")
    register_verifier(store, _verifier())

    # Assert — en orden de registro (determinista, no un set al azar)
    assert anchor_descriptors(store) == (
        {
            "anchor_digest": rule_set.rule_digest,
            "kind": "rule",
            "provenance": "registro-rules@0.1.0",
        },
        {
            "anchor_digest": otro,
            "kind": "dataset",
            "provenance": "corpus-x@v1",
        },
    )
    assert verifier_descriptors(store) == (
        {
            "verifier_id": "z3-rules",
            "binary_digest": _verifier().verifier_binary_digest,
        },
    )


def test_registrar_dos_veces_el_mismo_digest_no_duplica_el_descriptor() -> None:
    """El log es append-only (se registra dos veces y ambos eventos quedan),
    pero la PROYECCIÓN es un conjunto: un descriptor duplicado en el Bundle
    no aporta nada y ensucia lo que un auditor tiene que leer."""
    # Arrange
    store = create_event_store()
    rule_set = RuleSet.parse(SOURCE)

    # Act
    register_rule_set(store, rule_set)
    register_rule_set(store, rule_set)

    # Assert
    assert len(store.read_stream(TRUST_REGISTRY_STREAM)) == 2
    assert len(anchor_descriptors(store)) == 1


def test_un_ancla_con_digest_que_no_es_sha256_no_se_registra() -> None:
    """Fail-closed en la frontera: un `anchor_digest` mal formado convierte
    el punto 5 en un chequeo de igualdad de basura contra basura."""
    store = create_event_store()

    with pytest.raises(ValueError, match="sha256"):
        register_anchor(
            store, anchor_digest="no-es-un-digest", kind="rule", provenance="x"
        )


def test_el_registro_ignora_eventos_de_otros_streams() -> None:
    """La proyección lee SOLO su stream de sistema — un evento homónimo en
    el stream de un run no puede inyectar un descriptor."""
    # Arrange
    store = create_event_store()
    register_rule_set(store, RuleSet.parse(SOURCE))
    store.append(
        stream_id="run-impostor",
        type=ANCHOR_REGISTERED,
        actor_id="user:atacante",
        domain_id="d-default",
        payload={
            "anchor_digest": hashlib.sha256(b"falsa").hexdigest(),
            "kind": "rule",
            "provenance": "inyectada",
        },
    )

    # Assert
    assert [d["provenance"] for d in anchor_descriptors(store)] == [
        "registro-rules@0.1.0"
    ]
