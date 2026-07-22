"""Seed completo de la Policy (freeze §6): matriz kernel C0-C3, pisos por
flags (PR2/PR4) y campos v3.2 — el YAML 0.2.0 sigue validando sin cambios."""

from __future__ import annotations

from pathlib import Path

import yaml

from blite.verification.policy import (
    KERNEL_MATRIX,
    VerificationPolicy,
    criticality_floor,
    effective_criticality,
)

ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_YAML = (
    ROOT / "distributions" / "chimera" / "policies" / "verification-default.yaml"
)


# ── matriz kernel (freeze §6) ─────────────────────────────────────────────


def test_kernel_matrix_carries_the_frozen_rows() -> None:
    assert KERNEL_MATRIX["C0"].min_level == "AL0"
    assert KERNEL_MATRIX["C0"].required_legs == 0  # declarado — la única fila con 0
    assert KERNEL_MATRIX["C1"].min_level == "AL1"
    assert KERNEL_MATRIX["C1"].required_legs == 1
    assert KERNEL_MATRIX["C2"].min_level == "AL2"
    assert KERNEL_MATRIX["C2"].required_legs == 1


def test_c3_row_carries_the_full_hardening() -> None:
    c3 = KERNEL_MATRIX["C3"]
    assert c3.min_level == "AL3"
    assert c3.required_legs == 2
    assert c3.anchor_authority_min == "curated_internal"
    assert c3.requires_non_self_generated_leg is True
    assert c3.formalization is not None


# ── pisos por flags (PR2/PR4) ─────────────────────────────────────────────


def test_world_flag_floors_at_c2() -> None:
    assert criticality_floor(world=True) == "C2"
    assert effective_criticality("C0", world=True) == "C2"
    assert effective_criticality("C1", world=True) == "C2"


def test_irreversible_and_third_party_floor_at_c3_blocking() -> None:
    assert criticality_floor(irreversible=True, affects_third_party=True) == "C3"
    assert (
        effective_criticality("C1", irreversible=True, affects_third_party=True) == "C3"
    )


def test_irreversible_alone_does_not_floor() -> None:
    # el piso C3 exige la CONJUNCIÓN (freeze §6); irreversible solo lo cubren
    # las reglas por side_effects del YAML
    assert criticality_floor(irreversible=True) is None


def test_the_floor_only_raises_never_lowers() -> None:
    assert effective_criticality("C3", world=True) == "C3"
    assert effective_criticality("C2", world=True) == "C2"
    assert effective_criticality("C0") == "C0"


# ── campos v3.2 (opcionales — el YAML 0.2.0 valida sin cambios) ──────────


def test_the_committed_yaml_still_validates_with_empty_v32_fields() -> None:
    raw = yaml.safe_load(EXAMPLE_YAML.read_text(encoding="utf-8"))
    policy = VerificationPolicy.model_validate(raw)
    assert policy.max_attestation_age == {}
    assert policy.trusted_signer_roots == ()
    assert policy.retention is None


def test_v32_fields_load_when_present() -> None:
    policy = VerificationPolicy.model_validate(
        {
            "policy_id": "p",
            "version": "0.3.0",
            "rules": [
                {
                    "match": {"claim_type": "solution"},
                    "criticality": "C3",
                    "min_level": "AL3",
                    "on_inconclusive": "mark",
                }
            ],
            "max_attestation_age": {"solution": "P7D"},
            "trusted_signer_roots": ["org:blite"],
            "audience_profiles": {"executive": {"leads_with": "scope"}},
            "retention": "P1Y",
        }
    )
    assert policy.max_attestation_age["solution"] == "P7D"
    assert policy.trusted_signer_roots == ("org:blite",)
    assert policy.retention == "P1Y"
