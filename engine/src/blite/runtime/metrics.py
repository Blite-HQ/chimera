"""
`run.metrics.recorded` — el payload extendido C-4 y su derivación del log
(V2/M19 · `docs/specs/superficie-visual.md` §9, freeze §3 marca (b)).

El choque que cierra (cobertura C-4): el evento estaba congelado con campos de
CONFIANZA (`verification_latency_ms`, `attestations_total`, …) y el consumidor
del Studio esperaba campos CIENTÍFICOS por variante — un mismo tipo de evento
con dos payloads incompatibles, y nadie emitiéndolo. La resolución es aditiva:
los de confianza se mantienen tal cual; entran `variant` (enum de 4, cubre M6)
y los científicos opcionales `cut_cost`/`wall_ms` — exactamente lo que
`AblationMetric` consume, nada más.

**Las métricas se DERIVAN del log, no se acumulan en memoria.** Es la
diferencia entre un número que un tercero puede recomputar replayando el
stream y uno que hay que creerle al proceso que lo emitió. Por eso el
orquestador estampa `latency_ms` en cada `verification.completed` y esta
proyección suma: la evidencia vive en el log, como todo lo demás.

Post-terminal y FUERA del hash (freeze §2 [stress-final]): es una familia de
cierre. Emitirlo no invalida un certificado ya emitido, y el certificado no
lo ampara — es proyección visual, jamás amparo (letra C-4).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict

from blite.events.event import Event
from blite.events.rules import TERMINAL_RUN_EVENTS
from blite.events.store import EventStore

RUN_METRICS_RECORDED_TYPE = "run.metrics.recorded"
VERIFICATION_COMPLETED_TYPE = "verification.completed"
_RUNTIME_ACTOR = "service:runtime"

AblationVariant = Literal["quantum", "classical", "mitigated", "zne"]
"""Enum de 4 (C-4) — cubre M6 (`mitigated`/`zne`). Se extiende COORDINADO con
sus 4 espejos (este modelo, `AblationMetric`, el Zod y el chart), jamás con un
catchall que dejaría entrar una variante que ninguna superficie sabe pintar."""


class RunMetricsRecordedPayload(BaseModel):
    """Payload v2 de `run.metrics.recorded` — confianza (congelado) + ciencia
    (aditivo, opcional)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    verification_latency_ms: float
    attestations_total: int
    inconclusive_count: int
    false_reject_proxy: float
    cost_per_verification: float | None = None
    ms_por_clase: dict[str, float] | None = None

    variant: AblationVariant | None = None
    cut_cost: float | None = None
    wall_ms: float | None = None


def _verification_events(stream: tuple[Event, ...]) -> list[dict[str, Any]]:
    return [e.payload for e in stream if e.type == VERIFICATION_COMPLETED_TYPE]


def _verifier_class_of(payload: dict[str, Any]) -> str | None:
    attestation: object = payload.get("attestation")
    if not isinstance(attestation, dict):
        return None
    # El `isinstance` estrecha a `dict[Unknown, Unknown]`; el cast declara lo
    # que el contrato ya garantiza (freeze §3: el payload de un evento es
    # `dict[str, Any]`) — mismo criterio que `reads::_project_topology`.
    clase: object = cast("dict[str, Any]", attestation).get("verifier_class")
    return clase if isinstance(clase, str) else None


def _false_reject_proxy(payloads: list[dict[str, Any]]) -> float:
    """Proxy de falso rechazo MEDIBLE dentro de la corrida: de los claims que
    alguna pata rechazó, qué fracción otra pata independiente aceptó.

    Un desacuerdo entre patas sobre el MISMO claim es la única señal de
    "posible rechazo falso" que existe sin salir del run. La medición fuerte
    —soluciones factibles rechazadas contra un corpus de óptimos conocidos
    (trust/05 §1.3)— necesita el corpus runner (ítem O8) y NO se aproxima acá
    con un número inventado: sin rechazos, el proxy es 0.0.
    """
    verdicts: defaultdict[str, set[str]] = defaultdict(set)
    for payload in payloads:
        claim = payload.get("claim_digest")
        verdict = payload.get("verdict")
        if isinstance(claim, str) and isinstance(verdict, str):
            verdicts[claim].add(verdict)
    rechazados = [v for v in verdicts.values() if "fail" in v]
    if not rechazados:
        return 0.0
    disputados = sum(1 for v in rechazados if "pass" in v)
    return disputados / len(rechazados)


def derive_run_metrics(
    stream: tuple[Event, ...],
    *,
    variant: AblationVariant | None = None,
    cut_cost: float | None = None,
    wall_ms: float | None = None,
) -> RunMetricsRecordedPayload:
    """Proyecta las métricas de confianza desde el stream del run.

    Los campos científicos NO se derivan: los declara quien emite (el brazo de
    ablación sabe su variante y su costo de corte; el log de verificación no).
    """
    payloads = _verification_events(stream)
    latencias: defaultdict[str, float] = defaultdict(float)
    total_ms = 0.0
    for payload in payloads:
        latencia = payload.get("latency_ms")
        ms = float(latencia) if isinstance(latencia, (int, float)) else 0.0
        total_ms += ms
        clase = _verifier_class_of(payload)
        if clase is not None:
            latencias[clase] += ms

    return RunMetricsRecordedPayload(
        verification_latency_ms=total_ms,
        attestations_total=len(payloads),
        inconclusive_count=sum(
            1 for p in payloads if p.get("verdict") == "inconclusive"
        ),
        false_reject_proxy=_false_reject_proxy(payloads),
        ms_por_clase=dict(latencias) or None,
        variant=variant,
        cut_cost=cut_cost,
        wall_ms=wall_ms,
    )


def record_run_metrics(
    store: EventStore,
    *,
    run_id: str,
    domain_id: str,
    variant: AblationVariant | None = None,
    cut_cost: float | None = None,
    wall_ms: float | None = None,
    actor_id: str = _RUNTIME_ACTOR,
) -> RunMetricsRecordedPayload | None:
    """Emite el cierre métrico de un run terminado. `None` (no-op) cuando el
    run no tiene terminal todavía —un número parcial con cara de definitivo es
    peor que ninguno— o cuando ya lo emitió: la familia de cierre se escribe
    UNA vez.
    """
    stream = store.read_stream(run_id)
    if not stream:
        return None
    if not any(e.type in TERMINAL_RUN_EVENTS for e in stream):
        return None
    if any(e.type == RUN_METRICS_RECORDED_TYPE for e in stream):
        return None

    payload = derive_run_metrics(
        stream, variant=variant, cut_cost=cut_cost, wall_ms=wall_ms
    )
    store.append(
        stream_id=run_id,
        type=RUN_METRICS_RECORDED_TYPE,
        actor_id=actor_id,
        domain_id=domain_id,
        payload=payload.model_dump(mode="json", exclude_none=True),
    )
    return payload
