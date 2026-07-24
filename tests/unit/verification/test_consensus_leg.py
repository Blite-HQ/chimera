"""Unit tests de la extensión ADITIVA `ConsensusLeg`/`ConsensusReplicationPredicate.legs`
— docs/specs/evidencia-externa.md §`ConsensusReplicationPredicate` (freeze §11,
campos multi-backend del claim proponente portados a la pata de consenso).

`legs` es aditivo y opcional (`= ()` por default): los tests aquí verifican
que (a) el default vacío NUNCA dispara el validador (los usos existentes de
`ConsensusReplicationPredicate` sin `legs`, p.ej.
`tests/invariants/test_attestation_guardrail_contract.py`, siguen verdes sin
tocarlos) y (b) con `legs` no vacío, `len(legs) == replicas` y
`seeds == tuple(leg.seed for leg in legs)` son duros.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from blite.verification.evidence import ConsensusLeg, ConsensusReplicationPredicate


def _leg(**overrides: object) -> ConsensusLeg:
    kwargs: dict[str, object] = {
        "seed": 0,
        "backend_id": "H2-1LE",
        "transpiled_circuit_digest": "sha256:" + "a" * 64,
        "noise_config_digest": "sha256:" + "b" * 64,
    }
    kwargs.update(overrides)
    return ConsensusLeg(**kwargs)  # type: ignore[arg-type]


class TestConsensusLegShape:
    def test_carries_the_freeze_11_fields(self) -> None:
        leg = _leg(seed=3, backend_id="H2-Emulator")

        assert leg.seed == 3
        assert leg.backend_id == "H2-Emulator"

    def test_is_frozen(self) -> None:
        leg = _leg()
        with pytest.raises(ValidationError):
            leg.seed = 1

    def test_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            _leg(unexpected_field="nope")


class TestConsensusReplicationPredicateLegsIsAdditive:
    def test_existing_construction_without_legs_still_works(self) -> None:
        # Forma EXACTA ya usada por
        # tests/invariants/test_attestation_guardrail_contract.py — legs=()
        # por default no debe romper esto ni disparar el validador.
        predicate = ConsensusReplicationPredicate(
            replicas=3, seeds=(1, 2, 3), agreement=True
        )

        assert predicate.legs == ()
        assert predicate.replicas == 3
        assert predicate.seeds == (1, 2, 3)

    def test_default_legs_is_an_empty_tuple(self) -> None:
        predicate = ConsensusReplicationPredicate(
            replicas=2, seeds=(0, 1), agreement=False
        )
        assert predicate.legs == ()


class TestConsensusReplicationPredicateLegsValidator:
    def test_consistent_legs_pass(self) -> None:
        legs = (
            _leg(seed=0, backend_id="H2-1LE"),
            _leg(seed=0, backend_id="H2-Emulator"),
        )

        predicate = ConsensusReplicationPredicate(
            replicas=2, seeds=(0, 0), agreement=True, legs=legs
        )

        assert predicate.legs == legs

    def test_legs_count_mismatch_with_replicas_raises(self) -> None:
        legs = (_leg(seed=0), _leg(seed=1))

        with pytest.raises(ValidationError, match="replicas"):
            ConsensusReplicationPredicate(
                replicas=3, seeds=(0, 1, 2), agreement=True, legs=legs
            )

    def test_legs_seed_mismatch_with_seeds_raises(self) -> None:
        legs = (_leg(seed=0), _leg(seed=1))

        with pytest.raises(ValidationError, match="seeds"):
            ConsensusReplicationPredicate(
                replicas=2, seeds=(0, 99), agreement=True, legs=legs
            )

    def test_legs_order_matters_for_the_seeds_comparison(self) -> None:
        # seeds=(1, 0) exige legs en ESE orden — (0,1) no matchea aunque el
        # multiset de seeds coincida (comparación posicional, no de conjunto).
        legs = (_leg(seed=0), _leg(seed=1))

        with pytest.raises(ValidationError, match="seeds"):
            ConsensusReplicationPredicate(
                replicas=2, seeds=(1, 0), agreement=True, legs=legs
            )
