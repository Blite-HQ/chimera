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
POLICIES_DIR = REPO_ROOT / "distributions" / "chimera" / "policies"
EXAMPLE_YAML = POLICIES_DIR / "verification-default.yaml"
SCHEMA_JSON = POLICIES_DIR / "verification-policy.schema.json"
RETO3_TEMPLATE_YAML = POLICIES_DIR / "reto3-simulation.yaml"
RETO2_TEMPLATE_YAML = POLICIES_DIR / "reto2-statistical.yaml"


def test_example_yaml_loads_as_a_valid_verification_policy() -> None:
    raw = yaml.safe_load(EXAMPLE_YAML.read_text(encoding="utf-8"))
    policy = VerificationPolicy.model_validate(raw)

    assert policy.policy_id == "chimera-default"
    # [G4/#138] 0.3.0: adds the reto-2/reto-3 rules (generalidad-retos.md §Contrato-5).
    # [#141] 0.3.1: the statistical rule drops min_level AL3→AL2 (truth of today:
    # the property_rule leg is AL2-capped by freeze §4; AL3 aspiration recorded
    # in the template). Pre-existing rules stay byte-unchanged.
    assert policy.version == "0.3.1"
    assert len(policy.rules) == 5


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


def test_example_yaml_simulation_result_rule_is_c3_solver_dataset() -> None:
    """[G4/#138] reto 3 — docs/specs/generalidad-retos.md §Contrato-5."""
    raw = yaml.safe_load(EXAMPLE_YAML.read_text(encoding="utf-8"))
    policy = VerificationPolicy.model_validate(raw)

    rule = policy.rules[3]
    assert rule.match.claim_type == "simulation_result"
    assert rule.match.side_effects is None
    assert rule.criticality == "C3"
    assert rule.min_level == "AL3"
    assert rule.required_legs == 2
    assert rule.required_anchors == ("solver", "dataset")
    assert rule.on_inconclusive == "mark"
    assert rule.escalation is None


def test_example_yaml_statistical_rule_is_c3_dataset_rule() -> None:
    """[G4/#138] reto 2 — docs/specs/generalidad-retos.md §Contrato-5."""
    raw = yaml.safe_load(EXAMPLE_YAML.read_text(encoding="utf-8"))
    policy = VerificationPolicy.model_validate(raw)

    rule = policy.rules[4]
    assert rule.match.claim_type == "statistical"
    assert rule.match.side_effects is None
    assert rule.criticality == "C3"
    # [#141] AL2 = la verdad de hoy (pata property_rule con techo AL2, freeze §4);
    # la aspiración AL3 vive en la plantilla y sube cuando exista 2ª pata AL3.
    assert rule.min_level == "AL2"
    assert rule.required_legs == 2
    assert rule.required_anchors == ("dataset", "rule")
    assert rule.on_inconclusive == "mark"
    assert rule.escalation is None


def test_example_yaml_pre_existing_rules_are_unchanged_by_the_bump() -> None:
    """[G4/#138] aditivo puro (spec §Contrato-5 punto 3): `solution` e
    `intermediate` — las reglas pre-existentes — no cambian de forma."""
    raw = yaml.safe_load(EXAMPLE_YAML.read_text(encoding="utf-8"))
    policy = VerificationPolicy.model_validate(raw)

    intermediate_rule = policy.rules[1]
    assert intermediate_rule.match.side_effects == "pure"
    assert intermediate_rule.match.claim_type == "intermediate"
    assert intermediate_rule.criticality == "C1"
    assert intermediate_rule.min_level == "AL1"
    assert intermediate_rule.on_inconclusive == "mark"


class TestPlantillasPorReto:
    """[G4/#138] las plantillas single-rule cargan standalone Y son
    byte-equivalentes (mismos valores de campo) a la regla compuesta dentro
    de `verification-default.yaml` — si alguien edita una sin la otra, este
    test lo caza (docs/specs/generalidad-retos.md §Contrato-5)."""

    def test_reto3_template_carga_standalone(self) -> None:
        raw = yaml.safe_load(RETO3_TEMPLATE_YAML.read_text(encoding="utf-8"))
        template_policy = VerificationPolicy.model_validate(raw)

        assert template_policy.policy_id == "chimera-reto3-simulation"
        assert len(template_policy.rules) == 1
        assert template_policy.rules[0].match.claim_type == "simulation_result"

    def test_reto2_template_carga_standalone(self) -> None:
        raw = yaml.safe_load(RETO2_TEMPLATE_YAML.read_text(encoding="utf-8"))
        template_policy = VerificationPolicy.model_validate(raw)

        assert template_policy.policy_id == "chimera-reto2-statistical"
        assert len(template_policy.rules) == 1
        assert template_policy.rules[0].match.claim_type == "statistical"

    def test_reto3_template_es_byte_equivalente_a_la_regla_compuesta(self) -> None:
        template = VerificationPolicy.model_validate(
            yaml.safe_load(RETO3_TEMPLATE_YAML.read_text(encoding="utf-8"))
        )
        composed = VerificationPolicy.model_validate(
            yaml.safe_load(EXAMPLE_YAML.read_text(encoding="utf-8"))
        )

        assert template.rules[0] == composed.rules[3]

    def test_reto2_template_es_byte_equivalente_a_la_regla_compuesta(self) -> None:
        template = VerificationPolicy.model_validate(
            yaml.safe_load(RETO2_TEMPLATE_YAML.read_text(encoding="utf-8"))
        )
        composed = VerificationPolicy.model_validate(
            yaml.safe_load(EXAMPLE_YAML.read_text(encoding="utf-8"))
        )

        assert template.rules[0] == composed.rules[4]


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
