"""
InvocationContext — the minimal, frozen context a Verifier receives.

Mirrors docs/especificacion-contratos.md SS2 (runId/actor/domainId) without
depending on the full Identity contract (built in a later piece of this
session) — Verifier only needs to know who is asking and in which run/domain.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class InvocationContext(BaseModel):
    """Immutable context passed to a Verifier.verify() call."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    actor_id: str
    domain_id: str
