"""Contrato de costura de `POST /runs` modo misión — el fixture ES el contrato.

`docs/specs/README.md` §"Fixtures de costura — un solo origen" (mismo patrón
que `test_harness_contract_fixtures.py`):
1. cada fixture PARSEA de vuelta a su modelo Pydantic (Python es el origen);
2. el canónico (`tests/fixtures/...`) y el espejo de Studio
   (`apps/studio/src/fixtures/...`) son BYTE-IDÉNTICOS;
3. anti-drift falla-fuerte: lo commiteado == lo que el generador produce hoy
   (cambiar la costura sin regenerar su fixture = defecto).
El lado Studio del espejo lo fija `mutations.test.ts` (toCreateRunBody ==
fixture, literal) — spec `docs/specs/endpoints-studio.md` §"POST /runs —
modo misión".
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from chimera_api.runs import MissionRequest

_REPO = Path(__file__).resolve().parents[3]
_CANONICAL = _REPO / "tests" / "fixtures" / "contract" / "endpoints"
_STUDIO = _REPO / "apps" / "studio" / "src" / "fixtures" / "contract" / "endpoints"

_MODELS = {
    "post-runs-mission": MissionRequest,
}


def _load_generator() -> object:
    """Carga el generador (nombre con guiones ⇒ no importable como módulo)."""
    path = _REPO / "scripts" / "gen-contract-fixtures-endpoints.py"
    spec = importlib.util.spec_from_file_location(
        "gen_contract_fixtures_endpoints", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("case", list(_MODELS))
def test_fixture_parsea_de_vuelta_a_su_modelo(case: str) -> None:
    """(1) El JSON committeado valida contra el modelo Pydantic origen —
    el 422 del body misión-first muere por construcción."""
    text = (_CANONICAL / f"{case}.json").read_text(encoding="utf-8")
    parsed = _MODELS[case].model_validate_json(text)
    assert parsed.mission != ""


@pytest.mark.parametrize("case", list(_MODELS))
def test_canonico_y_espejo_studio_byte_identicos(case: str) -> None:
    """(2) Sin drift entre el canónico y el espejo que consume Studio."""
    canonical = (_CANONICAL / f"{case}.json").read_bytes()
    mirror = (_STUDIO / f"{case}.json").read_bytes()
    assert canonical == mirror


@pytest.mark.parametrize("case", list(_MODELS))
def test_anti_drift_committeado_igual_al_generador(case: str) -> None:
    """(3) Falla-fuerte: el fixture en disco == lo que el generador produce
    HOY desde el modelo. Cambiar la costura sin regenerar = defecto."""
    module = _load_generator()
    payload = module._cases()[case]  # type: ignore[attr-defined]
    expected = module.serialize(payload)  # type: ignore[attr-defined]
    on_disk = (_CANONICAL / f"{case}.json").read_text(encoding="utf-8")
    assert on_disk == expected
