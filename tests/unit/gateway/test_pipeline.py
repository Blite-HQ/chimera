"""Pipeline del gateway — freeze §8 [ejecución] + notas execution/01/08.

El orden congelado (C2) es una TUPLA ÚNICA de 8 etapas:
`identity → authorization → guardrails → provenance:pre → mediation →
verification → provenance:post → egress`. El pipeline es explícito e
in-process (jamás middleware), fail-closed: un `Rejection` en cualquier
etapa corta la cadena — en particular, el egreso nunca se alcanza si
`authorization` rechazó (nota 01 §1.3/§11.3, la defensa estructural de Inv-E).
"""

from __future__ import annotations

from typing import Any

import pytest

from blite.gateway.pipeline import (
    STAGE_ORDER,
    Context,
    PassthroughStage,
    Pipeline,
    Rejection,
    Stage,
)


class _RecordingStage:
    """Etapa de prueba que registra su ejecución en el ctx (inmutable: copia)."""

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def handle(self, ctx: Context) -> Context | Rejection:
        executed = [*ctx.get("executed", []), self._name]
        return {**ctx, "executed": executed}


class _RejectingStage:
    """Etapa de prueba que corta la cadena."""

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def handle(self, ctx: Context) -> Context | Rejection:
        return Rejection(stage=self._name, reason="test rejection")


def _stages(overrides: dict[str, Stage] | None = None) -> tuple[Stage, ...]:
    by_name: dict[str, Stage] = {
        name: _RecordingStage(name) for name in STAGE_ORDER
    }
    if overrides:
        by_name.update(overrides)
    return tuple(by_name[name] for name in STAGE_ORDER)


def test_stage_order_is_the_frozen_eight_stage_tuple() -> None:
    # freeze §8: test de orden como tupla única — si esto falla, alguien
    # reordenó el chokepoint.
    assert STAGE_ORDER == (
        "identity",
        "authorization",
        "guardrails",
        "provenance:pre",
        "mediation",
        "verification",
        "provenance:post",
        "egress",
    )


def test_pipeline_executes_all_stages_in_the_frozen_order() -> None:
    pipeline = Pipeline(_stages())

    result = pipeline.run({})

    assert not isinstance(result, Rejection)
    assert tuple(result["executed"]) == STAGE_ORDER


def test_rejection_cuts_the_chain_and_egress_is_never_reached() -> None:
    # nota 01 §11.3: si authz rechaza, el despacho (mediation) NUNCA corre —
    # la propiedad estructural central de Inv-E.
    pipeline = Pipeline(_stages({"authorization": _RejectingStage("authorization")}))

    ctx: dict[str, Any] = {"executed": []}
    result = pipeline.run(ctx)

    assert isinstance(result, Rejection)
    assert result.stage == "authorization"
    # El ctx original no fue tocado después del corte: solo corrió identity.
    assert ctx["executed"] == []


def test_stages_after_the_rejecting_one_never_execute() -> None:
    calls: list[str] = []

    class _Spy:
        def __init__(self, name: str) -> None:
            self._name = name

        @property
        def name(self) -> str:
            return self._name

        def handle(self, ctx: Context) -> Context | Rejection:
            calls.append(self._name)
            if self._name == "guardrails":
                return Rejection(stage=self._name, reason="blocked by guardrail")
            return ctx

    pipeline = Pipeline(tuple(_Spy(name) for name in STAGE_ORDER))
    result = pipeline.run({})

    assert isinstance(result, Rejection)
    assert calls == ["identity", "authorization", "guardrails"]


def test_pipeline_with_wrong_order_fails_closed_at_construction() -> None:
    shuffled = tuple(reversed(_stages()))

    with pytest.raises(ValueError, match="orden congelado"):
        Pipeline(shuffled)


def test_pipeline_with_missing_stage_fails_closed_at_construction() -> None:
    seven = _stages()[:-1]

    with pytest.raises(ValueError, match="orden congelado"):
        Pipeline(seven)


def test_passthrough_stage_is_a_noop_that_satisfies_the_protocol() -> None:
    stage = PassthroughStage("verification")

    assert isinstance(stage, Stage)
    assert stage.name == "verification"
    ctx: dict[str, Any] = {"untouched": True}
    assert stage.handle(ctx) == {"untouched": True}


def test_rejection_is_immutable() -> None:
    rejection = Rejection(stage="authorization", reason="denied")

    with pytest.raises(Exception, match="frozen"):
        rejection.reason = "tampered"
