#!/usr/bin/env python3
"""Genera los fixtures de contrato de costura de `POST /runs` (spec
`docs/specs/endpoints-studio.md` §"POST /runs — modo misión"; convención
`docs/specs/README.md` §"Fixtures de costura — un solo origen").

ORIGEN ÚNICO = `chimera_api.runs.MissionRequest` (el modelo Pydantic que el
endpoint valida). Emite el body canónico que el Studio produce
(`toCreateRunBody`) a `tests/fixtures/contract/endpoints/<caso>.json` y lo
ESPEJA byte-idéntico a `apps/studio/src/fixtures/contract/endpoints/` (Vite
solo importa dentro de `src/`). El par [fixture JSON + comparación literal en
`mutations.test.ts`] es el contrato — este script NO escribe TS (frontera D).
Mismo patrón que `scripts/gen-contract-fixtures-harness.py`.

Los campos con default del server (`max_turns`, `budget`) se EXCLUYEN de los
fixtures de REQUEST: el Studio no los manda, el server los aplica — el fixture
fija exactamente el wire que cruza la costura, no la forma interna del modelo.

**Extensión P2 (#143):** `chimera_api.reads.DiscardedStreams` es el segundo
origen — lo que el server RESPONDE en `GET /runs/discarded` (#104/#124). Los
fixtures de RESPUESTA no excluyen defaults: el server SÍ emite el campo
(`{"discarded_streams": []}` es el vacío honesto literal del wire).
"""

from __future__ import annotations

import json
from pathlib import Path

from chimera_api.reads import DiscardedStream, DiscardedStreams
from chimera_api.runs import MissionRequest
from pydantic import BaseModel

REPO = Path(__file__).resolve().parent.parent
CANONICAL_DIR = REPO / "tests" / "fixtures" / "contract" / "endpoints"
STUDIO_DIR = REPO / "apps" / "studio" / "src" / "fixtures" / "contract" / "endpoints"


_REQUEST_CASES = frozenset({"post-runs-mission"})
"""Casos que fijan un body de REQUEST — sus defaults del server se excluyen
(el Studio no los manda). Los demás fijan una RESPUESTA: se serializan
completos."""


def _cases() -> dict[str, BaseModel]:
    """Un ejemplo canónico por caso — el MISMO body que `toCreateRunBody`
    (apps/studio/src/data/mutations.ts) produce para el form canónico
    (instancia ieee14 + proposer qaoa)."""
    return {
        "post-runs-mission": MissionRequest(
            mission=(
                "Particionar la red ieee14 en islas controladas "
                "y certificar la optimalidad del corte"
            ),
            instance_id="ieee14",
            # Capability REAL (`blite.quantum.qaoa`, capabilities/quantum) —
            # `blite.solvers.qaoa` no existe en ningún manifest instalado
            # (decisiones #95-#98, `docs/mvp/decisiones.md` §"Análisis para
            # discusión" punto 1); mismo mapeo que
            # `apps/studio/src/data/mutations.ts::PROPOSER_CAPABILITY`.
            capability_id="blite.quantum.qaoa",
        ),
        # La píldora #96 vuelta contrato: el stream envenenado que `GET /runs`
        # omite, reportado con el vocabulario de `run.failed` (`error_kind` =
        # `type(exc).__name__`). `KeyError` es lo que `_row_from_created`
        # levanta ante un `run.created` sin `max_steps`/`policy_digest`.
        "get-runs-discarded": DiscardedStreams(
            discarded_streams=(
                DiscardedStream(
                    stream_id="run-envenenado",
                    error_kind="KeyError",
                    detail="'max_steps'",
                ),
            )
        ),
    }


def serialize(case: str, payload: BaseModel) -> str:
    """Forma canónica del fixture (claves ordenadas). En los casos de REQUEST
    se omiten defaults del server y optativos `None` — el wire de la costura,
    no el modelo interno; en los de RESPUESTA se serializa lo que el server
    emite de verdad (los defaults SÍ viajan)."""
    if case in _REQUEST_CASES:
        data = payload.model_dump(exclude_none=True, exclude_defaults=True)
    else:
        data = payload.model_dump(exclude_none=True)
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> int:
    CANONICAL_DIR.mkdir(parents=True, exist_ok=True)
    STUDIO_DIR.mkdir(parents=True, exist_ok=True)
    for case, payload in _cases().items():
        text = serialize(case, payload)
        (CANONICAL_DIR / f"{case}.json").write_text(text, encoding="utf-8")
        (STUDIO_DIR / f"{case}.json").write_text(text, encoding="utf-8")
        print(f"  {case}.json -> tests/ + apps/studio/ (byte-idéntico)")
    print(f"{len(_cases())} fixtures de contrato de endpoints emitidos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
