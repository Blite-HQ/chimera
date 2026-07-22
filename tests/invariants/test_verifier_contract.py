"""
Verifier contract tests — vocabulario §4 (clase + AL, la escalera murió).

INV-2/PR2 como gate de tipos: ni `AnchorKind` ni `VerifierClass` tienen el
valor "model" — no existe, no type-checkea, no valida. El Protocol exige
`verifier_class` + `determinism` + `verify()`.

Run: uv run pyright tests/invariants/test_verifier_contract.py
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, get_args

import pytest
from pydantic import ValidationError

from blite.verification.anchor import AnchorKind
from blite.verification.attestation import Attestation, VerifierClass
from blite.verification.context import InvocationContext
from blite.verification.evidence import Differential, FormalExactPredicate
from blite.verification.verifier import Determinism, Verifier

# ── AnchorKind ─────────────────────────────────────────────────────────────

_ALLOWED_ANCHOR_KINDS = {"solver", "execution", "dataset", "rule", "human"}


def test_anchor_kind_has_exactly_the_five_non_model_values() -> None:
    """AnchorKind = solver|execution|dataset|rule|human — 'model' has no value."""
    assert set(get_args(AnchorKind)) == _ALLOWED_ANCHOR_KINDS


# ── VerifierClass (freeze §4) ─────────────────────────────────────────────

_ALLOWED_CLASSES = {
    "formal_exact",
    "execution",
    "ground_truth",
    "property_rule",
    "consensus_replication",
    "human_expert",
}


def test_verifier_class_has_exactly_the_six_non_model_values() -> None:
    """INV-2 como gate de tipos: "model" no existe como VerifierClass."""
    assert set(get_args(VerifierClass)) == _ALLOWED_CLASSES
    assert "model" not in get_args(VerifierClass)


# Negative pyright tests: "model" must NOT type-check in either vocabulary.
# pyproject.toml sets reportUnnecessaryTypeIgnoreComment=error, so these fail
# loud if the types are ever widened to include "model".
_rejected_by_pyright: AnchorKind = "model"  # type: ignore[assignment]
_rejected_class_by_pyright: VerifierClass = "model"  # type: ignore[assignment]


# ── InvocationContext ─────────────────────────────────────────────────────


def test_invocation_context_is_frozen() -> None:
    ctx = InvocationContext(
        run_id="run-1", actor_id="user:dylan", domain_id="d-default"
    )
    with pytest.raises(ValidationError):
        ctx.run_id = "run-2"


# ── Verifier Protocol ──────────────────────────────────────────────────────


class _FakeSolverVerifier:
    """A minimal conforming Verifier — proves the Protocol shape is usable."""

    verifier_class: VerifierClass = "formal_exact"
    anchor_kind: AnchorKind = "solver"
    determinism: Determinism = "deterministic"

    def verify(self, claim: Any, ctx: InvocationContext) -> Attestation:
        return Attestation(
            verifier_id="fake-solver",
            verifier_class=self.verifier_class,
            anchor_kind=self.anchor_kind,
            level="AL3",
            verdict="pass",
            scope={"instance": "ieee14"},
            independence_group="leg-formal",
            run_id=ctx.run_id,
            claim_digest="sha256:abc",
            verifier_binary_digest="sha256:bin",
            verifier_params_digest="sha256:par",
            anchor_digest="sha256:anc",
            predicate=FormalExactPredicate(
                differential=Differential(
                    status="OPTIMAL", objective=3.0, reference_objective=3.0
                )
            ),
            issued_at=datetime.now(tz=UTC),
        )


class _NotAVerifier:
    """Missing determinism and verify() — must NOT satisfy the Protocol."""

    verifier_class: VerifierClass = "formal_exact"
    anchor_kind: AnchorKind = "solver"


def test_verifier_protocol_accepts_a_conforming_implementation() -> None:
    verifier: Verifier = _FakeSolverVerifier()
    assert isinstance(verifier, Verifier)
    attestation = verifier.verify(
        claim={"objective": 3},
        ctx=InvocationContext(
            run_id="run-1", actor_id="user:dylan", domain_id="d-default"
        ),
    )
    assert attestation.verdict == "pass"
    assert attestation.level == "AL3"


def test_verifier_protocol_rejects_a_non_conforming_object() -> None:
    assert not isinstance(_NotAVerifier(), Verifier)
