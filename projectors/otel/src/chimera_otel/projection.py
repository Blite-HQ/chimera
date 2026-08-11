"""Proyección evento→span — la mitad PURA del proyector (S-F §3/§4).

Sin base de datos, sin OTLP, sin `blite`: entra una lista de eventos del wire
(dicts JSON) y sale un plan de traza. Todo lo que decide la FORMA de la traza
vive acá, y por eso se puede probar sin levantar nada.

La frontera C-11 es estructural: **este módulo no importa el engine**. Parsea
el wire, que ES el contrato — el mismo desacople que el Studio. Un test lo
verifica leyendo el AST, no `sys.modules` (que la suite comparte y no sirve de
testigo).

**Determinismo (§4).** Los ids se derivan por hash de dominio versionado, y los
tiempos salen de `occurred_at`, jamás del reloj de la proyección. Consecuencia:
re-proyectar el mismo stream —o el stream de un replay fiel— produce trazas
byte-idénticas. Una divergencia de traza sin `replay.divergence` en el stream es
un bug del proyector, no del run.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

TRACE_DOMAIN = b"blite/otel-trace/v1\n"
SPAN_DOMAIN = b"blite/otel-span/v1\n"

PROJECTOR_VERSION = "1"
"""Cambiar el mapeo o el esquema de derivación = bump acá Y en el prefijo de
dominio (`.../v2`). Misma disciplina que el anexo de canonicalización."""

SEMCONV_VERSION = "1.38.0"
"""Pin de la convención semántica GenAI de OpenTelemetry (S-F §5 deja el pin a
O3, con registro). Las semconv GenAI siguen incubando: cada span porta esta
versión para que el consumidor sepa QUÉ dialecto lee y dos proyecciones con
convenciones distintas jamás se confundan."""

RUN_ANCHOR = "run"

_TERMINAL_TYPES = ("run.completed", "run.failed", "run.cancelled")

#: Eventos que NO merecen span propio: son marcas en la línea de tiempo del run
#: (S-F §3, última fila de la tabla). Un span por cada uno inflaría la traza sin
#: agregar duración que medir.
_ROOT_EVENT_PREFIXES = (
    "plan.",
    "approval.",
    "mission.message",
    "replay.divergence",
    "run.metrics.recorded",
)

#: Claves de payload que JAMÁS se exportan: contenido en claro. La regla dura de
#: §3 (hash-first §2 + soberanía §15.1) es que la traza lleva digests e ids, y
#: quien quiera el contenido lo resuelve contra el `ContentStore` con SUS
#: permisos. Una traza no es un canal de exfiltración.
_CONTENT_KEYS = frozenset(
    {
        "prompt",
        "response",
        "content",
        "text",
        "message",
        "messages",
        "inputs",
        "outputs",
        "payload",
        "attestation",
        "statement",
    }
)

AttrValue = str | int | float | bool
Attributes = Mapping[str, AttrValue]


def _no_attributes() -> Attributes:
    """`field(default_factory=dict)` deja el tipo en `dict[Unknown, Unknown]`
    y el gate estricto lo rechaza — con razón: un mapa sin tipo de valor deja
    pasar cualquier cosa a los atributos de un span exportado."""
    return {}


def trace_id_for_run(run_id: str) -> bytes:
    """16 bytes deterministas por run (§4)."""
    return hashlib.sha256(TRACE_DOMAIN + run_id.encode()).digest()[:16]


def span_id_for(run_id: str, anchor: str) -> bytes:
    """8 bytes deterministas por (run, ancla) (§4)."""
    return hashlib.sha256(SPAN_DOMAIN + f"{run_id}:{anchor}".encode()).digest()[:8]


@dataclass(frozen=True)
class SpanPlan:
    """Un span, ya resuelto: sin reloj, sin aleatoriedad, sin SDK."""

    name: str
    anchor: str
    parent_anchor: str | None
    start_ns: int
    end_ns: int
    status: str
    attributes: Attributes = field(default_factory=_no_attributes)


@dataclass(frozen=True)
class SpanEventPlan:
    """Una marca en el span raíz (los eventos que no merecen span propio)."""

    name: str
    time_ns: int
    attributes: Attributes = field(default_factory=_no_attributes)


@dataclass(frozen=True)
class TracePlan:
    """La traza completa de UN run."""

    run_id: str
    trace_id: bytes
    spans: tuple[SpanPlan, ...]
    events: tuple[SpanEventPlan, ...]

    def span_ids(self) -> dict[str, bytes]:
        return {
            span.anchor: span_id_for(self.run_id, span.anchor) for span in self.spans
        }


def to_unix_nanos(value: Any) -> int:
    """`occurred_at` del wire → nanos. El reloj de la proyección no participa."""
    if isinstance(value, (int, float)):
        return int(value * 1_000_000_000)
    text = str(value).replace("Z", "+00:00")
    return int(datetime.fromisoformat(text).timestamp() * 1_000_000_000)


def _safe_attributes(
    payload: Mapping[str, Any], keys: Sequence[str]
) -> dict[str, AttrValue]:
    """Solo escalares, solo claves declaradas, jamás contenido en claro."""
    out: dict[str, AttrValue] = {}
    for key in keys:
        if key in _CONTENT_KEYS:
            continue
        value = payload.get(key)
        if isinstance(value, (str, int, float, bool)):
            out[key] = value
    return out


def is_run_stream(stream_id: str) -> bool:
    """Los streams `system:*` quedan FUERA: no son el rastro de un run (§3)."""
    return not stream_id.startswith("system:")


def _status_for(event_type: str) -> str:
    if event_type.endswith(".failed"):
        return "error"
    if event_type.endswith((".completed", ".cancelled")):
        return "ok"
    return "unset"


class _SpanBuilder:
    """Acumula inicio/fin de un span mientras se recorre el stream."""

    def __init__(
        self, name: str, anchor: str, parent: str | None, start_ns: int
    ) -> None:
        self.name = name
        self.anchor = anchor
        self.parent = parent
        self.start_ns = start_ns
        self.end_ns = start_ns
        self.status = "unset"
        self.attributes: dict[str, AttrValue] = {}

    def close(self, end_ns: int, status: str) -> None:
        self.end_ns = max(end_ns, self.start_ns)
        self.status = status

    def build(self) -> SpanPlan:
        return SpanPlan(
            name=self.name,
            anchor=self.anchor,
            parent_anchor=self.parent,
            start_ns=self.start_ns,
            end_ns=self.end_ns,
            status=self.status,
            attributes=dict(self.attributes),
        )


def project_run(events: Sequence[Mapping[str, Any]]) -> TracePlan | None:
    """Proyecta el stream de UN run. `None` si no es un stream de run."""
    if not events:
        return None
    stream_id = str(events[0].get("stream_id", ""))
    if not is_run_stream(stream_id):
        return None

    run_id = stream_id
    ordered = sorted(events, key=lambda e: int(e.get("seq", 0)))
    builders: dict[str, _SpanBuilder] = {}
    root: _SpanBuilder | None = None
    marks: list[SpanEventPlan] = []

    for event in ordered:
        event_type = str(event.get("type", ""))
        payload: Mapping[str, Any] = event.get("payload") or {}
        when = to_unix_nanos(event.get("occurred_at"))

        if event_type == "run.created":
            root = _SpanBuilder("run", RUN_ANCHOR, None, when)
            root.attributes.update(
                _safe_attributes(payload, ("domain_id", "policy_digest", "max_steps"))
            )
            root.attributes["run_id"] = run_id
            actor = event.get("actor_id")
            if isinstance(actor, str):
                root.attributes["actor_id"] = actor
            builders[RUN_ANCHOR] = root
            continue

        if event_type in _TERMINAL_TYPES:
            if root is not None:
                root.close(when, _status_for(event_type))
                root.attributes["run.status"] = event_type.removeprefix("run.")
            continue

        if event_type.startswith("run.step."):
            anchor = str(payload.get("step_id", ""))
            if not anchor:
                continue
            builder = builders.get(anchor)
            if builder is None:
                builder = _SpanBuilder("step", anchor, RUN_ANCHOR, when)
                builders[anchor] = builder
            builder.attributes.update(
                _safe_attributes(
                    payload,
                    ("step_id", "kind", "input_digest", "output_digest", "status"),
                )
            )
            if not event_type.endswith(".started"):
                builder.close(when, _status_for(event_type))
            continue

        if event_type.startswith("capability.job."):
            anchor = str(payload.get("job_id", ""))
            if not anchor:
                continue
            builder = builders.get(anchor)
            if builder is None:
                parent = str(payload.get("step_id", "")) or RUN_ANCHOR
                builder = _SpanBuilder("capability", anchor, parent, when)
                builders[anchor] = builder
            builder.attributes.update(
                _safe_attributes(
                    payload,
                    (
                        "job_id",
                        "step_id",
                        "capability_id",
                        "input_digest",
                        "output_digest",
                    ),
                )
            )
            if not event_type.endswith(".submitted"):
                builder.close(when, _status_for(event_type))
            continue

        if event_type.startswith("model.call."):
            anchor = str(payload.get("prompt_digest", ""))
            if not anchor:
                continue
            builder = builders.get(anchor)
            if builder is None:
                builder = _SpanBuilder("gen_ai", anchor, RUN_ANCHOR, when)
                builders[anchor] = builder
            builder.attributes.update(
                _safe_attributes(
                    payload,
                    (
                        "backend_id",
                        "local",
                        "prompt_digest",
                        "response_digest",
                        "model_id",
                    ),
                )
            )
            if not event_type.endswith(".requested"):
                builder.close(when, _status_for(event_type))
            continue

        if event_type.startswith("verification."):
            anchor = f"verification:{payload.get('claim_digest', len(builders))}"
            builder = builders.get(anchor)
            if builder is None:
                builder = _SpanBuilder("verification", anchor, RUN_ANCHOR, when)
                builders[anchor] = builder
            builder.attributes.update(
                _safe_attributes(
                    payload,
                    (
                        "claim_digest",
                        "verifier_id",
                        "verdict",
                        "verifier_class",
                        "assurance_level",
                    ),
                )
            )
            builder.close(when, "ok" if payload.get("verdict") != "fail" else "error")
            continue

        if event_type.startswith(_ROOT_EVENT_PREFIXES):
            marks.append(
                SpanEventPlan(
                    name=event_type,
                    time_ns=when,
                    attributes=_safe_attributes(payload, tuple(payload.keys())),
                )
            )

    if root is None:
        return None

    # Un span sin cierre (el run se cayó a medio paso) hereda el fin del run: se
    # ve su duración real en vez de un span de longitud cero que miente.
    for builder in builders.values():
        if builder.status == "unset" and builder is not root:
            builder.close(root.end_ns, "unset")

    spans = tuple(builder.build() for builder in builders.values())
    return TracePlan(
        run_id=run_id,
        trace_id=trace_id_for_run(run_id),
        spans=spans,
        events=tuple(marks),
    )


def base_attributes() -> dict[str, AttrValue]:
    """Las dos marcas que S-F §5 vuelve contrato desde ya."""
    return {
        "chimera.semconv_version": SEMCONV_VERSION,
        "chimera.projector_version": PROJECTOR_VERSION,
    }
