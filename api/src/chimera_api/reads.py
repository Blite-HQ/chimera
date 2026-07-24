"""
Los 6 GETs de lectura del Studio — spec `docs/specs/endpoints-studio.md`
(E↔D, freeze §7/§9). [S-G · Steven+Dylan]

Router de LECTURA puro sobre la MISMA infra que `/runs`/`/runs/{id}/certificate`
(`RunResources` de `chimera_api.runs`): jamás la tabla cruda, jamás internals
de gateway/runtime/serving — solo el puerto `EventStore` (`blite.events`), la
proyección `project_runs` (freeze §2, ejecución) y el ensamblador de
certificados (`blite.certificate.assemble`, freeze §7), exactamente como
`certificate.py`.

Doctrina fail-closed de esta spec (verbatim en la tabla de la spec):
- `run_id`/`step_id` desconocido ⇒ 404 (mismo patrón que
  `certificate.py::get_certificate`) — jamás un 200 con datos fabricados.
- Un run vivo o sin certificado emitible TODAVÍA (sin `RunTicket` — nunca
  arrancó por `POST /runs` de ESTE proceso — o `AssembleError`) NO es error:
  `GET /runs` deja `conclusion/verdict/titular_level/titular_class` en
  `None`, `.../artifacts` y `.../knowledge` responden `[]`. Honestidad, no
  falla del endpoint (letra explícita de la spec).
- `.../steps/{step_id}/evidence` sobre un step sin `verification.completed`
  responde `attestations: []` (paso corrió, aún no lo verificaron).
- `.../ablation` y `.../topology` no tienen productor real todavía
  (`run.metrics.recorded` por variante / partición embebida en
  `verification.completed` — ninguno de los dos está cableado por
  `harness-agentico.md`/dominio ciencia aún); esta spec fija la FORMA de la
  respuesta, no quién la produce — sin esos eventos, honest-empty.
"""

from __future__ import annotations

import base64
import json
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from blite.certificate.assemble import AssembleError, assemble_bundle
from blite.certificate.predicate import AssuranceLevel, ConclusionVerdict
from blite.events.event import Event
from blite.events.rules import TERMINAL_RUN_EVENTS
from blite.runtime.projection import project_runs
from chimera_api.runs import RunResources

RunStatusWire = Literal["en_curso", "completado"]

# freeze §4/predicate.py: orden de fuerza de un AssuranceLevel — mismo mínimo
# local que `deriveRunSummary`/`titularClassFor` (apps/studio/src/data/projections.ts),
# portado server-side (letra de la spec: "MISMA lógica ... portada server-side").
_LEVEL_ORDER: dict[str, int] = {"AL0": 0, "AL1": 1, "AL2": 2, "AL3": 3, "AL4": 4}
_DEFAULT_TITULAR_CLASS = "formal_exact"

_CAPABILITY_JOB_PREFIX = "capability.job."
_RUN_STEP_PREFIX = "run.step."
_VERIFICATION_COMPLETED = "verification.completed"
_ABLATION_FIELDS = ("variant", "cut_cost", "wall_ms", "verification_latency_ms")
# Convención de ESTA ruta (no hay productor real todavía — spec: "no quién la
# produce ni cuándo"): un `verification.completed` puede embeber el
# resultado de partición bajo esta llave, en la MISMA forma snake_case que
# `PartitionView`/`Island` (apps/studio/src/spike/ieee14.ts).
_PARTITION_PAYLOAD_KEY = "partition"


class RunSummary(BaseModel):
    """`GET /runs` — proyección + certificado (freeze §2/§7), fila plana."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    status: RunStatusWire
    conclusion: str | None
    verdict: ConclusionVerdict | None
    titular_level: AssuranceLevel | None
    titular_class: str | None
    events_count: int
    actor: str
    completed_at: str | None = None


class ProjectArtifact(BaseModel):
    """`GET /runs/{run_id}/artifacts` — `certificate.predicate.deliverables`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    artifact_ref: str
    digest: str
    run_id: str
    titular_level: AssuranceLevel
    titular_class: str
    verdict: ConclusionVerdict
    issued_at: str


class KnowledgeClaim(BaseModel):
    """`GET /runs/{run_id}/knowledge` — `certificate.predicate.conclusions`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    statement: str
    scope: dict[str, Any]
    verdict: ConclusionVerdict
    level: AssuranceLevel
    titular_class: str
    run_id: str
    valid_as_of: str


class StepDetail(BaseModel):
    """`GET /runs/{run_id}/steps/{step_id}/evidence` — proyección filtrada
    por `step_id` sobre `run.step.*`/`capability.job.*`/`verification.completed`.

    `capability_id`/`input_digest`/`output_digest` son `None` cuando el log
    aún no tiene el evento que los carga (honesto, no fabricado) — TS
    (`views/types.ts::StepDetail`) los declara no-opcionales; D3 resuelve el
    coalesce en la rama live, esta ruta jamás inventa un digest.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    step_id: str
    capability_id: str | None = None
    input_digest: str | None = None
    output_digest: str | None = None
    attestations: tuple[dict[str, Any], ...] = ()


class AblationMetric(BaseModel):
    """`GET /runs/{run_id}/ablation` — `run.metrics.recorded` por variante."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    variant: Literal["quantum", "classical"]
    cut_cost: float
    wall_ms: float
    verification_latency_ms: float


class TopologyResponse(BaseModel):
    """`GET /runs/{run_id}/topology` — partición embebida en
    `verification.completed`; cada isla trae SU `verification` (freeze §9,
    sin excepción) — pass-through honesto, jamás badge fabricado por isla."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    topology_ref: str | None
    islands: tuple[dict[str, Any], ...]
    cut_branch_ids: tuple[str, ...]
    cut_cost: float


def _require_known_run(resources: RunResources, run_id: str) -> tuple[Event, ...]:
    """404 fail-closed (mismo patrón que `certificate.py::get_certificate`):
    un stream vacío es un `run_id` que el log jamás vio."""
    stream = resources.store.read_stream(run_id)
    if not stream:
        raise HTTPException(status_code=404, detail="run desconocido")
    return stream


def _bundle_for(resources: RunResources, run_id: str) -> dict[str, Any] | None:
    """Intenta ensamblar el certificado ya emitido — `None` = "sin
    certificado todavía" (honesto, no error): sin `RunTicket` (el run nunca
    arrancó por `POST /runs` de ESTE proceso), sin terminal, o
    `AssembleError` del ensamblador (evidencia insuficiente) caen acá."""
    ticket = resources.run_tickets.get(run_id)
    if ticket is None:
        return None
    stream = resources.store.read_stream(run_id)
    if not stream or stream[-1].type not in TERMINAL_RUN_EVENTS:
        return None
    try:
        return assemble_bundle(
            stream=stream,
            conclusions=ticket.conclusions,
            policy_yaml=resources.policy_bytes,
            signing_key=resources.signing_key,
            keyid=resources.keyid,
            anchor_descriptors=ticket.anchor_descriptors,
        )
    except AssembleError:
        return None


def _predicate_of(bundle: dict[str, Any]) -> dict[str, Any]:
    """Decodifica `envelope.payload` (base64 → JSON) al `predicate` — mismo
    helper que `tests/unit/api/test_certificate.py::_predicate_of`."""
    payload = base64.b64decode(bundle["envelope"]["payload"])
    statement: dict[str, Any] = json.loads(payload)
    predicate: dict[str, Any] = statement["predicate"]
    return predicate


def _titular_class_for(predicate: dict[str, Any], claim_digest: str) -> str:
    """Clase del attestation MÁS FUERTE amarrado a `claim_digest` — mismo
    cómputo que `titularClassFor` (`apps/studio/src/data/projections.ts`),
    portado server-side: empate se resuelve por orden de aparición en el log
    (`max` de Python es estable ante empates, igual que el sort de JS)."""
    bound = [a for a in predicate["attestations"] if a["claim_digest"] == claim_digest]
    if not bound:
        return _DEFAULT_TITULAR_CLASS
    strongest = max(bound, key=lambda a: _LEVEL_ORDER[a["level"]])
    return str(strongest["verifier_class"])


def _run_status(stream: tuple[Event, ...]) -> RunStatusWire:
    """Mismo cómputo que `deriveRunSummary` (client): `completado` exige el
    evento `run.completed` explícito, no cualquier terminal — mirror
    deliberado de la lógica cliente (letra de la spec), no una
    generalización propia."""
    if any(event.type == "run.completed" for event in stream):
        return "completado"
    return "en_curso"


def _run_summary(resources: RunResources, run_id: str, actor_id: str) -> RunSummary:
    stream = resources.store.read_stream(run_id)
    bundle = _bundle_for(resources, run_id)
    conclusion: str | None = None
    verdict: ConclusionVerdict | None = None
    titular_level: AssuranceLevel | None = None
    titular_class: str | None = None
    completed_at: str | None = None
    if bundle is not None:
        predicate = _predicate_of(bundle)
        conclusions = predicate["conclusions"]
        titular_level = predicate["titular_level"]
        completed_at = predicate["valid_as_of"]
        if conclusions:
            first = conclusions[0]
            conclusion = first["canonical_statement"]
            verdict = first["verdict"]
            titular_class = _titular_class_for(predicate, first["claim_digest"])
        else:
            titular_class = _DEFAULT_TITULAR_CLASS
    return RunSummary(
        run_id=run_id,
        status=_run_status(stream),
        conclusion=conclusion,
        verdict=verdict,
        titular_level=titular_level,
        titular_class=titular_class,
        events_count=len(stream),
        actor=actor_id,
        completed_at=completed_at,
    )


def _event_step_id(payload: dict[str, Any]) -> str | None:
    """El `step_id` de un evento — vive plano en `run.step.*`/
    `capability.job.*` y en la convención simplificada de
    `verification.completed` (freeze §9, `{step_id, verification}`), o
    anidado en `payload.attestation.step_id` (vocabulario real del
    orquestador, `Attestation.step_id` — `blite/verification/attestation.py`)."""
    step_id = payload.get("step_id")
    if step_id is not None:
        return str(step_id)
    attestation = payload.get("attestation")
    if isinstance(attestation, dict):
        nested = attestation.get("step_id")
        if nested is not None:
            return str(nested)
    return None


def _project_step_detail(stream: tuple[Event, ...], step_id: str) -> StepDetail | None:
    """Proyección del stream filtrada por `step_id` — `None` = el step jamás
    aparece en el log (404 fail-closed la capa de arriba)."""
    capability_id: str | None = None
    input_digest: str | None = None
    output_digest: str | None = None
    attestations: list[dict[str, Any]] = []
    found = False
    for event in stream:
        payload = event.payload
        if _event_step_id(payload) != step_id:
            continue
        found = True
        if event.type.startswith(_CAPABILITY_JOB_PREFIX):
            capability_id = payload.get("capability_id", capability_id)
            input_digest = payload.get("input_digest", input_digest)
            output_digest = payload.get("output_digest", output_digest)
        elif event.type.startswith(_RUN_STEP_PREFIX):
            input_digest = payload.get("input_digest", input_digest)
            output_digest = payload.get("output_digest") or output_digest
        elif event.type == _VERIFICATION_COMPLETED:
            attestation = payload.get("attestation") or payload.get("verification")
            attestations.append(attestation if attestation is not None else payload)
    if not found:
        return None
    return StepDetail(
        step_id=step_id,
        capability_id=capability_id,
        input_digest=input_digest,
        output_digest=output_digest,
        attestations=tuple(attestations),
    )


def _project_ablation(stream: tuple[Event, ...]) -> list[AblationMetric]:
    """Filas `run.metrics.recorded` por variante — un evento sin los 4 campos
    esperados se OMITE (honesto: nunca se fabrica el faltante), no se cae."""
    metrics: list[AblationMetric] = []
    for event in stream:
        if event.type != "run.metrics.recorded":
            continue
        payload = event.payload
        if not all(field in payload for field in _ABLATION_FIELDS):
            continue
        metrics.append(
            AblationMetric(**{field: payload[field] for field in _ABLATION_FIELDS})
        )
    return metrics


def _empty_topology() -> dict[str, Any]:
    return {"topology_ref": None, "islands": (), "cut_branch_ids": (), "cut_cost": 0.0}


def _is_valid_island(island: Any) -> bool:
    """freeze §9: `verification` POR ISLA, sin excepción — una partición
    embebida sin ese campo por isla se descarta ENTERA (fail-closed) en vez
    de exponerse a medias con un badge fabricado."""
    return isinstance(island, dict) and "verification" in island


def _project_topology(stream: tuple[Event, ...]) -> dict[str, Any]:
    """Última partición embebida en un `verification.completed` — honest-
    empty si ninguna aparece o si la que aparece no trae `verification` por
    isla (harness-agentico/dominio ciencia aún no cablea el productor real)."""
    for event in reversed(stream):
        if event.type != _VERIFICATION_COMPLETED:
            continue
        partition = event.payload.get(_PARTITION_PAYLOAD_KEY)
        if not isinstance(partition, dict):
            continue
        islands = partition.get("islands")
        if not isinstance(islands, list) or not all(
            _is_valid_island(island) for island in islands
        ):
            continue
        return {
            "topology_ref": partition.get("topology_ref"),
            "islands": tuple(islands),
            "cut_branch_ids": tuple(partition.get("cut_branch_ids", ())),
            "cut_cost": partition.get("cut_cost", 0.0),
        }
    return _empty_topology()


def create_reads_router(resources: RunResources) -> APIRouter:
    """Router de los 6 GETs de lectura, cerrado sobre la MISMA infra de
    vida-de-app que `/runs`/`/runs/{run_id}/certificate` (un `RunResources`
    por app — mismo `store`, mismos `run_tickets`)."""
    router = APIRouter()

    @router.get("/runs")
    def list_runs() -> list[RunSummary]:
        rows = project_runs(resources.store.read_all())
        return [
            _run_summary(resources, run_id, row.actor_id)
            for run_id, row in rows.items()
        ]

    @router.get("/runs/{run_id}/artifacts")
    def get_run_artifacts(run_id: str) -> list[ProjectArtifact]:
        _require_known_run(resources, run_id)
        bundle = _bundle_for(resources, run_id)
        if bundle is None:
            return []
        predicate = _predicate_of(bundle)
        conclusions = predicate["conclusions"]
        first = conclusions[0] if conclusions else None
        verdict: ConclusionVerdict = first["verdict"] if first else "inconclusive"
        titular_class = (
            _titular_class_for(predicate, first["claim_digest"])
            if first
            else _DEFAULT_TITULAR_CLASS
        )
        return [
            ProjectArtifact(
                artifact_ref=deliverable["artifact_ref"],
                digest=deliverable["digest"],
                run_id=run_id,
                titular_level=predicate["titular_level"],
                titular_class=titular_class,
                verdict=verdict,
                issued_at=predicate["valid_as_of"],
            )
            for deliverable in predicate["deliverables"]
        ]

    @router.get("/runs/{run_id}/knowledge")
    def get_run_knowledge(run_id: str) -> list[KnowledgeClaim]:
        _require_known_run(resources, run_id)
        bundle = _bundle_for(resources, run_id)
        if bundle is None:
            return []
        predicate = _predicate_of(bundle)
        return [
            KnowledgeClaim(
                statement=conclusion["canonical_statement"],
                scope=conclusion["scope"],
                verdict=conclusion["verdict"],
                level=conclusion["level"],
                titular_class=_titular_class_for(predicate, conclusion["claim_digest"]),
                run_id=run_id,
                valid_as_of=predicate["valid_as_of"],
            )
            for conclusion in predicate["conclusions"]
        ]

    @router.get("/runs/{run_id}/steps/{step_id}/evidence")
    def get_step_evidence(run_id: str, step_id: str) -> StepDetail:
        stream = _require_known_run(resources, run_id)
        detail = _project_step_detail(stream, step_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="step desconocido")
        return detail

    @router.get("/runs/{run_id}/ablation")
    def get_run_ablation(run_id: str) -> list[AblationMetric]:
        stream = _require_known_run(resources, run_id)
        return _project_ablation(stream)

    @router.get("/runs/{run_id}/topology")
    def get_run_topology(run_id: str) -> TopologyResponse:
        stream = _require_known_run(resources, run_id)
        return TopologyResponse(**_project_topology(stream))

    return router
