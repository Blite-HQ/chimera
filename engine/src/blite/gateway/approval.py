"""Aprobación humana estilo elicitation MCP — A6 (`docs/specs/harness-agentico.md`
§Contrato-6). [S-G · A6]

Par `approval.requested`/`approval.responded` (freeze §14 — `●ApprovalRequested`/
`●ApprovalResponded`, **nuevo en catálogo, PENDIENTE-Steven, misma ceremonia
#66**): forma "elicitation" de MCP — request→response tipado y replay-able,
mismo home conceptual que `OverridePayload` (freeze §10, `blite.gateway`) — el
Stage que abre la aprobación emite su propio evento vía `EventStore` (INV-4);
este módulo fija la FORMA de los dos payloads y la validación de
`authorized_by`, no el wiring del Stage ni quién estampa cada evento
(frontera Steven, spec §Fronteras: "qué estampa cada payload... no lo decide
esta spec").

`json_schema` es el JSON Schema (forma elicitation MCP) contra el cual el
humano llena `response`; quién valida el `response` contra ese schema es
frontera declarada (spec §Fronteras) — no se implementa acá.

## `authorized_by` — reuso de la maquinaria de permisos (freeze §8/§10)

Freeze §10 (`OverrideEvent`/`OverridePayload`) fija: `authorizedBy` es una URN
restringida a `user:*` (AX2 — la relajación exige responsable humano
identificable) y el autorizador debe portar `override:apply:<scope>` en su
**intersección efectiva** de permisos (freeze §8: la intersección la computa
`derive()` a lo largo de toda la cadena de delegación — `Identity.permissions`
que llega hasta acá YA es esa intersección, el gateway la computó antes).

**Hallazgo (verificado por grep antes de escribir este módulo):** ni
`OverrideEvent`/`OverridePayload` ni el string `override:apply:` existen
todavía como código — son doctrina de `docs/contract-freeze.md` §10, no una
clase Python. No hay nada que "importar" de un tipo que no existe. Lo que SÍ
existe y es exactamente la maquinaria que §10 describe reusar es:

- `blite.identity.identity.Identity` — `permissions: frozenset[str]`, la
  intersección efectiva ya resuelta (freeze §8).
- `blite.authz.AuthzDecision` — el ÚNICO tipo de veredicto de autorización
  que el resto del sistema entiende (egress lo exige por firma, Inv-E).

`authorize_approval_response()` reusa AMBOS sin reimplementar parsing de
scopes: arma el string `f"override:apply:{scope}"` con la MISMA convención
literal de §10 y comprueba pertenencia al frozenset ya intersectado — cero
infra nueva. Cuando `OverridePayload` se materialice en código, este chequeo
es textualmente el mismo que esa etapa hará.

Fail-closed en tres sentidos (ninguno es "el permiso correcto implícito"):
1. La `Identity` debe SER la declarada en `authorized_by` (mismo nombre, no
   solo "alguien con el permiso") — defensa en profundidad, mismo espíritu
   que `MediationStage`/`EgressStage` (`gateway/stages.py`) no confiar en que
   el Pipeline ya filtró.
2. `identity.kind` debe ser `"human"` — un `user:*` con `kind` inconsistente
   (dato corrupto o construcción indebida) no satisface AX2.
3. `override:apply:<scope>` debe estar en `identity.permissions` EXACTAMENTE
   para el `scope` pedido — portar otro scope (p. ej. `domain` cuando se pide
   `run`) no basta.

## Mitad tripwire (§Contrato-6, primera oración) — verificación, no código nuevo

"Veredictos de guardrail/authz viajan como eventos tipados con causa — REUSA
el catálogo ya frozen (§14)": verificado por grep en todo el engine antes de
tocar este archivo —

- **`●SignalRecorded`**: su vehículo tipado ya existe y está probado —
  `blite.guardrails.signal.Signal` (`detector`, `kind` convención
  `{etapa}.{mecanismo}`, `non_decisional: Literal[True]`, disjunto de
  `Attestation` por construcción — `tests/invariants/
  test_attestation_guardrail_contract.py`). Ningún `GuardrailsStage` lo
  journaliza todavía como evento `signal.recorded` (el Pipeline de 8 etapas
  solo tiene `mediation`/`egress` reales hoy — `gateway/stages.py`; las
  demás etapas son `PassthroughStage`) — ese wiring es un Stage nuevo, no un
  catálogo nuevo, y su construcción/emisión de evento es frontera declarada
  de quien cierre `GuardrailsStage` (mismo patrón INV-4 de esta spec).
- **`●EscalationOpened`**: ya wireado — `blite.runtime.policy_watch.
  on_policy_changed` emite `escalation.opened` (constante `ESCALATION_OPENED`)
  vía `EventStore.append` cuando una Policy nueva ENDURECE (EX-5). El
  docstring de ese módulo declara EXPLÍCITAMENTE que tipificar ese payload
  ("el payload de `escalation.opened` lo cierra Steven") es su frontera, no
  la mía — no se toca `runtime/policy_watch.py` desde A6.
- **`●Resolved`** (i.e. `escalation.resolved`): NO existe wiring todavía —
  gap real, pero fuera del alcance de A6 (mismo dueño/frontera que
  `EscalationOpened` de arriba); no se inventa un evento nuevo para cerrarlo.

Conclusión: cero catálogo nuevo para la mitad tripwire — se documenta el
hallazgo acá porque A6 es quien lo verificó, no porque A6 lo implemente.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from blite.authz import AuthzDecision
from blite.identity.identity import Identity

_USER_URN_PATTERN = r"^user:[a-z0-9-]+$"
"""Restricción de `Identity._URN_PATTERN` al prefijo `user:` únicamente
(freeze §10, AX2) — `agent:*`/`service:*` no pueden autorizar un override."""

OverrideScope = Literal["run", "domain", "global"]
"""Mismo conjunto CERRADO que `OverridePayload.scope` (freeze §10) — el
alcance sobre el que se exige `override:apply:<scope>`."""

_DECIDED_BY = "gateway.approval"


class ApprovalRequestedPayload(BaseModel):
    """`approval.requested` ↔ `●ApprovalRequested` — la mitad request del par
    elicitation; el Stage que la abre la emite (INV-4), este módulo solo fija
    su forma."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    approval_id: str
    json_schema: dict[str, Any]
    """JSON Schema (forma elicitation MCP) contra el cual el humano llena
    `response` — quién lo valida es frontera (spec §Fronteras)."""
    prompt: str
    step_id: str | None = None


class ApprovalRespondedPayload(BaseModel):
    """`approval.responded` ↔ `●ApprovalResponded` — la mitad response,
    correlacionada con el request por `run_id` + `approval_id`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    approval_id: str
    response: Any
    """Valor libre — lo que el humano llenó contra el `json_schema` del
    request (bool/str/número/objeto; forma elicitation MCP)."""
    authorized_by: str = Field(pattern=_USER_URN_PATTERN)
    """URN `user:*` (freeze §10, AX2) — validado en `authorize_approval_
    response()` contra `override:apply:<scope>` en la intersección efectiva."""


def authorize_approval_response(
    payload: ApprovalRespondedPayload,
    identity: Identity,
    *,
    scope: OverrideScope,
) -> AuthzDecision:
    """Valida `payload.authorized_by` contra `override:apply:<scope>` —
    reusa `Identity.permissions` (intersección efectiva, freeze §8) y
    `AuthzDecision` (freeze §5/EX-14) SIN reimplementar parsing de scopes.

    `identity` es la identidad YA resuelta (JWT/derive) para la URN que el
    payload declara — esta función no la busca, la recibe, igual que
    `MediationStage`/`EgressStage` reciben su `AuthzDecision` ya resuelta.

    Fail-closed: mismatch de identidad, `kind` no-humano, o ausencia del
    permiso exacto del scope pedido ⇒ `allowed=False`. Nunca una excepción —
    mismo contrato que el resto del gateway (`Rejection` en las etapas).
    """
    if identity.id != payload.authorized_by:
        return AuthzDecision(
            allowed=False,
            reason=(
                f"identity {identity.id!r} no coincide con authorized_by "
                f"{payload.authorized_by!r} (fail-closed, defensa en profundidad)"
            ),
            decided_by=_DECIDED_BY,
        )
    if identity.kind != "human":
        return AuthzDecision(
            allowed=False,
            reason=(
                f"authorized_by {payload.authorized_by!r} es user:* pero la "
                f"identidad resuelta tiene kind={identity.kind!r}, no 'human' (AX2)"
            ),
            decided_by=_DECIDED_BY,
        )
    required = f"override:apply:{scope}"
    if required not in identity.permissions:
        return AuthzDecision(
            allowed=False,
            reason=(
                f"{identity.id!r} no porta {required!r} en su intersección "
                "efectiva de permisos (freeze §8/§10)"
            ),
            decided_by=_DECIDED_BY,
        )
    return AuthzDecision(
        allowed=True,
        reason=f"{identity.id!r} porta {required!r} en su intersección efectiva",
        decided_by=_DECIDED_BY,
    )
