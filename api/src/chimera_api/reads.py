"""
`GET /runs` + 5 rutas de lectura del Studio — `docs/specs/endpoints-studio.md`
(costura E↔D, dueño Fase 1 Steven+Dylan). Todas sirven de PROYECCIONES del
`EventStore` — `blite.runtime.projection.project_runs` para la lista de runs,
`blite.certificate.assemble.assemble_bundle` para todo lo que depende del
certificado — jamás la tabla cruda, jamás internals de gateway/runtime.

Mismo patrón fail-closed que `chimera_api/certificate.py::get_certificate`:
`run_id`/`step_id` desconocido ⇒ 404, jamás un 200 con datos fabricados. Un
run vivo o sin certificado emitido todavía NO es error — es honestidad:
`[]` para artifacts/knowledge/ablation, envelope vacío para topology,
`attestations: []` para un step aún no verificado.

`GET /runs` porta server-side, campo por campo, la lógica que hoy vive
client-side en `apps/studio/src/data/projections.ts::deriveRunSummary` (y
`deriveArtifacts`/`deriveKnowledge` para las otras dos rutas con forma
`ProjectArtifact`/`KnowledgeClaim`) — mismo cómputo, nueva ubicación.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from blite.certificate.assemble import AssembleError, assemble_bundle
from blite.certificate.predicate import AssuranceLevel, ConclusionVerdict
from blite.events.event import Event
from blite.events.rules import TERMINAL_RUN_EVENTS
from blite.runtime.projection import RunRow, project_runs
from chimera_api.runs import RunResources

# Orden local de niveles — mismo valor que `assemble.py`/`predicate.py`
# (D20: cada consumidor mantiene su propia copia, a propósito, no se comparte).
_LEVEL_ORDER: dict[str, int] = {"AL0": 0, "AL1": 1, "AL2": 2, "AL3": 3, "AL4": 4}

_NO_CERT_CONCLUSION = "Sin conclusión registrada"
_NO_CERT_VERDICT: ConclusionVerdict = "inconclusive"
_NO_CERT_TITULAR_LEVEL: AssuranceLevel = "AL0"
_NO_CERT_TITULAR_CLASS = "formal_exact"

RunSummaryStatus = Literal["completado", "en_curso"]


class RunSummaryWire(BaseModel):
    """Fila de `GET /runs` — wire snake_case de `RunSummary` (`views/types.ts`)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    status: RunSummaryStatus
    conclusion: str
    verdict: ConclusionVerdict
    titular_level: AssuranceLevel
    titular_class: str
    events_count: int
    actor: str
    completed_at: str | None = None


class ProjectArtifactWire(BaseModel):
    """Fila de `GET /runs/{run_id}/artifacts` — wire de `ProjectArtifact`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    artifact_ref: str
    digest: str
    run_id: str
    titular_level: AssuranceLevel
    titular_class: str
    verdict: ConclusionVerdict
    issued_at: str


class KnowledgeClaimWire(BaseModel):
    """Fila de `GET /runs/{run_id}/knowledge` — wire de `KnowledgeClaim`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    statement: str
    scope: dict[str, Any]
    verdict: ConclusionVerdict
    level: AssuranceLevel
    titular_class: str
    run_id: str
    valid_as_of: str


class AblationMetricWire(BaseModel):
    """Fila de `GET /runs/{run_id}/ablation` — wire de `AblationMetric`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    variant: str
    cut_cost: float
    wall_ms: float
    verification_latency_ms: float


def _rfc3339(value: datetime) -> str:
    """Mismo formato que `chimera_api/projection.py::_rfc3339` (anexo §3)."""
    return value.isoformat().replace("+00:00", "Z")


def _run_exists(resources: RunResources, run_id: str) -> bool:
    """Un run existe si dejó rastro en el stream O si `POST /runs` le abrió
    ticket — cubre tanto runs reales como runs sembrados directo en tests."""
    return bool(resources.store.read_stream(run_id)) or run_id in resources.run_tickets


def _project_predicate(resources: RunResources, run_id: str) -> dict[str, Any] | None:
    """El predicate del certificado si el run terminó Y `assemble_bundle`
    encuentra evidencia amparándolo — `None` en cualquier otro caso (run
    vivo, sin ticket, o `AssembleError` fail-closed). Mismo helper que
    `tests/unit/api/test_certificate.py::_predicate_of`, aplicado server-side."""
    ticket = resources.run_tickets.get(run_id)
    if ticket is None:
        return None
    stream = resources.store.read_stream(run_id)
    if not stream or stream[-1].type not in TERMINAL_RUN_EVENTS:
        return None
    try:
        bundle = assemble_bundle(
            stream=stream,
            conclusions=ticket.conclusions,
            policy_yaml=resources.policy_bytes,
            signing_key=resources.signing_key,
            keyid=resources.keyid,
            anchor_descriptors=ticket.anchor_descriptors,
        )
    except AssembleError:
        return None
    payload_bytes = base64.b64decode(bundle["envelope"]["payload"])
    predicate: dict[str, Any] = json.loads(payload_bytes)["predicate"]
    return predicate


def _titular_class_for(predicate: dict[str, Any], claim_digest: str) -> str:
    """Puerto de `projections.ts::titularClassFor` — la clase del attestation
    MÁS FUERTE (mayor AL) amarrado a `claim_digest`; sin attestations
    amarradas, `"formal_exact"` (mismo default que el cliente)."""
    bound = [a for a in predicate["attestations"] if a["claim_digest"] == claim_digest]
    if not bound:
        return _NO_CERT_TITULAR_CLASS
    strongest = max(bound, key=lambda a: _LEVEL_ORDER[a["level"]])
    return str(strongest["verifier_class"])


def _run_summary_row(resources: RunResources, row: RunRow) -> RunSummaryWire:
    """Puerto server-side de `projections.ts::deriveRunSummary` — el enum wire
    congelado solo tiene `completado`/`en_curso` (failed/cancelled ⇒
    `en_curso`, misma regla que `events.some(type === 'run.completed')` del
    cliente: sin `run.completed` no hay "completado")."""
    stream = resources.store.read_stream(row.run_id)
    is_completed = row.status == "completed"
    predicate = _project_predicate(resources, row.run_id)

    if predicate is not None and predicate["conclusions"]:
        conclusion = predicate["conclusions"][0]
        conclusion_text = conclusion["canonical_statement"]
        verdict = conclusion["verdict"]
        titular_level = predicate["titular_level"]
        titular_class = _titular_class_for(predicate, conclusion["claim_digest"])
        actor = predicate["actor"]
    else:
        conclusion_text = _NO_CERT_CONCLUSION
        verdict = _NO_CERT_VERDICT
        titular_level = _NO_CERT_TITULAR_LEVEL
        titular_class = _NO_CERT_TITULAR_CLASS
        actor = row.actor_id

    completed_at = _rfc3339(stream[-1].occurred_at) if is_completed and stream else None
    return RunSummaryWire(
        run_id=row.run_id,
        status="completado" if is_completed else "en_curso",
        conclusion=conclusion_text,
        verdict=verdict,
        titular_level=titular_level,
        titular_class=titular_class,
        events_count=len(stream),
        actor=actor,
        completed_at=completed_at,
    )


def _project_step_detail(stream: tuple[Event, ...], step_id: str) -> dict[str, Any]:
    """Proyecta el stream filtrando por `step_id` (trust/07 §1.3 "Inspector de
    paso"). `capability.job.submitted`/`.completed` mandan; `run.step.*` es
    el fallback cuando esos eventos no aparecen para este `step_id`.

    Costura E↔A a flaggear: el orquestador real
    (`blite.verification.orchestrator.make_verification_delegate`) NO
    estampa `step_id` en el payload TOP-LEVEL de `verification.completed`
    (solo `claim_digest`/`verifier_id`/`verdict`/`attestation`) — el
    `step_id` vive, si acaso, DENTRO de `attestation.step_id`. Mientras esa
    costura no se cierre, `attestations` da `[]` para runs reales aunque la
    verificación sí corrió; no se inventa un binding no declarado por el
    emisor (honestidad > conveniencia)."""
    capability_id = ""
    primary_input_digest = ""
    primary_output_digest = ""
    fallback_input_digest = ""
    fallback_output_digest = ""
    attestations: list[dict[str, Any]] = []

    for event in stream:
        payload = event.payload
        if payload.get("step_id") != step_id:
            continue
        if event.type == "capability.job.submitted":
            capability_id = payload.get("capability_id", capability_id)
            primary_input_digest = payload.get("input_digest", primary_input_digest)
        elif event.type == "capability.job.completed":
            primary_output_digest = payload.get("output_digest", primary_output_digest)
        elif event.type.startswith("run.step."):
            fallback_input_digest = payload.get("input_digest", fallback_input_digest)
            fallback_output_digest = payload.get(
                "output_digest", fallback_output_digest
            )
        elif event.type == "verification.completed":
            attestation = payload.get("attestation", payload.get("verification"))
            if attestation is not None:
                attestations.append(attestation)

    return {
        "step_id": step_id,
        "capability_id": capability_id,
        "input_digest": primary_input_digest or fallback_input_digest,
        "output_digest": primary_output_digest or fallback_output_digest,
        "attestations": attestations,
    }


def _project_ablation(stream: tuple[Event, ...]) -> list[AblationMetricWire]:
    """`run.metrics.recorded` por variante (trust/07 §1.3 "Ablación") — hoy
    ningún run los emite (el emisor es dominio B/ciencia), así que en la
    práctica esto da `[]`; un evento sin `variant` en el payload se ignora
    (no es una fila de ablación)."""
    rows: list[AblationMetricWire] = []
    for event in stream:
        if event.type != "run.metrics.recorded":
            continue
        payload = event.payload
        variant = payload.get("variant")
        if variant is None:
            continue
        rows.append(
            AblationMetricWire(
                variant=variant,
                cut_cost=payload.get("cut_cost", 0),
                wall_ms=payload.get("wall_ms", 0),
                verification_latency_ms=payload.get("verification_latency_ms", 0),
            )
        )
    return rows


_TOPOLOGY_EVENT_TYPES = frozenset({"verification.completed", "run.step.completed"})


def _project_topology(stream: tuple[Event, ...]) -> dict[str, Any]:
    """El primer payload de partición (`islands` presente) en el stream,
    TAL CUAL — `verification` viaja POR ISLA, intacto (freeze §9, sin
    excepción). Sin partición en el stream ⇒ envelope vacío honesto: el run
    no produjo topología, no es un error de la ruta."""
    for event in stream:
        if event.type in _TOPOLOGY_EVENT_TYPES and "islands" in event.payload:
            return event.payload
    return {"topology_ref": "", "islands": [], "cut_branch_ids": [], "cut_cost": 0}


def create_reads_router(resources: RunResources) -> APIRouter:
    """Router de lectura del Studio cerrado sobre la MISMA infra de
    vida-de-app que `/runs` y `/runs/{run_id}/certificate` (mismo `store`,
    mismos `run_tickets`) — 6 rutas, todas GET, todas proyecciones."""
    router = APIRouter()

    # `completed_at` es Optional-y-OMITIDO (no `null`) cuando el run no
    # terminó — `exclude_none` en la respuesta, no un default fabricado.
    @router.get("/runs", response_model_exclude_none=True)
    def list_runs() -> list[RunSummaryWire]:
        rows = project_runs(resources.store.read_all())
        return [_run_summary_row(resources, row) for row in rows.values()]

    @router.get("/runs/{run_id}/artifacts")
    def list_artifacts(run_id: str) -> list[ProjectArtifactWire]:
        if not _run_exists(resources, run_id):
            raise HTTPException(status_code=404, detail="run desconocido")
        predicate = _project_predicate(resources, run_id)
        if predicate is None:
            return []
        conclusions = predicate["conclusions"]
        conclusion = conclusions[0] if conclusions else None
        return [
            ProjectArtifactWire(
                artifact_ref=deliverable["artifact_ref"],
                digest=deliverable["digest"],
                run_id=predicate["run_id"],
                titular_level=predicate["titular_level"],
                titular_class=(
                    _titular_class_for(predicate, conclusion["claim_digest"])
                    if conclusion is not None
                    else _NO_CERT_TITULAR_CLASS
                ),
                verdict=conclusion["verdict"]
                if conclusion is not None
                else _NO_CERT_VERDICT,
                issued_at=predicate["valid_as_of"],
            )
            for deliverable in predicate["deliverables"]
        ]

    @router.get("/runs/{run_id}/knowledge")
    def list_knowledge(run_id: str) -> list[KnowledgeClaimWire]:
        if not _run_exists(resources, run_id):
            raise HTTPException(status_code=404, detail="run desconocido")
        predicate = _project_predicate(resources, run_id)
        if predicate is None:
            return []
        return [
            KnowledgeClaimWire(
                statement=conclusion["canonical_statement"],
                scope=conclusion["scope"],
                verdict=conclusion["verdict"],
                level=conclusion["level"],
                titular_class=_titular_class_for(predicate, conclusion["claim_digest"]),
                run_id=predicate["run_id"],
                valid_as_of=predicate["valid_as_of"],
            )
            for conclusion in predicate["conclusions"]
        ]

    @router.get("/runs/{run_id}/steps/{step_id}/evidence")
    def get_step_evidence(run_id: str, step_id: str) -> dict[str, Any]:
        if not _run_exists(resources, run_id):
            raise HTTPException(status_code=404, detail="run desconocido")
        stream = resources.store.read_stream(run_id)
        return _project_step_detail(stream, step_id)

    @router.get("/runs/{run_id}/ablation")
    def list_ablation(run_id: str) -> list[AblationMetricWire]:
        if not _run_exists(resources, run_id):
            raise HTTPException(status_code=404, detail="run desconocido")
        stream = resources.store.read_stream(run_id)
        return _project_ablation(stream)

    @router.get("/runs/{run_id}/topology")
    def get_topology(run_id: str) -> dict[str, Any]:
        if not _run_exists(resources, run_id):
            raise HTTPException(status_code=404, detail="run desconocido")
        stream = resources.store.read_stream(run_id)
        return _project_topology(stream)

    return router
