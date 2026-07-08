"""
Verifier contract tests (ficha B2 piece 1 — docs/contract-freeze.md SS4).

AnchorKind excludes "model" by construction (PR2/ADR-027: the verifier is
never a model — knowledge/trust/03-escalera-verificacion-metodos.md SS1.1).
Verifier is a runtime_checkable Protocol; any conforming object satisfies it.

Run: uv run pyright tests/invariants/test_verifier_contract.py
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, get_args

import pytest
from pydantic import ValidationError

from blite.verification.anchor import AnchorKind
from blite.verification.attestation import Attestation, AttestationSubject
from blite.verification.context import InvocationContext
from blite.verification.evidence import DifferentialEvidence, DifferentialReference
from blite.verification.verifier import Verifier

# ── AnchorKind ─────────────────────────────────────────────────────────────

_ALLOWED_ANCHOR_KINDS = {"solver", "execution", "dataset", "rule", "human"}


def test_anchor_kind_has_exactly_the_five_non_model_values() -> None:
    """AnchorKind = solver|execution|dataset|rule|human — 'model' has no value."""
    assert set(get_args(AnchorKind)) == _ALLOWED_ANCHOR_KINDS


# Negative pyright test: "model" must NOT type-check as an AnchorKind.
# pyproject.toml sets reportUnnecessaryTypeIgnoreComment=error, so this fails
# loud if AnchorKind is ever widened to include "model": the ignore below
# would become unnecessary and pyright would flag it as an error.
_rejected_by_pyright: AnchorKind = "model"  # type: ignore[assignment]


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

    anchor_kind: AnchorKind = "solver"
    rung: Literal[1, 2, 3, 4, 7] = 1

    def verify(self, claim: Any, ctx: InvocationContext) -> Attestation:
        return Attestation(
            verifier_id="fake-solver",
            anchor_kind=self.anchor_kind,
            rung=self.rung,
            verdict="pass",
            evidence=DifferentialEvidence(
                reference=DifferentialReference(
                    solver="ortools-cpsat", version="9.15", params_digest="sha256:def"
                ),
                reference_value=3.0,
                candidate_value=3.0,
                gap=0.0,
                tolerance=1e-6,
                solver_status="OPTIMAL",
            ),
            subject=AttestationSubject(run_id=ctx.run_id, claim_digest="sha256:abc"),
            issued_at=datetime.now(tz=UTC),
        )


class _NotAVerifier:
    """Missing rung and verify() — must NOT satisfy the Protocol."""

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


def test_verifier_protocol_rejects_a_non_conforming_object() -> None:
    assert not isinstance(_NotAVerifier(), Verifier)
