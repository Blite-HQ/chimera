"""`chimera_otel` — proyector de observabilidad, consumer standalone.

Deriva spans OTLP del stream de eventos. FUERA de `blite.*` por la resolución
C-11: el exportador OTLP es egress y no puede vivir dentro del engine sin chocar
Inv-E/INV-6. No gobierna, no escribe, no importa el engine — parsea el wire.

Contrato: `docs/specs/observabilidad-proyeccion.md` (S-F, decisión #128).
"""

from chimera_otel.projection import (
    PROJECTOR_VERSION,
    SEMCONV_VERSION,
    SpanEventPlan,
    SpanPlan,
    TracePlan,
    project_run,
    span_id_for,
    trace_id_for_run,
)

__all__ = [
    "PROJECTOR_VERSION",
    "SEMCONV_VERSION",
    "SpanEventPlan",
    "SpanPlan",
    "TracePlan",
    "project_run",
    "span_id_for",
    "trace_id_for_run",
]
