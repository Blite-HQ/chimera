"""Seed de la extensión del puerto Verifier (C-6/#106 — S-B).

Contrato: freeze §7, marca [MEJORADO C-6/#106]: el puerto gana
`verify_all() -> tuple[Attestation, ...]` con default `= (verify(),)` —
compat total (todo adapter existente hereda el default). La regla semántica
que acompaña — «las islas de una MISMA corrida comparten independence_group,
jamás inflan patas» — es de los implementadores (C4/M4) y del punto 7 del
checklist; este seed fija SOLO la forma del puerto.
Implementación = ítem C4/M4 (Fase 1).

Directiva pyright per-file: el método objetivo no existe por diseño hasta
Fase 1; la directiva se retira junto con el xfail.
"""

# pyright: reportAttributeAccessIssue=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false

from __future__ import annotations

from typing import Any

import pytest

pytestmark = [
    pytest.mark.seed,
    pytest.mark.xfail(
        strict=False,
        reason=(
            "Fase 1 C4/M4: Verifier.verify_all no existe todavía — freeze §7 "
            "marca [MEJORADO C-6/#106]"
        ),
    ),
]

_CENTINELA: Any = object()


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

    resultado = _Uno().verify_all({"claim": True}, None)
    assert resultado == (_CENTINELA,)
    assert isinstance(resultado, tuple)
