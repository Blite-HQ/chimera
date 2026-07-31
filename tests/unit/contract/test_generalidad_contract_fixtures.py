"""Contrato de costura de generalidad — el fixture ES el contrato (S-C #126).

`docs/specs/generalidad-retos.md` + `docs/specs/README.md` §"Fixtures de
costura — un solo origen":
1. cada fixture PARSEA de vuelta a su modelo Pydantic (Python es el origen);
2. canónico y espejo de Studio BYTE-IDÉNTICOS (sin consumidor Zod todavía —
   mismo precedente que ingesta/informe: el espejo lo verifica Python);
3. anti-drift falla-fuerte: lo commiteado == lo que el generador produce hoy.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from blite.verification.claim import ClaimEmittedPayload
from blite.verification.evidence import GroundTruthPredicate, PropertyRulePredicate

_REPO = Path(__file__).resolve().parents[3]
_CANONICAL = _REPO / "tests" / "fixtures" / "contract" / "generalidad"
_STUDIO = _REPO / "apps" / "studio" / "src" / "fixtures" / "contract" / "generalidad"

_MODELS = {
    "claim-c3-simulation-result": ClaimEmittedPayload,
    "claim-c2-statistical": ClaimEmittedPayload,
    "predicate-ground-truth": GroundTruthPredicate,
    "predicate-property-rule": PropertyRulePredicate,
}


def _load_generator() -> object:
    """Carga el generador (nombre con guiones ⇒ no importable como módulo)."""
    path = _REPO / "scripts" / "gen-contract-fixtures-generalidad.py"
    spec = importlib.util.spec_from_file_location(
        "gen_contract_fixtures_generalidad", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("case", list(_MODELS))
def test_fixture_parsea_de_vuelta_a_su_modelo(case: str) -> None:
    """(1) El JSON committeado valida contra el modelo Pydantic origen."""
    text = (_CANONICAL / f"{case}.json").read_text(encoding="utf-8")
    _MODELS[case].model_validate_json(text)


def test_claim_types_del_registro_stem() -> None:
    """La letra de S-C: los claim_types de los retos son los del registro
    del perfil STEM §1 — jamás inventados."""
    c3 = ClaimEmittedPayload.model_validate_json(
        (_CANONICAL / "claim-c3-simulation-result.json").read_text(encoding="utf-8")
    )
    c2 = ClaimEmittedPayload.model_validate_json(
        (_CANONICAL / "claim-c2-statistical.json").read_text(encoding="utf-8")
    )
    assert c3.claim_type == "simulation_result" and c3.is_conclusion
    assert c3.sub_run_id == "sub-run-1"
    assert c2.claim_type == "statistical" and c2.is_conclusion


def test_identidad_de_corpus_generalizada() -> None:
    """S-C §4: dataset_id = <corpus>/<instancia>@v<n> — la regla islanding
    generalizada; tolerance = el criterio oficial ≤5% de C3."""
    predicate = GroundTruthPredicate.model_validate_json(
        (_CANONICAL / "predicate-ground-truth.json").read_text(encoding="utf-8")
    )
    assert predicate.dataset_id == "tfim-corpus/chain-n8-h10@v1"
    assert predicate.tolerance == 0.05


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
