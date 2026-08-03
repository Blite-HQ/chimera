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

**Frontera contra `loop.py` — CERRADA EN LA RAÍZ (P1/M32, 2026-08-02).**
Histórico: `_run_agentic_turn` llamaba `proposer(TurnContext(...))` SIN
try/except, así que un `raise` acá propagaba crudo fuera de `execute_run`
antes de journalizar nada y el run quedaba colgado sin terminal. Para
esquivarlo, este adapter traducía toda falla del seam modelo a un
`ProposedStep` con una capability CENTINELA que ningún registry conoce, de
modo que el turno cayera por el único paso ya protegido (`registry.get` ⇒
`KeyError`).

Ese rodeo MURIÓ con el guard del proposer en `loop.py` (la propia
`harness-agentico.md` §"Frontera declarada contra `loop.py`" lo anticipa
literal: envolver la llamada "volvería innecesaria la traducción a capability
centinela"). Hoy el adapter DEJA ESCAPAR la excepción y el loop la journaliza
como `run.failed {error_kind: type(exc).__name__}`. Por qué esto es
estrictamente mejor para la confianza:

1. **`error_kind` nombra la causa real** — `ReplayMissError` /
   `ModelResponseProtocolError`, en vez del `KeyError` genérico que
   escondía qué falló de verdad detrás de una capability inexistente.
2. **El stream deja de fabricar un paso que nunca ocurrió** — el centinela
   provocaba un `run.step.*` de resolve contra una capability que ningún
   registry registró jamás; evidencia inventada en el rastro que el
   certificado ampara (regla "cero mocks sin etiqueta").
3. **Un concepto menos**: el seam del proposer falla como cualquier otra
   frontera delegada del loop (`post_invoke` ya lo hacía así).

`parse_proposed_step` sigue siendo ESTRICTO, igual que antes — lo que cambia
es a dónde va su excepción.
"""

from __future__ import annotations

from pydantic import ValidationError

from blite.certificate.canonical import JSONValue, canonicalize
from blite.content import ContentStore
from blite.runtime.loop import ProposedStep, Proposer, TurnContext
from blite.runtime.registry import Registry
from blite.serving.model_port import ModelPort, ModelRequest
from blite_capability.manifest import CapabilityManifest

PROMPT_PROTOCOL = "chimera/mission-proposer-prompt/v1"
"""Versión del protocolo del PROMPT (lo que este adapter le manda al modelo)
— distinto del protocolo de RESPUESTA (que es, literalmente, `ProposedStep`,
freeze/loop.py). Cambiar la forma de `_prompt_view` es una supersesión de
ESTA constante, documentada en harness-agentico.md."""

_PROMPT_MEDIA_TYPE = "application/json"


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
        """Fail-loud sin red de seguridad propia: `ReplayMissError`,
        `ModelResponseProtocolError` o el `KeyError` de un digest ausente
        del `ContentStore` suben tal cual — el guard del proposer en
        `loop.py` los journaliza como `run.failed {error_kind}` con la causa
        REAL (P1/M32, ver docstring del módulo)."""
        view = _prompt_view(turn, registry.list())
        prompt_artifact = content_store.put(canonicalize(view), _PROMPT_MEDIA_TYPE, ctx)
        request = ModelRequest(
            backend_id=backend_id, local=local, prompt_digest=prompt_artifact.digest
        )
        response = model_server.call(request)
        response_bytes = content_store.get(response.response_digest, ctx)
        return parse_proposed_step(response_bytes)

    return _propose


__all__ = [
    "PROMPT_PROTOCOL",
    "ModelResponseProtocolError",
    "make_model_proposer",
    "parse_proposed_step",
]
