"""Aprobación humana estilo elicitation MCP — A6 (`docs/specs/harness-agentico.md`
§Contrato-6). [S-G · A6]

Par `approval.requested`/`approval.responded` (freeze §14, `●ApprovalRequested`/
`●ApprovalResponded` — nuevo en catálogo, misma ceremonia #66 (#94: sin gate
por persona)): request→response tipado y replay-able, mismo home conceptual que
`OverridePayload` (freeze §10) — el Stage que la abre emite su propio evento
(INV-4), esta suite solo cubre la FORMA de los payloads y la validación de
`authorized_by`, no el wiring del Stage (frontera Steven — "qué estampa cada
payload").

`authorized_by` es una URN `user:*` que debe portar `override:apply:<scope>`
en su intersección efectiva (freeze §8/§10) — MISMA maquinaria de
`AuthzDecision`/`Identity` que ya gobierna el egreso; cero infra nueva
(`OverridePayload` en sí no existe todavía como código — grep confirmado
antes de escribir este módulo — así que lo que se reusa es el sustrato de
permisos (`Identity.permissions`, `AuthzDecision`) que esa maquinaria
comparte, no un tipo que aún no existe).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from blite.authz import AuthzDecision
from blite.gateway.approval import (
    ApprovalRequestedPayload,
    ApprovalRespondedPayload,
    authorize_approval_response,
)
from blite.identity.identity import Identity


def _identity(
    *,
    id_: str = "user:dylan",
    kind: str = "human",
    permissions: frozenset[str] = frozenset({"override:apply:run"}),
) -> Identity:
    return Identity(
        id=id_,
        kind=kind,  # type: ignore[arg-type]
        domain_id="domain-a",
        permissions=permissions,
    )


class TestApprovalRequestedShape:
    def test_forma_completa_con_step_id(self) -> None:
        payload = ApprovalRequestedPayload(
            run_id="run-1",
            approval_id="approval-1",
            json_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
            prompt="¿Autorizar la relajación de PR2 para esta corrida?",
            step_id="item-2",
        )
        assert payload.run_id == "run-1"
        assert payload.approval_id == "approval-1"
        assert payload.step_id == "item-2"
        assert payload.json_schema["type"] == "object"

    def test_step_id_es_opcional(self) -> None:
        payload = ApprovalRequestedPayload(
            run_id="run-1",
            approval_id="approval-1",
            json_schema={"type": "object"},
            prompt="¿Continuar?",
        )
        assert payload.step_id is None

    def test_es_frozen(self) -> None:
        payload = ApprovalRequestedPayload(
            run_id="run-1",
            approval_id="approval-1",
            json_schema={"type": "object"},
            prompt="¿Continuar?",
        )
        with pytest.raises(ValidationError, match="frozen"):
            payload.prompt = "tampered"

    def test_forbid_extra_rechaza_campos_de_otro_evento(self) -> None:
        # Un campo de plan.created (p. ej. `items`) NO se cuela por descuido.
        with pytest.raises(ValidationError, match="extra"):
            ApprovalRequestedPayload(
                run_id="run-1",
                approval_id="approval-1",
                json_schema={"type": "object"},
                prompt="¿Continuar?",
                items=[],  # type: ignore[call-arg]
            )


class TestApprovalRespondedShape:
    def test_forma_completa(self) -> None:
        payload = ApprovalRespondedPayload(
            run_id="run-1",
            approval_id="approval-1",
            response={"ok": True},
            authorized_by="user:dylan",
        )
        assert payload.response == {"ok": True}
        assert payload.authorized_by == "user:dylan"

    def test_response_es_valor_libre_no_solo_dict(self) -> None:
        # forma "elicitation" MCP: el humano llena `response` contra el
        # json_schema del request — puede ser bool/str/número, no solo objeto.
        payload = ApprovalRespondedPayload(
            run_id="run-1",
            approval_id="approval-1",
            response=True,
            authorized_by="user:dylan",
        )
        assert payload.response is True

    def test_es_frozen(self) -> None:
        payload = ApprovalRespondedPayload(
            run_id="run-1",
            approval_id="approval-1",
            response={"ok": True},
            authorized_by="user:dylan",
        )
        with pytest.raises(ValidationError, match="frozen"):
            payload.response = {"ok": False}

    def test_forbid_extra(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            ApprovalRespondedPayload(
                run_id="run-1",
                approval_id="approval-1",
                response={"ok": True},
                authorized_by="user:dylan",
                step_id="item-2",  # type: ignore[call-arg]
            )

    def test_authorized_by_debe_ser_urn_user(self) -> None:
        # freeze §10 (AX2): el autorizador es SIEMPRE user:* — nunca agent:*
        # ni service:* — la relajación exige responsable humano identificable.
        with pytest.raises(ValidationError, match="pattern|string_pattern_mismatch"):
            ApprovalRespondedPayload(
                run_id="run-1",
                approval_id="approval-1",
                response={"ok": True},
                authorized_by="agent:planner-7",
            )
        with pytest.raises(ValidationError, match="pattern|string_pattern_mismatch"):
            ApprovalRespondedPayload(
                run_id="run-1",
                approval_id="approval-1",
                response={"ok": True},
                authorized_by="service:runtime",
            )


class TestRoundTripRequestResponse:
    def test_el_par_correlaciona_por_run_id_y_approval_id(self) -> None:
        requested = ApprovalRequestedPayload(
            run_id="run-1",
            approval_id="approval-1",
            json_schema={"type": "object"},
            prompt="¿Autorizar?",
            step_id="item-2",
        )
        responded = ApprovalRespondedPayload(
            run_id=requested.run_id,
            approval_id=requested.approval_id,
            response={"ok": True},
            authorized_by="user:dylan",
        )
        assert responded.run_id == requested.run_id
        assert responded.approval_id == requested.approval_id


class TestAuthorizeApprovalResponse:
    """`authorize_approval_response` — reusa `Identity.permissions`/
    `AuthzDecision` (freeze §8/§10), cero parsing de scopes nuevo."""

    def test_pasa_cuando_la_identidad_porta_override_apply_del_scope(self) -> None:
        payload = ApprovalRespondedPayload(
            run_id="run-1",
            approval_id="approval-1",
            response={"ok": True},
            authorized_by="user:dylan",
        )
        identity = _identity(permissions=frozenset({"override:apply:run"}))

        decision = authorize_approval_response(payload, identity, scope="run")

        assert isinstance(decision, AuthzDecision)
        assert decision.allowed is True
        assert decision.decided_by == "gateway.approval"

    def test_rechazo_fail_closed_sin_el_permiso_del_scope(self) -> None:
        payload = ApprovalRespondedPayload(
            run_id="run-1",
            approval_id="approval-1",
            response={"ok": True},
            authorized_by="user:dylan",
        )
        # Porta el scope equivocado (domain, no run) — fail-closed, no basta
        # "algún" override:apply:*.
        identity = _identity(permissions=frozenset({"override:apply:domain"}))

        decision = authorize_approval_response(payload, identity, scope="run")

        assert isinstance(decision, AuthzDecision)
        assert decision.allowed is False
        assert "override:apply:run" in decision.reason

    def test_rechazo_fail_closed_sin_ningun_permiso(self) -> None:
        payload = ApprovalRespondedPayload(
            run_id="run-1",
            approval_id="approval-1",
            response={"ok": True},
            authorized_by="user:dylan",
        )
        identity = _identity(permissions=frozenset())

        decision = authorize_approval_response(payload, identity, scope="global")

        assert decision.allowed is False

    def test_rechazo_fail_closed_cuando_la_identidad_no_coincide_con_authorized_by(
        self,
    ) -> None:
        # Defensa en profundidad (mismo espíritu que mediation/egress): quien
        # responde debe SER la identidad que el payload declara, no solo
        # portar el permiso correcto bajo otro nombre.
        payload = ApprovalRespondedPayload(
            run_id="run-1",
            approval_id="approval-1",
            response={"ok": True},
            authorized_by="user:dylan",
        )
        identity = _identity(
            id_="user:other", permissions=frozenset({"override:apply:run"})
        )

        decision = authorize_approval_response(payload, identity, scope="run")

        assert decision.allowed is False
        assert "user:dylan" in decision.reason

    def test_rechazo_fail_closed_si_la_identidad_no_es_humana(self) -> None:
        # AX2: la URN user:* debe corresponder a un actor kind=human — un
        # agent/service que se hiciera pasar por user:* (dato inconsistente)
        # tampoco satisface la autoridad de override.
        payload = ApprovalRespondedPayload(
            run_id="run-1",
            approval_id="approval-1",
            response={"ok": True},
            authorized_by="user:dylan",
        )
        identity = _identity(
            id_="user:dylan",
            kind="agent",
            permissions=frozenset({"override:apply:run"}),
        )

        decision = authorize_approval_response(payload, identity, scope="run")

        assert decision.allowed is False

    @pytest.mark.parametrize("scope", ["run", "domain", "global"])
    def test_los_tres_scopes_cerrados_funcionan(self, scope: str) -> None:
        payload = ApprovalRespondedPayload(
            run_id="run-1",
            approval_id="approval-1",
            response={"ok": True},
            authorized_by="user:dylan",
        )
        identity = _identity(permissions=frozenset({f"override:apply:{scope}"}))

        decision = authorize_approval_response(payload, identity, scope=scope)  # type: ignore[arg-type]

        assert decision.allowed is True
