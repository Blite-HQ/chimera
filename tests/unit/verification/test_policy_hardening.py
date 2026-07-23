"""Palanca EX-5, mitad Policy (freeze §6): ¿la Policy nueva ENDURECE?

El runtime (carril Steven) decide abrir `●EscalationOpened` sobre cases en
vuelo con ESTE veredicto — acá solo se computa si la exigencia subió y por
qué. El pin no cambia jamás (R-Pol1): la palanca es alarma, no revocación.
"""

from __future__ import annotations

from blite.verification.policy import (
    MatchCondition,
    VerificationPolicy,
    VerificationRule,
)
from blite.verification.policy_diff import assess_hardening


def _rule(**overrides: object) -> VerificationRule:
    base: dict[str, object] = {
        "match": MatchCondition(claim_type="solution"),
        "criticality": "C2",
        "min_level": "AL2",
        "required_legs": 1,
        "on_inconclusive": "mark",
    }
    base.update(overrides)
    return VerificationRule(**base)  # type: ignore[arg-type]


def _policy(*rules: VerificationRule, version: str = "0.2.0") -> VerificationPolicy:
    return VerificationPolicy(policy_id="p", version=version, rules=rules)


class TestNoEndurece:
    def test_identica_no_endurece(self) -> None:
        verdict = assess_hardening(_policy(_rule()), _policy(_rule(), version="0.2.1"))
        assert verdict.hardened is False
        assert verdict.causes == ()

    def test_bajar_exigencia_no_endurece(self) -> None:
        old = _policy(_rule(min_level="AL3", required_legs=2, criticality="C3"))
        new = _policy(_rule(min_level="AL2", required_legs=1, criticality="C2"))
        assert assess_hardening(old, new).hardened is False

    def test_quitar_una_regla_no_endurece(self) -> None:
        extra = _rule(
            match=MatchCondition(claim_type="intermediate"),
            criticality="C1",
            min_level="AL1",
        )
        assert (
            assess_hardening(_policy(_rule(), extra), _policy(_rule())).hardened
            is False
        )


class TestEndurece:
    def test_subir_min_level(self) -> None:
        verdict = assess_hardening(_policy(_rule()), _policy(_rule(min_level="AL3")))
        assert verdict.hardened is True
        assert any("min_level" in c for c in verdict.causes)

    def test_subir_required_legs(self) -> None:
        verdict = assess_hardening(_policy(_rule()), _policy(_rule(required_legs=2)))
        assert verdict.hardened is True

    def test_subir_criticidad(self) -> None:
        verdict = assess_hardening(_policy(_rule()), _policy(_rule(criticality="C3")))
        assert verdict.hardened is True

    def test_exigir_anclas_nuevas(self) -> None:
        verdict = assess_hardening(
            _policy(_rule()), _policy(_rule(required_anchors=("solver",)))
        )
        assert verdict.hardened is True

    def test_endurecer_on_inconclusive(self) -> None:
        # mark < escalate_human < hold_run (afecta el estado del run, jamás
        # el egreso — Inv-E): subir el escalón de reacción es endurecer.
        verdict = assess_hardening(
            _policy(_rule()), _policy(_rule(on_inconclusive="hold_run"))
        )
        assert verdict.hardened is True

    def test_regla_nueva_donde_no_habia(self) -> None:
        # Forma monotónica ("deny unless proven"): una regla nueva es
        # exigencia nueva sobre claims antes sin regla propia.
        extra = _rule(match=MatchCondition(claim_type="simulation_result"))
        verdict = assess_hardening(_policy(_rule()), _policy(_rule(), extra))
        assert verdict.hardened is True
        assert any("simulation_result" in c for c in verdict.causes)

    def test_las_causas_nombran_cada_dimension(self) -> None:
        old = _policy(_rule())
        new = _policy(_rule(min_level="AL3", required_legs=2))
        verdict = assess_hardening(old, new)
        assert len(verdict.causes) == 2
