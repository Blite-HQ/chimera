"""
GatewayContext — el ctx del chokepoint, CONGELADO. [S-G · Steven + Dylan]

Acuerdo 2026-07-22 (mensaje de Dylan al publicar `AuthzDecision`): con
`Identity` (freeze §8) y `AuthzDecision` (freeze §5/EX-14) reales, el ctx
deja de ser el dict provisional de nota 01 §10 y se congela como modelo
inmutable. La regla "un `{flagged: false}` no equivale a un pass" queda
hecha TIPO: el campo `authz` solo acepta `AuthzDecision` — un `Signal` (o
cualquier dict con `flagged`/`score`) explota en validación, jamás se
interpreta como decisión.

Cada etapa retorna un ctx NUEVO vía `model_copy(update=...)` — la
inmutabilidad por copia de nota 01 deja de ser convención y pasa a ser
`frozen=True`.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from blite.authz import AuthzDecision
from blite.identity.identity import Identity


class GatewayContext(BaseModel):
    """Lo que viaja por las 8 etapas del Pipeline (freeze §8)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    identity: Identity
    """El actor atribuible (AX1) — lo estampa la etapa `identity`."""

    capability_id: str
    """Qué se invoca — el despacho resuelve por VALOR, jamás por escenario."""

    inputs: dict[str, Any]
    """Entrada genérica de la invocación (ADR-029)."""

    authz: AuthzDecision | None = None
    """La decisión de `authorization` — lo ÚNICO que el egreso sabe leer
    (Inv-E). None = la etapa aún no corrió: el egreso lo trata como rechazo."""

    outputs: dict[str, Any] | None = None
    """Resultado del despacho — lo estampa `mediation`."""
