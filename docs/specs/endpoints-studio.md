# Spec de costura — `chimera_api`: endpoints REST del Studio (E↔D)

**Gobernada por:** freeze **§9** (mismo puerto `EventStore`/proyecciones, mismo API
`chimera_api`) + **§7** (forma del `Certificate`/predicate) + **§3/§14** (vocabulario de eventos
y catálogo ●) · `docs/specs/confianza-api-sse.md` (el paquete/API que este documento extiende
con rutas planas — mismo dueño, mismo puerto, misma regla "jamás la tabla cruda") · research
`docs/planeado/03-research-estado-del-arte.md` §R6.
**Costura:** E↔D · **Dueño (Fase 1):** Steven+Dylan · **Estado:** SPEC (Fase 0, 2026-07-24)

> R6 lo dice explícito: "sin research externo necesario — REST plano coherente con lo existente,
> especificado con el mismo formato de `confianza-api-sse.md`. Las formas ya están congeladas;
> falta solo la ruta y el egress." Esta spec fija esa ruta y ese egress; no inventa forma nueva.

## Contrato

Todas las rutas de abajo son **GET**, viven en el MISMO paquete `chimera_api` y consumen el
MISMO puerto `EventStore` (`blite.events`) + las MISMAS proyecciones que
`confianza-api-sse.md` — jamás la tabla cruda, jamás internals de `gateway/runtime/serving`.
Mismo JWT en cookie (freeze §9 P1-9, decidido, no se reinventa acá). El wire es **snake_case**
(misma convención que `sseProjectedEventSchema`); cada ruta mapea 1:1 a un tipo YA existente en
`apps/studio/src/views/types.ts` — el Studio lo parsea con su schema Zod espejo
(`apps/studio/src/data/schemas.ts`, a escribir en Fase 1; declarado en prosa abajo).

| Ruta                                          | Devuelve (TS, `views/types.ts`)             | Wire (snake_case)                                                                                         | Fuente de la proyección                                                                                                                                                                                                                                                                                                             |
| --------------------------------------------- | ------------------------------------------- | --------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /runs`                                   | `RunSummary[]`                              | `{run_id, status, conclusion, verdict, titular_level, titular_class, events_count, actor, completed_at?}` | `blite.runtime.projection.project_runs` (freeze §2 [ejecución], YA VERDE) para `run_id/status/actor`, + certificado emitido (si existe, freeze §7) para `conclusion/verdict/titular_level/titular_class` — MISMA lógica que hoy vive client-side en `deriveRunSummary` (`apps/studio/src/data/projections.ts`), portada server-side |
| `GET /runs/{run_id}/artifacts`                | `ProjectArtifact[]`                         | `{artifact_ref, digest, run_id, titular_level, titular_class, verdict, issued_at}`                        | `certificate.predicate.deliverables` (freeze §7) — misma lógica que `deriveArtifacts`                                                                                                                                                                                                                                               |
| `GET /runs/{run_id}/knowledge`                | `KnowledgeClaim[]`                          | `{statement, scope, verdict, level, titular_class, run_id, valid_as_of}`                                  | `certificate.predicate.conclusions` (freeze §7) — misma lógica que `deriveKnowledge`                                                                                                                                                                                                                                                |
| `GET /runs/{run_id}/steps/{step_id}/evidence` | `StepDetail`                                | `{step_id, capability_id, input_digest, output_digest, attestations: [...]}`                              | proyección del stream del run filtrada por `step_id` sobre `run.step.*`/`capability.job.*`/`verification.completed` (trust/07 §1.3 fila "Inspector de paso")                                                                                                                                                                        |
| `GET /runs/{run_id}/ablation`                 | `AblationMetric[]`                          | `{variant, cut_cost, wall_ms, verification_latency_ms}[]`                                                 | `run.metrics.recorded` (freeze §3 [S-F]) por variante (quantum/classical) — trust/07 §1.3 fila "Ablación"                                                                                                                                                                                                                           |
| `GET /runs/{run_id}/topology`                 | payload de mapa (`superficie-visual.md` §4) | `{topology_ref, islands: [{id, name, bus_ids, verification}], cut_branch_ids, cut_cost}`                  | resultado de partición embebido en `verification.completed` — MISMA forma que trust/07 §1.3 fila "Visualizador de red" / spike `apps/studio/src/spike/ieee14.ts` `PartitionView`; `verification` **POR ISLA** (regla §9, sin excepción)                                                                                             |

**Errores:** `404` si `run_id` (o `step_id`) no existe — mismo patrón que
`chimera_api/certificate.py::get_certificate` (`HTTPException(404, "run desconocido")`); jamás
un 200 con datos fabricados. Un run vivo (sin certificado emitido todavía) no es error: `GET
/runs/{id}/artifacts` y `GET /runs/{id}/knowledge` responden `[]` — sin certificado no hay
conclusiones que mostrar, y eso es honestidad, no una falla del endpoint. `GET
/runs/{id}/steps/{step_id}/evidence` sobre un `step_id` sin `verification.completed` todavía
responde con `attestations: []` (paso corrió pero aún no lo verificaron) por el mismo principio.

## POST /runs — modo misión (extensión ADITIVA, checkpoint 5, 2026-07-29)

**Hueco de spec que esta sección cierra:** la Fase 0 fijó las rutas GET pero NUNCA definió el
contrato de arranque conversacional — `POST /runs` quedó solo con el body claim-first del MVP
(decisión #6: claim completo con `instance`+`assignment` en el request), mientras el Studio
(`apps/studio/src/data/mutations.ts::toCreateRunBody`) mandaba misión-first sin
instance/assignment → 422 vivo. No era solo un bug del mapper: era un contrato sin escribir.

### Contrato

`POST /runs` acepta **dos bodies alternativos**, discriminados por presencia de campo —
`mission` vs `claim` (ambos modelos Pydantic con `extra="forbid"`, así que un body con AMBOS
campos, o con ninguno, falla la validación de los dos lados de la unión → `422`):

1. **Body claim-first (MVP, INTACTO):** `{capability_id, inputs, claim: {...}, max_steps?}` —
   compat total, cero cambios; sigue gobernado por `docs/mvp/01-runtime-api.md` §1 y las
   decisiones #6/#7/#11.
2. **Body modo misión (NUEVO):**

   ```
   {
     mission: str,           // no vacía — el encargo conversacional (product-model.md, D6)
     instance_id?: str,      // instancia sobre la que versa la misión (scope, no claim)
     capability_id?: str,    // capability meta del arranque; default del server si falta
     max_turns?: int,        // default del server: 3 (ver "Gate ausente" abajo)
     budget?: { tokens?: int, cost_usd?: float }   // misma forma que RunBudget (harness-agentico.md)
   }
   ```

**Respuesta:** `202 {run_id}` — idéntica al modo claim-first; el resultado vive en el stream,
jamás en la respuesta HTTP.

### Semántica del arranque (costura A↔E)

- El modo misión agenda `execute_run` en **modo agéntico** (`proposer` inyectado —
  `harness-agentico.md` §Contrato-1): el plan viaja como eventos `plan.created`/
  `plan.item_updated` YA existentes (freeze §14, decisión #84). Cero evento nuevo.
- **La misión queda journalizada como `description` del ítem fundacional del plan** (el
  `plan_items` sembrado por el API): entra al alcance del `provenance_hash` del certificado
  (freeze §2) SIN extender la forma congelada de `run.created` (§3) — cero supersesión.
- El modo misión **NO exige assignment ni claim**: los claims los emiten los sub-runs/steps
  (`●ClaimEmitted {sub_run_id, ...}`, §Contrato-4 de `harness-agentico.md`) cuando el agente
  real los produzca — frontera P4, no de este endpoint.
- **Proposer placeholder (etiquetado):** hasta que P4 cablee el agente real (`ModelServer`
  tras `ModelPort`, decisión #81), `chimera_api` inyecta un proposer determinista que propone
  la capability meta en cada turno. Es la MISMA costura `Proposer` que el agente real ocupará
  — un seam, no "el agente" (el mapeo determinista como agente está RECHAZADO, decisión de
  producto Planeado). Reemplazarlo = swap del inyectable, cero cambio de contrato HTTP.
- **Gate ausente (honestidad):** sin verificación cableada no hay `done` — la doctrina
  (`harness-agentico.md` §Contrato-3) manda: `done` ⟺ el verifier pasa, JAMÁS un
  `run.completed` implícito. Un run de misión de hoy termina por `max_turns`/`budget` con
  `run.failed {error_kind: "exhausted"}` — eso es lo honesto, no un defecto. Por eso el
  default de `max_turns` del modo misión es **3** (conservador: cada turno extra del proposer
  determinista es gasto sin información nueva), no el 30 del loop con agente real; el caller
  lo sube vía `max_turns` cuando el gate exista.
- **Fail-loud intacto:** capability desconocida ⇒ `202` + `run.failed` DENTRO del stream
  (mismo contrato que el modo claim-first — el arranque HTTP solo falla por errores del
  REQUEST). El `run_ticket` del modo misión se registra VACÍO (sin conclusiones declaradas):
  `GET /runs/{id}/certificate` no da 404 por desconocido, y sin conclusiones no se fabrica
  certificado — honestidad, no error.

### Contrato con el Studio (costura E↔D)

`toCreateRunBody` (Studio) emite el body de misión desde el form actual
(instancia+proposer): `{mission, instance_id, capability_id}`. El fixture de costura
single-origin es `tests/fixtures/contract/endpoints/post-runs-mission.json` (validado contra
`MissionRequest` — el modelo Pydantic origen — por el test de contrato del API) espejado
byte-idéntico a `apps/studio/src/fixtures/contract/endpoints/post-runs-mission.json` (el test
del Studio fija que `toCreateRunBody` produce exactamente ese body). Misma convención que
`contract/harness/` (README de specs, "Fixtures de costura — un solo origen").

## Discrepancia de vocabulario a flaggear (costura E↔D) — bloqueante para D3, no para esta spec

El Studio **hoy** (`apps/studio/src/gatewayClient.ts`, constante `KNOWN_RUN_EVENT_TYPES`)
escucha estos tipos de evento del SSE real:

```
'run.started', 'capability.job.invoked', 'capability.job.completed',
'verification.completed', 'claim.emitted', 'run.completed', 'run.failed', 'run.cancelled'
```

El freeze fija otro nombre para el mismo evento de provenance:pre:

- **freeze §3:** `capability.job.submitted` (ANTES de ejecutar — PR1, etapa provenance:pre).
- **freeze §14 (C4, "Mapeo con la semilla v2"):** `tool.invoked ≡ capability.job.submitted` —
  el mapeo explícito con el vocabulario legado usa `.submitted`, NUNCA `.invoked`.
- `claim.emitted` (wire dotted-lowercase de `●ClaimEmitted`, §14) SÍ coincide con lo que el
  Studio ya escucha — ese nombre está correcto.

**Pin canónico de esta spec = freeze §3/§14: `capability.job.submitted` + `claim.emitted`.**
El único nombre desalineado en el Studio es `capability.job.invoked` (debería decir
`capability.job.submitted`); el resto del array de `KNOWN_RUN_EVENT_TYPES` ya está correcto.

**Impacto concreto:** mientras `gatewayClient.ts` registre un listener para
`capability.job.invoked`, el SSE real (que el harness emitirá como `capability.job.submitted`
por el pin de arriba) nunca dispara ESE listener — el evento se pierde silenciosamente para ese
tipo puntual (el resto del stream sigue funcionando, incluidos `claim.emitted` y
`verification.completed`). Bajo fixture/demo mode no hay impacto: los fixtures no pasan por
`EventSource`, así que el desalineamiento es invisible hasta que el Studio se conecte al SSE
real.

**Resolución:** el mirror del Studio se alinea en **Fase 1, dominio D, tarea D3** (junto con el
resto del egress live de las 6 queries fixture-only, abajo) — NO en esta spec de Fase 0, que no
edita código de `apps/studio/src` (regla del mandato: Fase 0 = contratos, no features). Esta
spec deja el pin escrito para que D3 no lo redescubra a mitad de integración.

## Las 6 queries fixture-only del Studio — su rama live sale de estas rutas

`apps/studio/src/data/queries.ts` tiene hoy **6 queryOptions que sirven SIEMPRE fixture**, sin
rama `isLiveMode()` — a diferencia de `certificateQueryOptions`/`loadCertificate`, que YA
ramifica fixture-vs-live vía `gatewayClient.getCertificate` (Task 3, S10):

1. `runSummariesQueryOptions` → rama live: `GET /runs`.
2. `artifactsQueryOptions` → rama live: `GET /runs/{run_id}/artifacts` (nota: hoy esta query no
   recibe `run_id` como parámetro — Fase 1 lo agrega junto con la rama live, ya que la ruta lo
   exige en el path).
3. `knowledgeQueryOptions` → rama live: `GET /runs/{run_id}/knowledge` (mismo ajuste de
   parámetro que el punto anterior).
4. `runEventsQueryOptions` → **NO** consume una ruta de esta tabla: ya vive del SSE real vía
   `openRunEventStream` (`gatewayClient.ts`) — se menciona acá solo para no confundirla con las
   5 que sí necesitan ruta REST nueva.
5. `stepEvidenceQueryOptions` → rama live: `GET /runs/{run_id}/steps/{step_id}/evidence` (mismo
   ajuste: la query hoy no recibe `step_id`, la ruta lo exige).
6. `ablationQueryOptions` → rama live: `GET /runs/{run_id}/ablation`.

`GET /runs/{run_id}/topology` no tiene query en `queries.ts` todavía — Fase 1 la agrega junto
con la vista de mapa real (`superficie-visual.md` §4).

**D3 (Fase 1, dueño Steven+Dylan)** agrega a estas 6 (5 + topología) la MISMA convención
fixture-vs-live que `certificateQueryOptions` ya demuestra: `isLiveMode()` decide la fuente, la
`queryKey` y el tipo de retorno NO cambian — un swap, no un rewrite (mismo principio que
`create_event_store(dsn=None)` en el lado del engine, `confianza-api-sse.md`).

## Contrato Zod (prosa — NO se escribe TS en esta spec)

Misma convención de costura que `superficie-visual.md` §7 (README "Fixtures de costura — un
solo origen"): el fixture de `tests/fixtures/contract/endpoints/<caso>.json` se genera desde los
modelos Pydantic que YA existen (`RunRow`, `blite.certificate` predicate) — a diferencia de
`superficie-visual.md`, el origen Python de estas 6 rutas **ya existe hoy**: `project_runs` y
`assemble_bundle` están VERDES. Fase 1 puede generar estos fixtures desde el primer día sin
esperar a `harness-agentico.md`.

El Zod espejo (a mano, `apps/studio/src/data/schemas.ts`) para las respuestas de lista reusa
composición sobre los schemas ya existentes donde el shape coincide (p. ej. `ablationMetricSchema`
ya existe y es el mismo shape que devuelve `GET /runs/{id}/ablation` salvo casing — el mapper
wire→UI sigue el mismo patrón que `toProjectedEvent`). Los tres schemas nuevos que Fase 1 agrega:

- `runSummaryWireSchema`: `{run_id, status: enum(en_curso|completado), conclusion, verdict: enum(pass|fail|inconclusive), titular_level: assuranceLevelSchema, titular_class: string, events_count: number, actor: string, completed_at: string.optional()}`.
- `projectArtifactWireSchema`: `{artifact_ref, digest, run_id, titular_level: assuranceLevelSchema, titular_class, verdict, issued_at}`.
- `knowledgeClaimWireSchema`: `{statement, scope: record(string, string), verdict, level: assuranceLevelSchema, titular_class, run_id, valid_as_of}`.

`stepDetailSchema` y `ablationMetricSchema` (ya existentes en `schemas.ts`) se reutilizan tal
cual para `GET /runs/{id}/steps/{id}/evidence` y `GET /runs/{id}/ablation` — sus shapes ya
coinciden con la tabla de arriba salvo el envoltorio de wire (snake_case), que sigue el mismo
patrón de mapper que `toProjectedEvent`.

## Fronteras (qué NO decide esta spec)

- **Autenticación (JWT en cookie)** — ya decidida en `confianza-api-sse.md`/freeze §9 P1-9, no
  se reinventa acá.
- **Compose/reverse proxy** (Geovanni).
- **La lógica que PRODUCE `certificate.predicate.deliverables/conclusions`** — ya existe
  (`blite.certificate.assemble`); esta spec solo expone rutas de LECTURA sobre lo ya
  ensamblado/proyectado, no cambia el ensamblador.
- **El payload EXACTO que el harness emite para partición** (topología) — depende de
  `harness-agentico.md`/dominio ciencia; esta spec fija la FORMA de la respuesta HTTP, no quién
  la produce ni cuándo.
- **El código de `apps/studio/src`** (D3, la rama live de las queries) — Fase 1, no esta spec.

## Interfaces con otros dominios

| Interfaz                                                                                                   | Dominio afectado | Estado                                                                                                       |
| ---------------------------------------------------------------------------------------------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------ |
| D3 (egress de `queries.ts`) contra estas 6 rutas                                                           | E↔D              | SPEC — pin de nombres de ruta y forma; implementación Fase 1                                                 |
| E proyecta los eventos que A emite (`capability.job.submitted`, `claim.emitted`, `verification.completed`) | E↔A              | Proyección genérica VERDE (`confianza-api-sse.md`); PIN de nombres = freeze §3/§14 (ver discrepancia arriba) |
| Payload de topología consumido por `superficie-visual.md`                                                  | E↔D              | forma pinneada en ambos documentos, sin duplicar la fuente de verdad                                         |

## Eventos/payloads nuevos

Ninguno propio al stream: esta spec expone rutas REST derivadas de proyecciones **ya
congeladas** (§7 certificado, §2/ejecución `runs_projection`, §3 `run.metrics.recorded`) — no
introduce ningún tipo de evento nuevo. Su única novedad de "wire" es la FORMA de la respuesta
HTTP (tabla de arriba), no un evento SSE nuevo.

## Tests semilla

- `tests/seeds/test_seed_endpoints_rutas.py` — **xfail** (todas las rutas 404 hoy; ninguna
  existe en `chimera_api/app.py`). El seed importa `chimera_api.app.create_app` DENTRO de cada
  función de test (no a nivel de módulo — las rutas que asertan no existen todavía, pero el
  paquete `chimera_api` sí, así que el import module-level sería seguro; se mantiene dentro de
  la función de todos modos para no divergir del patrón "collection-safe" pedido para esta
  sesión) y fija, por ruta, el contrato **ruta → forma de la respuesta** contra un store con un
  run mínimo servido — el dueño de Fase 1 quita el `xfail` ruta por ruta a medida que las
  implementa, sin esperar a que las 6 estén listas a la vez.
