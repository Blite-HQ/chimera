"""
Puerto `JobQueue` — la casa de `interaction: job` / `execution_profile:
remote-job` (P11, extensión #120). [A · runtime]

**El hueco que cierra.** El manifest v2 congela `interaction: job` y
`execution_profile: remote-job` (freeze §1), y `ProfileDispatcher` los rechaza
con `NotImplementedError` explícito — «jamás fallback silencioso a in-process»,
porque tratar un trabajo largo como síncrono es exactamente el modo de falla
que la nota execution/06 §6 señala. O sea: el vocabulario existía y **no tenía
dónde correr**. La dependencia (`procrastinate`) y el servicio (`worker` del
compose) ya estaban pagados desde el MVP, sin nadie detrás.

**Hexagonal, como el resto del runtime.** Este módulo define el PUERTO y una
estrategia que lo usa; jamás importa `procrastinate` ni toca la red o la base
(mismo principio que `ModelPort` con litellm, AX3-b: la casa legítima del SDK
está afuera). El adapter concreto se INYECTA, igual que `proposer`, `crossing`
y `approval_gate`.

**Qué NO cambia.** `remote-job` sigue retornando `JobRef` y jamás un `Result`
(freeze §1): encolar no es ejecutar. Quien quiera el resultado lo espera por
eventos, que es como el sistema entero comunica hechos.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from blite.runtime.dispatch import JobRef


@runtime_checkable
class JobQueue(Protocol):
    """El puerto: encolar un trabajo y obtener su referencia.

    `enqueue` recibe el `capability_id` (no la capability) a propósito: el
    worker que lo levante resolverá esa id contra SU registry — mandar el
    objeto exigiría serializar código, que es justo lo que el patrón de
    entry points evita."""

    def enqueue(self, capability_id: str, inputs: dict[str, Any]) -> str:
        """Devuelve el `job_id` con el que el trabajo quedó encolado."""
        ...


class RemoteJobStrategy:
    """Estrategia de despacho para `execution_profile: remote-job`.

    Encola y devuelve `JobRef` — **nunca** un `Result`. Esa asimetría es el
    contrato (freeze §1) y también la honestidad: un trabajo que va a tardar
    no puede fingir haber terminado."""

    def __init__(self, queue: JobQueue) -> None:
        self._queue = queue

    def execute(self, capability: Any, inputs: dict[str, Any]) -> JobRef:
        capability_id = capability.manifest.id
        return JobRef(job_id=self._queue.enqueue(capability_id, inputs))


def _default_job_id(numero: int) -> str:
    return f"job-{numero}"


class InMemoryJobQueue:
    """Respaldo en memoria del puerto — para tests y para el modo embebido.

    **Etiquetado con honestidad**: NO es una cola durable. No sobrevive al
    proceso, no reintenta y no tiene worker. Existe para ejercitar la costura
    sin una base de datos, igual que `InMemoryReplayManifest` para el modelo.
    Un despliegue que necesite durabilidad inyecta el adapter real."""

    def __init__(self, job_id_factory: Callable[[int], str] | None = None) -> None:
        self._jobs: list[tuple[str, str, dict[str, Any]]] = []
        self._job_id_factory: Callable[[int], str] = (
            job_id_factory if job_id_factory is not None else _default_job_id
        )

    def enqueue(self, capability_id: str, inputs: dict[str, Any]) -> str:
        job_id = self._job_id_factory(len(self._jobs) + 1)
        self._jobs.append((job_id, capability_id, inputs))
        return job_id

    def pending(self) -> tuple[tuple[str, str, dict[str, Any]], ...]:
        """Lo encolado, en orden — enumeración explícita para tests."""
        return tuple(self._jobs)


__all__ = ["InMemoryJobQueue", "JobQueue", "RemoteJobStrategy"]
