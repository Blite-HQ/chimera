# Spec — Harness agéntico: loop, plan, terminación, sub-runs y replay (costura A↔E↔D)

**Gobernada por:** freeze §13 (Run jerárquico, supersede A1 — decisión #66) · §8 (pipeline
de 8 etapas, fail-closed) · §3 (vocabulario de eventos del run) · §14 (catálogo ●) · §15.7
(`ModelPort`/replay) · **Dueño:** Dylan + Steven · **Estado:** SPEC (2026-07-24)

> Materializa la ceremonia de supersede A1 (decisión #66, `docs/mvp/decisiones.md`): el
> freeze §13 congeló "pipeline fijo Fase 1 — NO ReAct, NO plan-execute, NO jerárquico"
> siguiendo la recomendación de POC de `knowledge/execution/02-runtime-agent-loop.md` §11;
> el mandato v2 (decisión #61, "Chimera genera, no solo verifica") lo requiere. **PENDIENTE-
> Steven** (es su plano, §13/§8): esta spec registra el diseño con causa (regla 3 del
> freeze) — `engine/src/blite/runtime/loop.py` no se toca hasta su ratificación; si no
> ratifica, la sesión de implementación A avanza igual sobre este contrato (regla del plan,
> `docs/planeado/05-plan-paralelo.md`). Cita sin repetir:
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
**PENDIENTE-Steven (supersesión aditiva, misma ceremonia #66)**, mismo patrón ya usado en
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
una decisión nueva. Seed abajo.

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
- **`plan.item_updated`** ↔ `●PlanItemUpdated` (**nuevo en catálogo §14 — PENDIENTE-Steven,
  misma ceremonia #66**). Payload: `{plan_id, run_id, item_id, status, cause?}`. Módulo:
  `blite.runtime.plan` (`PlanItemUpdatedPayload`).
- **`replay.divergence`** ↔ `●ReplayDivergenceDetected` (**nuevo en catálogo §14 —
  PENDIENTE-Steven**). Payload: `{run_id, effect_kind: "model_call"|"capability_job",
  request_digest, expected_response_digest, actual_response_digest, step_id?}`. Módulo:
  `blite.runtime.replay` (`ReplayDivergencePayload`, `EffectKind`).
- **`approval.requested`** ↔ `●ApprovalRequested` (**nuevo en catálogo §14 —
  PENDIENTE-Steven**). Payload: `{run_id, approval_id, json_schema, prompt, step_id?}`.
  Módulo: `blite.gateway.approval` (mismo home conceptual que `OverridePayload`, §10 — el
  Stage que la abre emite su propio evento, INV-4).
- **`approval.responded`** ↔ `●ApprovalResponded` (**nuevo en catálogo §14 —
  PENDIENTE-Steven**). Payload: `{run_id, approval_id, response, authorized_by}` —
  `authorized_by` valida contra `override:apply:<scope>` (§8/§10). Módulo:
  `blite.gateway.approval`.
- **`run.created`** (ya frozen, §3) gana dos campos ADITIVOS — **PENDIENTE-Steven**:
  `max_turns: int` (default `30`) y `budget: {tokens?: int, cost_usd?: float}`, mismo lugar
  que `max_steps`/`policy_digest` ya obligatorios ahí.
- **`run.failed {error_kind: "exhausted"}`** — valor nuevo de un campo ya abierto (`str`
  libre, freeze §3); constante `EXHAUSTED_ERROR_KIND` propuesta en `loop.py` junto a
  `MAX_STEPS_EXCEEDED` (ya existente).

## Interfaces con otros dominios

| Interfaz                                     | Dominio                                                     | Estado                                          |
| --------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------ |
| `plan.created` / `plan.item_updated`         | D (Studio · timeline) + E (endpoint SSE · proyección)       | SPEC                                             |
| `approval.requested` / `approval.responded`  | D (Studio · card inline bloqueante) + E (endpoint SSE)       | SPEC                                             |
| `replay.divergence`                          | E (SSE) + confianza (certificado — `check_bundle` punto 8)  | SPEC                                             |
| `●ClaimEmitted` + campo `sub_run_id`         | confianza (predicate §7 / bundle)                             | PENDIENTE (campo a añadir — no es supersesión)   |
| `ModelServer` + backends `replay`/`record`   | frontera Dylan + Steven (§15.7)                               | SPEC (puerto listo, adapter no)                  |

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
