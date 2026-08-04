"""Contrato de costura del harness — el fixture ES el contrato (A2-A6).

`docs/specs/README.md` §"Fixtures de costura — un solo origen":
1. cada fixture PARSEA de vuelta a su modelo Pydantic (Python es el origen);
2. el canónico (`tests/fixtures/...`) y el espejo de Studio
   (`apps/studio/src/fixtures/...`) son BYTE-IDÉNTICOS;
3. anti-drift falla-fuerte: lo commiteado == lo que el generador produce hoy
   (cambiar una costura sin regenerar su fixture = defecto).
El lado Zod del espejo lo agrega Studio (frontera D, `superficie-visual.md` §7).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

from blite.gateway.approval import ApprovalRequestedPayload, ApprovalRespondedPayload
from blite.runtime.mission import MissionMessagePayload
from blite.runtime.plan import PlanCreatedPayload, PlanItemUpdatedPayload
from blite.runtime.replay import ReplayDivergencePayload

_REPO = Path(__file__).resolve().parents[3]
_CANONICAL = _REPO / "tests" / "fixtures" / "contract" / "harness"
_STUDIO = _REPO / "apps" / "studio" / "src" / "fixtures" / "contract" / "harness"

_MODELS = {
    "plan-created": PlanCreatedPayload,
    "plan-item-updated": PlanItemUpdatedPayload,
    "replay-divergence": ReplayDivergencePayload,
    "approval-requested": ApprovalRequestedPayload,
    "approval-responded": ApprovalRespondedPayload,
    "mission-message": MissionMessagePayload,
}


def _load_generator() -> object:
    """Carga el generador (nombre con guiones ⇒ no importable como módulo)."""
    path = _REPO / "scripts" / "gen-contract-fixtures-harness.py"
    spec = importlib.util.spec_from_file_location("gen_contract_fixtures_harness", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("case", list(_MODELS))
def test_fixture_parsea_de_vuelta_a_su_modelo(case: str) -> None:
    """(1) El JSON committeado valida contra el modelo Pydantic origen."""
    text = (_CANONICAL / f"{case}.json").read_text(encoding="utf-8")
    model = _MODELS[case]
    parsed = model.model_validate_json(text)
    assert parsed.run_id == "run-1"


@pytest.mark.parametrize("case", list(_MODELS))
def test_canonico_y_espejo_studio_byte_identicos(case: str) -> None:
    """(2) Sin drift entre el canónico y el espejo que consume Studio."""
    canonical = (_CANONICAL / f"{case}.json").read_bytes()
    mirror = (_STUDIO / f"{case}.json").read_bytes()
    assert canonical == mirror


@pytest.mark.parametrize("case", list(_MODELS))
def test_anti_drift_committeado_igual_al_generador(case: str) -> None:
    """(3) Falla-fuerte: el fixture en disco == lo que el generador produce
    HOY desde los modelos. Cambiar una costura sin regenerar = defecto."""
    module = _load_generator()
    payload = module._cases()[case]  # type: ignore[attr-defined]
    expected = module.serialize(payload)  # type: ignore[attr-defined]
    on_disk = (_CANONICAL / f"{case}.json").read_text(encoding="utf-8")
    assert on_disk == expected


def test_models_cubre_todos_los_casos_del_generador() -> None:
    """(4) El guard del guard: `_MODELS` es un espejo A MANO de `_cases()`, y
    los tres tests de arriba parametrizan sobre `_MODELS` — así que un caso
    NUEVO en el generador no entra a la parametrización y su fixture queda
    SIN anti-drift, en silencio y con la suite en verde.

    Pasó de verdad: `mission-message` se generó (spec chat-conversacion.md
    §"Tests de contrato" lo declaró para Fase 1) y ningún test lo cubría.
    Este test convierte ese descuido en un fallo ruidoso."""
    module: Any = _load_generator()
    casos: dict[str, object] = module._cases()
    sin_cubrir: set[str] = set(casos) - set(_MODELS)
    assert sin_cubrir == set(), (
        f"casos del generador sin entrada en _MODELS (quedan sin anti-drift): {sorted(sin_cubrir)}"
    )
