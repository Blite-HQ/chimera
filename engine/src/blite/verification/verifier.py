"""
Verifier — el puerto que implementa todo adapter de ancla dura. Vocabulario §4.

docs/contract-freeze.md §4: `Verifier(Protocol)` = `verifier_class` +
`determinism` + `verify(claim, ctx) -> Attestation`. La confianza se expresa
como clase de verificador + AL (freeze §4). En no-deterministas la
rerun_policy aplica a AMBOS veredictos. La distinción dura: **error de
proceso NO emite Attestation** — `verdict: "fail"` es un veredicto sobre el
claim, jamás una falla del verificador.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, Literal, Protocol, cast, runtime_checkable

from blite.verification.anchor import AnchorKind
from blite.verification.attestation import Attestation, VerifierClass
from blite.verification.context import InvocationContext

Determinism = Literal["deterministic", "nondeterministic"]


def verify_all_of(
    verifier: Any, claim: Any, ctx: InvocationContext
) -> tuple[Attestation, ...]:
    """`verify_all()` aplicado desde AFUERA — el camino que usan los
    llamadores (orquestador incluido).

    Existe porque los adapters del repo satisfacen `Verifier`
    ESTRUCTURALMENTE (frozen dataclasses que no heredan del Protocol) y por
    lo tanto NO heredan el cuerpo del default de arriba: sin este helper,
    «compat total» sería falso justo para los adapters que existen. La regla
    es la misma en los dos lados — quien implemente `verify_all` manda;
    quien no, emite su constancia única."""
    metodo = cast(
        "Callable[[Any, InvocationContext], Iterable[Attestation]] | None",
        getattr(verifier, "verify_all", None),
    )
    if metodo is not None:
        return tuple(metodo(claim, ctx))
    return (cast("Attestation", verifier.verify(claim, ctx)),)


@runtime_checkable
class Verifier(Protocol):
    """Adapter de ancla dura: contrasta un claim contra un oráculo no-modelo.

    Los miembros son properties READ-ONLY: un adapter congelado (frozen
    dataclass) debe poder conformar — exigir atributos escribibles
    contradiría la inmutabilidad que el resto del plano impone.
    """

    @property
    def verifier_class(self) -> VerifierClass: ...

    @property
    def anchor_kind(self) -> AnchorKind: ...

    @property
    def determinism(self) -> Determinism: ...

    def verify(self, claim: Any, ctx: InvocationContext) -> Attestation:
        """Verifica `claim` y devuelve una constancia — un error de proceso
        levanta excepción; jamás se disfraza de `fail`."""
        ...

    def verify_all(self, claim: Any, ctx: InvocationContext) -> tuple[Attestation, ...]:
        """Todas las constancias que este verificador puede emitir sobre el
        claim — una por sub-entidad del resultado cuando la granularidad
        existe (freeze §7 [MEJORADO C-6/#106]).

        Default = `(verify(),)`: compat total, ningún adapter existente
        cambia. **Regla semántica que acompaña al puerto:** las constancias
        de una MISMA corrida comparten `independence_group` — partir un
        verdict en N no crea N patas independientes (extensión del punto 7
        del checklist; el conteo de patas es por grupo)."""
        return (self.verify(claim, ctx),)
