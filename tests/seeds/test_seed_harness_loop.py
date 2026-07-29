"""SEED · A · Harness — loop agéntico: plan como artefacto + terminación triple.

docs/specs/harness-agentico.md (spec de costura A↔E↔D, decisión #66 — PENDIENTE
ratificación de Steven). Collection-safe: ningún import de `blite`/`chimera_api`
a nivel de módulo — cada test importa dentro de su cuerpo, así el archivo se
colecta aunque los módulos origen todavía no existan (Fase 0 entrega spec+seed,
no la feature — docs/specs/README.md §"Specs de costura").
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest

if TYPE_CHECKING:
    from blite.runtime.plan import PlanItemStatus

pytestmark = [pytest.mark.seed]
"""A3 (plan.created/plan.item_updated, max_turns/budget, EXHAUSTED_ERROR_KIND)
y A4 (sub_run_id en ClaimEmittedPayload) implementados — los 5 tests de este
seed pasan en verde; el `xfail` se retira (docs/specs/README.md §"Specs de
costura": el dueño implementa y quita el xfail al cerrar)."""


def test_plan_created_payload_shape_and_closed_status_set() -> None:
    """freeze §14 (●PlanCreated) + docs/specs/harness-agentico.md §Contrato-2.

    `plan.created` porta `{plan_id, run_id, items: [{id, description,
    verification, status}]}`, con `status` en el conjunto CERRADO
    `{pending, running, ok, failed}` — la misma disciplina que
    `RunStep.status` (freeze §3). Verde cuando Steven emita el evento desde
    el loop y Dylan publique `blite.runtime.plan.PlanCreatedPayload`.
    """
    from blite.runtime.plan import PlanCreatedPayload, PlanItem

    item = PlanItem(
        id="item-1",
        description="formular QUBO del corte máximo",
        verification="formal_exact",
        status="pending",
    )
    payload = PlanCreatedPayload(plan_id="plan-1", run_id="run-1", items=(item,))
    assert payload.run_id == "run-1"
    assert payload.items[0].status == "pending"

    with pytest.raises(ValueError):
        PlanItem(
            id="item-2",
            description="fuera del conjunto cerrado",
            verification="formal_exact",
            status=cast("PlanItemStatus", "bogus"),
        )


def test_plan_item_updated_payload_shape_with_optional_cause() -> None:
    """freeze §14 + docs/specs/harness-agentico.md §Contrato-2/§Eventos.

    `plan.item_updated` porta `{plan_id, run_id, item_id, status, cause?}` —
    la única mitad del par que el agente puede emitir en cada transición de
    ítem (replanificar = append con causa, nunca reescritura in-place,
    INV-5). Verde cuando Dylan publique
    `blite.runtime.plan.PlanItemUpdatedPayload` y Steven la emita desde el
    loop.
    """
    from blite.runtime.plan import PlanItemUpdatedPayload

    without_cause = PlanItemUpdatedPayload(
        plan_id="plan-1", run_id="run-1", item_id="item-1", status="running"
    )
    assert without_cause.cause is None

    with_cause = PlanItemUpdatedPayload(
        plan_id="plan-1",
        run_id="run-1",
        item_id="item-1",
        status="failed",
        cause="capability.job.failed",
    )
    assert with_cause.cause == "capability.job.failed"


def test_execute_run_signature_gains_max_turns_and_budget() -> None:
    """freeze §3 (max_steps obligatorio) + docs/specs/harness-agentico.md
    §Contrato-3 (terminación triple).

    `max_turns` (~30, cota del loop agéntico) y `budget` (tokens/costo,
    declarado en `run.created`) son PARÁMETROS NUEVOS de `execute_run` —
    distintos de `max_steps` (cota estructural sobre cada `RunStep`, ya
    obligatoria): por construcción `max_turns <= max_steps`. Verde cuando
    Steven extienda la firma de `execute_run` (blite.runtime.loop).
    """
    import inspect

    from blite.runtime.loop import execute_run

    parameters = inspect.signature(execute_run).parameters
    assert "max_turns" in parameters
    assert "budget" in parameters


def test_exhausted_error_kind_constant_declared() -> None:
    """docs/specs/harness-agentico.md §Contrato-3.

    Agotar `max_turns` o `budget` ⇒ terminal
    `run.failed {error_kind: "exhausted"}` — JAMÁS un `run.completed`
    implícito. `EXHAUSTED_ERROR_KIND` convive con `MAX_STEPS_EXCEEDED`
    (ya en `blite.runtime.loop`): dos guards distintos, dos error_kind
    distintos, mismo campo `str` libre (freeze §3). Verde cuando Steven
    declare la constante y el guard la emita.
    """
    from blite.runtime import loop

    assert hasattr(loop, "EXHAUSTED_ERROR_KIND")
    assert loop.EXHAUSTED_ERROR_KIND == "exhausted"


def test_claim_emitted_payload_gains_sub_run_id_field() -> None:
    """freeze §13 (Las 3 reglas del run jerárquico, regla 2) +
    docs/specs/harness-agentico.md §Contrato-4.

    `●ClaimEmitted` YA exige `{claim_digest, sub_run_id,
    sub_run_provenance_hash}` en el freeze congelado — el hash encadena la
    integridad, el id correlaciona el sub-run con el claim que aportó.
    `ClaimEmittedPayload` (blite.verification.claim) hoy solo declara
    `sub_run_provenance_hash`: esto es un campo FALTANTE contra un contrato
    ya vigente, no una decisión nueva. Verde cuando Dylan añada el campo.
    """
    from blite.verification.claim import ClaimEmittedPayload

    assert "sub_run_id" in ClaimEmittedPayload.model_fields
