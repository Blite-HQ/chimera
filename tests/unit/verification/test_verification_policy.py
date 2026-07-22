"""
VerificationPolicy — declarative, versioned policy-as-data (ficha B2 piece 5).

docs/contract-freeze.md SS6 / knowledge/trust/05-verificacion-adaptativa-politica-tradeoffs.md
SS1.2: the engine defines the type; the distribution
(distributions/chimera/policies/) brings the policy. This test loads the
committed example YAML through the model (not a hand-built fixture) so the
file and the type can never silently drift, and checks the on-disk JSON
Schema against the model's own model_json_schema() for the same reason.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from blite.verification.policy import VerificationPolicy

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_YAML = (
    REPO_ROOT / "distributions" / "chimera" / "policies" / "verification-default.yaml"
)
SCHEMA_JSON = (
    REPO_ROOT
    / "distributions"
    / "chimera"
    / "policies"
    / "verification-policy.schema.json"
)


def test_example_yaml_loads_as_a_valid_verification_policy() -> None:
    raw = yaml.safe_load(EXAMPLE_YAML.read_text(encoding="utf-8"))
    policy = VerificationPolicy.model_validate(raw)

    assert policy.policy_id == "chimera-default"
    # [S-F] 0.2.0: the 0.1.0 spoke `min_rung`, vocabulary removed by the freeze SS4.
    assert policy.version == "0.2.0"
    assert len(policy.rules) == 3


def test_example_yaml_pure_solution_rule_is_c3_with_two_independent_legs() -> None:
    raw = yaml.safe_load(EXAMPLE_YAML.read_text(encoding="utf-8"))
    policy = VerificationPolicy.model_validate(raw)

    solution_rule = policy.rules[0]
    assert solution_rule.match.side_effects == "pure"
    assert solution_rule.match.claim_type == "solution"
    assert solution_rule.criticality == "C3"
    assert solution_rule.min_level == "AL3"
    assert solution_rule.required_legs == 2
    assert solution_rule.required_anchors == ("solver", "execution")
    assert solution_rule.on_inconclusive == "mark"


def test_example_yaml_irreversible_rule_escalates_to_human_and_holds_run() -> None:
    raw = yaml.safe_load(EXAMPLE_YAML.read_text(encoding="utf-8"))
    policy = VerificationPolicy.model_validate(raw)

    irreversible_rule = policy.rules[2]
    assert irreversible_rule.match.side_effects == "irreversible-external"
    assert irreversible_rule.escalation == "human"
    assert irreversible_rule.on_inconclusive == "hold_run"


def test_committed_schema_matches_the_model_json_schema() -> None:
    """Fails loud on drift: regenerate the file, don't hand-edit it."""
    on_disk = json.loads(SCHEMA_JSON.read_text(encoding="utf-8"))
    assert on_disk == VerificationPolicy.model_json_schema()


def test_on_inconclusive_rejects_a_value_outside_the_closed_set() -> None:
    with pytest.raises(ValidationError):
        VerificationPolicy.model_validate(
            {
                "policy_id": "test",
                "version": "0.2.0",
                "rules": [
                    {
                        "match": {},
                        "criticality": "C1",
                        "min_level": "AL1",
                        "on_inconclusive": "ignore",
                    }
                ],
            }
        )


def test_min_rung_vocabulary_is_dead() -> None:
    """[S-F · T1] The 1-7 ladder was superseded by the freeze SS4 — a rule speaking
    `min_rung` must be rejected, never silently accepted alongside the new fields."""
    with pytest.raises(ValidationError):
        VerificationPolicy.model_validate(
            {
                "policy_id": "test",
                "version": "0.2.0",
                "rules": [{"match": {}, "min_rung": 1, "on_inconclusive": "mark"}],
            }
        )


def test_verification_policy_is_frozen() -> None:
    raw = yaml.safe_load(EXAMPLE_YAML.read_text(encoding="utf-8"))
    policy = VerificationPolicy.model_validate(raw)
    with pytest.raises(ValidationError):
        policy.policy_id = "tampered"


@pytest.mark.parametrize("bad_legs", [0, -5, True])
def test_required_legs_rejects_non_positive_and_bool(bad_legs: object) -> None:
    # Stress final 2026-07-22: legs <= 0 son basura sin semantica y bool->int
    # es coercion silenciosa — la matriz C3 => 2 patas exige enteros >= 1.
    raw = yaml.safe_load(EXAMPLE_YAML.read_text(encoding="utf-8"))
    raw["rules"][0]["required_legs"] = bad_legs
    with pytest.raises(ValidationError):
        VerificationPolicy.model_validate(raw)
