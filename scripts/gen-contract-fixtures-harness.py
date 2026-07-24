#!/usr/bin/env python3
"""Genera los fixtures de contrato de costura del harness (spec
`docs/specs/harness-agentico.md` §"Tests de contrato"; convención
`docs/specs/README.md` §"Fixtures de costura — un solo origen").

ORIGEN ÚNICO = los modelos Pydantic del engine (A2-A6). De cada uno emite un
ejemplo canónico a `tests/fixtures/contract/harness/<caso>.json` y lo ESPEJA
byte-idéntico a `apps/studio/src/fixtures/contract/harness/<caso>.json` (Vite
solo importa dentro de `src/`). El par [fixture JSON + Zod espejo a mano en
Studio] es el contrato — este script NO escribe TS (frontera D, superficie-
visual.md §7). Mismo patrón que `scripts/gen-example-bundle.py`.

Falla-fuerte por construcción: al reimportar los modelos, cualquier cambio de
forma cambia el JSON emitido; el test anti-drift
(`tests/unit/contract/test_harness_contract_fixtures.py`) exige que lo
commiteado sea byte-idéntico a lo que este script produce hoy.
"""

from __future__ import annotations

import json
from pathlib import Path

from blite.gateway.approval import ApprovalRequestedPayload, ApprovalRespondedPayload
from blite.runtime.plan import PlanCreatedPayload, PlanItem, PlanItemUpdatedPayload
from blite.runtime.replay import ReplayDivergencePayload

REPO = Path(__file__).resolve().parent.parent
CANONICAL_DIR = REPO / "tests" / "fixtures" / "contract" / "harness"
STUDIO_DIR = REPO / "apps" / "studio" / "src" / "fixtures" / "contract" / "harness"

_A = "a" * 64
_B = "b" * 64
_C = "c" * 64


def _cases() -> dict[str, object]:
    """Un ejemplo canónico por payload — optativos POBLADOS donde son
    significativos (para que el fixture ejercite la forma completa)."""
    return {
        "plan-created": PlanCreatedPayload(
            plan_id="plan-run-1",
            run_id="run-1",
            items=(
                PlanItem(
                    id="item-1",
                    description="formular el QUBO del corte máximo",
                    verification="formal_exact",
                    status="pending",
                ),
            ),
        ),
        "plan-item-updated": PlanItemUpdatedPayload(
            plan_id="plan-run-1",
            run_id="run-1",
            item_id="item-1",
            status="failed",
            cause="capability.job.failed",
        ),
        "replay-divergence": ReplayDivergencePayload(
            run_id="run-1",
            effect_kind="model_call",
            request_digest=_A,
            expected_response_digest=_B,
            actual_response_digest=_C,
            step_id="step-1",
        ),
        "approval-requested": ApprovalRequestedPayload(
            run_id="run-1",
            approval_id="approval-1",
            json_schema={
                "type": "object",
                "properties": {"aprobado": {"type": "boolean"}},
                "required": ["aprobado"],
            },
            prompt="El paso escribe al mundo (irreversible). ¿Aprobás?",
            step_id="step-1",
        ),
        "approval-responded": ApprovalRespondedPayload(
            run_id="run-1",
            approval_id="approval-1",
            response={"aprobado": True},
            authorized_by="user:dylan",
        ),
    }


def serialize(payload: object) -> str:
    """Forma canónica del fixture (snake_case de wire, claves ordenadas,
    optativos None omitidos → compat con `.optional()` de Zod)."""
    data = payload.model_dump(exclude_none=True)  # type: ignore[attr-defined]
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> int:
    CANONICAL_DIR.mkdir(parents=True, exist_ok=True)
    STUDIO_DIR.mkdir(parents=True, exist_ok=True)
    for case, payload in _cases().items():
        text = serialize(payload)
        (CANONICAL_DIR / f"{case}.json").write_text(text, encoding="utf-8")
        (STUDIO_DIR / f"{case}.json").write_text(text, encoding="utf-8")
        print(f"  {case}.json -> tests/ + apps/studio/ (byte-idéntico)")
    print(f"{len(_cases())} fixtures de contrato del harness emitidos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
