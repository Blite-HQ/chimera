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

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from blite.verification.attestation import Attestation
from blite.verification.claim import ClaimEmittedPayload, claim_view_digest
from blite.verification.context import InvocationContext
from blite.verification.verifier import Verifier

_RUNTIME_ACTOR = "service:runtime"

_RESERVED_PAYLOAD_KEYS = frozenset(
    {"claim_digest", "verifier_id", "verdict", "attestation", "step_id"}
)
"""El binding de confianza del evento. Una proyección del caller EXTIENDE el
payload; jamás reescribe lo que el verificador dictó — eso sería falsificar la
constancia desde afuera."""

AppendEvent = Callable[[str, dict[str, Any]], None]


class RunContextLike(Protocol):
    """Lo mínimo que el delegate necesita del contexto del run (duck-typed:
    lo satisfacen tanto el `PostInvokeContext` del loop como el
    `InvocationContext` de verificación).

    `step_id` NO entra al Protocol a propósito: solo el contexto del loop lo
    tiene, y el `InvocationContext` (espejo congelado de freeze §8) no se
    extiende por comodidad de este módulo. Se lee de forma oportunista — ver
    `_step_id_of`.
    """

    run_id: str
    domain_id: str


ResultProjection = Callable[[Attestation], Mapping[str, Any] | None]
"""Traduce una attestation ya emitida al payload de superficie que su dominio
consume (C-8: la partición viaja EMBEBIDA en `verification.completed`, no como
evento nuevo). Vive en el caller — el orquestador no sabe de dominios; devolver
`None` es la respuesta honesta cuando la attestation no ampara esa superficie.
"""


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
    result_projection: ResultProjection | None = None


VerificationDelegate = Callable[[RunContextLike, AppendEvent], None]


def _step_id_of(ctx: RunContextLike) -> str | None:
    """El paso que produjo el resultado, si el contexto lo trae (M23a/N3).

    Sin esto la evidencia por paso llegaba `attestations: []`: la ruta de
    lectura filtra por `step_id` y el orquestador nunca lo hilvanaba, aunque
    el loop se lo pasa desde siempre.
    """
    step_id: object = getattr(ctx, "step_id", None)
    return step_id if isinstance(step_id, str) and step_id else None


def _projected(
    declaration: ClaimDeclaration, attestation: Attestation
) -> dict[str, Any]:
    if declaration.result_projection is None:
        return {}
    extra = declaration.result_projection(attestation)
    if not extra:
        return {}
    colisiones = sorted(_RESERVED_PAYLOAD_KEYS.intersection(extra))
    if colisiones:
        msg = (
            f"la proyección de resultado intentó escribir la llave reservada "
            f"{colisiones} — el binding de confianza lo dicta el verificador"
        )
        raise ValueError(msg)
    return dict(extra)


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

    El payload lleva además `step_id` cuando el contexto lo trae (M23a/N3) y
    lo que la `result_projection` de la declaración devuelva (C-8: la
    partición viaja embebida acá). Ambos son ADITIVOS: el binding de confianza
    (`claim_digest`/`verifier_id`/`verdict`/`attestation`) es intocable.
    """

    def _delegate(ctx: RunContextLike, append: AppendEvent) -> None:
        invocation_ctx = InvocationContext(
            run_id=ctx.run_id, actor_id=_RUNTIME_ACTOR, domain_id=ctx.domain_id
        )
        step_id = _step_id_of(ctx)
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
                attestation = verifier.verify(declaration.claim, invocation_ctx)
                verification: dict[str, Any] = {
                    "claim_digest": attestation.claim_digest,
                    "verifier_id": attestation.verifier_id,
                    "verdict": attestation.verdict,
                    "attestation": attestation.model_dump(mode="json"),
                }
                if step_id is not None:
                    verification["step_id"] = step_id
                verification.update(_projected(declaration, attestation))
                append("verification.completed", verification)

    return _delegate
