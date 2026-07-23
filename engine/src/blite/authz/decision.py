"""
AuthzDecision — el único tipo que la etapa de egreso acepta. [S-F/EX-14]

docs/contract-freeze.md §5 (refuerzo estructural, execution/01): la firma de
la etapa de egreso acepta `AuthzDecision`, **no puede recibir `Signal`** —
un `{flagged: false}` no equivale a un `pass` ni por descuido de tipos
(S1/Inv-E hechos firma). Tipo DISJUNTO de `Signal` por construcción: no
porta `non_decisional`, no porta score/flagged, y `extra="forbid"` hace que
un campo de Signal EXPLOTE en vez de ignorarse. Letra: semilla v2
(`especificacion-contratos-v2.md` — `AuthzDecision`); esta traducción
Pydantic es la verdad ejecutable.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AuthzDecision(BaseModel):
    """La decisión de la etapa authorization — gobierna el egreso (PR3/AX1b)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    allowed: bool
    reason: str = Field(min_length=1)
    """Fail-closed honesto: una decisión sin razón es un default disfrazado."""
    decided_by: str = Field(min_length=1)
    """La etapa authorization — jamás un Detector ni un Verifier."""
