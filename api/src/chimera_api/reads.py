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

# pyright: reportUnusedFunction=false
# ^ Los handlers de FastAPI se registran por DECORADOR (`@router.get/post`), no
#   por llamada: pyright los ve como funciones locales que nadie usa. Silenciar
#   la regla acá —y solo acá— evita 15 falsos positivos sin apagar la
#   comprobación en el resto del proyecto, donde una función sin usar SÍ es
#   señal de código muerto.

from __future__ import annotations

import base64
import json
from typing import Any, Literal, cast

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from blite.certificate.assemble import AssembleError, assemble_bundle
from blite.certificate.predicate import AssuranceLevel, ConclusionVerdict
from blite.events.event import Event
from blite.events.rules import TERMINAL_RUN_EVENTS, provenance_slice
from blite.runtime.metrics import AblationVariant
from blite.runtime.projection import RunRow, project_runs
from chimera_api.runs import RunResources

RunStatusWire = Literal["en_curso", "completado", "fallido", "cancelado"]

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


class DiscardedStream(BaseModel):
    """Una fila del reporte de `GET /runs/discarded` (#104/#124) — qué stream
    se omitió del listado y por qué. `error_kind` reusa el vocabulario de
    `run.failed` (`type(exc).__name__`); `detail` es legible, opcional."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    stream_id: str
    error_kind: str
    detail: str | None = None


class DiscardedStreams(BaseModel):
    """Envelope OBJETO de la ruta nueva (#124): el array desnudo de
    `GET /runs` no admite un campo hermano sin romper E↔D, así que el reporte
    vive en su propia ruta — extensible sin tocar el contrato existente."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    discarded_streams: tuple[DiscardedStream, ...] = ()


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
    """`GET /runs/{run_id}/ablation` — `run.metrics.recorded` por variante.

    [V2/M19 · C-4] `variant` pasa de 2 a 4 valores EN EL MISMO checkpoint que
    su productor (`blite.runtime.metrics`), de donde se importa el enum: dos
    copias del mismo Literal es exactamente el drift que C-15 prohíbe. Una
    fila sin los 4 campos se OMITE (ver `_project_ablation`) — un run que solo
    reportó confianza no aparece como un punto científico fabricado."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    variant: AblationVariant
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
    # [V2/M19] El corte NO es "el último evento del stream": freeze §2
    # [stress-final] admite familias de CIERRE post-terminales
    # (`run.metrics.recorded`, ● de cierre del case) que quedan FUERA del
    # hash. Comprobar `stream[-1]` daba 409 en cuanto el cierre métrico
    # existió — y pasarle el stream completo a `assemble_bundle` habría metido
    # un evento post-terminal DENTRO del provenance_hash. Por eso: el run está
    # terminado si TIENE terminal, y lo que se certifica es el corte.
    if not stream or not any(e.type in TERMINAL_RUN_EVENTS for e in stream):
        return None
    try:
        return assemble_bundle(
            stream=provenance_slice(stream),
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


_STATUS_BY_TERMINAL_EVENT: dict[str, RunStatusWire] = {
    "run.completed": "completado",
    "run.failed": "fallido",
    "run.cancelled": "cancelado",
}


def _run_status(stream: tuple[Event, ...]) -> RunStatusWire:
    """Mismo cómputo que `deriveRunSummary` (client): el PRIMER evento
    terminal (`TERMINAL_RUN_EVENTS`, freeze §2) que aparece en el stream
    manda su status; sin ninguno todavía, `en_curso`.

    Extensión ADITIVA (auditoría Fase 2, `docs/mvp/decisiones.md`
    §"Análisis para discusión" punto 3): antes esta función solo miraba
    `run.completed`, así que un run terminado por `run.failed`/
    `run.cancelled` quedaba "en_curso" PARA SIEMPRE en `GET /runs`
    (verificado vivo). `run.completed` conserva su cómputo exacto anterior
    (sin cambio de comportamiento para el camino ya congelado)."""
    for event in stream:
        status = _STATUS_BY_TERMINAL_EVENT.get(event.type)
        if status is not None:
            return status
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
    attestation: object = payload.get("attestation")
    if isinstance(attestation, dict):
        nested = cast(dict[str, Any], attestation).get("step_id")
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
    isla (harness-agentico/dominio ciencia aún no cablea el productor real).

    Nota de tipos: `isinstance(x, dict)` estrecha a `dict[Unknown, Unknown]`
    y pierde el tipo de los valores. El `cast` declara lo que el contrato ya
    garantiza (freeze §3: el payload de un evento es `dict[str, Any]`) en vez
    de arrastrar `Unknown` por toda la proyección — y va DESPUÉS del
    `isinstance`, así que la comprobación en runtime sigue siendo real."""
    for event in reversed(stream):
        if event.type != _VERIFICATION_COMPLETED:
            continue
        cruda: object = event.payload.get(_PARTITION_PAYLOAD_KEY)
        if not isinstance(cruda, dict):
            continue
        partition = cast(dict[str, Any], cruda)
        islas: object = partition.get("islands")
        if not isinstance(islas, list):
            continue
        islands = cast(list[Any], islas)
        if not all(_is_valid_island(island) for island in islands):
            continue
        cortes = cast(list[Any], partition.get("cut_branch_ids", []))
        return {
            "topology_ref": partition.get("topology_ref"),
            "islands": tuple(islands),
            "cut_branch_ids": tuple(str(branch) for branch in cortes),
            "cut_cost": partition.get("cut_cost", 0.0),
        }
    return _empty_topology()


def _events_por_stream(events: tuple[Event, ...]) -> dict[str, list[Event]]:
    """Agrupa preservando el orden del log dentro de cada stream (el fold de
    `project_runs` depende del orden, no del `global_seq` absoluto)."""
    agrupados: dict[str, list[Event]] = {}
    for event in events:
        agrupados.setdefault(event.stream_id, []).append(event)
    return agrupados


def _proyectar_salteando_envenenados(
    events: tuple[Event, ...],
) -> tuple[dict[str, RunRow], tuple[DiscardedStream, ...]]:
    """Skip honesto de la ruta de LECTURA (#104): proyecta stream POR STREAM
    y omite el que explote, en vez de perder el listado entero.

    La píldora #96 lo probó en vivo: UN `run.created` sin `policy_digest`/
    `max_steps` (payload que el freeze §3 declara obligatorio, así que
    `_row_from_created` explota POR DISEÑO) tumbaba `GET /runs` con 500 —
    un stream ajeno al pedido dejaba ciego al Studio completo.

    `project_runs` se reusa TAL CUAL, sin tocar su semántica: el camino de
    escritura, los certificados y el `provenance_hash` siguen fail-loud
    (línea roja de #104 — este skip es de lectura y NADA más; la ruta
    hermana `GET /runs/discarded` lo REPORTA, no lo cura)."""
    rows: dict[str, RunRow] = {}
    discarded: list[DiscardedStream] = []
    for stream_id, stream_events in _events_por_stream(events).items():
        try:
            rows.update(project_runs(tuple(stream_events)))
        except Exception as exc:  # noqa: BLE001 — skip honesto de lectura: CUALQUIER falla de proyección de un stream se reporta, jamás tumba el listado
            discarded.append(
                DiscardedStream(
                    stream_id=stream_id,
                    error_kind=type(exc).__name__,
                    detail=str(exc) or None,
                )
            )
    return rows, tuple(discarded)


def create_reads_router(resources: RunResources) -> APIRouter:
    """Router de los 6 GETs de lectura, cerrado sobre la MISMA infra de
    vida-de-app que `/runs`/`/runs/{run_id}/certificate` (un `RunResources`
    por app — mismo `store`, mismos `run_tickets`)."""
    router = APIRouter()

    def _listar() -> tuple[list[RunSummary], tuple[DiscardedStream, ...]]:
        """Las DOS rutas salen del mismo cómputo — una sola definición de qué
        se lista y qué se descartó (si divergieran, `GET /runs/discarded`
        dejaría de explicar lo que `GET /runs` omitió)."""
        rows, descartados = _proyectar_salteando_envenenados(resources.store.read_all())
        filas: list[RunSummary] = []
        fallidos: list[DiscardedStream] = list(descartados)
        for run_id, row in rows.items():
            try:
                filas.append(_run_summary(resources, run_id, row.actor_id))
            except Exception as exc:  # noqa: BLE001 — segunda mitad del skip honesto: el RESUMEN también puede explotar, y tumbar el listado por un run ajeno es el mismo defecto que #104 cierra
                fallidos.append(
                    DiscardedStream(
                        stream_id=run_id,
                        error_kind=type(exc).__name__,
                        detail=str(exc) or None,
                    )
                )
        return filas, tuple(fallidos)

    @router.get("/runs")
    def list_runs() -> list[RunSummary]:
        """Forma INTACTA (array desnudo, byte-idéntica): lo único que cambia
        es que un run que no se puede resumir se omite en vez de tumbar el
        listado entero."""
        filas, _ = _listar()
        return filas

    @router.get("/runs/discarded")
    def list_discarded_streams() -> DiscardedStreams:
        """Ruta hermana (#104/#124): qué omitió `GET /runs` y por qué. Vacío
        honesto cuando no se descartó nada — jamás filas fabricadas. El
        segmento literal `discarded` no colisiona con un `run_id` (uuid4)."""
        _, descartados = _listar()
        return DiscardedStreams(discarded_streams=descartados)

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
