"""
GuardrailSignal — probabilistic detection. Informs; never verifies.

docs/contract-freeze.md SS5 / knowledge/trust/04-anclas-duras-mapa-oraculos.md
SS1.3. Disjoint type from blite.verification.attestation.Attestation: rung is
restricted to {5,6} (consensus/model detection), the exact complement of
Attestation's {1,2,3,4,7}. D18/D21/Inv-E: a GuardrailSignal never satisfies
an egress decision and never becomes an Attestation — there is no conversion.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

GuardrailRung = Literal[5, 6]
"""The escalera rungs that are detection, not verification (SS1.1)."""


class GuardrailSignal(BaseModel):
    """A probabilistic detection signal — informs, never decides egress."""

    model_config = ConfigDict(frozen=True)

    name: str
    flagged: bool
    confidence: float = Field(ge=0.0, le=1.0)
    rung: GuardrailRung
    detail: dict[str, Any] = Field(default_factory=dict)
