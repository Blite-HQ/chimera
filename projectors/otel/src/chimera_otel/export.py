"""Del `TracePlan` a spans OTLP reales.

El SDK de OpenTelemetry genera ids ALEATORIOS por diseño; acá son DETERMINISTAS
(S-F §4). Sin eso, dos proyecciones del mismo stream producirían trazas
distintas y la propiedad entera que O3 demuestra se caería.

La forma de conseguirlo importa: se usa el punto de extensión que el SDK ofrece
(`IdGenerator`) y NO se toca el `_context` privado del span. Escribir un
atributo privado habría funcionado hoy y se habría roto en la próxima versión
del SDK, en silencio y justo en la propiedad que sostiene el diseño.

Los tiempos también salen del plan (`occurred_at`), nunca del reloj de la
exportación.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.sdk.trace.id_generator import IdGenerator
from opentelemetry.trace import (
    NonRecordingSpan,
    SpanContext,
    Status,
    StatusCode,
    TraceFlags,
    set_span_in_context,
)

from chimera_otel.projection import SpanPlan, TracePlan, base_attributes, span_id_for

_STATUS = {
    "ok": StatusCode.OK,
    "error": StatusCode.ERROR,
    "unset": StatusCode.UNSET,
}


class PlannedIdGenerator(IdGenerator):
    """Devuelve los ids que el plan ya decidió, en el orden en que se piden.

    El SDK llama `generate_span_id()` una vez por span creado; la exportación es
    secuencial, así que encolar el id justo antes de crear su span es exacto.
    Si alguna vez se pidiera un id sin haberlo encolado, es un bug de esta clase
    y no un id aleatorio silencioso: la cola vacía levanta.
    """

    def __init__(self) -> None:
        self._trace_id = 0
        self._span_ids: deque[int] = deque()

    def expect(self, trace_id: bytes, span_id: bytes) -> None:
        self._trace_id = int.from_bytes(trace_id, "big")
        self._span_ids.append(int.from_bytes(span_id, "big"))

    def generate_span_id(self) -> int:
        if not self._span_ids:
            msg = "PlannedIdGenerator: se pidió un span_id que nadie encoló"
            raise RuntimeError(msg)
        return self._span_ids.popleft()

    def generate_trace_id(self) -> int:
        return self._trace_id


def _context_for(trace_id: bytes, span_id: bytes) -> SpanContext:
    return SpanContext(
        trace_id=int.from_bytes(trace_id, "big"),
        span_id=int.from_bytes(span_id, "big"),
        is_remote=False,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
    )


def build_provider(exporter: SpanExporter) -> tuple[TracerProvider, PlannedIdGenerator]:
    """Provider + el generador que hay que alimentar antes de cada span."""
    generator = PlannedIdGenerator()
    provider = TracerProvider(id_generator=generator)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    return provider, generator


def _emit_span(
    provider: TracerProvider,
    generator: PlannedIdGenerator,
    plan: TracePlan,
    span: SpanPlan,
) -> None:
    tracer = provider.get_tracer("chimera_otel")
    generator.expect(plan.trace_id, span_id_for(plan.run_id, span.anchor))

    parent_ctx = None
    if span.parent_anchor is not None:
        parent_id = span_id_for(plan.run_id, span.parent_anchor)
        parent_ctx = set_span_in_context(
            NonRecordingSpan(_context_for(plan.trace_id, parent_id))
        )

    otel_span = tracer.start_span(
        span.name,
        context=parent_ctx,
        start_time=span.start_ns,
        attributes={
            **base_attributes(),
            **span.attributes,
            "chimera.anchor": span.anchor,
        },
    )
    otel_span.set_status(Status(_STATUS[span.status]))
    if span.parent_anchor is None:
        for mark in plan.events:
            otel_span.add_event(
                mark.name, attributes=dict(mark.attributes), timestamp=mark.time_ns
            )
    otel_span.end(end_time=span.end_ns)


def export_trace(
    provider: TracerProvider, generator: PlannedIdGenerator, plan: TracePlan
) -> None:
    """Emite la traza completa de un run. Padres antes que hijos."""
    ordered = sorted(
        plan.spans, key=lambda s: (s.parent_anchor is not None, s.start_ns)
    )
    for span in ordered:
        _emit_span(provider, generator, plan, span)


def export_all(
    provider: TracerProvider, generator: PlannedIdGenerator, plans: Sequence[TracePlan]
) -> int:
    for plan in plans:
        export_trace(provider, generator, plan)
    return len(plans)
