"""
Identity — a stable, URN-shaped actor reference (AX1).

docs/contract-freeze.md SS8 / knowledge/trust/08-identidad-lite-kagenti.md
SS1.3: the SPIFFE-ID shape without the SPIFFE infrastructure — `id` migrates
cleanly to a real SPIFFE path in Fase 2 (the reserved `spiffe_id` field) with
no contract change.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_URN_PATTERN = r"^(user|agent|service):[a-z0-9-]+$"


class Identity(BaseModel):
    """A single, unambiguously attributable actor (AX1)."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=_URN_PATTERN)
    kind: Literal["human", "agent", "service"]
    domain_id: str
    permissions: frozenset[str]
    spiffe_id: str | None = None
