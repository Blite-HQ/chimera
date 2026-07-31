"""Plan como artefacto en el stream — freeze §14 (`●PlanCreated`), decisión
#66 registrada en el ledger (#94: sin gate por persona). [S-G · A3]

docs/specs/harness-agentico.md §Contrato-2: el agente jamás reescribe el plan
in-place (INV-5, append-only) — `plan.created` es el evento fundacional
(1:1 con el run, emitido antes del primer step que cubre) y `plan.item_updated`
es la ÚNICA forma de anunciar una transición de un ítem. Ambos modelos viven
aquí, mismo home conceptual que `RunStep` en `runtime/loop.py`: viajan COMO
payload de eventos, jamás en un almacén propio.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

PlanItemStatus = Literal["pending", "running", "ok", "failed"]
"""Conjunto CERRADO — misma disciplina que `RunStep.status` (freeze §3): un
valor fuera de este vocabulario es un error de contrato, no un string libre."""


class PlanItem(BaseModel):
    """Un ítem del plan — unidad mínima que el certificado puede citar como
    "qué se planeó" frente a "qué se ejecutó" (freeze §2, `provenance_hash`)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    description: str
    verification: str
    status: PlanItemStatus


class PlanCreatedPayload(BaseModel):
    """`plan.created` ↔ `●PlanCreated` — el fundacional del plan, 1:1 con el
    run, emitido antes del primer step que cubre."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    plan_id: str
    run_id: str
    items: tuple[PlanItem, ...]


class PlanItemUpdatedPayload(BaseModel):
    """`plan.item_updated` ↔ `●PlanItemUpdated` — una emisión por transición
    de ítem, append-only (replanificar = un evento nuevo con causa, jamás una
    reescritura del ítem original)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    plan_id: str
    run_id: str
    item_id: str
    status: PlanItemStatus
    cause: str | None = None
