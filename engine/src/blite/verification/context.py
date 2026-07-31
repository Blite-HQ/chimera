"""
InvocationContext — the minimal, frozen context a Verifier receives.

Mirrors docs/contract-freeze.md SS8 (runId/actor/domainId; TS mirror in
docs/especificacion-contratos-v2.md) without depending on the full Identity
contract — Verifier only needs to know who is asking and in which run/domain.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class InvocationContext(BaseModel):
    """Immutable context passed to a Verifier.verify() call."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    actor_id: str
    domain_id: str
