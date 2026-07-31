"""
Replay por digest de cada efecto — A5 (`docs/specs/harness-agentico.md`
§Contrato-5). [S-G · confianza]

Extiende (no reemplaza) la doctrina `replay` ya congelada en
`blite.serving.model_port` (miss ⇒ `REPLAY_MISS_ERROR_KIND`, JAMÁS
passthrough — freeze §15.7). Lo NUEVO acá es la comprobación de FIDELIDAD
tras una pasada de replay/auditoría: por CADA efecto (llamada de modelo o
`capability.job`) journalizado como `(request_digest, response_digest)`,
recomputar y comparar — una divergencia ⇒ `replay.divergence`, evento
tipado, nunca una excepción silenciosa. Doctrina R1 (exclusiva de Chimera):
"el certificado DSSE verifica ⟺ el replay fue fiel" — `check_bundle` (punto
8, `blite.certificate.bundle_check`) consume el resultado de este módulo
indirectamente: si CUALQUIER `replay.divergence` quedó en el stream, el
bundle falla sin importar que la firma sea válida.

`knowledge/execution/03-durable-execution.md`: "durabilidad por replay del
log, no motor nuevo" — este módulo es exactamente eso: ninguna ejecución
nueva, solo una comprobación que LEE el stream ya journalizado.

Emparejamiento de efectos (`extract_effects`) — dos convenciones distintas:
- `capability_job`: `capability.job.submitted`/`capability.job.completed`,
  correlacionados por `job_id` — forma YA real de
  `blite.runtime.loop._RunRecorder` (freeze §3, PR1: submitted ANTES de
  ejecutar).
- `model_call`: `model.call.requested`/`model.call.completed`, por
  ADYACENCIA secuencial (FIFO) dentro del stream. El contrato congelado
  (`docs/contract-freeze.md` §3) todavía no declara un id de correlación
  propio para este par (a diferencia de `job_id`) — la wiring real del
  `ModelPort`/`ModelServer` es frontera Dylan+Steven, declarada pero NO
  entregada en Fase 0 (`docs/specs/harness-agentico.md` §Contrato-5). FIFO
  es la convención más simple defendible mientras esa frontera no decide un
  id propio. Limitación conocida (decisión candidata a `decisiones.md`):
  llamadas de modelo CONCURRENTES dentro de un mismo run romperían el
  emparejamiento FIFO — no es un riesgo en Fase 1 porque el loop es
  secuencial (nota 02).
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

_SHA256_HEX = r"^[0-9a-f]{64}$"

EffectKind = Literal["model_call", "capability_job"]
"""Conjunto CERRADO — un valor fuera de este set es error de contrato
(misma disciplina que `RunStep.status`/`error_kind` tipados)."""

_CAPABILITY_JOB_SUBMITTED = "capability.job.submitted"
_CAPABILITY_JOB_COMPLETED = "capability.job.completed"
_MODEL_CALL_REQUESTED = "model.call.requested"
_MODEL_CALL_COMPLETED = "model.call.completed"


class ReplayDivergencePayload(BaseModel):
    """`replay.divergence` ↔ `●ReplayDivergenceDetected` (docs/specs/harness-
    agentico.md §Eventos) — evento tipado, nunca una excepción silenciosa."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    effect_kind: EffectKind
    request_digest: str = Field(pattern=_SHA256_HEX)
    expected_response_digest: str = Field(pattern=_SHA256_HEX)
    actual_response_digest: str = Field(pattern=_SHA256_HEX)
    step_id: str | None = None


class JournaledEffect(BaseModel):
    """Un efecto tal como quedó journalizado — el par `(request_digest,
    response_digest)` que R1 exige recomputar y comparar."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    effect_kind: EffectKind
    request_digest: str = Field(pattern=_SHA256_HEX)
    response_digest: str = Field(pattern=_SHA256_HEX)
    step_id: str | None = None


Recomputer = Callable[[JournaledEffect], str]
"""Recomputa el response_digest ACTUAL de un efecto — INYECTABLE a propósito:
este módulo nunca llama un SDK de modelo, un Dispatcher, ni red directamente
(mantiene `blite.runtime` libre de AX3-b/INV-5 por construcción); quien
invoca `find_replay_divergences` inyecta la implementación real (o, en
tests, un stub determinista)."""


def extract_effects(stream: Sequence[Mapping[str, Any]]) -> tuple[JournaledEffect, ...]:
    """Empareja efectos journalizados del stream de un run — ver docstring
    del módulo para la convención de correlación de cada `effect_kind`.
    Efectos sin contraparte `completed` (p. ej. un `capability.job.failed`,
    o un `model.call.failed`) no producen `JournaledEffect`: no hay
    `response_digest` que recomputar."""
    effects: list[JournaledEffect] = []
    pending_jobs: dict[str, tuple[str, str | None]] = {}
    pending_model_calls: deque[str] = deque()

    for event in stream:
        event_type = event.get("type")
        payload = event.get("payload", {})
        if event_type == _CAPABILITY_JOB_SUBMITTED:
            pending_jobs[payload["job_id"]] = (
                payload["input_digest"],
                payload.get("step_id"),
            )
        elif event_type == _CAPABILITY_JOB_COMPLETED:
            pending = pending_jobs.pop(payload["job_id"], None)
            if pending is None:
                continue  # completed sin su submitted: nada que emparejar
            request_digest, step_id = pending
            effects.append(
                JournaledEffect(
                    effect_kind="capability_job",
                    request_digest=request_digest,
                    response_digest=payload["output_digest"],
                    step_id=step_id,
                )
            )
        elif event_type == _MODEL_CALL_REQUESTED:
            pending_model_calls.append(payload["prompt_digest"])
        elif event_type == _MODEL_CALL_COMPLETED:
            if not pending_model_calls:
                continue  # completed sin su requested: nada que emparejar
            request_digest = pending_model_calls.popleft()
            effects.append(
                JournaledEffect(
                    effect_kind="model_call",
                    request_digest=request_digest,
                    response_digest=payload["response_digest"],
                    step_id=payload.get("step_id"),
                )
            )
    return tuple(effects)


def find_replay_divergences(
    run_id: str,
    stream: Sequence[Mapping[str, Any]],
    recompute: Recomputer,
) -> tuple[ReplayDivergencePayload, ...]:
    """El núcleo de A5 (R1): por CADA efecto journalizado en `stream`,
    recomputa su `response_digest` vía `recompute` (inyectable) y compara
    contra lo journalizado — una divergencia ⇒ un `ReplayDivergencePayload`,
    nunca una excepción silenciosa. Cubre `model_call` Y `capability_job`
    por el mismo camino; `effect_kind` distingue cuál es cuál."""
    divergences: list[ReplayDivergencePayload] = []
    for effect in extract_effects(stream):
        actual = recompute(effect)
        if actual != effect.response_digest:
            divergences.append(
                ReplayDivergencePayload(
                    run_id=run_id,
                    effect_kind=effect.effect_kind,
                    request_digest=effect.request_digest,
                    expected_response_digest=effect.response_digest,
                    actual_response_digest=actual,
                    step_id=effect.step_id,
                )
            )
    return tuple(divergences)
