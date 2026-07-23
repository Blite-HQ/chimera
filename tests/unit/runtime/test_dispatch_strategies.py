"""Dispatcher real de Fase 1 — freeze §1 + nota execution/06 §11.

Contrato: `Dispatcher.resolve(execution_profile)` con `InProcessStrategy` como
ÚNICA estrategia real; `service`/`remote-job` existen en el contrato pero sin
estrategia ⇒ `NotImplementedError` explícito, jamás fallback silencioso a
in-process; valor fuera del vocabulario congelado ⇒ `ValueError`.
"""

from __future__ import annotations

from typing import Any

import pytest

from blite.runtime.dispatch import (
    DispatchStrategy,
    InProcessStrategy,
    ProfileDispatcher,
)
from blite_capability.manifest import CapabilityManifest


class _FakeCapability:
    """Doble genérico del puerto Capability (ADR-029: sin términos de escenario)."""

    def __init__(self) -> None:
        self.seen_inputs: dict[str, Any] | None = None

    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id="cap.generic",
            description="generic test capability",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        self.seen_inputs = inputs
        return {"echo": inputs}


def test_resolve_in_process_returns_the_real_strategy() -> None:
    dispatcher = ProfileDispatcher()

    strategy = dispatcher.resolve("in-process")

    assert isinstance(strategy, InProcessStrategy)
    assert isinstance(strategy, DispatchStrategy)


@pytest.mark.parametrize("profile", ["service", "remote-job"])
def test_contract_profiles_without_strategy_explode_explicitly(profile: str) -> None:
    # Nota 06 §11: el mensaje distingue "existe en el contrato" de "no
    # implementado" — jamás fallback silencioso a in-process.
    dispatcher = ProfileDispatcher()

    with pytest.raises(NotImplementedError, match=profile):
        dispatcher.resolve(profile)


def test_profile_outside_the_frozen_vocabulary_raises_value_error() -> None:
    dispatcher = ProfileDispatcher()

    with pytest.raises(ValueError, match="vocabulario congelado"):
        dispatcher.resolve("lambda")


def test_in_process_execute_is_a_direct_function_call() -> None:
    capability = _FakeCapability()
    strategy = InProcessStrategy()

    result = strategy.execute(capability, {"x": 1})

    # in-process retorna el Result directo de invoke() — nunca un JobRef
    # (JobRef es lo ÚNICO que remote-job puede retornar, freeze §1).
    assert result == {"echo": {"x": 1}}
    assert capability.seen_inputs == {"x": 1}
