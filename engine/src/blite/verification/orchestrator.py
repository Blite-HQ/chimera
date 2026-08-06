"""
Orquestador de verificación — el emisor de `claim.emitted` y
`verification.completed` (freeze §3/§6). [S-G · costura loop↔confianza]

El loop NO verifica (INV-2): ofrece la costura `post_invoke` y ESTE módulo
fabrica el delegate que la ocupa. Orden canónico (gen-example-bundle):
`claim.emitted` → `verification.completed` → terminal — todo DENTRO del
corte de procedencia, o el certificado no lo ampara.

Reglas duras:
- El claim viaja con sus portadores (`ClaimEmittedPayload` §14): quien emite
  estampa los flags; la criticidad se COMPUTA río abajo, no se declara.
- El binding claim↔attestation es el `claim_digest` (mismo helper
  `claim_view_digest` en ambos extremos — §7).
- Error de proceso del verificador PROPAGA (error ≠ fail): el loop lo
  registra como `run.failed` fail-loud; jamás se disfraza de verdict.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from blite.verification.claim import ClaimEmittedPayload, claim_view_digest
from blite.verification.context import InvocationContext
from blite.verification.verifier import Verifier, verify_all_of

_RUNTIME_ACTOR = "service:runtime"

AppendEvent = Callable[[str, dict[str, Any]], None]


class RunContextLike(Protocol):
    """Lo mínimo que el delegate necesita del contexto del run (duck-typed:
    lo satisfacen tanto el `PostInvokeContext` del loop como el
    `InvocationContext` de verificación)."""

    run_id: str
    domain_id: str


@dataclass(frozen=True)
class ClaimDeclaration:
    """Lo que el caller declara sobre un claim a verificar — datos, no juicio."""

    claim: Any
    canonical_statement: str
    scope: dict[str, Any]
    claim_type: str
    is_conclusion: bool
    world: bool = False
    irreversible: bool = False
    affects_third_party: bool = False


VerificationDelegate = Callable[[RunContextLike, AppendEvent], None]


def make_verification_delegate(
    *,
    verifiers: Sequence[Verifier],
    declarations: Sequence[ClaimDeclaration],
) -> VerificationDelegate:
    """Fabrica el delegate para la costura `post_invoke` del loop.

    Por cada declaración: emite `claim.emitted` (portadores §14) y una
    `verification.completed` por verificador, con la attestation completa en
    el payload — la doctrina "los eventos son la única fuente de verdad"
    exige que la constancia viva en el log, no en memoria del caller.
    """

    def _delegate(ctx: RunContextLike, append: AppendEvent) -> None:
        invocation_ctx = InvocationContext(
            run_id=ctx.run_id, actor_id=_RUNTIME_ACTOR, domain_id=ctx.domain_id
        )
        for declaration in declarations:
            digest = claim_view_digest(
                declaration.canonical_statement, declaration.scope
            )
            payload = ClaimEmittedPayload(
                claim_digest=digest,
                claim_type=declaration.claim_type,
                is_conclusion=declaration.is_conclusion,
                world=declaration.world,
                irreversible=declaration.irreversible,
                affects_third_party=declaration.affects_third_party,
            )
            append("claim.emitted", payload.model_dump())
            for verifier in verifiers:
                # `verify_all_of` (C4/M4 · C-6/#106): un verificador con
                # granularidad emite UNA constancia por sub-entidad (las islas
                # del ExecutionVerifier); el resto sigue emitiendo la suya
                # única por el default del puerto. El conteo de patas del
                # punto 7 no cambia: todas comparten `independence_group`.
                for attestation in verify_all_of(
                    verifier, declaration.claim, invocation_ctx
                ):
                    append(
                        "verification.completed",
                        {
                            "claim_digest": attestation.claim_digest,
                            "verifier_id": attestation.verifier_id,
                            "verdict": attestation.verdict,
                            "attestation": attestation.model_dump(mode="json"),
                        },
                    )

    return _delegate
