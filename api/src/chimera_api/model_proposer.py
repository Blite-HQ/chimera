"""
Adapter `Proposer ← ModelServer` — el agente real entra por el MISMO seam
`Proposer` (decisión #92, `docs/mvp/decisiones.md`; freeze §15.7). [E · P4]

`_start_mission_run` (`chimera_api.runs`) hoy inyecta `_make_goal_proposer`
(placeholder determinista etiquetado). Este módulo construye el REEMPLAZO
real: por turno arma el request del modelo desde `TurnContext` + el catálogo
de capabilities (`Registry.list()`), llama `ModelPort.call` (A2,
`blite.protocols.model_server.ModelServer`), y parsea la respuesta con un
protocolo JSON ESTRICTO — documentado en
`docs/specs/harness-agentico.md` §"Protocolo de mensaje del proposer real".

**Determinismo del request (mismos bytes ⇒ mismo `replay_key`):** la "vista"
del prompt (`_prompt_view`) es una función PURA de `TurnContext` +
`registry.list()` — mismo turno + mismo registry ⇒ mismos bytes canónicos
(`blite.certificate.canonical.canonicalize`, la única puerta de
canonicalización del proyecto) ⇒ mismo `prompt_digest` ⇒ mismo `replay_key`
(`ModelServer.replay_key_digest` ya incluye `backend_id`, freeze §15.7 punto
2). El prompt en sí se `put()` en el `ContentStore` — el `ModelPort` solo
viaja por digest (freeze §3, `model.call.requested`).

**Frontera declarada contra `loop.py` (fuera de mi carril, Steven):**
`_run_agentic_turn` llama `proposer(TurnContext(...))` SIN try/except — un
`raise` ahí tumba el turno completo antes de journalizar cualquier evento
(verificado empíricamente: `execute_run` propaga la excepción cruda, ningún
`run.failed` queda en el stream). El único paso del loop agéntico que SÍ es
fail-loud por contrato es `_run_resolve_and_invoke` (`registry.get` /
`dispatcher.execute`, ambos con try/except). Por eso este adapter NUNCA deja
escapar una excepción cruda de la función que satisface `Proposer`: toda
falla del seam modelo (`ReplayMissError`, protocolo no parseable, digest no
visible en el `ContentStore`) se traduce a un `ProposedStep` con la
capability centinela `PROTOCOL_VIOLATION_CAPABILITY_ID` — que ningún registry
real registrará jamás — de modo que el turno sigue su curso normal por el
paso YA protegido y el run cierra `run.failed {error_kind: "KeyError"}`,
MISMO contrato que una capability desconocida cualquiera
(`TestCapabilityDesconocida`, `tests/unit/api/test_runs.py`). Esto no es
tolerancia: `parse_proposed_step` (el parser en sí) SIGUE siendo estricto y
levanta `ModelResponseProtocolError` con causa clara — lo que cambia es que
el WRAPPER que arma el `Proposer` inyectable atrapa esa excepción para
canalizarla por el único camino del loop que ya es fail-loud, en vez de
dejarla escapar hacia un camino que hoy no journaliza nada.
"""

from __future__ import annotations

from pydantic import ValidationError

from blite.certificate.canonical import JSONValue, canonicalize
from blite.content import ContentStore
from blite.runtime.loop import ProposedStep, Proposer, TurnContext
from blite.runtime.registry import Registry
from blite.serving.model_port import ModelPort, ModelRequest, ReplayMissError
from blite_capability.manifest import CapabilityManifest

PROMPT_PROTOCOL = "chimera/mission-proposer-prompt/v1"
"""Versión del protocolo del PROMPT (lo que este adapter le manda al modelo)
— distinto del protocolo de RESPUESTA (que es, literalmente, `ProposedStep`,
freeze/loop.py). Cambiar la forma de `_prompt_view` es una supersesión de
ESTA constante, documentada en harness-agentico.md."""

PROTOCOL_VIOLATION_CAPABILITY_ID = "chimera.model_proposer.protocol_violation"
"""Capability CENTINELA — jamás registrada por ningún `Registry` real (no es
reverse-domain de ningún dominio de cómputo, ADR-029). Ver docstring del
módulo: el registry.get() de `_run_resolve_and_invoke` la rechaza con
`KeyError`, que SÍ es fail-loud por contrato (a diferencia de un `raise`
crudo desde el `Proposer`)."""

_PROMPT_MEDIA_TYPE = "application/json"
_MAX_ERROR_MESSAGE_LEN = 500
"""Tope del mensaje de error empacado en `inputs` del `ProposedStep`
centinela — evidencia para debug, no un log ilimitado."""


class ModelResponseProtocolError(Exception):
    """La respuesta del modelo no es un `ProposedStep` válido bajo el
    protocolo JSON ESTRICTO (mismo `extra="forbid"` que el resto de los
    modelos del freeze) — causa clara, nunca tolerancia silenciosa."""


def parse_proposed_step(response_bytes: bytes) -> ProposedStep:
    """Protocolo de respuesta ESTRICTO: la respuesta del modelo ES,
    literalmente, un `ProposedStep` serializado (`{capability_id, inputs,
    tokens?, cost_usd?}`, `extra="forbid"`) — reusa el tipo que `loop.py` ya
    declara como el contrato del `Proposer` en vez de inventar una segunda
    forma paralela (DRY, single source of truth). JSON malformado, campo
    requerido ausente, o campo extra ⇒ `ModelResponseProtocolError`."""
    try:
        return ProposedStep.model_validate_json(response_bytes)
    except ValidationError as exc:
        msg = (
            f"respuesta del modelo no conforme al protocolo "
            f"{PROMPT_PROTOCOL!r} (ProposedStep estricto): {exc}"
        )
        raise ModelResponseProtocolError(msg) from exc


def _prompt_view(
    turn: TurnContext, capabilities: tuple[CapabilityManifest, ...]
) -> dict[str, JSONValue]:
    """Vista determinista del turno — PURA función de `TurnContext` +
    `registry.list()` (orden ya determinista por id, `EntryPointRegistry`).
    El "capability meta" que el modelo ve para elegir QUÉ invocar (§Contrato-4
    harness-agentico.md: "el agente elige sub-runs del Registry").

    `run_id` se EXCLUYE a propósito: `POST /runs` mintea un `uuid4` fresco en
    cada request (`_start_mission_run`, `chimera_api.runs`) — si viajara en
    la vista, la clave de replay jamás repetiría entre una sesión grabada y
    la demo reproduciéndola (cada `docker compose up` arranca un run_id
    nuevo), lo que volvería inútil el backend `replay` para su propósito
    real. `domain_id` SÍ viaja: hoy es la constante `domain-default` en todo
    el proceso (`_DEFAULT_DOMAIN`), no una fuente de no-determinismo."""
    return {
        "protocol": PROMPT_PROTOCOL,
        "domain_id": turn.domain_id,
        "turn": turn.turn,
        "goal_capability_id": turn.goal_capability_id,
        "goal_inputs": turn.goal_inputs,
        "plan_item_id": turn.plan_item_id,
        "previous_output_digest": turn.previous_output_digest,
        "capabilities": [
            {
                "id": capability.id,
                "description": capability.description,
                "input_schema": capability.input_schema,
            }
            for capability in capabilities
        ],
    }


def _protocol_violation_step(exc: Exception) -> ProposedStep:
    """El `ProposedStep` centinela que canaliza CUALQUIER falla del seam
    modelo hacia el único paso del loop que ya es fail-loud por contrato
    (ver docstring del módulo — frontera contra `loop.py`)."""
    return ProposedStep(
        capability_id=PROTOCOL_VIOLATION_CAPABILITY_ID,
        inputs={
            "error_kind": type(exc).__name__,
            "error": str(exc)[:_MAX_ERROR_MESSAGE_LEN],
        },
    )


def make_model_proposer(
    *,
    model_server: ModelPort,
    registry: Registry,
    content_store: ContentStore,
    ctx: object,
    backend_id: str,
    local: bool = False,
) -> Proposer:
    """Construye el `Proposer` real sobre un `ModelPort` ya configurado
    (replay/record/live, A2) — mismo seam que `_make_goal_proposer`, cero
    cambio de contrato HTTP (decisión #92)."""

    def _propose(turn: TurnContext) -> ProposedStep:
        view = _prompt_view(turn, registry.list())
        prompt_artifact = content_store.put(canonicalize(view), _PROMPT_MEDIA_TYPE, ctx)
        request = ModelRequest(
            backend_id=backend_id, local=local, prompt_digest=prompt_artifact.digest
        )
        try:
            response = model_server.call(request)
            response_bytes = content_store.get(response.response_digest, ctx)
            return parse_proposed_step(response_bytes)
        except (ReplayMissError, ModelResponseProtocolError, KeyError) as exc:
            return _protocol_violation_step(exc)

    return _propose


__all__ = [
    "PROMPT_PROTOCOL",
    "PROTOCOL_VIOLATION_CAPABILITY_ID",
    "ModelResponseProtocolError",
    "make_model_proposer",
    "parse_proposed_step",
]
