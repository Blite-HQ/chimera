# Spec — Harness agéntico: loop, plan, terminación, sub-runs y replay (costura A↔E↔D)

**Gobernada por:** freeze §13 (Run jerárquico, supersede A1 — decisión #66) · §8 (pipeline
de 8 etapas, fail-closed) · §3 (vocabulario de eventos del run) · §14 (catálogo ●) · §15.7
(`ModelPort`/replay) · **Dueño:** Dylan + Steven · **Estado:** SPEC (2026-07-24)

> Materializa la ceremonia de supersede A1 (decisión #66, `docs/mvp/decisiones.md`): el
> freeze §13 congeló "pipeline fijo Fase 1 — NO ReAct, NO plan-execute, NO jerárquico"
> siguiendo la recomendación de POC de `knowledge/execution/02-runtime-agent-loop.md` §11;
> el mandato v2 (decisión #61, "Chimera genera, no solo verifica") lo requiere. **[S3
> 2026-07-30: era PENDIENTE-Steven — gate por persona muerto por #94; el supersede A1 se
> EJECUTÓ: `engine/src/blite/runtime/loop.py` corre el loop agéntico (`execute_run` con
> seam `Proposer`, `max_turns`/`budget`) y Planeado cerró con #100 (misión viva + proposer
> real cableado, `docs/mvp/decisiones.md`); la condición «no se toca hasta su ratificación»
> de abajo es histórica]** (es su plano, §13/§8): esta spec registra el diseño con causa (regla 3 del
> freeze) — `engine/src/blite/runtime/loop.py` no se toca hasta su ratificación; si no
> ratifica, la sesión de implementación A avanza igual sobre este contrato (regla del plan,
> `docs/archivo/planeado/05-plan-paralelo.md`). Cita sin repetir:
> `docs/planeado/03-research-estado-del-arte.md` §R1 (research que funda los componentes) ·
> `docs/specs/confianza-api-sse.md` (formato) · `docs/specs/README.md` §"Specs de costura"
> (ciclo de vida SPEC→SEED→VERDE, convención de fixtures) · `knowledge/execution/02`
> (agent loop) · `03` (durable execution — replay del log, no motor nuevo) · `05`/`09`
> (`ModelPort`/`ModelServer`, egress) · `knowledge/trust/07` (SSE, payloads por vista) ·
> `13` (OPA/Cedar/OWASP agéntico, tripwire) · `16` (guardrails, disjunción Signal/Attestation).

## Contrato

**1 · Loop plano — quién propone, quién ejecuta.** El loop sigue siendo plano (freeze §13,
"el runtime es dueño del loop"): `proponer → gobernar (8 etapas, §8) → ejecutar →
journalizar → verificar → repetir`. El MODELO (vía `ModelPort.call`, §15.7) SOLO propone el
próximo `RunStep` candidato — nunca lo ejecuta ni decide egreso (INV-2 intacto); el HARNESS
(`execute_run`, `engine/src/blite/runtime/loop.py`) es el ÚNICO ejecutor: recibe la
propuesta, la corre a través del `Pipeline` de 8 etapas completo (§8, `gateway/pipeline.py`)
y journaliza la transición como evento inmutable. **Replanificar = `run.step.*` nuevos con
causa, apendeados** — jamás una segunda pasada por el gateway a mitad de un step ya en
curso: §8 ya declara la reautorización a mitad de pipeline "error de contrato
fail-closed"; un replan es, por construcción, un step NUEVO que cruza las 8 etapas desde
`identity` (mismo camino que cualquier otro step — §13, "cada step cruza el gateway
completo"), nunca una excepción al orden congelado.

**2 · Plan como artefacto en el stream.** `plan.created` (evento fundacional del plan, 1:1
con el run, emitido antes del primer step que cubre) y `plan.item_updated` (una emisión por
transición de ítem). El agente (vía el delegate post-invoke, o una etapa de "planificación"
del loop) SOLO emite estos dos eventos — nunca reescribe el plan in-place (INV-5,
append-only). La historia completa del plan queda dentro del alcance del `provenance_hash`
del certificado (freeze §2: cubre el stream del run raíz desde `run.created` hasta el
terminal) — el certificado reconstruye "qué se planeó vs qué se ejecutó" sin almacén nuevo.
**Arranque HTTP (costura A↔E, checkpoint 5):** el body misión-first de `POST /runs`
(`{mission, instance_id?, capability_id?, max_turns?, budget?}`, discriminado del claim-first
por presencia de campo) vive en `endpoints-studio.md` §"POST /runs — modo misión" — arranca
ESTE contrato (plan como eventos) sembrando la misión como `description` del ítem fundacional
del plan; esta spec no lo duplica, solo lo referencia.

**3 · Terminación triple — y su relación con `max_steps`.** Tres condiciones; la primera en
dispararse termina el run: **(a)** `max_turns` (default `30`, patrón OpenAI Agents SDK
citado en R1) — cota de ITERACIONES del loop agéntico completo (proponer→gobernar→
ejecutar→journalizar→verificar), concepto nuevo que no existía en el pipeline fijo de 2
steps; **(b)** `budget` (tokens/costo) declarado en el payload de `run.created`; **(c)** el
gate de verificación — `done` ⟺ el verifier pasa (doctrina Anthropic, R1), nunca un
`run.completed` implícito por "se acabaron los steps". **Relación con `max_steps` (§3, ya
obligatorio):** `max_steps` sigue siendo el guard estructural sobre CADA `RunStep`
individual emitido (resolve/invoke hoy; +1 por turno del loop agéntico mañana) — una cota de
MECANISMO (cuántos eventos `run.step.*` puede escribir el runtime); `max_turns` es una cota
de PRODUCTO (cuántas iteraciones de razonamiento del agente se permiten). Por construcción
**`max_turns` ≤ `max_steps`** (cada turno consume ≥1 `RunStep`); ambos guards conviven — el
loop corta en el PRIMERO que se agote. Agotar `max_turns` o `budget` ⇒ terminal
`run.failed {error_kind: "exhausted"}` (constante nueva, junto a `MAX_STEPS_EXCEEDED` ya en
`loop.py`) — jamás `done` implícito. `error_kind` ya es `str` libre (freeze §3): `"exhausted"`
es un valor nuevo dentro de un tipo ya abierto, no una supersesión. Los campos
`max_turns`/`budget` en `run.created` SÍ extienden la forma exacta que §3 fija hoy —
**[S3 2026-07-30: era PENDIENTE-Steven (supersesión aditiva, misma ceremonia #66) — sin
gate por persona (#94); supersesión EJECUTADA: implementada en
`engine/src/blite/runtime/loop.py` (firma de `execute_run` + payload de `run.created` +
`EXHAUSTED_ERROR_KIND`) y portada al freeze §3 (marca «(c) Ceremonia #66»,
`docs/contract-freeze.md`)]**, mismo patrón ya usado en
decisión #64 para vistas SSE nuevas.

**4 · Sub-runs elegidos por el agente.** El set hardcodeado de §13
("formular/QAOA/baseline/verificar") se limpia: el agente elige QUÉ sub-run correr del
`Registry` (execution/04) en cada turno — el criterio de qué CALIFICA como sub-run no
cambia (§13 [S-F]: "sub-run SOLO la unidad que produce claims propios que el certificado
citará"; todo lo demás son steps del loop). Las 3 reglas del run jerárquico de §13 se REUSAN
sin cambio: **(i)** cascada de cancelación (`run.cancelled {reason: "parent_cancelled"}` a
cada sub-run activo, appends post-terminales rechazados); **(ii)** aporte de claims al raíz
vía `●ClaimEmitted {claim_digest, sub_run_id, sub_run_provenance_hash}`; **(iii)** herencia
fail-closed de `policy_digest`. **Gap contra el freeze YA vigente (frontera Dylan, no
supersesión):** `ClaimEmittedPayload` (`engine/src/blite/verification/claim.py`) hoy declara
`sub_run_provenance_hash` pero NO `sub_run_id` — §13 regla 2 ya exige ambos textualmente (el
hash encadena, el id correlaciona); es un campo faltante contra un contrato ya congelado, no
una decisión nueva. Seed abajo. **[S3 2026-07-30 — D-N2: CERRADO.** El campo existe:
`claim.py:59` declara `sub_run_id` citando esta spec como origen; la fila «PENDIENTE (campo a
añadir)» de la tabla de interfaces quedó atrás del código.**]**

**5 · Replay por digest de cada efecto.** Extiende (no reemplaza) la doctrina `replay` de
§15.7 (`ModelPort`, `REPLAY_MISS_ERROR_KIND`, prefijo `blite/model-replay/v1`): un MISS (sin
fixture) ya es fail-closed a nivel de puerto — eso no cambia. Lo NUEVO es la comprobación de
FIDELIDAD tras una pasada de replay/auditoría: por CADA efecto (llamada de modelo o
`capability.job`) journalizado como `(request_digest, response_digest)`, recomputar y
comparar; una divergencia ⇒ `replay.divergence` — evento tipado, nunca una excepción
silenciosa. Propiedad resultante (R1, exclusiva de Chimera): **el certificado DSSE verifica
⟺ el replay fue fiel** — `scripts/verify-bundle.py`/`check_bundle` (7 puntos hoy, freeze §7)
gana un punto 8 que FALLA el bundle si el stream del run contiene CUALQUIER
`replay.divergence`, sin importar que la firma DSSE sea válida (frontera Dylan, seed). El
adapter `ModelServer` + los backends `replay`/`record` no existen aún (solo el puerto +
doctrina, §15.7 [S-F]) — construir esa comprobación es frontera Dylan/Steven, declarada, no
entregada en Fase 0.

> **[S3 2026-07-30]** Implementado (D-N7): el adapter `ModelServer` y sus backends
> `replay`/`record` existen — `engine/src/blite/protocols/model_server.py` (única casa
> legítima de litellm, AX3-b). Esto resuelve la contradicción interna del doc: la
> declaración de arriba («no existen aún», 2026-07-24) es la histórica; la sección
> «Wiring del proposer real (carril P4)» al final, que lo describe funcionando, es la
> vigente. La letra no se reescribe — manda esta marca.

**6 · Gobernanza tripwire + aprobación humana.** Veredictos de guardrail/authz viajan como
eventos tipados con causa — REUSA el catálogo ya frozen (§14): `●SignalRecorded` (detector,
non-decisional — trust/16, disjunto de `Attestation`), `●EscalationOpened`/`●Resolved` (vía
tareas, §6 EX-5). Cero catálogo nuevo para esta mitad. La aprobación humana SÍ es nueva —
forma elicitation de MCP (par de eventos replay-able, request→response tipados):
`approval.requested`/`approval.responded`. `authorized_by` es una URN `user:*` que debe
portar `override:apply:<scope>` en su intersección efectiva (§8/§10 — misma maquinaria de
`OverrideEvent`, cero infra nueva). La superficie visual (D) y los endpoints (E) consumen
estos MISMOS nombres de wire — no hay traducción intermedia.

## Eventos / payloads nuevos

- **`plan.created`** ↔ `●PlanCreated` (ya en el catálogo §14 — primera materialización en
  código, no supersesión). Payload: `{plan_id, run_id, items: [{id, description,
verification, status}]}`; `status ∈ {pending, running, ok, failed}` (conjunto cerrado,
  misma disciplina que `RunStep.status`). Módulo propuesto: `blite.runtime.plan`
  (`PlanItem`, `PlanCreatedPayload`) — mismo home conceptual que `RunStep` en
  `runtime/loop.py`.
- **`plan.item_updated`** ↔ `●PlanItemUpdated` (**nuevo en catálogo §14 — [S3 2026-07-30:
  era PENDIENTE-Steven, sin gate por persona (#94); implementado en
  `engine/src/blite/runtime/plan.py` (`PlanItemUpdatedPayload`), emitido por `loop.py` y
  absorbido por el freeze §14 (marca [MEJORADO #102])], misma ceremonia #66**). Payload:
  `{plan_id, run_id, item_id, status, cause?}`. Módulo:
  `blite.runtime.plan` (`PlanItemUpdatedPayload`).
- **`replay.divergence`** ↔ `●ReplayDivergenceDetected` (**nuevo en catálogo §14 — [S3
  2026-07-30: era PENDIENTE-Steven, sin gate por persona (#94); implementado en
  `engine/src/blite/runtime/replay.py` (`ReplayDivergencePayload`, `EffectKind`) y
  absorbido por el freeze §14 (marca [MEJORADO #102]); el Studio ya lo escucha
  (`KNOWN_RUN_EVENT_TYPES`)]**). Payload: `{run_id, effect_kind: "model_call"|"capability_job",
request_digest, expected_response_digest, actual_response_digest, step_id?}`. Módulo:
  `blite.runtime.replay` (`ReplayDivergencePayload`, `EffectKind`).
- **`approval.requested`** ↔ `●ApprovalRequested` (**nuevo en catálogo §14 — [S3
  2026-07-30: era PENDIENTE-Steven, sin gate por persona (#94); forma implementada en
  `engine/src/blite/gateway/approval.py` (`ApprovalRequestedPayload`) y absorbida por el
  freeze §14 (marca [MEJORADO #102]); el wiring del Stage emisor sigue ABIERTO — frontera
  declarada en el docstring de ese módulo, ya sin dueño asignado]**). Payload:
  `{run_id, approval_id, json_schema, prompt, step_id?}`.
  Módulo: `blite.gateway.approval` (mismo home conceptual que `OverridePayload`, §10 — el
  Stage que la abre emite su propio evento, INV-4).
- **`approval.responded`** ↔ `●ApprovalResponded` (**nuevo en catálogo §14 — [S3
  2026-07-30: era PENDIENTE-Steven, sin gate por persona (#94); implementado en
  `engine/src/blite/gateway/approval.py` (`ApprovalRespondedPayload` +
  `authorize_approval_response()`) y absorbido por el freeze §14 (marca [MEJORADO #102]);
  mismo estado de wiring que el request]**). Payload:
  `{run_id, approval_id, response, authorized_by}` —
  `authorized_by` valida contra `override:apply:<scope>` (§8/§10). Módulo:
  `blite.gateway.approval`.
- **`run.created`** (ya frozen, §3) gana dos campos ADITIVOS — **[S3 2026-07-30: era
  PENDIENTE-Steven, sin gate por persona (#94); implementado en
  `engine/src/blite/runtime/loop.py` (el payload de `run.created` ya lleva ambos) y
  portado al freeze §3 (marca «(c) Ceremonia #66»)]**:
  `max_turns: int` (default `30`) y `budget: {tokens?: int, cost_usd?: float}`, mismo lugar
  que `max_steps`/`policy_digest` ya obligatorios ahí.
- **`run.failed {error_kind: "exhausted"}`** — valor nuevo de un campo ya abierto (`str`
  libre, freeze §3); constante `EXHAUSTED_ERROR_KIND` propuesta en `loop.py` junto a
  `MAX_STEPS_EXCEEDED` (ya existente).

## Interfaces con otros dominios

| Interfaz                                     | Dominio                                                     | Estado                                                                            |
| -------------------------------------------- | ----------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `plan.created` / `plan.item_updated`         | D (Studio · timeline) + E (endpoint SSE · proyección)       | SPEC                                                                              |
| `approval.requested` / `approval.responded`  | D (Studio · card inline bloqueante) + E (endpoint SSE)      | SPEC                                                                              |
| `replay.divergence`                          | E (SSE) + confianza (certificado — `check_bundle` punto 8)  | SPEC                                                                              |
| `●ClaimEmitted` + campo `sub_run_id`         | confianza (predicate §7 / bundle)                           | **[S3 2026-07-30]** HECHO — `claim.py:59` (era «PENDIENTE, campo a añadir»; D-N2) |
| `ModelServer` + backends `replay`/`record`   | frontera Dylan + Steven (§15.7)                             | SPEC (puerto listo, adapter no)                                                   |
| `POST /runs` modo misión (arranque del loop) | E (`endpoints-studio.md` §"POST /runs — modo misión") ↔ A↔D | CONTRATO (checkpoint 5, 2026-07-29)                                               |

## Fronteras (qué NO decide esta spec)

- **Firma DSSE**: la forma del envelope/predicate (§7) es de Dylan; esta spec solo agrega
  el punto 8 del checklist (`replay.divergence` tumba el bundle) — no reabre la firma ni el
  predicate mínimo.
- **Autenticación del stream**: JWT en cookie ya decidido (§9) — esta spec no inventa auth
  para `plan.*`/`approval.*`/`replay.divergence`; viajan por el MISMO stream ya autenticado.
- **Qué estampa cada payload**: el emisor exacto (qué Stage, qué línea del loop) es de
  Steven — esta spec fija la FORMA del payload, no quién lo llena ni cuándo exactamente.
- **La ratificación del supersede A1** (freeze §13/§8 → loop agéntico) es de Steven,
  decisión #66 — esta spec es el material que ratifica o rechaza, no se auto-ratifica.
  **[S3 2026-07-30:** la ratificación por persona murió con #94; el supersede quedó
  APLICADO en el freeze §13 con la marca `[MEJORADO #102]` — esta frontera está cerrada.**]**

## Tests de contrato (fixtures de costura)

- Convención de origen único: `docs/specs/README.md` §"Specs de costura" (fixture canónico
  emitido desde los modelos Pydantic del engine, espejado a Studio, byte-idéntico). Ningún
  modelo origen de esta spec existe todavía (`blite.runtime.plan`/`replay`,
  `blite.gateway.approval`) — **Fase 0 declara la ruta, Fase 1 la genera**, misma regla que
  el README: "donde el modelo aún no existe, el fixture verde lo entrega el dueño."
- Rutas declaradas (NO generadas): `tests/fixtures/contract/harness/plan-created.json`,
  `tests/fixtures/contract/harness/plan-item-updated.json`,
  `tests/fixtures/contract/harness/replay-divergence.json`,
  `tests/fixtures/contract/harness/approval-requested.json`,
  `tests/fixtures/contract/harness/approval-responded.json` — espejadas a
  `apps/studio/src/fixtures/contract/harness/`.

## Tests semilla

- `tests/seeds/test_seed_harness_loop.py` — forma de `plan.created`/`plan.item_updated`
  (conjunto cerrado de `status`), la firma de `execute_run` ganando `max_turns`/`budget`, la
  constante `EXHAUSTED_ERROR_KIND`, y el campo `sub_run_id` en `ClaimEmittedPayload`.
  **SEED, xfail(strict=False)** — verde cuando Steven+Dylan implementen cada pieza.
- `tests/seeds/test_seed_harness_replay.py` — forma de `ReplayDivergencePayload`
  (`effect_kind` como conjunto cerrado) y que `check_bundle` gane un punto 8 que falla el
  bundle ante cualquier `replay.divergence` en el stream. **SEED, xfail(strict=False)** —
  verde cuando Dylan implemente el punto 8 y Steven journalice el request/response digest de
  cada efecto.

## Wiring del proposer real (carril P4, mandato Dylan 2026-07-29 — sección ADITIVA)

Decisión #92 ratificada: el agente real entra por el MISMO seam `Proposer` de `loop.py`
(`Callable[[TurnContext], ProposedStep]`) — cero cambio de contrato HTTP. Esta sección
documenta el diseño de P4: `api/src/chimera_api/model_proposer.py` (adapter
`Proposer ← ModelServer`), `api/src/chimera_api/model_session.py` (persistencia de sesión),
y el flip por entorno en `_start_mission_run`.

### Protocolo de mensaje del proposer real

**Request (prompt) — determinista por construcción.** Por turno, el adapter arma una vista
JSON PURA de `TurnContext` + `Registry.list()` (protocolo `chimera/mission-proposer-prompt/v1`):

```json
{
  "protocol": "chimera/mission-proposer-prompt/v1",
  "domain_id": "domain-default",
  "turn": 1,
  "goal_capability_id": "blite.solvers.qubo",
  "goal_inputs": { "...": "..." },
  "plan_item_id": "mission-1",
  "previous_output_digest": null,
  "capabilities": [
    { "id": "blite.solvers.qubo", "description": "...", "input_schema": { "...": "..." } }
  ]
}
```

`run_id` se EXCLUYE a propósito: `POST /runs` mintea un `uuid4` fresco por request — si
viajara en la vista, la clave de replay (`replay_key_digest`, freeze §15.7 punto 2, sobre
`{backend_id, local, prompt_digest}`) jamás repetiría entre la sesión grabada y su
reproducción (cada `docker compose up` arranca un run_id nuevo), lo que volvería inútil el
backend `replay` para su propósito real (reproducir la MISMA sesión en cada puesta en
escena). La vista se canonicaliza (`blite.certificate.canonical.canonicalize`, la única
puerta de canonicalización del proyecto) y se `put()`ea en el `ContentStore` — el
`ModelPort` viaja por digest (`ModelRequest{backend_id, local, prompt_digest}`, freeze §3),
nunca el prompt en claro.

**Response — protocolo JSON ESTRICTO, reusa `ProposedStep` como wire.** La respuesta del
modelo ES, literalmente, un `ProposedStep` serializado (`{capability_id, inputs, tokens?,
cost_usd?}`, `extra="forbid"` — mismo tipo que `loop.py` ya declara, sin una segunda forma
paralela):

```json
{
  "capability_id": "blite.solvers.qubo",
  "inputs": {
    "matrix": [
      [0, -1],
      [-1, 0]
    ]
  },
  "tokens": 512,
  "cost_usd": 0.0031
}
```

JSON malformado, campo requerido ausente, o campo extra ⇒ `ModelResponseProtocolError`
(`chimera_api.model_proposer.parse_proposed_step`) — causa clara, nunca tolerancia
silenciosa.

### Frontera declarada contra `loop.py` — el seam del proposer no es fail-loud por sí solo

> **[MEJORADO P1/M32 · 2026-08-02 — CERRADA EN LA RAÍZ].** Esta sección describe el estado
> ANTERIOR y su rodeo; queda como historia, la manda esta marca. Lo ejecutado, exactamente
> lo que el último párrafo pedía: `_run_agentic_turn` envuelve la llamada al `proposer` en
> try/except y journaliza `plan.item_updated {failed, cause}` + `run.failed
{error_kind: type(exc).__name__}` ANTES de cortar (orden #100.1 — el terminal siempre
> último, jamás post-terminal). Consecuencias registradas:
>
> - **La capability CENTINELA `PROTOCOL_VIOLATION_CAPABILITY_ID` MURIÓ** — el propio párrafo
>   de abajo anticipaba que el guard «volvería innecesaria la traducción». `make_model_proposer`
>   deja escapar `ReplayMissError`/`ModelResponseProtocolError`/`KeyError` y el loop los
>   journaliza con su causa REAL: el `error_kind` deja de ser un `KeyError` prestado, y el
>   stream deja de fabricar un `run.step.*` de resolve contra una capability que ningún
>   registry registró jamás (evidencia inventada dentro del corte que el certificado ampara).
> - **Guard de nivel TASK** (`chimera_api.runs.run_in_background`): `BackgroundTasks` no
>   atrapa nada, así que lo que escape de `execute_run` por una frontera aún sin guard cierra
>   el run con `run.failed` de último recurso — y jamás duplica un terminal ya journalizado.
> - Regresión: `tests/unit/runtime/test_agentic_loop.py::test_proposer_que_levanta_*` y
>   `tests/unit/api/test_runs.py::TestGuardDeNivelTask`.

Verificado empíricamente (no es una suposición): `_run_agentic_turn` (`engine/src/blite/
runtime/loop.py`, fuera del carril P4) llama `proposer(TurnContext(...))` SIN try/except —
un `raise` ahí propaga la excepción cruda fuera de `execute_run` (agendado vía
`BackgroundTasks`, que tampoco atrapa nada — `starlette.background.BackgroundTask.__call__`
no tiene try/except) ANTES de journalizar cualquier evento; el run queda colgado en el
stream (sin `run.failed`) en vez de cerrar honesto. El único paso del loop agéntico que SÍ
es fail-loud por contrato es `_run_resolve_and_invoke` (`registry.get`/`dispatcher.execute`,
ambos con try/except propio).

`chimera_api.model_proposer.make_model_proposer` NUNCA deja escapar una excepción cruda de
la función que satisface `Proposer`: toda falla del seam modelo (`ReplayMissError`,
`ModelResponseProtocolError`, digest no visible en el `ContentStore`) se traduce a un
`ProposedStep` centinela —`capability_id = PROTOCOL_VIOLATION_CAPABILITY_ID =
"chimera.model_proposer.protocol_violation"` (jamás registrada por ningún `Registry` real,
no es reverse-domain de ningún dominio de cómputo, ADR-029) — de modo que el turno sigue su
curso normal por el paso YA protegido y el run cierra `run.failed {error_kind: "KeyError"}`,
MISMO contrato que una capability desconocida cualquiera (`TestCapabilityDesconocida`,
`tests/unit/api/test_runs.py`). Esto NO es tolerancia: el parser en sí (`parse_proposed_step`)
sigue siendo estricto y levanta con causa clara — lo que cambia es que el WRAPPER canaliza
esa excepción por el único camino del loop que ya es fail-loud, en vez de dejarla escapar
hacia uno que hoy no journaliza nada. **Frontera para Steven** (dueño de `loop.py`): envolver
la llamada al `proposer` en `_run_agentic_turn` con el mismo try/except que ya protege
resolve/invoke (journalizando `run.failed {error_kind: type(exc).__name__}` antes de cortar)
cerraría este gap en la raíz y volvería innecesaria la traducción a capability centinela —
cambio fuera del carril P4 (`engine/src/blite/runtime/loop.py` no es uno de mis archivos).

### Formato de sesión en disco

`chimera_api.model_session` (`write_session`/`load_session`):

```
<session_dir>/manifest.json           — SessionManifest {backend_id, local, mission?, entries}
<session_dir>/responses/<digest>.json — bytes EXACTOS de cada respuesta grabada
```

`entries: [{replay_key, response_digest}]` es el MISMO par que `ReplayManifest.record`
(freeze §15.7 punto 4) — `manifest.json` completa `backend_id`/`local`, los dos campos que
faltan para reconstruir el `ModelRequest` exacto (`replay_key_digest` incluye `backend_id`,
freeze §15.7 punto 2: dos backends nunca colisionan). Integridad: `load_session` NO confía
ciegamente en el `response_digest` declarado — recalcula el digest real vía
`content_store.put()` (el mismo puerto que graba, freeze §12; agnóstico al algoritmo
concreto) y compara; una divergencia (archivo editado a mano, sesión a medio copiar) es
`SessionCorruptError`, fail-loud.

### Config por entorno (`_start_mission_run`, `chimera_api.runs`)

| Variable                    | Valores                | Efecto                                                                                                                                                                                     |
| --------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `CHIMERA_MODEL_BACKEND`     | `replay\|record\|live` | Ausente (default) ⇒ `_make_goal_proposer` placeholder, comportamiento INTACTO.                                                                                                             |
| `CHIMERA_MODEL_SESSION_DIR` | ruta                   | Exigida SOLO si `backend=replay` — directorio `chimera_api.model_session.load_session`.                                                                                                    |
| `CHIMERA_MODEL_ID`          | string litellm         | Solo `record`/`live` (identifica el modelo ante litellm); `replay` usa el `backend_id` del `manifest.json` de la sesión, NUNCA esta env var (tiene que ser el mismo que se usó al grabar). |

Un `CHIMERA_MODEL_BACKEND` inválido, o `replay` sin `CHIMERA_MODEL_SESSION_DIR`, es un error
de CONFIGURACIÓN — `ValueError` al construir `RunResources` (arranque de la app), nunca a
mitad de un run. `live_caller` real (record/live) vive en `blite.protocols.model_server.
_default_live_caller` (A2, AX3-b: única casa legítima de litellm) — `chimera_api` jamás
importa litellm directo.

### `scripts/record_session.py` — runbook de grabación

Corre UNA misión completa (`execute_run` en modo agéntico) con el proposer real detrás de un
`ModelServer(mode="record")`, y dumpea la sesión resultante vía `write_session`. Uso real
(Dylan, con su propia key — env estándar de litellm, nunca en este repo):
`uv run python scripts/record_session.py --session-dir knowledge/sessions/<nombre> --mission
"..." --instance-id cr8-uniforme --model-id anthropic/claude-sonnet-4-5 --max-turns 3`.
`--fake` reemplaza litellm/los entry points reales por un `live_caller`+registry
deterministas locales (dry-run de CI, sin red ni API key) — el único modo ejercitado por
`tests/unit/api/test_record_session.py` en esta sesión de trabajo (invocar un LLM externo
estuvo PROHIBIDO).
