"""
Signal (antes GuardrailSignal) — detección probabilística. Informa; jamás verifica.

docs/contract-freeze.md §5: `Signal = {detector, target, score/label,
non_decisional: true}` — tipo DISJUNTO de `Attestation` por firma de función
(S1): lo probabilístico informa, jamás verifica ni satisface egreso
(D18/D21/Inv-E hechos tipo). La numeración "rung 5/6" desaparece con la
escalera; el `kind` usa la convención `{etapa}.{mecanismo}` (trust/16),
catálogo abierto (incl. `unclaimed_assertion`). No existe conversión
Signal→Attestation — un `{flagged: false}` no equivale a un `pass`.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Signal(BaseModel):
    """Una señal de detección probabilística — informa, jamás decide egreso."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    detector: str
    kind: str
    """Convención `{etapa}.{mecanismo}` (trust/16) — ej. `egress.prompt_injection`."""
    target: str
    """Qué señala: digest del claim/contenido observado."""
    flagged: bool
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    label: str | None = None
    non_decisional: Literal[True] = True
    """Hecho tipo: no existe el valor False — la señal jamás decide."""
    detail: dict[str, Any] = Field(default_factory=dict)

    @field_validator("kind")
    @classmethod
    def _kind_con_convencion(cls, v: str) -> str:
        etapa, sep, mecanismo = v.partition(".")
        if not sep or not etapa or not mecanismo:
            msg = f"kind {v!r} no sigue la convención '{{etapa}}.{{mecanismo}}' (trust/16)"
            raise ValueError(msg)
        return v
