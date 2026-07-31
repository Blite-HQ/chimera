"""
`POST /runs` — arranque de runs con verificación. Plan `docs/mvp/01-runtime-api.md`
§1 (decisiones `docs/mvp/decisiones.md` #6 claim completo en el request, #7
verifiers por instancia, #11 BackgroundTasks, #13 DI de registry, #14
ContentStore/Dispatcher).

Este módulo compone lo mismo que el golden path real de
`tests/unit/certificate/test_assemble.py::TestDosPatasReales` — el mismo
`execute_run(...post_invoke=make_verification_delegate(...))` — pero
disparado por HTTP en vez de invocado directo. El endpoint SOLO arma el
claim, resuelve sus verifiers, y agenda; el loop del runtime no verifica
(INV-2) y el verdict final vive en el stream, jamás en la respuesta HTTP.

Fail-closed (decisión #7 / plan §3): si `resolve_verifiers` no ampara el
claim con NINGÚN verifier, el endpoint devuelve 400 — jamás un run sin
verificación. Fail-loud para el resto: una capability desconocida o una
excepción de invocación no tumban el API — el runtime las registra como
`run.failed` en el stream (freeze del loop, `execute_run`); el arranque HTTP
solo falla por errores del REQUEST (claim de dominio inválido o
fail-closed), nunca por lo que pase DENTRO del run.

Modo misión (decisión #91, `docs/specs/endpoints-studio.md` §"POST /runs —
modo misión"): el MISMO endpoint acepta un body alternativo `{mission, ...}`
discriminado del claim-first por presencia de campo (ambos modelos con
`extra="forbid"` ⇒ ni ambos ni ninguno validan → 422). El modo misión NO
exige assignment ni claim — los claims los emiten los sub-runs/steps
(frontera P4); arranca `execute_run` en modo agéntico con la misión
journalizada como `description` del ítem fundacional del plan, y SIN gate de
verificación termina `run.failed {error_kind: "exhausted"}` — jamás un
`run.completed` implícito (harness-agentico.md §Contrato-3).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric import ed25519
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from blite.certificate.assemble import ConclusionDeclaration
from blite.content import ContentStore
from blite.events.store import EventStore
from blite.protocols.model_server import InMemoryReplayManifest, ModelServer
from blite.runtime.content_store import InMemoryContentStore
from blite.runtime.dispatch import Dispatcher, ProfileDispatcher
from blite.runtime.loop import (
    ProposedStep,
    Proposer,
    RunBudget,
    TurnContext,
    execute_run,
)
from blite.runtime.plan import PlanItem
from blite.runtime.registry import Registry, load_registry
from blite.serving.model_port import ModelPort
from blite.verification.exact_solver import MaxCutInstance, OptimalityClaim
from blite.verification.orchestrator import ClaimDeclaration, make_verification_delegate
from chimera_api.instance_verifiers import resolve_verifiers
from chimera_api.model_proposer import make_model_proposer
from chimera_api.model_session import load_session

# Sin auth aún — el trabajo pendiente de auth (ítem C2/M2 del backlog) fija
# el actor real; este placeholder es explícito para no fingir identidad
# (Planeado §7).
_API_ACTOR = "user:api"
_DEFAULT_DOMAIN = "domain-default"
_KEYID = "certificate:api-ephemeral"
_MODEL_CTX: dict[str, str] = {"domain_id": _DEFAULT_DOMAIN}

# Flip del agente real (P4, decisión #92 · el camino dorado de
# docs/archivo/planeado/01-demo-dia-d.md: "el agente es real... en escena
# corre por defecto en replay"). Env AUSENTE
# (default) ⇒ `_make_goal_proposer` placeholder, comportamiento intacto.
_MODEL_BACKEND_ENV = "CHIMERA_MODEL_BACKEND"
_MODEL_SESSION_DIR_ENV = "CHIMERA_MODEL_SESSION_DIR"
_MODEL_ID_ENV = "CHIMERA_MODEL_ID"
_VALID_MODEL_BACKENDS = ("replay", "record", "live")
_DEFAULT_MODEL_ID = "anthropic/claude-sonnet-4-5"
"""Solo importa para `record`/`live` (identifica el modelo ante litellm); en
`replay` el `backend_id` real viene del propio `manifest.json` de la sesión
grabada (`chimera_api.model_session.load_session`) — el que se usó al
grabar, no un default reconfigurable por accidente."""

# api/src/chimera_api/runs.py -> parents[3] es la raíz del repo (mismo
# cómputo que REPO en test_assemble.py, tres niveles menos porque este
# archivo vive un nivel más adentro).
_REPO_ROOT = Path(__file__).parents[3]
_DEFAULT_POLICY_PATH = (
    _REPO_ROOT / "distributions" / "chimera" / "policies" / "verification-default.yaml"
)
_ISLANDING_CORPUS_DIR = _REPO_ROOT / "knowledge" / "islanding" / "corpus"


class InstanceRequest(BaseModel):
    """Instancia Max-Cut del claim — espejo HTTP de `MaxCutInstance`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    n_nodes: int = Field(ge=1)
    edges: tuple[tuple[int, int, int], ...]


class ClaimRequest(BaseModel):
    """Claim completo en el request (decisión #6) — nada se infiere server-side."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    instance: InstanceRequest
    assignment: tuple[int, ...]
    canonical_statement: str
    scope: dict[str, Any]
    claim_type: str


class CreateRunRequest(BaseModel):
    """Body de `POST /runs`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    capability_id: str
    inputs: dict[str, Any]
    claim: ClaimRequest
    max_steps: int = Field(default=8, ge=1)


_DEFAULT_MISSION_CAPABILITY = "blite.solvers.qubo"
"""Capability meta cuando el body de misión no la trae — si el registry no
la conoce, el run falla fail-loud DENTRO del stream (mismo contrato que una
capability desconocida en modo claim-first), jamás el arranque HTTP."""

_DEFAULT_MISSION_MAX_TURNS = 3
"""Default conservador del modo misión (spec §"POST /runs — modo misión"):
sin gate de verificación cableado, cada turno extra del proposer determinista
es gasto sin información nueva — el 30 del loop llega con el agente real."""

_STEPS_PER_TURN = 2
"""Cada turno agéntico consume exactamente 2 `RunStep` (resolve+invoke) —
`max_steps = max_turns * 2` garantiza `max_turns <= max_steps` (§Contrato-3,
responsabilidad del caller)."""


class MissionBudgetRequest(BaseModel):
    """Espejo HTTP de `RunBudget` (harness-agentico.md §Contrato-3)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tokens: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)


class MissionRequest(BaseModel):
    """Body modo misión de `POST /runs` — discriminado del claim-first por
    presencia de campo (`mission` vs `claim`); `extra="forbid"` en ambos
    lados de la unión hace la discriminación excluyente."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mission: str = Field(min_length=1)
    instance_id: str | None = None
    capability_id: str | None = None
    max_turns: int = Field(default=_DEFAULT_MISSION_MAX_TURNS, ge=1)
    budget: MissionBudgetRequest | None = None


class CreateRunResponse(BaseModel):
    """202: el run se agendó — el resultado vive en el stream, no aquí."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str


@dataclass(frozen=True)
class RunTicket:
    """Lo que el arranque declaró sobre un run — insumo del ensamblador de
    certificados (Task C): conclusiones + descriptores de ancla, en orden."""

    conclusions: tuple[ConclusionDeclaration, ...]
    anchor_descriptors: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class ModelBackendConfig:
    """El agente real ya construido — `server` despacha por `mode` (A2,
    `ModelServer`); `backend_id`/`local` completan el `ModelRequest` que
    `chimera_api.model_proposer.make_model_proposer` arma por turno.
    `None` en `RunResources.model_backend` ⇒ placeholder determinista
    (default intacto, decisión #92)."""

    server: ModelPort
    backend_id: str
    local: bool = False


def _build_model_backend(content: ContentStore) -> ModelBackendConfig | None:
    """Lee `CHIMERA_MODEL_BACKEND`/`CHIMERA_MODEL_SESSION_DIR`/`CHIMERA_MODEL_ID`
    UNA sola vez, al construir `RunResources` (arranque de la app, nunca por
    request) — mismo espíritu que `registry()` perezoso, pero acá la lectura
    de env + (en replay) el `load_session` de disco son baratos una única vez
    y estables durante la vida del proceso.

    Env AUSENTE ⇒ `None` (placeholder intacto). Un valor de backend inválido,
    o `replay` sin `CHIMERA_MODEL_SESSION_DIR`, es un error de CONFIGURACIÓN
    del servicio — falla RÁPIDO acá (al construir la app), nunca a mitad de
    un run."""
    backend = os.environ.get(_MODEL_BACKEND_ENV)
    if backend is None:
        return None
    if backend not in _VALID_MODEL_BACKENDS:
        msg = (
            f"{_MODEL_BACKEND_ENV} inválido: {backend!r} "
            f"(válidos: {', '.join(_VALID_MODEL_BACKENDS)})"
        )
        raise ValueError(msg)

    if backend == "replay":
        session_dir_raw = os.environ.get(_MODEL_SESSION_DIR_ENV)
        if session_dir_raw is None:
            msg = (
                f"{_MODEL_BACKEND_ENV}=replay exige {_MODEL_SESSION_DIR_ENV} "
                "(directorio de la sesión grabada — manifest.json + responses/)"
            )
            raise ValueError(msg)
        manifest, backend_id, local = load_session(
            Path(session_dir_raw), content, _MODEL_CTX
        )
        server: ModelPort = ModelServer(
            mode="replay", content_store=content, ctx=_MODEL_CTX, manifest=manifest
        )
        return ModelBackendConfig(server=server, backend_id=backend_id, local=local)

    # record/live: backend_id configurable (identifica el modelo ante
    # litellm, `blite.protocols.model_server._default_live_caller`); manifest
    # en memoria — `record` lo llena por request, `scripts/record_session.py`
    # es quien lo dumpea a disco al terminar la corrida (no la API viva).
    backend_id = os.environ.get(_MODEL_ID_ENV, _DEFAULT_MODEL_ID)
    server = ModelServer(
        mode=backend,
        content_store=content,
        ctx=_MODEL_CTX,
        manifest=InMemoryReplayManifest(),
    )
    return ModelBackendConfig(server=server, backend_id=backend_id)


@dataclass
class RunResources:
    """Infra de vida-de-app (decisiones #13/#14) — NO frozen: cachea el
    registry (carga perezosa, una sola vez) y acumula los `run_tickets` que
    cada `POST /runs` deja para que Task C los recoja al ensamblar."""

    store: EventStore
    dispatcher: Dispatcher
    content: ContentStore
    policy_bytes: bytes
    signing_key: ed25519.Ed25519PrivateKey
    keyid: str
    run_tickets: dict[str, RunTicket]
    _registry: Registry | None = None
    model_backend: ModelBackendConfig | None = None

    def registry(self) -> Registry:
        """Registry perezoso: `load_registry` corre SOLO al primer uso real,
        nunca al arrancar la app (decisión #13) — y nunca si un test ya
        inyectó uno hermético en la construcción."""
        if self._registry is None:
            self._registry = load_registry(self.store)
        return self._registry


def build_run_resources(
    store: EventStore, *, registry: Registry | None = None
) -> RunResources:
    """Construye la infra de vida-de-app de `/runs` sobre el `store` del
    caller — el mismo que sirve el SSE (un solo EventStore por app)."""
    content = InMemoryContentStore()
    return RunResources(
        store=store,
        dispatcher=ProfileDispatcher(),
        content=content,
        policy_bytes=_DEFAULT_POLICY_PATH.read_bytes(),
        signing_key=ed25519.Ed25519PrivateKey.generate(),
        keyid=_KEYID,
        run_tickets={},
        _registry=registry,
        model_backend=_build_model_backend(content),
    )


def _build_domain_claim(claim_request: ClaimRequest) -> OptimalityClaim:
    """Construye el claim de dominio o levanta 400 — un claim mal formado
    (instancia inconsistente, assignment de largo incorrecto, etc.) es un
    error del REQUEST, no del run."""
    try:
        return OptimalityClaim(
            instance=MaxCutInstance(
                n_nodes=claim_request.instance.n_nodes,
                edges=claim_request.instance.edges,
            ),
            assignment=claim_request.assignment,
            canonical_statement=claim_request.canonical_statement,
            scope=claim_request.scope,
        )
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


_MISSION_INSTANCE_ERRORS: tuple[type[Exception], ...] = (
    OSError,
    KeyError,
    ValueError,
    TypeError,
    IndexError,
)
"""Excepciones que `_load_corpus_matrix` puede levantar sobre un
`instance_id` desconocido o un registro de corpus malformado — TODAS caen al
fallback de `_resolve_mission_inputs` (jamás propagan)."""


def _load_corpus_matrix(instance_id: str) -> list[list[int]]:
    """Transform canónico grafo→QUBO sobre `<instance_id>.json` del corpus
    de islanding (`knowledge/islanding/corpus/`) — MISMA aritmética que
    `scripts/exp_r_vs_p.py::load_instance` (Q simétrica, se MAXIMIZA
    xᵀQx). No se importa desde ahí: `scripts/` no es un paquete instalable
    (no está en `tool.uv.workspace` ni en el `include` de pyright — mismo
    comentario que `tests/unit/experiment/test_exp_r_vs_p.py`); replicar
    esta aritmética mecánica no duplica ciencia — la ciencia (QAOA, CP-SAT,
    max-cut) sigue viviendo únicamente en las capabilities.

    Desconocido o malformado ⇒ deja que la excepción suba — el caller
    (`_resolve_mission_inputs`) decide el fallback fail-loud."""
    # `instance_id` viene del body HTTP: solo slugs del corpus — jamás se
    # interpola una forma de traversal en la ruta (validación en frontera).
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", instance_id):
        msg = f"instance_id fuera del espacio de slugs del corpus: {instance_id!r}"
        raise ValueError(msg)
    record: dict[str, Any] = json.loads(
        (_ISLANDING_CORPUS_DIR / f"{instance_id}.json").read_text(encoding="utf-8")
    )
    edges = [(int(u), int(v), int(w)) for u, v, w in record["aristas"]]
    n = int(record["n_nodos"])
    matrix = [[0] * n for _ in range(n)]
    for u, v, w in edges:
        matrix[u][u] += w
        matrix[v][v] += w
        matrix[u][v] -= w
        matrix[v][u] -= w
    return matrix


def _resolve_mission_inputs(mission: str, instance_id: str | None) -> dict[str, Any]:
    """Inputs del proposer determinista de arranque de misión (decisiones
    #95-#98, `docs/mvp/decisiones.md` §"Análisis para discusión" punto 1).

    `instance_id` conocido en el corpus ⇒ `{"matrix": <QUBO simétrica>}` —
    lo único que las capabilities meta de este modo (`blite.solvers.qubo`,
    `blite.quantum.qaoa`, `blite.graphs.maxcut`) requieren de verdad.

    `instance_id` ausente, desconocido, o con datos malformados ⇒ cae al
    body previo (`{"mission", "instance_id"?}`) — el MISMO que ya fallaba
    fail-loud DENTRO del stream (una capability real rechaza `matrix`
    ausente, p.ej. `QuboSolver._validate_matrix`): jamás un 4xx nuevo del
    arranque HTTP, y jamás una excepción sin capturar escapando del
    proposer (`_run_agentic_turn` no envuelve la llamada al proposer en
    try/except — un raise ahí tumbaría el turno entero antes de journalizar
    nada, no solo el paso resolve→invoke que SÍ está protegido)."""
    fallback: dict[str, Any] = {"mission": mission}
    if instance_id is None:
        return fallback
    fallback["instance_id"] = instance_id
    try:
        matrix = _load_corpus_matrix(instance_id)
    except _MISSION_INSTANCE_ERRORS:
        return fallback
    return {"matrix": matrix}


def _make_goal_proposer(capability_id: str, inputs: dict[str, Any]) -> Proposer:
    """Proposer determinista PLACEHOLDER (etiquetado — jamás "el agente"):
    propone la capability meta con los mismos inputs en cada turno, hasta que
    P4 cablee el agente real (`ModelServer` tras `ModelPort`, decisión #81)
    por la MISMA costura `Proposer`. Sin llamada de modelo no hay gasto que
    auto-reportar (`tokens`/`cost_usd` en `None` — honesto, no cero fingido)."""

    def _propose(_ctx: TurnContext) -> ProposedStep:
        return ProposedStep(capability_id=capability_id, inputs=inputs)

    return _propose


def _resolve_proposer(
    resources: RunResources, capability_id: str, inputs: dict[str, Any]
) -> Proposer:
    """Selecciona el proposer del turno — el agente real (P4, `ModelServer`
    tras `ModelPort`) si `CHIMERA_MODEL_BACKEND` está configurado, si no el
    placeholder determinista etiquetado (default INTACTO, decisión #92).
    MISMO seam `Proposer` en ambos casos — cero cambio de contrato HTTP."""
    if resources.model_backend is None:
        return _make_goal_proposer(capability_id, inputs)
    return make_model_proposer(
        model_server=resources.model_backend.server,
        registry=resources.registry(),
        content_store=resources.content,
        ctx=_MODEL_CTX,
        backend_id=resources.model_backend.backend_id,
        local=resources.model_backend.local,
    )


def _start_claim_run(
    resources: RunResources, body: CreateRunRequest, background_tasks: BackgroundTasks
) -> CreateRunResponse:
    """Arranque claim-first (decisión #6) — INTACTO desde el Nivel-1."""
    claim = _build_domain_claim(body.claim)

    instance_id = str(body.claim.scope.get("instancia", ""))
    resolution = resolve_verifiers(
        claim_type=body.claim.claim_type, instance_id=instance_id
    )
    if not resolution.verifiers:
        raise HTTPException(
            status_code=400,
            detail=(
                "instancia sin verifiers — jamás un run sin verificación (fail-closed)"
            ),
        )

    declaration = ClaimDeclaration(
        claim=claim,
        canonical_statement=body.claim.canonical_statement,
        scope=body.claim.scope,
        claim_type=body.claim.claim_type,
        is_conclusion=True,
    )
    delegate = make_verification_delegate(
        verifiers=resolution.verifiers, declarations=(declaration,)
    )

    run_id = f"run-{uuid4().hex}"
    resources.run_tickets[run_id] = RunTicket(
        conclusions=(
            ConclusionDeclaration(
                canonical_statement=body.claim.canonical_statement,
                scope=body.claim.scope,
                claim_type=body.claim.claim_type,
            ),
        ),
        anchor_descriptors=resolution.anchor_descriptors,
    )

    # Agendado, jamás inline (decisión #11): el POST responde 202 en
    # cuanto el claim y sus verifiers son válidos — el run corre después.
    background_tasks.add_task(
        execute_run,
        resources.store,
        resources.registry(),
        resources.dispatcher,
        resources.content,
        run_id=run_id,
        actor_id=_API_ACTOR,
        domain_id=_DEFAULT_DOMAIN,
        max_steps=body.max_steps,
        policy_digest=hashlib.sha256(resources.policy_bytes).hexdigest(),
        capability_id=body.capability_id,
        inputs=body.inputs,
        post_invoke=delegate,
    )

    return CreateRunResponse(run_id=run_id)


def _start_mission_run(
    resources: RunResources, body: MissionRequest, background_tasks: BackgroundTasks
) -> CreateRunResponse:
    """Arranque modo misión (spec §"POST /runs — modo misión"): agenda
    `execute_run` en modo agéntico — el plan viaja como eventos y la misión
    queda journalizada como `description` del ítem fundacional del plan
    (dentro del `provenance_hash`, sin extender `run.created`).

    Sin gate de verificación (`post_invoke` ausente A PROPÓSITO): `done` ⟺
    el verifier pasa (§Contrato-3) — hoy no hay verifier del lado misión,
    así que el run termina `run.failed {error_kind: "exhausted"}`; el gate
    real llega con los claims de sub-runs/steps (frontera P4)."""
    run_id = f"run-{uuid4().hex}"

    # Ticket VACÍO: el modo misión no declara conclusiones — los claims los
    # emiten los sub-runs/steps. `GET /runs/{id}/certificate` no responde
    # 404 por desconocido; sin conclusiones no se fabrica certificado.
    resources.run_tickets[run_id] = RunTicket(conclusions=(), anchor_descriptors=())

    capability_id = (
        body.capability_id
        if body.capability_id is not None
        else _DEFAULT_MISSION_CAPABILITY
    )
    inputs = _resolve_mission_inputs(body.mission, body.instance_id)

    budget = (
        RunBudget(tokens=body.budget.tokens, cost_usd=body.budget.cost_usd)
        if body.budget is not None
        else None
    )

    background_tasks.add_task(
        execute_run,
        resources.store,
        resources.registry(),
        resources.dispatcher,
        resources.content,
        run_id=run_id,
        actor_id=_API_ACTOR,
        domain_id=_DEFAULT_DOMAIN,
        max_steps=body.max_turns * _STEPS_PER_TURN,
        policy_digest=hashlib.sha256(resources.policy_bytes).hexdigest(),
        capability_id=capability_id,
        inputs=inputs,
        max_turns=body.max_turns,
        budget=budget,
        proposer=_resolve_proposer(resources, capability_id, inputs),
        plan_items=(
            PlanItem(
                id="mission-1",
                description=body.mission,
                verification="delegate",
                status="pending",
            ),
        ),
    )

    return CreateRunResponse(run_id=run_id)


def create_runs_router(resources: RunResources) -> APIRouter:
    """Router de `/runs` cerrado sobre la infra de vida-de-app (§14) — un
    `RunResources` por app, compartido con el SSE vía el mismo `store`."""
    router = APIRouter()

    @router.post("/runs", status_code=202)
    def start_run(
        body: CreateRunRequest | MissionRequest, background_tasks: BackgroundTasks
    ) -> CreateRunResponse:
        # Discriminación por presencia de campo (`mission` vs `claim`) —
        # `extra="forbid"` en ambos modelos hace la unión excluyente: un
        # body con ambos (o ninguno) no valida contra ningún lado → 422.
        if isinstance(body, MissionRequest):
            return _start_mission_run(resources, body, background_tasks)
        return _start_claim_run(resources, body, background_tasks)

    return router
