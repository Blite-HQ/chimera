"""Sub-runs — A4 (docs/specs/harness-agentico.md §Contrato-4, freeze §13).

Contrato bajo prueba: `spawn_sub_run` corre un hijo con `parent_run_id` tras
comprobar la herencia FAIL-CLOSED de `policy_digest` (regla 3);
`contribute_sub_run_claims` aporta los `claim.emitted` del sub-run al stream
del RAÍZ con `sub_run_id` (correlaciona) + `sub_run_provenance_hash`
(encadena) estampados (regla 2); `cancel_run_with_cascade` cancela un run y
cascada `run.cancelled {reason: "parent_cancelled"}` a cada sub-run DIRECTO
activo, saltando los ya terminales (regla 1) — y el rechazo de appends
post-terminales a un sub-run ya cancelado lo sigue garantizando el
`EventStore` (freeze §2), no este módulo.
"""

from __future__ import annotations

from typing import Any

import pytest

from blite.events import create_event_store
from blite.events.rules import PostTerminalAppendError
from blite.runtime.content_store import InMemoryContentStore
from blite.runtime.dispatch import ProfileDispatcher
from blite.runtime.projection import project_runs
from blite.runtime.registry import EntryPointRegistry
from blite.runtime.subrun import (
    PARENT_CANCELLED_REASON,
    PolicyInheritanceError,
    cancel_run_with_cascade,
    compute_sub_run_provenance_hash,
    contribute_sub_run_claims,
    spawn_sub_run,
)
from blite_capability.manifest import CapabilityManifest

_ROOT_POLICY = "pol-digest-root"
_DOMAIN = "domain-a"


class _EchoCapability:
    """Doble genérico (ADR-029), mismo patrón que test_agentic_loop.py."""

    def __init__(self, capability_id: str = "cap.echo") -> None:
        self._id = capability_id

    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id=self._id,
            description="generic test capability",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return {"doubled": inputs["x"] * 2}


class _ExplodingCapability:
    """Doble que SIEMPRE falla — para forzar un sub-run `failed`."""

    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id="cap.boom",
            description="always fails",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        msg = "boom"
        raise RuntimeError(msg)


def _registry(*capabilities: Any) -> EntryPointRegistry:
    return EntryPointRegistry({cap.manifest.id: cap for cap in capabilities})


def _make_root(store: Any, *, run_id: str = "run-root") -> None:
    """Simula un run raíz ya en `running` — directo al store, sin pasar por
    `execute_run` (estos tests ejercitan `subrun.py` de forma aislada, no el
    loop completo — mismo patrón que otros tests unitarios de proyección)."""
    store.append(
        stream_id=run_id,
        type="run.created",
        actor_id="user:steven",
        domain_id=_DOMAIN,
        payload={
            "run_id": run_id,
            "actor_id": "user:steven",
            "domain_id": _DOMAIN,
            "max_steps": 64,
            "policy_digest": _ROOT_POLICY,
        },
    )
    store.append(
        stream_id=run_id,
        type="run.started",
        actor_id="service:runtime",
        domain_id=_DOMAIN,
        payload={},
    )


def _claim_payload(*, claim_digest: str, claim_type: str = "solution") -> dict[str, Any]:
    """Payload crudo de `claim.emitted` — construido a mano (sin importar
    `blite.verification`, mismo espíritu de aislamiento que `subrun.py`) con
    exactamente los portadores que `ClaimEmittedPayload` exige."""
    return {
        "claim_digest": claim_digest,
        "claim_type": claim_type,
        "is_conclusion": True,
        "world": False,
        "irreversible": False,
        "affects_third_party": False,
        "sub_run_provenance_hash": None,
        "sub_run_id": None,
    }


class TestSpawnSubRun:
    def test_spawns_child_run_with_parent_run_id_and_inherited_policy(self) -> None:
        store = create_event_store()
        _make_root(store)

        row = spawn_sub_run(
            store,
            _registry(_EchoCapability()),
            ProfileDispatcher(),
            InMemoryContentStore(),
            parent_run_id="run-root",
            parent_policy_digest=_ROOT_POLICY,
            sub_run_id="run-sub-1",
            actor_id="user:steven",
            domain_id=_DOMAIN,
            max_steps=8,
            capability_id="cap.echo",
            inputs={"x": 3},
        )

        assert row.status == "completed"
        assert row.parent_run_id == "run-root"
        assert row.policy_digest == _ROOT_POLICY

    def test_explicit_policy_digest_matching_parent_is_allowed(self) -> None:
        store = create_event_store()
        _make_root(store)

        row = spawn_sub_run(
            store,
            _registry(_EchoCapability()),
            ProfileDispatcher(),
            InMemoryContentStore(),
            parent_run_id="run-root",
            parent_policy_digest=_ROOT_POLICY,
            sub_run_id="run-sub-2",
            actor_id="user:steven",
            domain_id=_DOMAIN,
            max_steps=8,
            capability_id="cap.echo",
            inputs={"x": 3},
            policy_digest=_ROOT_POLICY,
        )

        assert row.policy_digest == _ROOT_POLICY

    def test_diverging_policy_digest_is_rejected_fail_closed_before_any_event(
        self,
    ) -> None:
        store = create_event_store()
        _make_root(store)

        with pytest.raises(PolicyInheritanceError):
            spawn_sub_run(
                store,
                _registry(_EchoCapability()),
                ProfileDispatcher(),
                InMemoryContentStore(),
                parent_run_id="run-root",
                parent_policy_digest=_ROOT_POLICY,
                sub_run_id="run-sub-3",
                actor_id="user:steven",
                domain_id=_DOMAIN,
                max_steps=8,
                capability_id="cap.echo",
                inputs={"x": 3},
                policy_digest="pol-digest-weaker",
            )

        # Fail-closed de verdad: ni el run.created del sub-run se escribió.
        assert store.read_stream("run-sub-3") == ()


class TestContributeSubRunClaims:
    def test_emits_claim_emitted_on_root_with_sub_run_id_and_hash(self) -> None:
        store = create_event_store()
        _make_root(store)
        digest = "c" * 64

        def _post_invoke(ctx: Any, append: Any) -> bool:
            append("claim.emitted", _claim_payload(claim_digest=digest))
            return True

        spawn_sub_run(
            store,
            _registry(_EchoCapability()),
            ProfileDispatcher(),
            InMemoryContentStore(),
            parent_run_id="run-root",
            parent_policy_digest=_ROOT_POLICY,
            sub_run_id="run-sub-4",
            actor_id="user:steven",
            domain_id=_DOMAIN,
            max_steps=8,
            capability_id="cap.echo",
            inputs={"x": 3},
            post_invoke=_post_invoke,
        )

        expected_hash = compute_sub_run_provenance_hash(store.read_stream("run-sub-4"))
        returned_hash = contribute_sub_run_claims(
            store, root_run_id="run-root", sub_run_id="run-sub-4", domain_id=_DOMAIN
        )
        assert returned_hash == expected_hash
        assert len(expected_hash) == 64

        root_claims = [
            e for e in store.read_stream("run-root") if e.type == "claim.emitted"
        ]
        assert len(root_claims) == 1
        assert root_claims[0].payload["claim_digest"] == digest
        assert root_claims[0].payload["sub_run_id"] == "run-sub-4"
        assert root_claims[0].payload["sub_run_provenance_hash"] == expected_hash

    def test_contributes_every_claim_the_sub_run_emitted(self) -> None:
        store = create_event_store()
        _make_root(store)
        digest_a, digest_b = "a" * 64, "b" * 64

        def _post_invoke(ctx: Any, append: Any) -> bool:
            append("claim.emitted", _claim_payload(claim_digest=digest_a))
            append("claim.emitted", _claim_payload(claim_digest=digest_b))
            return True

        spawn_sub_run(
            store,
            _registry(_EchoCapability()),
            ProfileDispatcher(),
            InMemoryContentStore(),
            parent_run_id="run-root",
            parent_policy_digest=_ROOT_POLICY,
            sub_run_id="run-sub-5",
            actor_id="user:steven",
            domain_id=_DOMAIN,
            max_steps=8,
            capability_id="cap.echo",
            inputs={"x": 3},
            post_invoke=_post_invoke,
        )

        contribute_sub_run_claims(
            store, root_run_id="run-root", sub_run_id="run-sub-5", domain_id=_DOMAIN
        )

        root_digests = {
            e.payload["claim_digest"]
            for e in store.read_stream("run-root")
            if e.type == "claim.emitted"
        }
        assert root_digests == {digest_a, digest_b}

    def test_rejects_contribution_from_a_non_completed_sub_run(self) -> None:
        store = create_event_store()
        _make_root(store)

        spawn_sub_run(
            store,
            _registry(_ExplodingCapability()),
            ProfileDispatcher(),
            InMemoryContentStore(),
            parent_run_id="run-root",
            parent_policy_digest=_ROOT_POLICY,
            sub_run_id="run-sub-6",
            actor_id="user:steven",
            domain_id=_DOMAIN,
            max_steps=8,
            capability_id="cap.boom",
            inputs={"x": 3},
        )

        assert project_runs(store.read_all())["run-sub-6"].status == "failed"

        with pytest.raises(ValueError, match="completed"):
            contribute_sub_run_claims(
                store, root_run_id="run-root", sub_run_id="run-sub-6", domain_id=_DOMAIN
            )

        assert [e for e in store.read_stream("run-root") if e.type == "claim.emitted"] == []


class TestCancelRunWithCascade:
    def test_cascades_parent_cancelled_to_active_sub_runs_and_skips_terminal_ones(
        self,
    ) -> None:
        store = create_event_store()
        _make_root(store)
        # sub-run activo: created + started, sin terminal.
        store.append(
            stream_id="run-sub-active",
            type="run.created",
            actor_id="service:runtime",
            domain_id=_DOMAIN,
            payload={
                "run_id": "run-sub-active",
                "actor_id": "service:runtime",
                "domain_id": _DOMAIN,
                "max_steps": 8,
                "policy_digest": _ROOT_POLICY,
                "parent_run_id": "run-root",
            },
        )
        store.append(
            stream_id="run-sub-active",
            type="run.started",
            actor_id="service:runtime",
            domain_id=_DOMAIN,
            payload={},
        )
        # sub-run ya terminal (completed) — no debe recibir nada.
        store.append(
            stream_id="run-sub-done",
            type="run.created",
            actor_id="service:runtime",
            domain_id=_DOMAIN,
            payload={
                "run_id": "run-sub-done",
                "actor_id": "service:runtime",
                "domain_id": _DOMAIN,
                "max_steps": 8,
                "policy_digest": _ROOT_POLICY,
                "parent_run_id": "run-root",
            },
        )
        store.append(
            stream_id="run-sub-done",
            type="run.completed",
            actor_id="service:runtime",
            domain_id=_DOMAIN,
            payload={"output_digest": "deadbeef"},
        )
        done_events_before = store.read_stream("run-sub-done")

        cancelled = cancel_run_with_cascade(
            store, run_id="run-root", domain_id=_DOMAIN, reason="user_requested"
        )

        assert cancelled == ("run-root", "run-sub-active")

        root_events = store.read_stream("run-root")
        assert root_events[-1].type == "run.cancelled"
        assert root_events[-1].payload["reason"] == "user_requested"

        active_events = store.read_stream("run-sub-active")
        assert active_events[-1].type == "run.cancelled"
        assert active_events[-1].payload["reason"] == PARENT_CANCELLED_REASON

        # El sub-run ya terminal no ganó ningún evento nuevo.
        assert store.read_stream("run-sub-done") == done_events_before

    def test_noop_on_already_terminal_root_still_cascades_to_active_children(
        self,
    ) -> None:
        store = create_event_store()
        _make_root(store)
        store.append(
            stream_id="run-root",
            type="run.completed",
            actor_id="service:runtime",
            domain_id=_DOMAIN,
            payload={"output_digest": "cafe"},
        )
        store.append(
            stream_id="run-sub-active",
            type="run.created",
            actor_id="service:runtime",
            domain_id=_DOMAIN,
            payload={
                "run_id": "run-sub-active",
                "actor_id": "service:runtime",
                "domain_id": _DOMAIN,
                "max_steps": 8,
                "policy_digest": _ROOT_POLICY,
                "parent_run_id": "run-root",
            },
        )
        store.append(
            stream_id="run-sub-active",
            type="run.started",
            actor_id="service:runtime",
            domain_id=_DOMAIN,
            payload={},
        )
        root_events_before = store.read_stream("run-root")

        cancelled = cancel_run_with_cascade(
            store, run_id="run-root", domain_id=_DOMAIN, reason="user_requested"
        )

        assert cancelled == ("run-sub-active",)
        # El raíz, ya terminal, NO gana un segundo evento terminal.
        assert store.read_stream("run-root") == root_events_before

    def test_late_step_append_to_a_cascaded_sub_run_is_rejected_post_terminal(
        self,
    ) -> None:
        store = create_event_store()
        _make_root(store)
        store.append(
            stream_id="run-sub-active",
            type="run.created",
            actor_id="service:runtime",
            domain_id=_DOMAIN,
            payload={
                "run_id": "run-sub-active",
                "actor_id": "service:runtime",
                "domain_id": _DOMAIN,
                "max_steps": 8,
                "policy_digest": _ROOT_POLICY,
                "parent_run_id": "run-root",
            },
        )
        store.append(
            stream_id="run-sub-active",
            type="run.started",
            actor_id="service:runtime",
            domain_id=_DOMAIN,
            payload={},
        )

        cancel_run_with_cascade(
            store, run_id="run-root", domain_id=_DOMAIN, reason="user_requested"
        )

        # Un job en vuelo que aún no había reportado su resultado no puede
        # apendear tras la cancelación — la garantía DURA del rechazo
        # post-terminal (freeze §2), aquí compuesta con la cascada de §13.
        with pytest.raises(PostTerminalAppendError):
            store.append(
                stream_id="run-sub-active",
                type="run.step.completed",
                actor_id="service:runtime",
                domain_id=_DOMAIN,
                payload={
                    "step_id": "step-99",
                    "run_id": "run-sub-active",
                    "kind": "invoke",
                    "input_digest": "d" * 64,
                    "status": "completed",
                },
            )
