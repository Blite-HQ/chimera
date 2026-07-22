"""
Verifier — el puerto que implementa todo adapter de ancla dura. Vocabulario §4.

docs/contract-freeze.md §4: `Verifier(Protocol)` = `verifier_class` +
`determinism` + `verify(claim, ctx) -> Attestation`. El campo `rung: int`
DESAPARECE (la escalera quedó supersedida). En no-deterministas la
rerun_policy aplica a AMBOS veredictos. La distinción dura: **error de
proceso NO emite Attestation** — `verdict: "fail"` es un veredicto sobre el
claim, jamás una falla del verificador.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable

from blite.verification.anchor import AnchorKind
from blite.verification.attestation import Attestation, VerifierClass
from blite.verification.context import InvocationContext

Determinism = Literal["deterministic", "nondeterministic"]


@runtime_checkable
class Verifier(Protocol):
    """Adapter de ancla dura: contrasta un claim contra un oráculo no-modelo."""

    verifier_class: VerifierClass
    anchor_kind: AnchorKind
    determinism: Determinism

    def verify(self, claim: Any, ctx: InvocationContext) -> Attestation:
        """Verifica `claim` y devuelve una constancia — un error de proceso
        levanta excepción; jamás se disfraza de `fail`."""
        ...
