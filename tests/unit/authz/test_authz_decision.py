"""AuthzDecision — el único tipo que la etapa de egreso acepta (freeze §5).

[S-F/EX-14] La firma del egreso recibe `AuthzDecision`, NO PUEDE recibir
`Signal` — un `{flagged: false}` no equivale a un `pass` ni por descuido de
tipos (S1/Inv-E hechos firma; semilla v2 + execution/01). La traducción
Pydantic es la verdad ejecutable de la semilla TypeScript.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from blite.authz import AuthzDecision


class TestForma:
    def test_forma_de_la_semilla_v2(self) -> None:
        decision = AuthzDecision(
            allowed=True,
            reason="actor porta capability:invoke y el dominio lo permite",
            decided_by="stage:authorization",
        )
        assert decision.allowed is True
        assert decision.decided_by == "stage:authorization"

    def test_es_inmutable(self) -> None:
        decision = AuthzDecision(
            allowed=False, reason="sin permiso", decided_by="stage:authorization"
        )
        with pytest.raises(ValidationError):
            decision.allowed = True

    def test_reason_y_decided_by_no_pueden_ser_vacios(self) -> None:
        # Fail-closed honesto: una decisión sin razón ni responsable no es
        # una decisión — es un default disfrazado.
        with pytest.raises(ValidationError):
            AuthzDecision(allowed=True, reason="", decided_by="stage:authorization")
        with pytest.raises(ValidationError):
            AuthzDecision(allowed=True, reason="ok", decided_by="")


class TestDisyuncionConSignal:
    def test_los_campos_de_signal_no_entran_ni_por_descuido(self) -> None:
        # freeze §5: extra="forbid" hace tipo la regla — pasarle campos de un
        # Signal (flagged/score/detector) EXPLOTA, jamás se ignora.
        with pytest.raises(ValidationError):
            AuthzDecision(
                allowed=True,
                reason="ok",
                decided_by="stage:authorization",
                flagged=False,  # type: ignore[call-arg]
            )
        with pytest.raises(ValidationError):
            AuthzDecision(
                allowed=True,
                reason="ok",
                decided_by="stage:authorization",
                score=0.1,  # type: ignore[call-arg]
            )

    def test_no_es_un_signal(self) -> None:
        from blite.guardrails.signal import Signal

        decision = AuthzDecision(
            allowed=True, reason="ok", decided_by="stage:authorization"
        )
        assert not isinstance(decision, Signal)
        # El Signal declara non_decisional=True por tipo; la decisión NO
        # porta ese campo — son disjuntos por construcción.
        assert "non_decisional" not in AuthzDecision.model_fields
