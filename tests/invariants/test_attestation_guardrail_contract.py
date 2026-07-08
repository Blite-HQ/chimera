"""
Attestation + GuardrailSignal contract tests (ficha B2 piece 2).

docs/contract-freeze.md SS4-SS5 /
knowledge/trust/03-escalera-verificacion-metodos.md SS1.2-SS1.4 /
knowledge/trust/04-anclas-duras-mapa-oraculos.md SS1.3.

Attestation (rung in {1,2,3,4,7}, evidence discriminated by method, subject
for process verification) and GuardrailSignal (rung in {5,6}) are disjoint
types by construction: no rung value is shared, and neither type's required
fields satisfy the other's validation.

Run: uv run pyright tests/invariants/test_attestation_guardrail_contract.py
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, get_args

import pytest
from pydantic import ValidationError

from blite.guardrails.signal import GuardrailSignal
from blite.verification.attestation import Attestation, AttestationSubject
from blite.verification.evidence import (
    DifferentialEvidence,
    DifferentialReference,
    ExecutionCheck,
    ExecutionEnvironment,
    ExecutionEvidence,
    HumanEvidence,
    KnownTruthEvidence,
    MetamorphicEvidence,
    MetamorphicRelation,
    PropertyCheck,
    PropertyEvidence,
)

ISSUED_AT = datetime(2026, 7, 7, 12, 0, 0, tzinfo=UTC)


def _subject() -> AttestationSubject:
    return AttestationSubject(run_id="run-1", claim_digest="sha256:abc")


def _differential_evidence() -> DifferentialEvidence:
    return DifferentialEvidence(
        reference=DifferentialReference(
            solver="ortools-cpsat", version="9.15", params_digest="sha256:def"
        ),
        reference_value=3.0,
        candidate_value=3.0,
        gap=0.0,
        tolerance=1e-6,
        solver_status="OPTIMAL",
    )


# ── rung disjunction (the core of this piece) ─────────────────────────────

_ATTESTATION_RUNGS = {1, 2, 3, 4, 7}
_GUARDRAIL_RUNGS = {5, 6}


def test_attestation_rung_and_guardrail_rung_share_no_value() -> None:
    """The escalera formalized as a type: rungs 5-6 are unrepresentable as an Attestation."""
    assert (
        set(get_args(Attestation.model_fields["rung"].annotation)) == _ATTESTATION_RUNGS
    )
    assert (
        set(get_args(GuardrailSignal.model_fields["rung"].annotation))
        == _GUARDRAIL_RUNGS
    )
    assert _ATTESTATION_RUNGS.isdisjoint(_GUARDRAIL_RUNGS)


# Negative pyright test: rung=5 must NOT type-check as an AttestationRung.
_rejected_attestation_rung: Literal[1, 2, 3, 4, 7] = 5  # type: ignore[assignment]


# ── disjunction: neither type satisfies the other's construction ─────────


def test_guardrail_signal_cannot_be_built_from_attestation_fields() -> None:
    attestation_kwargs = {
        "verifier_id": "ortools-cpsat",
        "anchor_kind": "solver",
        "rung": 1,
        "verdict": "pass",
        "evidence": _differential_evidence(),
        "subject": _subject(),
        "issued_at": ISSUED_AT,
    }
    with pytest.raises(ValidationError):
        GuardrailSignal(**attestation_kwargs)  # type: ignore[arg-type]


def test_attestation_cannot_be_built_from_guardrail_signal_fields() -> None:
    guardrail_kwargs = {
        "name": "self-consistency",
        "flagged": True,
        "confidence": 0.82,
        "rung": 5,
        "detail": {"samples": 8, "agreement": 0.625},
    }
    with pytest.raises(ValidationError):
        Attestation(**guardrail_kwargs)  # type: ignore[arg-type,call-arg]


# ── Attestation: evidence union, subject, tri-state verdict ──────────────


def test_attestation_requires_subject_and_evidence() -> None:
    with pytest.raises(ValidationError):
        Attestation(
            verifier_id="ortools-cpsat",
            anchor_kind="solver",
            rung=1,
            verdict="pass",
            issued_at=ISSUED_AT,
        )  # type: ignore[call-arg]


def test_attestation_accepts_inconclusive_verdict() -> None:
    attestation = Attestation(
        verifier_id="ortools-cpsat",
        anchor_kind="solver",
        rung=1,
        verdict="inconclusive",
        evidence=_differential_evidence(),
        subject=_subject(),
        issued_at=ISSUED_AT,
    )
    assert attestation.verdict == "inconclusive"


def test_evidence_discriminates_by_method() -> None:
    execution = ExecutionEvidence(
        harness="pandapower-powerflow",
        input_digest="sha256:111",
        checks=(ExecutionCheck(name="island_connectivity", passed=True),),
        runtime_ms=42.0,
        environment=ExecutionEnvironment(package="pandapower", version="2.14"),
    )
    known_truth = KnownTruthEvidence(
        dataset_id="ieee14-partitions-v1",
        case_id="case-1",
        expected_digest="sha256:222",
        observed_digest="sha256:222",
        match=True,
        tolerance=0.0,
    )
    property_ev = PropertyEvidence(
        properties=(
            PropertyCheck(name="cut_cost_nonnegative", passed=True, examples_run=100),
        ),
        seed=42,
        generator_version="hypothesis-6.156",
    )
    metamorphic = MetamorphicEvidence(
        relations=(
            MetamorphicRelation(
                name="rename-invariant",
                transform_digest="sha256:333",
                expected_relation="invariant",
                held=True,
            ),
        )
    )
    human = HumanEvidence(
        reviewer="user:dylan",
        decision="approve",
        rationale="irreversible egress reviewed manually",
        reviewed_digest="sha256:444",
    )

    attestations = (
        Attestation(
            verifier_id="verifier-differential",
            anchor_kind="solver",
            rung=1,
            verdict="pass",
            evidence=_differential_evidence(),
            subject=_subject(),
            issued_at=ISSUED_AT,
        ),
        Attestation(
            verifier_id="verifier-execution",
            anchor_kind="execution",
            rung=2,
            verdict="pass",
            evidence=execution,
            subject=_subject(),
            issued_at=ISSUED_AT,
        ),
        Attestation(
            verifier_id="verifier-known_truth",
            anchor_kind="dataset",
            rung=3,
            verdict="pass",
            evidence=known_truth,
            subject=_subject(),
            issued_at=ISSUED_AT,
        ),
        Attestation(
            verifier_id="verifier-property",
            anchor_kind="rule",
            rung=4,
            verdict="pass",
            evidence=property_ev,
            subject=_subject(),
            issued_at=ISSUED_AT,
        ),
        Attestation(
            verifier_id="verifier-metamorphic",
            anchor_kind="rule",
            rung=4,
            verdict="pass",
            evidence=metamorphic,
            subject=_subject(),
            issued_at=ISSUED_AT,
        ),
        Attestation(
            verifier_id="verifier-human",
            anchor_kind="human",
            rung=7,
            verdict="pass",
            evidence=human,
            subject=_subject(),
            issued_at=ISSUED_AT,
        ),
    )
    expected_methods = {
        "differential",
        "execution",
        "known_truth",
        "property",
        "metamorphic",
        "human",
    }
    assert {a.evidence.method for a in attestations} == expected_methods


# ── GuardrailSignal: confidence bounds ────────────────────────────────────


def test_guardrail_signal_confidence_must_be_within_zero_and_one() -> None:
    with pytest.raises(ValidationError):
        GuardrailSignal(
            name="prompt-injection", flagged=True, confidence=1.5, rung=6, detail={}
        )


def test_guardrail_signal_is_frozen() -> None:
    signal = GuardrailSignal(
        name="prompt-injection", flagged=False, confidence=0.1, rung=6
    )
    with pytest.raises(ValidationError):
        signal.flagged = True
