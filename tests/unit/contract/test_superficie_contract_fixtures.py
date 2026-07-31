"""Contrato de costura de la superficie visual — el fixture ES el contrato.

`docs/specs/superficie-visual.md` §8 (decisión #125) + `docs/specs/README.md`
§"Fixtures de costura — un solo origen":
1. el fixture PARSEA de vuelta a `TopologyResponse` (Python es el origen);
2. canónico y espejo de Studio BYTE-IDÉNTICOS;
3. anti-drift falla-fuerte: lo commiteado == lo que el generador produce hoy.
Además fija la LETRA del caso: `verification` POR isla (freeze §9, sin
excepción) y branch-ids en AMBAS formas de la convención C-8.
El lado Zod del espejo: `topologySnapshotSchema` (`schemas.test.ts`).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from chimera_api.reads import TopologyResponse

_REPO = Path(__file__).resolve().parents[3]
_CANONICAL = _REPO / "tests" / "fixtures" / "contract" / "superficie"
_STUDIO = _REPO / "apps" / "studio" / "src" / "fixtures" / "contract" / "superficie"
_CASE = "topology-snapshot"


def _load_generator() -> object:
    """Carga el generador (nombre con guiones ⇒ no importable como módulo)."""
    path = _REPO / "scripts" / "gen-contract-fixtures-superficie.py"
    spec = importlib.util.spec_from_file_location(
        "gen_contract_fixtures_superficie", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fixture_parsea_de_vuelta_a_topology_response() -> None:
    """(1) El JSON committeado valida contra el modelo Pydantic origen."""
    text = (_CANONICAL / f"{_CASE}.json").read_text(encoding="utf-8")
    parsed = TopologyResponse.model_validate_json(text)
    assert parsed.topology_ref == "ieee14-topology@v1"
    assert len(parsed.islands) == 2


def test_verification_por_isla_sin_excepcion() -> None:
    """Regla §9 (letra de superficie-visual §4): CADA isla trae su bloque
    `verification` completo — jamás un bloque global-only."""
    data = json.loads((_CANONICAL / f"{_CASE}.json").read_text(encoding="utf-8"))
    for island in data["islands"]:
        verification = island["verification"]
        for key in (
            "verdict",
            "verifier_class",
            "level",
            "anchor_kind",
            "method",
            "summary",
        ):
            assert key in verification, f"isla {island['id']} sin {key}"


def test_branch_ids_ejercitan_la_convencion_hibrida() -> None:
    """C-8: el caso trae id canónico simple, canónico con paralela y
    edge_id_property de GIS — las tres formas que la convención §8 admite."""
    data = json.loads((_CANONICAL / f"{_CASE}.json").read_text(encoding="utf-8"))
    assert data["cut_branch_ids"] == ["L3-6", "L4-8-2", "70143"]


def test_canonico_y_espejo_studio_byte_identicos() -> None:
    """(2) Sin drift entre el canónico y el espejo que consume Studio."""
    canonical = (_CANONICAL / f"{_CASE}.json").read_bytes()
    mirror = (_STUDIO / f"{_CASE}.json").read_bytes()
    assert canonical == mirror


def test_anti_drift_committeado_igual_al_generador() -> None:
    """(3) Falla-fuerte: el fixture en disco == lo que el generador produce
    HOY desde el modelo. Cambiar la costura sin regenerar = defecto."""
    module = _load_generator()
    payload = module._cases()[_CASE]  # type: ignore[attr-defined]
    expected = module.serialize(payload)  # type: ignore[attr-defined]
    on_disk = (_CANONICAL / f"{_CASE}.json").read_text(encoding="utf-8")
    assert on_disk == expected
