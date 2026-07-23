"""Ensamblador del Bundle desde un run VIVO — el certificado deja el script.

El flujo completo del golden path (freeze §15.4 P0-1) como test: run real
(loop + costura) → eventos en el EventStore → `assemble_bundle` proyecta el
certificado DEL stream → `check_bundle` 7/7 offline. El oráculo es el checker
real — el ensamblador no se auto-declara correcto.

Honestidad de patas: la pata formal es el ExactSolverVerifier REAL; la pata
execution es un DOBLE etiquetado (la real es pandapower — spec trust/12,
siguiente eslabón). Con solo la pata formal, la policy default DEBE fallar el
punto 7 (2 patas exigidas) — ese fallo es el sistema funcionando, y se
prueba. El certificado de refutación (titular AL0, verdict refuted) también
verifica 7/7: refutar es un veredicto de primera clase, no un error.
"""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from blite.certificate.assemble import (
    AssembleError,
    ConclusionDeclaration,
    assemble_bundle,
)
from blite.certificate.bundle_check import check_bundle
from blite.events import create_event_store
from blite.events.event import Event
from blite.runtime.content_store import InMemoryContentStore
from blite.runtime.dispatch import ProfileDispatcher
from blite.runtime.loop import execute_run
from blite.runtime.registry import EntryPointRegistry
from blite.verification.anchor import AnchorKind
from blite.verification.attestation import Attestation, Verdict, VerifierClass
from blite.verification.claim import claim_view_digest
from blite.verification.context import InvocationContext
from blite.verification.evidence import (
    ExecutionCheck,
    ExecutionEnvironment,
    ExecutionPredicate,
)
from blite.verification.exact_solver import (
    ExactSolverVerifier,
    MaxCutInstance,
    OptimalityClaim,
)
from blite.verification.orchestrator import (
    ClaimDeclaration,
    make_verification_delegate,
)
from blite.verification.verifier import Determinism
from blite_capability.manifest import CapabilityManifest

REPO = Path(__file__).parents[3]
POLICY_BYTES = (
    REPO / "distributions" / "chimera" / "policies" / "verification-default.yaml"
).read_bytes()

ANCHOR_SOLVER = hashlib.sha256(b"anchor:cpsat-reference-v1").hexdigest()
ANCHOR_EXEC = hashlib.sha256(b"anchor:execution-double-v1").hexdigest()

STATEMENT = "la asignación propuesta es el corte máximo exacto"
SCOPE: dict[str, Any] = {"instancia": "k3-test"}

K3 = ((0, 1, 1), (1, 2, 1), (0, 2, 1))

ANCHOR_DESCRIPTORS = (
    {
        "anchor_digest": ANCHOR_SOLVER,
        "kind": "solver",
        "provenance": "cpsat-reference-v1",
    },
    {
        "anchor_digest": ANCHOR_EXEC,
        "kind": "execution",
        "provenance": "execution-double-v1",
    },
)


class _ExecutionDouble:
    """DOBLE de la pata execution (etiquetado): emite una Attestation real de
    clase execution con el verdict configurado. La pata honesta es pandapower
    (spec trust/12) — este doble existe para probar el ENSAMBLADOR, no para
    fingir verificación eléctrica."""

    verifier_class: VerifierClass = "execution"
    anchor_kind: AnchorKind = "execution"
    determinism: Determinism = "deterministic"

    def __init__(self, verdict: Verdict = "pass") -> None:
        self._verdict: Verdict = verdict

    def verify(self, claim: Any, ctx: InvocationContext) -> Attestation:
        assert isinstance(claim, OptimalityClaim)
        return Attestation(
            verifier_id="verifier:execution-double",
            verifier_class="execution",
            anchor_kind="execution",
            level="AL3",
            verdict=self._verdict,
            scope=claim.scope,
            independence_group="leg-execution",
            run_id=ctx.run_id,
            claim_digest=claim_view_digest(claim.canonical_statement, claim.scope),
            verifier_binary_digest=hashlib.sha256(b"execution-double-0").hexdigest(),
            verifier_params_digest=hashlib.sha256(b"execution-double-p").hexdigest(),
            anchor_digest=ANCHOR_EXEC,
            predicate=ExecutionPredicate(
                harness="double-harness",
                input_digest=hashlib.sha256(b"double-input").hexdigest(),
                checks=(ExecutionCheck(name="double-check", passed=True),),
                runtime_ms=0.1,
                environment=ExecutionEnvironment(package="test-double", version="0"),
            ),
            issued_at=datetime.now(UTC),
        )


class _EchoCapability:
    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id="cap.echo",
            description="generic test capability",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return {"echoed": inputs["x"]}


def _cpsat() -> ExactSolverVerifier:
    return ExactSolverVerifier(
        verifier_id="verifier:cpsat-differential",
        independence_group="leg-formal",
        anchor_digest=ANCHOR_SOLVER,
    )


def _run_stream(
    verifiers: tuple[Any, ...], assignment: tuple[int, ...] = (0, 0, 1)
) -> tuple[Event, ...]:
    """Un run REAL de punta a punta; retorna su stream del EventStore."""
    claim = OptimalityClaim(
        instance=MaxCutInstance(n_nodes=3, edges=K3),
        assignment=assignment,
        canonical_statement=STATEMENT,
        scope=SCOPE,
    )
    delegate = make_verification_delegate(
        verifiers=verifiers,
        declarations=(
            ClaimDeclaration(
                claim=claim,
                canonical_statement=STATEMENT,
                scope=SCOPE,
                claim_type="solution",
                is_conclusion=True,
            ),
        ),
    )
    store = create_event_store()
    execute_run(
        store,
        EntryPointRegistry({"cap.echo": _EchoCapability()}),
        ProfileDispatcher(),
        InMemoryContentStore(),
        run_id="run-cert",
        actor_id="user:dylan",
        domain_id="domain-a",
        max_steps=8,
        policy_digest=hashlib.sha256(POLICY_BYTES).hexdigest(),
        capability_id="cap.echo",
        inputs={"x": 21},
        post_invoke=delegate,
    )
    return store.read_stream("run-cert")


def _assemble(stream: tuple[Event, ...]) -> dict[str, Any]:
    return assemble_bundle(
        stream=stream,
        conclusions=(
            ConclusionDeclaration(
                canonical_statement=STATEMENT, scope=SCOPE, claim_type="solution"
            ),
        ),
        policy_yaml=POLICY_BYTES,
        signing_key=ed25519.Ed25519PrivateKey.generate(),
        keyid="certificate:test",
        anchor_descriptors=ANCHOR_DESCRIPTORS,
        deliverables=(("partition.json", b'{"assignment":[0,0,1]}\n'),),
    )


def _predicate_of(bundle: dict[str, Any]) -> dict[str, Any]:
    payload = base64.b64decode(bundle["envelope"]["payload"])
    statement: dict[str, Any] = json.loads(payload)
    return statement["predicate"]


class TestGoldenPath:
    def test_run_real_con_dos_patas_da_7_de_7(self) -> None:
        stream = _run_stream((_cpsat(), _ExecutionDouble()))

        bundle = _assemble(stream)
        results = check_bundle(bundle)

        assert all(r.ok for r in results), [
            (r.number, r.failures) for r in results if not r.ok
        ]
        predicate = _predicate_of(bundle)
        assert predicate["titular_level"] == "AL3"
        assert predicate["conclusions"][0]["verdict"] == "verified"
        assert len(predicate["attestations"]) == 2

    def test_certificado_de_refutacion_verifica_7_de_7_con_titular_al0(
        self,
    ) -> None:
        # El artefacto estrella del demo: la propuesta subóptima produce un
        # certificado FIRMADO de refutación — verificable offline igual que
        # un pass. Refutar es un veredicto de primera clase.
        stream = _run_stream(
            (_cpsat(), _ExecutionDouble(verdict="fail")), assignment=(0, 0, 0)
        )

        bundle = _assemble(stream)
        results = check_bundle(bundle)

        assert all(r.ok for r in results), [
            (r.number, r.failures) for r in results if not r.ok
        ]
        predicate = _predicate_of(bundle)
        assert predicate["conclusions"][0]["verdict"] == "refuted"
        assert predicate["titular_level"] == "AL0"

    def test_solo_pata_formal_falla_el_punto_7_bajo_la_policy_default(self) -> None:
        # No es un bug: es la Policy exigiendo independencia. Con una sola
        # pata (formal) el checker DEBE rechazar — el sistema funcionando.
        stream = _run_stream((_cpsat(),))

        bundle = _assemble(stream)
        results = check_bundle(bundle)

        for r in results[:6]:
            assert r.ok, (r.number, r.failures)
        punto_7 = results[6]
        assert not punto_7.ok
        assert any("pata" in f for f in punto_7.failures)
        assert any("execution" in f for f in punto_7.failures)


class TestFailClosed:
    def test_stream_adulterado_rompe_el_punto_2(self) -> None:
        stream = _run_stream((_cpsat(), _ExecutionDouble()))
        bundle = _assemble(stream)

        bundle["stream"][2]["payload"] = {"tampered": True}

        punto_2 = check_bundle(bundle)[1]
        assert not punto_2.ok

    def test_declaracion_sin_claim_en_el_stream_levanta(self) -> None:
        stream = _run_stream((_cpsat(), _ExecutionDouble()))

        with pytest.raises(AssembleError):
            assemble_bundle(
                stream=stream,
                conclusions=(
                    ConclusionDeclaration(
                        canonical_statement="otro claim que el run jamás emitió",
                        scope={"instancia": "fantasma"},
                        claim_type="solution",
                    ),
                ),
                policy_yaml=POLICY_BYTES,
                signing_key=ed25519.Ed25519PrivateKey.generate(),
                keyid="certificate:test",
                anchor_descriptors=ANCHOR_DESCRIPTORS,
            )

    def test_stream_sin_terminal_levanta(self) -> None:
        stream = _run_stream((_cpsat(), _ExecutionDouble()))

        with pytest.raises(AssembleError):
            assemble_bundle(
                stream=stream[:-1],
                conclusions=(
                    ConclusionDeclaration(
                        canonical_statement=STATEMENT,
                        scope=SCOPE,
                        claim_type="solution",
                    ),
                ),
                policy_yaml=POLICY_BYTES,
                signing_key=ed25519.Ed25519PrivateKey.generate(),
                keyid="certificate:test",
                anchor_descriptors=ANCHOR_DESCRIPTORS,
            )
