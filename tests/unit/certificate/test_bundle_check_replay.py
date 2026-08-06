"""Punto 8 del checklist (`docs/specs/harness-agentico.md` §Contrato-5): un
`replay.divergence` en el stream tumba el bundle SIN IMPORTAR que la firma
DSSE (punto 1) y el resto del checklist (puntos 2-7) verifiquen — R1: "el
certificado DSSE verifica ⟺ el replay fue fiel".

El bundle se ENSAMBLA de un run real (`execute_run` → `assemble_bundle`,
mismo patrón que `test_assemble.py`) — nunca se fabrica el JSON a mano: así
la firma y el `provenance_hash` son genuinamente válidos, y el test prueba
que punto 8 es el ÚNICO que cacha la divergencia.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric import ed25519

from blite.certificate.assemble import assemble_bundle
from blite.certificate.bundle_check import check_bundle
from blite.certificate.keys import LocalKeyProvider
from blite.events import create_event_store
from blite.events.event import Event
from blite.runtime.content_store import InMemoryContentStore
from blite.runtime.dispatch import ProfileDispatcher
from blite.runtime.loop import execute_run
from blite.runtime.registry import EntryPointRegistry
from blite_capability.manifest import CapabilityManifest

REPO = Path(__file__).resolve().parents[3]
POLICY_BYTES = (
    REPO / "distributions" / "chimera" / "policies" / "verification-default.yaml"
).read_bytes()


class _EchoCapability:
    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id="cap.echo",
            description="test capability",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            side_effects="pure",
            required_permission="capability:invoke",
            interaction="request_response",
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return {"echoed": inputs["x"]}


def _run_stream() -> tuple[Event, ...]:
    """Un run real y mínimo — sin verificación (cero conclusiones
    declaradas), así los puntos 3-7 pasan trivialmente y el test se enfoca
    exclusivamente en el punto 8."""
    store = create_event_store()
    execute_run(
        store,
        EntryPointRegistry({"cap.echo": _EchoCapability()}),
        ProfileDispatcher(),
        InMemoryContentStore(),
        run_id="run-replay-check",
        actor_id="user:dylan",
        domain_id="domain-a",
        max_steps=8,
        policy_digest="pol-digest-1",
        capability_id="cap.echo",
        inputs={"x": 21},
    )
    return store.read_stream("run-replay-check")


def _with_divergence_before_terminal(stream: tuple[Event, ...]) -> tuple[Event, ...]:
    """Inserta un `replay.divergence` ANTES del terminal — el corte del
    provenance_hash (freeze §2) sigue cerrando en el terminal, INCLUSIVE, así
    que la firma/hash de `assemble_bundle` sobre este stream siguen siendo
    genuinamente válidos (puntos 1-2 OK); solo punto 8 debe reprobar."""
    events = list(stream)
    terminal = events[-1]
    divergence = Event(
        id=uuid4(),
        stream_id=terminal.stream_id,
        seq=terminal.seq,  # renumerado abajo — 1..n estricto (punto 2)
        global_seq=terminal.global_seq,
        type="replay.divergence",
        actor_id="service:runtime",
        domain_id=terminal.domain_id,
        payload={
            "run_id": terminal.stream_id,
            "effect_kind": "capability_job",
            "request_digest": "a" * 64,
            "expected_response_digest": "b" * 64,
            "actual_response_digest": "c" * 64,
        },
        occurred_at=terminal.occurred_at,
    )
    reordered = [*events[:-1], divergence, terminal]
    return tuple(
        e.model_copy(update={"seq": i}) for i, e in enumerate(reordered, start=1)
    )


def _assemble(stream: tuple[Event, ...]) -> dict[str, Any]:
    return assemble_bundle(
        stream=stream,
        conclusions=(),
        policy_yaml=POLICY_BYTES,
        key_provider=LocalKeyProvider(ed25519.Ed25519PrivateKey.generate()),
    )


def test_a_clean_stream_passes_point_8() -> None:
    bundle = _assemble(_run_stream())

    results = check_bundle(bundle)

    # El punto 8 es el que este archivo cuida; el checklist creció a 10 con
    # C5 (sub-runs y hash-chain) y el total no se escribe a mano.
    assert results[7].number == 8
    assert all(r.ok for r in results), [(r.number, r.failures) for r in results]


def test_a_replay_divergence_event_fails_point_8_even_with_valid_signature_and_hash() -> (
    None
):
    stream = _with_divergence_before_terminal(_run_stream())
    bundle = _assemble(stream)

    results = check_bundle(bundle)

    # Puntos 1-7 siguen OK: la firma es válida y el provenance_hash se
    # recomputó sobre el MISMO stream (con el evento ya insertado) — el
    # bundle es, en todo sentido criptográfico, legítimo.
    for r in results[:7]:
        assert r.ok, (r.number, r.failures)

    punto_8 = results[7]
    assert punto_8.number == 8
    assert not punto_8.ok
    assert "replay.divergence" in punto_8.failures[0]
