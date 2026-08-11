#!/usr/bin/env python3
"""Genera el fixture de costura de la proyección OTel (S-F §Tests de contrato).

    uv run python scripts/gen-contract-fixtures-observabilidad.py

Un solo origen (`docs/specs/README.md`): el fixture lo produce este script y el
test anti-drift exige que el archivo en disco sea BYTE-IDÉNTICO a esta salida.
El golden es estable por construcción — los ids son deterministas (§4), así que
no hay nada que «congelar» salvo el propio mapeo.

Espejo del Studio: NO aplica. El consumidor de esta costura es un collector
OTLP, no el Studio.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from chimera_otel.projection import project_run, span_id_for

_REPO_ROOT = Path(__file__).parents[1]
_DESTINO = (
    _REPO_ROOT
    / "tests"
    / "fixtures"
    / "contract"
    / "observabilidad"
    / "trace-example.json"
)

_RUN_ID = "run-fixture-0001"


def _event(
    seq: int, type_: str, payload: dict[str, Any], segundo: int
) -> dict[str, Any]:
    return {
        "stream_id": _RUN_ID,
        "seq": seq,
        "global_seq": seq,
        "type": type_,
        "actor_id": "user:externo",
        "domain_id": "chimera",
        "payload": payload,
        "occurred_at": f"2026-08-05T12:00:{segundo:02d}+00:00",
    }


def build_stream() -> list[dict[str, Any]]:
    """Un run con las CINCO clases de span de la tabla §3, más una marca."""
    return [
        _event(
            1,
            "run.created",
            {"domain_id": "chimera", "policy_digest": "pd-0", "max_steps": 8},
            0,
        ),
        _event(2, "run.started", {}, 1),
        _event(
            3,
            "run.step.started",
            {
                "step_id": "step-1",
                "kind": "invoke",
                "input_digest": "in-1",
                "status": "running",
            },
            2,
        ),
        _event(
            4,
            "capability.job.submitted",
            {
                "job_id": "job-1",
                "step_id": "step-1",
                "capability_id": "blite.graphs.maxcut",
            },
            3,
        ),
        _event(
            5,
            "model.call.requested",
            {"prompt_digest": "pr-1", "backend_id": "replay", "local": True},
            4,
        ),
        _event(
            6,
            "model.call.completed",
            {
                "prompt_digest": "pr-1",
                "response_digest": "rs-1",
                "backend_id": "replay",
            },
            5,
        ),
        _event(
            7,
            "capability.job.completed",
            {"job_id": "job-1", "step_id": "step-1", "output_digest": "out-1"},
            6,
        ),
        _event(
            8,
            "run.step.completed",
            {
                "step_id": "step-1",
                "kind": "invoke",
                "input_digest": "in-1",
                "output_digest": "out-1",
                "status": "ok",
            },
            7,
        ),
        _event(
            9,
            "verification.completed",
            {
                "claim_digest": "cl-1",
                "verifier_id": "verifier:cpsat-differential",
                "verdict": "pass",
            },
            8,
        ),
        _event(
            10,
            "run.metrics.recorded",
            {"attestations_total": 1, "inconclusive_count": 0},
            9,
        ),
        _event(11, "run.completed", {}, 10),
    ]


def main() -> int:
    stream = build_stream()
    plan = project_run(stream)
    if plan is None:  # pragma: no cover - el stream fixture siempre proyecta
        msg = "el stream fixture no produjo traza"
        raise SystemExit(msg)

    fixture = {
        "_comentario": (
            "Golden de la proyección evento→span (S-F §3/§4). Generado por "
            "scripts/gen-contract-fixtures-observabilidad.py — no editar a mano."
        ),
        "run_id": plan.run_id,
        "trace_id": plan.trace_id.hex(),
        "stream": stream,
        "spans": {
            span.anchor: {
                "name": span.name,
                "span_id": span_id_for(plan.run_id, span.anchor).hex(),
                "parent_anchor": span.parent_anchor,
                "status": span.status,
            }
            for span in plan.spans
        },
    }

    _DESTINO.parent.mkdir(parents=True, exist_ok=True)
    _DESTINO.write_text(
        json.dumps(fixture, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"escrito: {_DESTINO.relative_to(_REPO_ROOT)}")
    print(f"trace_id: {plan.trace_id.hex()}   spans: {len(plan.spans)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
