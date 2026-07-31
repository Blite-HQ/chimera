"""Contrato de costura del manifest v2 — el fixture ES el contrato (S-E #127).

`docs/specs/manifest-v2-sdk.md` §"Tests de contrato" + `docs/specs/README.md`
§"Fixtures de costura — un solo origen":
1. cada fixture PARSEA de vuelta al dataclass origen (Python es el origen;
   dataclass → asdict, la letra de S-E);
2. canónico y espejo de Studio BYTE-IDÉNTICOS (sin consumidor Zod todavía —
   mismo precedente que generalidad: el espejo lo verifica Python);
3. anti-drift falla-fuerte: lo commiteado == lo que el generador produce hoy.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from blite_capability.manifest import CapabilityManifest

_REPO = Path(__file__).resolve().parents[3]
_CANONICAL = _REPO / "tests" / "fixtures" / "contract" / "manifest"
_STUDIO = _REPO / "apps" / "studio" / "src" / "fixtures" / "contract" / "manifest"

_CASES = ("capability-manifest-v2",)


def _load_generator() -> object:
    """Carga el generador (nombre con guiones ⇒ no importable como módulo)."""
    path = _REPO / "scripts" / "gen-contract-fixtures-manifest.py"
    spec = importlib.util.spec_from_file_location(
        "gen_contract_fixtures_manifest", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _parse_manifest(text: str) -> CapabilityManifest:
    """El camino de vuelta del asdict: tags list→tuple, el resto tal cual."""
    data = json.loads(text)
    data["tags"] = tuple(data["tags"])
    return CapabilityManifest(**data)


@pytest.mark.parametrize("case", _CASES)
def test_fixture_parsea_de_vuelta_al_dataclass(case: str) -> None:
    """(1) El JSON committeado reconstruye el dataclass origen sin explotar
    (los literals se validan en __post_init__ — fail-closed #127)."""
    text = (_CANONICAL / f"{case}.json").read_text(encoding="utf-8")
    manifest = _parse_manifest(text)
    assert manifest.id


def test_los_cuatro_campos_con_la_letra_de_s_e() -> None:
    """La letra §1: los 4 campos viajan en el wire; execution_profile con su
    default in-process explícito en el fixture (asdict serializa TODO)."""
    manifest = _parse_manifest(
        (_CANONICAL / "capability-manifest-v2.json").read_text(encoding="utf-8")
    )
    assert manifest.side_effects == "pure"
    assert manifest.required_permission == "capability:invoke"
    assert manifest.interaction == "request_response"
    assert manifest.execution_profile == "in-process"


@pytest.mark.parametrize("case", _CASES)
def test_canonico_y_espejo_studio_byte_identicos(case: str) -> None:
    """(2) Sin drift entre el canónico y el espejo que consume Studio."""
    canonical = (_CANONICAL / f"{case}.json").read_bytes()
    mirror = (_STUDIO / f"{case}.json").read_bytes()
    assert canonical == mirror


@pytest.mark.parametrize("case", _CASES)
def test_anti_drift_committeado_igual_al_generador(case: str) -> None:
    """(3) Falla-fuerte: el fixture en disco == lo que el generador produce
    HOY desde el dataclass. Cambiar la costura sin regenerar = defecto."""
    module = _load_generator()
    payload = module._cases()[case]  # type: ignore[attr-defined]
    expected = module.serialize(payload)  # type: ignore[attr-defined]
    committed = (_CANONICAL / f"{case}.json").read_text(encoding="utf-8")
    assert committed == expected
