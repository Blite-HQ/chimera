"""Puerto `JobQueue` y despacho `remote-job` — P11 (extensión #120).

El vocabulario `interaction: job` / `execution_profile: remote-job` está
congelado (freeze §1) desde el manifest v2, y hasta ahora **no tenía dónde
correr**: `ProfileDispatcher` lo rechazaba con `NotImplementedError`. Estos
tests fijan las dos garantías que importan: que encolar NO es ejecutar, y que
un despliegue sin cola sigue fallando fuerte en vez de degradar a síncrono.
"""

from __future__ import annotations

from typing import Any

import pytest

from blite.runtime.dispatch import JobRef, ProfileDispatcher
from blite.runtime.jobs import InMemoryJobQueue, JobQueue, RemoteJobStrategy
from blite_capability.manifest import CapabilityManifest


class _JobCapability:
    """Doble genérico (ADR-029) declarado como trabajo remoto."""

    def __init__(self) -> None:
        self.invocaciones = 0

    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id="cap.trabajo-largo",
            description="generic long-running test capability",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            side_effects="pure",
            required_permission="capability:invoke",
            interaction="job",
            execution_profile="remote-job",
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        self.invocaciones += 1
        return {"no": "deberia correr acá"}


def test_encolar_no_es_ejecutar() -> None:
    """La garantía central (freeze §1): `remote-job` devuelve `JobRef`, jamás
    un `Result` — y la capability NO se invoca en este proceso. Un trabajo que
    va a tardar no puede fingir haber terminado."""
    capability = _JobCapability()
    queue = InMemoryJobQueue()

    resultado = RemoteJobStrategy(queue).execute(capability, {"x": 1})

    assert isinstance(resultado, JobRef)
    assert resultado.job_id == "job-1"
    assert capability.invocaciones == 0
    assert queue.pending() == (("job-1", "cap.trabajo-largo", {"x": 1}),)


def test_se_encola_el_id_de_la_capability_no_el_objeto() -> None:
    """El worker resuelve la id contra SU registry — mandar el objeto exigiría
    serializar código, justo lo que el patrón de entry points evita."""
    queue = InMemoryJobQueue()
    RemoteJobStrategy(queue).execute(_JobCapability(), {})
    _, capability_id, _ = queue.pending()[0]
    assert capability_id == "cap.trabajo-largo"
    assert isinstance(capability_id, str)


def test_sin_cola_inyectada_remote_job_sigue_fallando_fuerte() -> None:
    """Regresión del invariante: un despliegue SIN cola no degrada a
    in-process en silencio (nota execution/06 §6, el modo de falla central)."""
    with pytest.raises(NotImplementedError, match="jamás fallback silencioso"):
        ProfileDispatcher().resolve("remote-job")


def test_con_cola_inyectada_el_dispatcher_resuelve_remote_job() -> None:
    dispatcher = ProfileDispatcher(remote_job=RemoteJobStrategy(InMemoryJobQueue()))
    estrategia = dispatcher.resolve("remote-job")
    resultado = estrategia.execute(_JobCapability(), {})
    assert isinstance(resultado, JobRef)


def test_in_process_sigue_intacto_con_la_extension() -> None:
    """La inyección es ADITIVA: el camino que ya funcionaba no cambia."""
    capability = _JobCapability()
    dispatcher = ProfileDispatcher(remote_job=RemoteJobStrategy(InMemoryJobQueue()))
    salida = dispatcher.resolve("in-process").execute(capability, {"x": 1})
    assert salida == {"no": "deberia correr acá"}
    assert capability.invocaciones == 1


def test_la_cola_en_memoria_satisface_el_puerto() -> None:
    """`runtime_checkable`: el respaldo en memoria ES un `JobQueue` — el
    adapter durable (Procrastinate) entra por la MISMA firma."""
    assert isinstance(InMemoryJobQueue(), JobQueue)


def test_el_loop_todavia_no_sabe_journalizar_un_trabajo_encolado() -> None:
    """FRONTERA DECLARADA (P11, 2026-08-17) — no un test de comportamiento
    deseado, sino la prueba de por qué la cola durable NO se cableó al
    dispatcher del despliegue.

    `RemoteJobStrategy` cumple su contrato (devuelve `JobRef`, no ejecuta),
    pero el loop que la llamaría espera un `Result`: journaliza
    `capability.job.submitted`, y con lo que la estrategia devuelve intenta
    `digest_of(...)` — que canonicaliza a JSON y revienta con un `JobRef`.
    O sea: el camino `remote-job` NUNCA se recorrió de punta a punta, y este
    test lo estampa en vez de dejarlo como sospecha.

    Lo importante NO es el `TypeError` (eso es un síntoma arreglable). Es la
    pregunta que hay detrás y que es de CONTRATO, no de wiring: qué emite el
    loop cuando un trabajo fue ENCOLADO y no ejecutado. `capability.job.
    completed` mentiría —encolar no es ejecutar, #148—, y el turno tampoco
    tiene `output_digest` con el que seguir. Decidirlo es ceremonia de
    contrato (catálogo §14 + freeze §1), así que P11 dejó `remote-job` sin
    estrategia: sigue fallando fuerte, que es la postura correcta mientras la
    pregunta esté abierta.

    Cuando esa decisión se tome, este test cambia — y su cambio será el
    registro de que se tomó."""
    from blite.events import create_event_store
    from blite.runtime.content_store import InMemoryContentStore
    from blite.runtime.loop import execute_run
    from blite.runtime.registry import EntryPointRegistry

    store = create_event_store()
    with pytest.raises(TypeError, match="JobRef is not JSON serializable"):
        execute_run(
            store,
            EntryPointRegistry({"cap.trabajo-largo": _JobCapability()}),
            ProfileDispatcher(remote_job=RemoteJobStrategy(InMemoryJobQueue())),
            InMemoryContentStore(),
            run_id="run-remote-job",
            actor_id="user:quien-sea",
            domain_id="domain-a",
            max_steps=4,
            policy_digest="pol-1",
            capability_id="cap.trabajo-largo",
            inputs={},
        )

    tipos = [e.type for e in store.read_stream("run-remote-job")]
    # El rastro llega hasta el submitted y ahí se corta: ni completed (que
    # mentiría) ni terminal (lo pone el guard de último recurso del arranque,
    # `chimera_api.runs.run_in_background` — fuera del runtime).
    assert tipos[-1] == "capability.job.submitted"
    assert "capability.job.completed" not in tipos
