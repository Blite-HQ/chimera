#!/usr/bin/env python3
"""Genera los fixtures de contrato de generalidad (spec
`docs/specs/generalidad-retos.md` §"Tests de contrato"; decisión #125;
convención `docs/specs/README.md` §"Fixtures de costura — un solo origen").

ORIGEN ÚNICO = modelos YA existentes del plano de confianza:
`ClaimEmittedPayload` (portadores §14) y los predicates congelados
`GroundTruthPredicate`/`PropertyRulePredicate` (freeze §4). Los casos fijan la
LETRA de S-C: claim_types del registro STEM (`simulation_result` para C3,
`statistical` para C2), identidad de corpus generalizada
(`tfim-corpus/...@v1`) y los checks canónicos de C2 (PSD + simetría).
El caso del predicate C-14 (`EXACT_DIAGONALIZATION` + `relative_tolerance`)
queda DECLARADO — su modelo extendido es Fase 1 (G1).

Falla-fuerte por construcción: mismo patrón anti-drift que los otros
generadores de contrato (byte-identidad exigida por el test).
"""

from __future__ import annotations

import json
from pathlib import Path

from blite.verification.claim import ClaimEmittedPayload
from blite.verification.evidence import (
    GroundTruthPredicate,
    MetamorphicRelation,
    PropertyCheck,
    PropertyRulePredicate,
)

REPO = Path(__file__).resolve().parent.parent
CANONICAL_DIR = REPO / "tests" / "fixtures" / "contract" / "generalidad"
STUDIO_DIR = REPO / "apps" / "studio" / "src" / "fixtures" / "contract" / "generalidad"

_A = "a" * 64
_B = "b" * 64
_C = "c" * 64
_D = "d" * 64


def _cases() -> dict[str, object]:
    return {
        "claim-c3-simulation-result": ClaimEmittedPayload(
            claim_digest=_A,
            claim_type="simulation_result",
            is_conclusion=True,
            sub_run_id="sub-run-1",
            sub_run_provenance_hash=_B,
        ),
        "claim-c2-statistical": ClaimEmittedPayload(
            claim_digest=_C,
            claim_type="statistical",
            is_conclusion=True,
        ),
        "predicate-ground-truth": GroundTruthPredicate(
            dataset_id="tfim-corpus/chain-n8-h10@v1",
            case_id="chain-n8-h10",
            expected_digest=_B,
            observed_digest=_B,
            match=True,
            tolerance=0.05,
        ),
        "predicate-property-rule": PropertyRulePredicate(
            properties=(
                PropertyCheck(
                    name="kernel-psd-lambda-min",
                    passed=True,
                    examples_run=200,
                    counterexample=None,
                ),
            ),
            relations=(
                MetamorphicRelation(
                    name="simetria-kernel",
                    transform_digest=_D,
                    expected_relation="invariant",
                    held=True,
                ),
            ),
            seed=7,
            generator_version="hypothesis-6",
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
    print(f"{len(_cases())} fixtures de contrato de generalidad emitidos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
