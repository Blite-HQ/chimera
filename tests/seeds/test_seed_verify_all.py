"""Seed de la extensión del puerto Verifier (C-6/#106 — S-B).

Contrato: freeze §7, marca [MEJORADO C-6/#106]: el puerto gana
`verify_all() -> tuple[Attestation, ...]` con default `= (verify(),)` —
compat total (todo adapter existente hereda el default). La regla semántica
que acompaña — «las islas de una MISMA corrida comparten
independence_group, jamás inflan patas» — es de los implementadores (C4/M4)
y del punto 7 del checklist; este seed fija SOLO la forma del puerto.

VERDE 2026-08-05 (ítem C4/M4): el default vive en
`blite.verification.verifier.Verifier.verify_all`; el camino de los adapters
ESTRUCTURALES (frozen dataclasses que no heredan del Protocol y por eso no
heredan el cuerpo del default) es el helper `verify_all_of`, cubierto en
`tests/unit/verification/test_verify_all_por_isla.py` junto con la regla
semántica y las constancias por isla del `ExecutionVerifier`. El xfail y la
directiva de pyright que lo acompañaba se retiraron juntos, como mandaba
esta nota.
"""

from __future__ import annotations

from typing import Any

import pytest

from blite.verification.context import InvocationContext

pytestmark = [pytest.mark.seed]

_CENTINELA: Any = object()
_CTX = InvocationContext(
    run_id="run:seed", actor_id="service:runtime", domain_id="dom:seed"
)


def test_verify_all_default_envuelve_verify() -> None:
    """Un adapter que solo implementa verify() hereda verify_all == (verify(),)."""
    from blite.verification.verifier import Verifier

    class _Uno(Verifier):
        @property
        def verifier_class(self) -> Any:
            return "ground_truth"

        @property
        def anchor_kind(self) -> Any:
            return "dataset"

        @property
        def determinism(self) -> Any:
            return "deterministic"

        def verify(self, claim: Any, ctx: Any) -> Any:
            return _CENTINELA

    resultado = _Uno().verify_all({"claim": True}, _CTX)
    assert resultado == (_CENTINELA,)
    assert isinstance(resultado, tuple)
