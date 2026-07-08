"""
Verifier — the port every hard anchor adapter implements.

docs/contract-freeze.md SS4 / knowledge/trust/03-escalera-verificacion-metodos.md
SS1.2. `anchor_kind` is never "model" (AnchorKind excludes it by construction);
`rung` records which step of the 1-7 ladder this verifier occupies.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from blite.verification.anchor import AnchorKind
from blite.verification.attestation import Attestation, AttestationRung
from blite.verification.context import InvocationContext


@runtime_checkable
class Verifier(Protocol):
    """A hard-anchor adapter: contrasts a claim against a non-model oracle."""

    anchor_kind: AnchorKind
    rung: AttestationRung

    def verify(self, claim: Any, ctx: InvocationContext) -> Attestation:
        """Verify `claim` and return a constancy — never raises to signal fail."""
        ...
