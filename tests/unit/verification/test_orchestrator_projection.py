"""`step_id` top-level + proyección de resultado en `verification.completed`
(V1/M18 — M23a/N3 y C-8).

M23a: la evidencia por paso llegaba `attestations: []` porque el orquestador
nunca hilvanaba el `step_id` que el loop YA le entrega — la ruta
`GET /runs/{id}/steps/{step_id}/evidence` no tenía cómo atribuir la
attestation a su paso.

C-8: el payload de partición viaja EMBEBIDO en `verification.completed`
(trust/07 §1.3 lo fijó así; no es un tipo de evento nuevo). El orquestador
sigue siendo genérico: quien sabe traducir una attestation a payload de
dominio es el CALLER, vía `result_projection`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from blite.verification.attestation import Attestation
from blite.verification.claim import claim_view_digest
from blite.verification.context import InvocationContext
from blite.verification.evidence import Differential, FormalExactPredicate
from blite.verification.orchestrator import (
    ClaimDeclaration,
    make_verification_delegate,
)


class _ContextoConPaso:
    """Lo que el loop entrega de verdad (`PostInvokeContext`): trae `step_id`."""

    run_id = "run-vf"
    domain_id = "domain-a"
    step_id = "step-2"


def _attestation() -> Attestation:
    return Attestation(
        verifier_id="verifier:fake",
        verifier_class="formal_exact",
        anchor_kind="solver",
        level="AL1",
        verdict="pass",
        scope={"instancia": "x"},
        independence_group="leg-formal",
        run_id="run-vf",
        claim_digest=claim_view_digest("enunciado", {"instancia": "x"}),
        verifier_binary_digest="b" * 64,
        verifier_params_digest="p" * 64,
        anchor_digest="a" * 64,
        predicate=FormalExactPredicate(
            differential=Differential(
                status="OPTIMAL", objective=1.0, reference_objective=1.0
            )
        ),
        issued_at=datetime(2026, 8, 5, tzinfo=UTC),
    )


class _Verifier:
    verifier_class = "formal_exact"
    anchor_kind = "solver"
    determinism = "deterministic"

    def verify(self, claim: Any, ctx: InvocationContext) -> Attestation:
        return _attestation()


def _declaration(**extra: Any) -> ClaimDeclaration:
    return ClaimDeclaration(
        claim={"x": 1},
        canonical_statement="enunciado",
        scope={"instancia": "x"},
        claim_type="solution",
        is_conclusion=True,
        **extra,
    )


def _emit(declaration: ClaimDeclaration, ctx: Any) -> list[tuple[str, dict[str, Any]]]:
    delegate = make_verification_delegate(
        verifiers=(_Verifier(),),  # pyright: ignore[reportArgumentType]
        declarations=(declaration,),
    )
    emitted: list[tuple[str, dict[str, Any]]] = []
    delegate(ctx, lambda t, p: emitted.append((t, p)))
    return emitted


def _verification_payload(emitted: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    return next(p for t, p in emitted if t == "verification.completed")


class TestStepIdTopLevel:
    def test_el_step_id_del_loop_viaja_en_el_payload(self) -> None:
        # Act
        emitted = _emit(_declaration(), _ContextoConPaso())

        # Assert
        assert _verification_payload(emitted)["step_id"] == "step-2"

    def test_sin_step_id_la_llave_no_aparece(self) -> None:
        """Honest-empty de campo: ausente, jamás un `null` que la ruta de
        lectura tenga que interpretar."""
        # Arrange — el contexto de verificación puro no tiene paso
        ctx = InvocationContext(
            run_id="run-vf", actor_id="service:runtime", domain_id="domain-a"
        )

        # Act
        emitted = _emit(_declaration(), ctx)

        # Assert
        assert "step_id" not in _verification_payload(emitted)


class TestResultProjection:
    def test_la_proyeccion_del_caller_se_embebe_en_el_payload(self) -> None:
        # Arrange

        def _project(att: Attestation) -> dict[str, Any]:
            return {"partition": {"verdict": att.verdict}}

        declaration = _declaration(result_projection=_project)

        # Act
        emitted = _emit(declaration, _ContextoConPaso())

        # Assert
        assert _verification_payload(emitted)["partition"] == {"verdict": "pass"}

    def test_una_proyeccion_vacia_no_agrega_nada(self) -> None:
        """El caller devuelve `None` cuando la attestation no ampara la
        superficie — el evento queda como estaba, sin llave fabricada."""
        # Arrange

        def _project(_att: Attestation) -> None:
            return None

        declaration = _declaration(result_projection=_project)

        # Act
        emitted = _emit(declaration, _ContextoConPaso())

        # Assert
        assert "partition" not in _verification_payload(emitted)

    def test_sin_proyeccion_el_payload_es_el_de_siempre(self) -> None:
        payload = _verification_payload(_emit(_declaration(), _ContextoConPaso()))
        assert set(payload) == {
            "claim_digest",
            "verifier_id",
            "verdict",
            "attestation",
            "step_id",
            # V2/M19: la latencia se estampa SIEMPRE — es lo que hace que
            # `run.metrics.recorded` se derive del log y no de memoria.
            "latency_ms",
        }

    def test_la_proyeccion_no_puede_pisar_el_binding_de_confianza(self) -> None:
        """Fail-loud: una proyección que reescriba `verdict`/`claim_digest`
        estaría falsificando la constancia desde afuera del verificador."""
        # Arrange

        def _project(_att: Attestation) -> dict[str, Any]:
            return {"verdict": "pass"}

        declaration = _declaration(result_projection=_project)

        # Act / Assert
        with pytest.raises(ValueError, match="reservada"):
            _emit(declaration, _ContextoConPaso())
