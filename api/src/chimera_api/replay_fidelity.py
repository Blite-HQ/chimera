"""
Conductor de fidelidad de replay — P4/M31. [E]

`blite.runtime.replay` implementa el NÚCLEO de la propiedad R1 desde A5
(`extract_effects` + `find_replay_divergences`), pero con un `Recomputer`
INYECTABLE y sin nadie que lo inyectara: era infraestructura sin uso, por dos
razones encadenadas —

1. nadie emitía `model.call.*` (P4 lo cierra: `chimera_api.model_proposer`),
   así que `extract_effects` no tenía efectos de modelo que emparejar;
2. nadie construía el `Recomputer` real contra una sesión grabada.

Este módulo cierra (2): `session_recomputer` arma el recomputador sobre el
manifest de una sesión en disco, y `check_run_fidelity` corre la comprobación
sobre el stream de un run y emite un `replay.divergence` por cada desvío —
evento TIPADO, jamás una excepción silenciosa (`harness-agentico.md`
§Contrato-5).

**Qué propiedad habilita esto.** El punto 8 del checklist de `verify-bundle`
falla un bundle si su stream contiene CUALQUIER `replay.divergence`, sin
importar que la firma DSSE sea válida. Con el conductor vivo, la propiedad
«el certificado verifica ⟺ el replay fue fiel» deja de ser prosa: una sesión
retocada a mano produce divergencias, y las divergencias tumban el bundle.

**Frontera honesta.** El recomputador de `capability_job` NO vive acá:
recomputar un job es re-ejecutar la capability (Dispatcher, posiblemente con
efectos), decisión de política que este módulo no toma. `session_recomputer`
cubre `model_call` y declara el resto como no-recomputable en vez de
inventarle un digest — un `UnrecomputableEffectError` es información, un digest
fabricado sería una mentira.
"""

from __future__ import annotations

from blite.events.event import Event
from blite.protocols.model_server import InMemoryReplayManifest, replay_key_digest
from blite.runtime.replay import (
    JournaledEffect,
    Recomputer,
    ReplayDivergencePayload,
    find_replay_divergences,
)
from blite.serving.model_port import ModelRequest

REPLAY_DIVERGENCE_EVENT = "replay.divergence"
"""`●ReplayDivergenceDetected` (catálogo §14 vía #102)."""


class UnrecomputableEffectError(Exception):
    """El efecto no se puede recomputar con los insumos disponibles — se
    reporta como tal, JAMÁS se le fabrica un digest para que la comparación
    "pase". Un check que no se pudo hacer no es un check que pasó."""


def session_recomputer(
    manifest: InMemoryReplayManifest, *, backend_id: str, local: bool
) -> Recomputer:
    """Recomputador de `model_call` contra una sesión grabada.

    La correlación es la MISMA que usa el backend `replay` en producción: el
    `replay_key` se deriva del `ModelRequest` (freeze §15.7 punto 2, incluye
    `backend_id`), así que preguntarle al manifest por esa clave devuelve el
    `response_digest` que la sesión promete para ESE request. Compararlo
    contra el journalizado es, literalmente, «¿el replay fue fiel?».
    """

    def _recompute(effect: JournaledEffect) -> str:
        if effect.effect_kind != "model_call":
            msg = (
                f"efecto {effect.effect_kind!r} no recomputable por este "
                "conductor: recomputar un capability_job es re-ejecutar la "
                "capability (posibles efectos) — decisión de política, no de "
                "este módulo"
            )
            raise UnrecomputableEffectError(msg)
        clave = replay_key_digest(
            ModelRequest(
                backend_id=backend_id,
                local=local,
                prompt_digest=effect.request_digest,
            )
        )
        grabado = manifest.lookup(clave)
        if grabado is None:
            msg = (
                f"la sesión no tiene respuesta para el request "
                f"{effect.request_digest!r} (clave {clave!r}) — el stream "
                "journalizó una llamada que esta sesión no contiene"
            )
            raise UnrecomputableEffectError(msg)
        return grabado

    return _recompute


def check_run_fidelity(
    run_id: str, stream: tuple[Event, ...], recompute: Recomputer
) -> tuple[ReplayDivergencePayload, ...]:
    """Corre la comprobación de fidelidad sobre el stream de un run.

    Adapta `Event` (objetos) a los `Mapping` que `find_replay_divergences`
    consume — el núcleo del engine trabaja sobre vistas planas a propósito
    (sirve igual para un stream leído de disco que del store vivo)."""
    vistas = [{"type": event.type, "payload": event.payload} for event in stream]
    return find_replay_divergences(run_id, vistas, recompute)


__all__ = [
    "REPLAY_DIVERGENCE_EVENT",
    "UnrecomputableEffectError",
    "check_run_fidelity",
    "session_recomputer",
]
