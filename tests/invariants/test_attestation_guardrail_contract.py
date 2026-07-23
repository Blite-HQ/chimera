"""
Attestation + Signal contract tests — vocabulario §4/§5.

Attestation (clase+AL con techos, binding 4 digests, predicate por clase) y
Signal (detector, kind "{etapa}.{mecanismo}", non_decisional: true) son tipos
DISJUNTOS por construcción: ninguno valida con los campos del otro
(extra="forbid" en ambos), y no existe conversión — lo probabilístico informa,
jamás verifica (S1/D18/D21/Inv-E hechos tipo).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from blite.guardrails.signal import Signal
from blite.verification.attestation import Attestation
from blite.verification.evidence import (
    ConsensusReplicationPredicate,
    Differential,
    ExecutionCheck,
    ExecutionEnvironment,
    ExecutionPredicate,
    FormalExactPredicate,
    GroundTruthPredicate,
    HumanExpertPredicate,
    MetamorphicRelation,
    Proof,
    PropertyCheck,
    PropertyRulePredicate,
)

ISSUED_AT = datetime(2026, 7, 22, 12, 0, 0, tzinfo=UTC)


def _formal_predicate(*, with_proof: bool = False) -> FormalExactPredicate:
    return FormalExactPredicate(
        differential=Differential(
            status="OPTIMAL", objective=3.0, reference_objective=3.0
        ),
        proof=Proof(
            certificate_ref="cert:chk", checker_id="brute-force", checker_verdict="pass"
        )
        if with_proof
        else None,
    )


def _att(**overrides: Any) -> Attestation:
    kwargs: dict[str, Any] = {
        "verifier_id": "ortools-cpsat",
        "verifier_class": "formal_exact",
        "anchor_kind": "solver",
        "level": "AL3",
        "verdict": "pass",
        "scope": {"instance": "ieee14"},
        "independence_group": "leg-formal",
        "run_id": "run-1",
        "claim_digest": "sha256:abc",
        "verifier_binary_digest": "sha256:bin",
        "verifier_params_digest": "sha256:par",
        "anchor_digest": "sha256:anc",
        "predicate": _formal_predicate(),
        "issued_at": ISSUED_AT,
    }
    kwargs.update(overrides)
    return Attestation(**kwargs)


# ── disyunción por construcción (el corazón de esta pieza) ────────────────


def test_signal_cannot_be_built_from_attestation_fields() -> None:
    with pytest.raises(ValidationError):
        Signal(
            verifier_id="ortools-cpsat",  # type: ignore[call-arg]
            verifier_class="formal_exact",  # type: ignore[call-arg]
            verdict="pass",  # type: ignore[call-arg]
        )


def test_attestation_cannot_be_built_from_signal_fields() -> None:
    with pytest.raises(ValidationError):
        Attestation(
            detector="self-consistency",  # type: ignore[call-arg]
            kind="egress.self_consistency",  # type: ignore[call-arg]
            target="sha256:abc",  # type: ignore[call-arg]
            flagged=True,  # type: ignore[call-arg]
        )


def test_signal_is_non_decisional_by_type() -> None:
    """El valor False no existe — la señal jamás decide (S1/Inv-E)."""
    with pytest.raises(ValidationError):
        Signal(
            detector="self-consistency",
            kind="egress.self_consistency",
            target="sha256:abc",
            flagged=False,
            non_decisional=False,  # type: ignore[arg-type]
        )


# ── endurecimientos [S-F] del binding ─────────────────────────────────────


def test_pass_without_anchor_is_unrepresentable() -> None:
    with pytest.raises(ValidationError, match="irrepresentable"):
        _att(anchor_digest=None)


def test_fail_without_anchor_is_unrepresentable_too() -> None:
    # [stress-final] el CHECK cubre fail, no solo pass
    with pytest.raises(ValidationError, match="irrepresentable"):
        _att(verdict="fail", anchor_digest=None)


def test_inconclusive_requires_a_typed_reason_and_allows_no_anchor() -> None:
    with pytest.raises(ValidationError, match="reason"):
        _att(verdict="inconclusive", anchor_digest=None)
    attestation = _att(
        verdict="inconclusive",
        anchor_digest=None,
        inconclusive_reason="no_applicable_anchor",
    )
    assert attestation.anchor_digest is None


def test_level_cannot_exceed_the_class_ceiling() -> None:
    with pytest.raises(ValidationError, match="techo"):
        _att(
            verifier_class="property_rule",
            anchor_kind="rule",
            level="AL3",
            predicate=PropertyRulePredicate(
                properties=(PropertyCheck(name="p", passed=True, examples_run=10),)
            ),
        )


def test_al4_requires_an_independent_checker_proof() -> None:
    with pytest.raises(ValidationError, match="proof"):
        _att(level="AL4", predicate=_formal_predicate(with_proof=False))
    attestation = _att(level="AL4", predicate=_formal_predicate(with_proof=True))
    assert attestation.level == "AL4"


def test_process_error_statuses_cannot_become_a_predicate() -> None:
    # freeze §4: error de proceso ≠ verdict fail — MODEL_INVALID/INFEASIBLE explotan
    for status in ("MODEL_INVALID", "INFEASIBLE"):
        with pytest.raises(ValidationError, match="error de proceso"):
            Differential(status=status, objective=3.0, reference_objective=3.0)


def test_predicate_must_match_the_verifier_class() -> None:
    with pytest.raises(ValidationError, match="clase"):
        _att(
            verifier_class="execution",
            level="AL3",
            predicate=_formal_predicate(),
        )


# ── predicate discriminado: las 6 clases construyen ───────────────────────


def test_all_six_classes_have_a_constructible_predicate() -> None:
    cases = (
        ("formal_exact", "solver", "AL3", _formal_predicate()),
        (
            "execution",
            "execution",
            "AL3",
            ExecutionPredicate(
                harness="pandapower-powerflow",
                input_digest="sha256:111",
                checks=(ExecutionCheck(name="island_connectivity", passed=True),),
                runtime_ms=42.0,
                environment=ExecutionEnvironment(package="pandapower", version="3.5.4"),
            ),
        ),
        (
            "ground_truth",
            "dataset",
            "AL3",
            GroundTruthPredicate(
                dataset_id="ieee14-partitions-v1",
                case_id="case-1",
                expected_digest="sha256:222",
                observed_digest="sha256:222",
                match=True,
                tolerance=0.0,
            ),
        ),
        (
            "property_rule",
            "rule",
            "AL2",
            PropertyRulePredicate(
                relations=(
                    MetamorphicRelation(
                        name="rename-invariant",
                        transform_digest="sha256:333",
                        expected_relation="invariant",
                        held=True,
                    ),
                )
            ),
        ),
        (
            "consensus_replication",
            "rule",
            "AL2",
            ConsensusReplicationPredicate(replicas=3, seeds=(1, 2, 3), agreement=True),
        ),
        (
            "human_expert",
            "human",
            "AL3",
            HumanExpertPredicate(
                reviewer="user:dylan",
                decision="approve",
                rationale="irreversible egress reviewed manually",
                reviewed_digest="sha256:444",
            ),
        ),
    )
    methods: set[str] = set()
    for verifier_class, anchor_kind, level, predicate in cases:
        attestation = _att(
            verifier_class=verifier_class,
            anchor_kind=anchor_kind,
            level=level,
            predicate=predicate,
        )
        methods.add(attestation.predicate.method)
    assert methods == {
        "formal_exact",
        "execution",
        "ground_truth",
        "property_rule",
        "consensus_replication",
        "human_expert",
    }


# ── Signal: convención de kind, score acotado, frozen ─────────────────────


def test_signal_kind_follows_the_etapa_mecanismo_convention() -> None:
    with pytest.raises(ValidationError, match="convención"):
        Signal(detector="d", kind="sin-punto", target="sha256:abc", flagged=True)


def test_signal_score_must_be_within_zero_and_one() -> None:
    with pytest.raises(ValidationError):
        Signal(
            detector="d",
            kind="egress.prompt_injection",
            target="sha256:abc",
            flagged=True,
            score=1.5,
        )


def test_signal_is_frozen() -> None:
    signal = Signal(
        detector="d", kind="egress.prompt_injection", target="sha256:abc", flagged=False
    )
    with pytest.raises(ValidationError):
        signal.flagged = True
