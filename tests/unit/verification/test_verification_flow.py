"""La costura loop↔verificación — los eventos de verificación nacen del run.

Freeze §3/§6 + orden canónico del bundle (gen-example-bundle): los eventos
`claim.emitted` y `verification.completed` aterrizan DESPUÉS del step de
invocación y ANTES del terminal — si cayeran post-terminal quedarían fuera
del corte de procedencia y el certificado no los ampararía. El loop NO
verifica (INV-2): ofrece la costura `post_invoke` y el orquestador de
`blite.verification` es quien emite. Error de proceso del verificador ⇒
`run.failed` fail-loud, jamás un verdict disfrazado.
"""

from __future__ import annotations

import hashlib
from typing import Any

import pytest

from blite.events import create_event_store
from blite.events.rules import provenance_slice
from blite.events.store import EventStore
from blite.runtime.content_store import InMemoryContentStore
from blite.runtime.dispatch import ProfileDispatcher
from blite.runtime.loop import execute_run
from blite.runtime.registry import EntryPointRegistry
from blite.verification.anchor import AnchorKind
from blite.verification.attestation import Attestation, VerifierClass
from blite.verification.claim import claim_view_digest
from blite.verification.context import InvocationContext
from blite.verification.exact_solver import (
    ExactSolverVerifier,
    MaxCutInstance,
    OptimalityClaim,
    VerificationProcessError,
)
from blite.verification.orchestrator import (
    ClaimDeclaration,
    make_verification_delegate,
)
from blite.verification.verifier import Determinism
from blite_capability.manifest import CapabilityManifest

ANCHOR_DIGEST = hashlib.sha256(b"anchor:cpsat-reference-v1").hexdigest()

K3 = ((0, 1, 1), (1, 2, 1), (0, 2, 1))


def _claim(assignment: tuple[int, ...] = (0, 0, 1)) -> OptimalityClaim:
    return OptimalityClaim(
        instance=MaxCutInstance(n_nodes=3, edges=K3),
        assignment=assignment,
        canonical_statement="la asignación propuesta es el corte máximo exacto",
        scope={"instancia": "k3-test"},
    )


def _declaration(claim: OptimalityClaim) -> ClaimDeclaration:
    return ClaimDeclaration(
        claim=claim,
        canonical_statement=claim.canonical_statement,
        scope=claim.scope,
        claim_type="solution",
        is_conclusion=True,
    )


def _verifier() -> ExactSolverVerifier:
    return ExactSolverVerifier(
        verifier_id="verifier:cpsat-differential",
        independence_group="leg-formal",
        anchor_digest=ANCHOR_DIGEST,
    )


class _ExplodingVerifier:
    """Doble del puerto Verifier cuyo proceso SIEMPRE falla (error ≠ fail)."""

    verifier_class: VerifierClass = "formal_exact"
    anchor_kind: AnchorKind = "solver"
    determinism: Determinism = "deterministic"

    def verify(self, claim: Any, ctx: InvocationContext) -> Attestation:
        msg = "proceso de verificación roto a propósito"
        raise VerificationProcessError(msg)


class _EchoCapability:
    """Doble genérico (ADR-029) — el mismo patrón del test del loop."""

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


def _run_with_delegate(delegate: Any) -> EventStore:
    store = create_event_store()
    execute_run(
        store,
        EntryPointRegistry({"cap.echo": _EchoCapability()}),
        ProfileDispatcher(),
        InMemoryContentStore(),
        run_id="run-vf",
        actor_id="user:dylan",
        domain_id="domain-a",
        max_steps=8,
        policy_digest="pol-digest-1",
        capability_id="cap.echo",
        inputs={"x": 21},
        post_invoke=delegate,
    )
    return store


class TestDelegateUnit:
    """El delegate solo — emite en orden y con el binding correcto."""

    def test_emite_claim_y_attestation_en_orden(self) -> None:
        claim = _claim()
        delegate = make_verification_delegate(
            verifiers=(_verifier(),), declarations=(_declaration(claim),)
        )
        emitted: list[tuple[str, dict[str, Any]]] = []

        delegate_ctx = InvocationContext(
            run_id="run-vf", actor_id="service:runtime", domain_id="domain-a"
        )
        delegate(delegate_ctx, lambda t, p: emitted.append((t, p)))

        assert [t for t, _ in emitted] == ["claim.emitted", "verification.completed"]
        claim_payload = emitted[0][1]
        expected_digest = claim_view_digest(claim.canonical_statement, claim.scope)
        assert claim_payload["claim_digest"] == expected_digest
        assert claim_payload["claim_type"] == "solution"
        assert claim_payload["is_conclusion"] is True

    def test_verification_completed_porta_la_attestation_completa(self) -> None:
        claim = _claim()
        delegate = make_verification_delegate(
            verifiers=(_verifier(),), declarations=(_declaration(claim),)
        )
        emitted: list[tuple[str, dict[str, Any]]] = []

        delegate(
            InvocationContext(
                run_id="run-vf", actor_id="service:runtime", domain_id="domain-a"
            ),
            lambda t, p: emitted.append((t, p)),
        )

        payload = emitted[1][1]
        assert payload["verdict"] == "pass"
        assert payload["verifier_id"] == "verifier:cpsat-differential"
        # binding claim↔attestation: el mismo digest en ambos eventos
        assert payload["claim_digest"] == emitted[0][1]["claim_digest"]
        assert payload["attestation"]["level"] == "AL3"
        assert payload["attestation"]["independence_group"] == "leg-formal"

    def test_error_de_proceso_propaga_jamas_se_disfraza(self) -> None:
        delegate = make_verification_delegate(
            verifiers=(_ExplodingVerifier(),), declarations=(_declaration(_claim()),)
        )

        with pytest.raises(VerificationProcessError):
            delegate(
                InvocationContext(
                    run_id="run-vf", actor_id="service:runtime", domain_id="domain-a"
                ),
                lambda t, p: None,
            )


class TestCosturaConElLoop:
    """execute_run + delegate: los eventos aterrizan DENTRO de la procedencia."""

    def test_secuencia_completa_con_verificacion_antes_del_terminal(self) -> None:
        claim = _claim()
        delegate = make_verification_delegate(
            verifiers=(_verifier(),), declarations=(_declaration(claim),)
        )

        store = _run_with_delegate(delegate)

        types = [e.type for e in store.read_stream("run-vf")]
        assert types == [
            "run.created",
            "run.started",
            "run.step.started",
            "run.step.completed",
            "run.step.started",
            "capability.job.submitted",
            "capability.job.completed",
            "run.step.completed",
            "claim.emitted",
            "verification.completed",
            "run.completed",
        ]

    def test_los_eventos_de_verificacion_entran_al_corte_de_procedencia(
        self,
    ) -> None:
        delegate = make_verification_delegate(
            verifiers=(_verifier(),), declarations=(_declaration(_claim()),)
        )

        store = _run_with_delegate(delegate)

        sliced = provenance_slice(store.read_stream("run-vf"))
        sliced_types = {e.type for e in sliced}
        assert "claim.emitted" in sliced_types
        assert "verification.completed" in sliced_types

    def test_la_falla_sembrada_viaja_como_fail_en_el_log(self) -> None:
        # El demo en miniatura: la propuesta subóptima queda REFUTADA en el
        # rastro del run — el fail es un veredicto registrado, no un error.
        claim = _claim(assignment=(0, 0, 0))  # corte 0 vs óptimo 2
        delegate = make_verification_delegate(
            verifiers=(_verifier(),), declarations=(_declaration(claim),)
        )

        store = _run_with_delegate(delegate)

        events = store.read_stream("run-vf")
        verification = next(e for e in events if e.type == "verification.completed")
        assert verification.payload["verdict"] == "fail"
        assert [e.type for e in events][-1] == "run.completed"

    def test_error_de_proceso_del_verificador_corta_el_run(self) -> None:
        delegate = make_verification_delegate(
            verifiers=(_ExplodingVerifier(),), declarations=(_declaration(_claim()),)
        )

        store = _run_with_delegate(delegate)

        events = store.read_stream("run-vf")
        assert events[-1].type == "run.failed"
        assert events[-1].payload["error_kind"] == "VerificationProcessError"
        assert "run.completed" not in {e.type for e in events}


class TestDigestComun:
    def test_exact_solver_y_claim_view_digest_coinciden(self) -> None:
        # DRY con candado: el adapter y el helper común producen el MISMO
        # digest — si divergen, el binding claim↔attestation se rompe.
        from blite.verification.exact_solver import claim_digest_of

        claim = _claim()
        assert claim_digest_of(claim) == claim_view_digest(
            claim.canonical_statement, claim.scope
        )
