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


def test_el_productor_real_emite_la_misma_forma_que_el_fixture() -> None:
    """(4, V1/M18) El puente que faltaba: el fixture describía una forma que
    NADIE emitía. Ahora `build_partition` es el productor, y lo que produce
    valida contra el mismo modelo origen y trae exactamente las mismas llaves
    por isla que el caso commiteado — o el contrato se habría bifurcado en dos
    verdades (fixture verde, superficie viva distinta)."""
    from datetime import UTC, datetime

    from blite.verification.attestation import Attestation
    from blite.verification.evidence import (
        ExecutionCheck,
        ExecutionEnvironment,
        ExecutionPredicate,
    )
    from blite.verification.partition import build_partition

    attestation = Attestation(
        verifier_id="verifier:pandapower-islanding",
        verifier_class="execution",
        anchor_kind="execution",
        level="AL3",
        verdict="pass",
        scope={"instancia": "ieee14"},
        independence_group="leg-execution",
        run_id="run-contract",
        claim_digest="c" * 64,
        verifier_binary_digest="b" * 64,
        verifier_params_digest="p" * 64,
        anchor_digest="a" * 64,
        predicate=ExecutionPredicate(
            harness="pandapower-islanding-v1",
            input_digest="i" * 64,
            checks=(
                ExecutionCheck(name="island-0:island_connectivity", passed=True),
                ExecutionCheck(name="island-1:island_connectivity", passed=True),
            ),
            runtime_ms=1.0,
            environment=ExecutionEnvironment(package="pandapower", version="3.5.4"),
        ),
        issued_at=datetime(2026, 8, 5, tzinfo=UTC),
    )
    produced = build_partition(
        attestation=attestation,
        assignment=(0, 0, 1, 1),
        edges=((0, 1, 1), (1, 2, 5), (2, 3, 1)),
        topology_ref="ieee14-topology@v1",
    )
    assert produced is not None

    parsed = TopologyResponse.model_validate(produced)
    assert len(parsed.islands) == 2

    fixture = json.loads((_CANONICAL / f"{_CASE}.json").read_text(encoding="utf-8"))
    assert set(produced) == set(fixture)
    assert set(produced["islands"][0]) == set(fixture["islands"][0])
    assert set(produced["islands"][0]["verification"]) == set(
        fixture["islands"][0]["verification"]
    )
