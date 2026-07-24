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
"""

from __future__ import annotations

import hashlib
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
from blite.runtime.content_store import InMemoryContentStore
from blite.runtime.dispatch import Dispatcher, ProfileDispatcher
from blite.runtime.loop import execute_run
from blite.runtime.registry import Registry, load_registry
from blite.verification.exact_solver import MaxCutInstance, OptimalityClaim
from blite.verification.orchestrator import ClaimDeclaration, make_verification_delegate
from chimera_api.instance_verifiers import resolve_verifiers

# Sin auth aún — la sesión de seguridad del API (carril Steven) fija el actor
# real; este placeholder es explícito para no fingir identidad (Planeado §7).
_API_ACTOR = "user:api"
_DEFAULT_DOMAIN = "domain-default"
_KEYID = "certificate:api-ephemeral"

# api/src/chimera_api/runs.py -> parents[3] es la raíz del repo (mismo
# cómputo que REPO en test_assemble.py, tres niveles menos porque este
# archivo vive un nivel más adentro).
_REPO_ROOT = Path(__file__).parents[3]
_DEFAULT_POLICY_PATH = (
    _REPO_ROOT / "distributions" / "chimera" / "policies" / "verification-default.yaml"
)


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
    return RunResources(
        store=store,
        dispatcher=ProfileDispatcher(),
        content=InMemoryContentStore(),
        policy_bytes=_DEFAULT_POLICY_PATH.read_bytes(),
        signing_key=ed25519.Ed25519PrivateKey.generate(),
        keyid=_KEYID,
        run_tickets={},
        _registry=registry,
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


def create_runs_router(resources: RunResources) -> APIRouter:
    """Router de `/runs` cerrado sobre la infra de vida-de-app (§14) — un
    `RunResources` por app, compartido con el SSE vía el mismo `store`."""
    router = APIRouter()

    @router.post("/runs", status_code=202)
    def start_run(
        body: CreateRunRequest, background_tasks: BackgroundTasks
    ) -> CreateRunResponse:
        claim = _build_domain_claim(body.claim)

        instance_id = str(body.claim.scope.get("instancia", ""))
        resolution = resolve_verifiers(
            claim_type=body.claim.claim_type, instance_id=instance_id
        )
        if not resolution.verifiers:
            raise HTTPException(
                status_code=400,
                detail=(
                    "instancia sin verifiers — jamás un run sin verificación "
                    "(fail-closed)"
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

    return router
