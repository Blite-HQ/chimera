#!/usr/bin/env python3
"""Runbook ejecutable — graba una sesión agéntica REAL para el modo replay
del demo (carril P4, mandato Dylan 2026-07-29, tarea 4;
`docs/planeado/01-demo-dia-d.md`: "el agente es real... en escena corre por
defecto en replay — reproducción determinista de una sesión agéntica real
grabada").

Corre UNA misión completa (`execute_run` en modo agéntico, MISMA costura
`Proposer` que `POST /runs`) con el agente real
(`chimera_api.model_proposer.make_model_proposer`) detrás de un
`ModelServer(mode="record")` (A2), y al terminar dumpea la sesión resultante
a `--session-dir` (`chimera_api.model_session.write_session`) — queda lista
para `CHIMERA_MODEL_BACKEND=replay CHIMERA_MODEL_SESSION_DIR=<esa ruta>`.

USO REAL (Dylan, con su propia key — env ESTÁNDAR de litellm, p.ej.
`ANTHROPIC_API_KEY`; este script NUNCA lee ni hardcodea una API key, litellm
la toma del entorno por su cuenta — freeze §15.7, `_default_live_caller`):

    uv run python scripts/record_session.py \\
        --session-dir knowledge/sessions/cr8-uniforme-demo \\
        --mission "Particione cr8-uniforme en islas controladas y certifique el corte" \\
        --instance-id cr8-uniforme \\
        --model-id anthropic/claude-sonnet-4-5 \\
        --max-turns 3

DRY-RUN (CI/tests, SIN red ni API key — `--fake`): un `live_caller` +
registry deterministas locales reemplazan litellm/los entry points
instalados, pero recorren el MISMO camino de producción (proposer real →
`ModelServer(mode="record")` → `write_session`). Esta sesión NO ejecuta el
script contra litellm real (prohibido invocar un LLM externo en esta
sesión) — solo `--fake` está probado (`tests/unit/api/test_record_session.py`).

`scripts/` no es un paquete instalable (no está en `tool.uv.workspace` ni en
el `include` de pyright — mismo comentario que
`chimera_api.runs._load_corpus_matrix`); `record_session`/`main` son
funciones puras de orquestación para que el test las llame directo, sin
pasar por `argv`.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any
from uuid import uuid4

from chimera_api.model_proposer import make_model_proposer
from chimera_api.model_session import write_session
from chimera_api.runs import _DEFAULT_MISSION_CAPABILITY, _resolve_mission_inputs

from blite.events import create_event_store
from blite.protocols.model_server import InMemoryReplayManifest, ModelServer
from blite.runtime.content_store import InMemoryContentStore
from blite.runtime.dispatch import ProfileDispatcher
from blite.runtime.loop import execute_run
from blite.runtime.plan import PlanItem
from blite.runtime.registry import EntryPointRegistry, Registry, load_registry
from blite.serving.model_port import ModelRequest
from blite_capability.manifest import CapabilityManifest

_CTX = {"domain_id": "domain-default"}
_ACTOR = "user:record-session"
_STEPS_PER_TURN = 2
_PLAN_ITEM_ID = "mission-1"
_DEFAULT_MODEL_ID = "anthropic/claude-sonnet-4-5"

_FAKE_CAPABILITY_ID = "chimera.record_session.fake"
"""Capability determinista de `--fake` — doble de test, jamás una capability
de dominio real (ADR-029: reverse-domain genérico, no específico)."""


class _FakeCapability:
    """Doble determinista para `--fake` — mismo espíritu que
    `cap.mission-echo` en `tests/unit/api/test_runs.py`, vive acá para no
    importar un módulo de test desde código de producción."""

    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id=_FAKE_CAPABILITY_ID,
            description="fake deterministic capability para --fake/dry-run",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return {"echo": inputs}


def _fake_live_caller(_request: ModelRequest) -> bytes:
    """Respuesta determinista de `--fake`: propone la capability fake con
    inputs vacíos en cada turno — ejercita el pipeline real completo
    (proposer → `ModelServer(record)` → `ContentStore` → protocolo JSON
    estricto) sin red ni API key."""
    return f'{{"capability_id": "{_FAKE_CAPABILITY_ID}", "inputs": {{}}}}'.encode()


def _build_registry(*, fake: bool) -> Registry:
    if fake:
        return EntryPointRegistry({_FAKE_CAPABILITY_ID: _FakeCapability()})
    # Producción: entry points REALES instalados (`blite.capabilities`,
    # mismo camino que `RunResources.registry()` en la API) — un
    # `EventStore` efímero basta acá, solo interesan las capabilities.
    return load_registry(create_event_store())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Graba una sesión agéntica para CHIMERA_MODEL_BACKEND=replay "
            "(--fake para dry-run sin red/API key)"
        )
    )
    parser.add_argument(
        "--session-dir",
        required=True,
        type=str,
        help="directorio destino (p.ej. knowledge/sessions/cr8-uniforme-demo)",
    )
    parser.add_argument("--mission", required=True, help="texto de la misión")
    parser.add_argument(
        "--instance-id",
        default=None,
        help="instancia del corpus de islanding (p.ej. cr8-uniforme); opcional",
    )
    parser.add_argument(
        "--capability-id",
        default=None,
        help="capability meta objetivo; default blite.solvers.qubo (o la fake en --fake)",
    )
    parser.add_argument(
        "--model-id",
        default=_DEFAULT_MODEL_ID,
        help="backend_id litellm (p.ej. anthropic/claude-sonnet-4-5)",
    )
    parser.add_argument("--max-turns", type=int, default=3)
    parser.add_argument(
        "--fake",
        action="store_true",
        help="dry-run determinista sin red/API key (CI/tests) — NUNCA usar para grabar la sesión real",
    )
    return parser


def record_session(
    *,
    session_dir: Path,
    mission: str,
    instance_id: str | None,
    capability_id: str | None,
    model_id: str,
    max_turns: int,
    fake: bool,
) -> str:
    """Orquesta UNA corrida completa y dumpea la sesión — función pura de
    orquestación (sin tocar `sys.argv`), testeable directo con `fake=True`.

    Reusa `chimera_api.runs._resolve_mission_inputs` (misma resolución
    instancia→matrix que `POST /runs` modo misión, decisiones #95-#98) para
    que la sesión grabada quede consistente con lo que el endpoint real
    construiría para la MISMA misión/instancia."""
    store = create_event_store()
    registry = _build_registry(fake=fake)
    dispatcher = ProfileDispatcher()
    content = InMemoryContentStore()
    manifest = InMemoryReplayManifest()

    resolved_capability_id = capability_id or (
        _FAKE_CAPABILITY_ID if fake else _DEFAULT_MISSION_CAPABILITY
    )
    inputs = _resolve_mission_inputs(mission, instance_id)

    model_server = ModelServer(
        mode="record",
        content_store=content,
        ctx=_CTX,
        manifest=manifest,
        live_caller=_fake_live_caller if fake else None,
    )
    proposer = make_model_proposer(
        model_server=model_server,
        registry=registry,
        content_store=content,
        ctx=_CTX,
        backend_id=model_id,
    )

    run_id = f"run-{uuid4().hex}"
    execute_run(
        store,
        registry,
        dispatcher,
        content,
        run_id=run_id,
        actor_id=_ACTOR,
        domain_id=_CTX["domain_id"],
        max_steps=max_turns * _STEPS_PER_TURN,
        policy_digest=hashlib.sha256(b"record-session").hexdigest(),
        capability_id=resolved_capability_id,
        inputs=inputs,
        max_turns=max_turns,
        proposer=proposer,
        plan_items=(
            PlanItem(
                id=_PLAN_ITEM_ID,
                description=mission,
                verification="delegate",
                status="pending",
            ),
        ),
    )

    write_session(
        session_dir,
        backend_id=model_id,
        local=False,
        manifest=manifest,
        content_store=content,
        ctx=_CTX,
        mission=mission,
    )
    return run_id


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_id = record_session(
        session_dir=Path(args.session_dir),
        mission=args.mission,
        instance_id=args.instance_id,
        capability_id=args.capability_id,
        model_id=args.model_id,
        max_turns=args.max_turns,
        fake=args.fake,
    )
    print(f"sesión grabada en {args.session_dir!r} (run_id={run_id!r})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
