"""Predicate mínimo del certificado (freeze §7): titular = mínimo del camino
crítico con socavamiento — jamás promedio, jamás AL vacuo, jamás inflado."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from blite.certificate.predicate import (
    AssuranceLevel,
    Conclusion,
    ConclusionVerdict,
    TrustCertificatePredicate,
    compute_titular_level,
)


def _conclusion(verdict: ConclusionVerdict, level: AssuranceLevel) -> Conclusion:
    return Conclusion(
        claim_digest="sha256:aa",
        canonical_statement="stmt",
        scope={"instance": "ieee14"},
        verdict=verdict,
        level=level,
    )


def _predicate(
    conclusions: tuple[Conclusion, ...], titular: AssuranceLevel
) -> TrustCertificatePredicate:
    return TrustCertificatePredicate(
        run_id="r1",
        actor="user:dylan",
        conclusions=conclusions,
        titular_level=titular,
        assumptions=(),
        deliverables=(),
        policy_digest="sha256:pp",
        calculus_version="cal-2.4",
        valid_as_of=datetime.now(tz=UTC),
    )


def test_empty_conclusions_yield_al0_never_a_vacuous_minimum() -> None:
    assert compute_titular_level(()) == "AL0"
    assert _predicate((), "AL0").titular_level == "AL0"


def test_an_undermined_verdict_collapses_level_efectivo_to_al0() -> None:
    # Arrange / Act — [S-F stress · SF-P2-4]
    refuted = _conclusion("refuted", "AL4")
    declared = _conclusion("not_required_declared", "AL3")

    # Assert
    assert refuted.level_efectivo == "AL0"
    assert declared.level_efectivo == "AL0"


def test_titular_is_the_minimum_of_the_critical_path() -> None:
    # Arrange
    conclusions = (_conclusion("verified", "AL3"), _conclusion("verified", "AL2"))

    # Act / Assert
    assert compute_titular_level(conclusions) == "AL2"
    assert _predicate(conclusions, "AL2").titular_level == "AL2"


def test_an_inflated_titular_explodes_at_validation() -> None:
    # Arrange — un refuted en el camino crítico arrastra el titular a AL0
    conclusions = (_conclusion("verified", "AL4"), _conclusion("refuted", "AL4"))

    # Act / Assert — inflar el titular es fraude de cálculo (freeze §7)
    with pytest.raises(ValidationError, match="fraude"):
        _predicate(conclusions, "AL4")
    assert _predicate(conclusions, "AL0").titular_level == "AL0"
