# Spec de costura — Superficie visual del Studio: plan, aprobación y mapa (D↔E↔A)

**Gobernada por:** freeze **§9** (contrato SSE Studio↔Engine, extendido ADITIVAMENTE) + **§14**
(catálogo ● de la capa de confianza) · research `docs/planeado/03-research-estado-del-arte.md` §R5 ·
decisión #66 (`docs/mvp/decisiones.md`, ceremonia A1 → loop agéntico) fija el wire canónico que
esta spec consume.
**Insumo:** trust/07 §1.3 (payload mínimo por vista) + trust/18 §2 (specs de componente) —
**[S3 2026-07-30]** slot normalizado: las notas de knowledge estaban en «Gobernada por:»;
knowledge es insumo, jamás autoridad (#108).
**Costura:** D↔E↔A · **Dueño (Fase 1):** Dylan · **Estado:** SPEC (Fase 0, 2026-07-24)

> **Regla de aditividad (README "Specs de costura"):** los payloads nuevos de este documento
> EXTIENDEN §9 — no tocan ninguna forma ya congelada (`run.*`, `verification.completed`,
> `certificate`, ablación). `docs/specs/confianza-api-sse.md` sigue siendo la autoridad del
> transporte SSE (endpoint, framing `id/event/data`, cabeceras anti-buffering, catch-up
> `Last-Event-ID`); esta spec solo fija payloads y su render.

## Contrato

### 1 · Eventos que esta spec consume de A (harness) — wire canónico, sin traducir

Decisión #66 fija estos cuatro tipos de evento (mismos nombres de wire, dotted-lowercase,
`event:` del frame SSE) — D los consume tal cual, jamás inventa un vocabulario propio:

- `plan.created` → `{plan_id, run_id, items: [{id, description, verification, status}]}`,
  `status ∈ {pending, running, ok, failed}`. `●PlanCreated` en el catálogo §14.
- `plan.item_updated` → `{plan_id, run_id, item_id, status, cause?}`. Progreso incremental
  sobre el plan ya creado — mismo `plan_id`.
- `approval.requested` → `{run_id, approval_id, json_schema, prompt, step_id?}`.
- `approval.responded` → `{run_id, approval_id, response, authorized_by}`.

Los cuatro viajan por el MISMO framing de §9 (`id: global_seq`, `event: <type>`,
`data: <proyección JSON>`) y por la MISMA proyección genérica
(`chimera_api.projection.project_event`/`sse_frame`, spec `confianza-api-sse.md`) — esa función
no distingue por `type`: el payload entero (incluido cualquier bloque `verification`) llega
intacto. Verificado por el seed de esta spec (abajo) sin esperar a que `harness-agentico.md` se
implemente.

### 2 · Plan-checklist + cards con drill-down (`RunTimeline`/`StepInspector`, trust/18 §2.1–2.2)

- El plan es un checklist vivo (patrón Claude Code / `write_todos` de deepagents, R5): cada
  `item` del payload de `plan.created` es una fila; `plan.item_updated` muta SOLO el `item_id`
  referido — el cliente NUNCA reconstruye el plan entero desde cero por cada update.
- Cada paso del plan abre una card colapsada con drill-down a evidencia (Devin, R5) — mismo
  patrón que `StepInspector` (trust/18 §2.2): badge clase+AL siempre visible, `evidence` crudo
  solo al expandir.
- **Reducer del cliente (R5 "UX agéntica"):** convención `start/delta/end` sobre IDs estables —
  aquí `plan_id`/`item_id` cumplen el rol de `stepId`/`jobId` de trust/07. Transiciones de
  `status`: `pending → running → {ok | failed}`, conjunto cerrado (mismo espíritu que
  `RunStep.status` del freeze §3 — un `item` en `running` no salta directo a `pending`).
- **Scrubber de replay:** el timeline de plan/aprobación se reproduce con scrub sobre el MISMO
  catch-up `Last-Event-ID` ya congelado (freeze §9 P1-9) — no es mecanismo nuevo, es UI que
  reutiliza F5+catch-up ("cero eventos perdidos") como feature de replay verificable con hash
  (R5). `PlaybackControls` (trust/18 §2.1, ya en `apps/studio/src/views/types.ts`) es la
  interfaz de cliente para este scrub; sigue siendo fixture/demo-only para el modo simulado,
  real para el modo replay del stream ya cerrado.

### 3 · Aprobación humana — card inline bloqueante

- `approval.requested`/`approval.responded` se renderizan como par de eventos con card inline
  bloqueante (semántica `tool-approval-request/response` de Vercel AI SDK, patrón Operator —
  R5): la UI NO deja avanzar el timeline en vivo más allá del punto de una aprobación pendiente
  sin respuesta.
- `json_schema` es el JSON Schema (forma "elicitation" de MCP, R1) contra el cual el cliente
  humano completa `response`; la validación de ese schema es responsabilidad de quien EMITE
  `approval.responded` (A/harness) — esta spec solo renderiza el form y lo postea; el endpoint
  HTTP exacto para postear la respuesta vive fuera de este documento (frontera, abajo).
- `step_id?` es opcional: una aprobación puede bloquear un paso puntual del plan o el run
  completo (ausencia de `step_id` = bloqueo a nivel run).

### 4 · Payload de MAPA (topología / partición)

> **[S3 2026-07-30]** (superficie de dominio Reto-1 — lente): silueta de Costa Rica,
> ancho-por-kV, `pmtiles --region=cr` — dominio del caso demo presentado como superficie de
> plataforma (censo §4, tipo (iii)); la doctrina que lo resuelve es la de lentes de
> `docs/studio/product-model.md` §Superficies.
>
> **[S3 2026-07-30] Registro del divorcio D-N12 (censo §1.7-A — SIN supersede
> decidido, se reporta):** el mapa que el Studio construyó no es el payload que
> esta sección fija — `DataFormatRouter.tsx` enruta a `GridMap`/GeoJSON propio, y
> el endpoint que SÍ implementa esta spec (`api/src/chimera_api/reads.py:440`) no
> tiene consumidor. Divorcio distinto de C-9; su resolución es trabajo de
> V1/M18, no de saneamiento.

**Orden de construcción (R5, fallback primero — garantía del día D):**

1. **Fase 1 (S, ~0.5 día):** mapa abstracto-geográfico SIN basemap — silueta de Costa Rica
   (Natural Earth GeoJSON) proyectada con `d3-geo` `fitSize()` a SVG, tokens del design system
   para color-por-isla y ancho-por-kV; red, hulls de islas y badges como SVG. Cero tiles, cero
   riesgo air-gap.
2. **Fase 2 (M, ~2 días, upgrade):** `maplibre-gl` + `react-map-gl@8/maplibre` + `pmtiles@4` +
   `@protomaps/basemaps@5` flavor `black` re-tokenizado; `pmtiles extract --region=cr`; glyphs y
   sprites **self-hosted** (probar con red cortada — el fallo silencioso clásico del air-gap);
   atribución ODbL visible. Badges = `maplibregl.Marker` montando `AssuranceBadge` ya existente;
   estados vivos vía `setFeatureState`.
3. La vista topológica Cytoscape (validada por el spike, `apps/studio/src/spike/ieee14.ts`) SE
   MANTIENE en paralelo — el dual "diagrama + mapa" es el patrón PowSyBl/OpenInfraMap, no un
   reemplazo.

**Forma del payload** — misma fila "Visualizador de red" de trust/07 §1.3, formalizada acá y
alineada al shape ya validado por el spike (`PartitionView`/`Island` en `ieee14.ts`):

```
{
  topology_ref: str,
  islands: [
    {
      id: str,
      name: str,
      bus_ids: [str, ...],
      verification: {          // regla §9 — NUNCA opcional, NUNCA global-only
        verdict: "pass" | "fail" | "inconclusive",
        verifier_class: str,   // freeze §4 — sin "model" por construcción
        level: "AL0".."AL4",
        anchor_kind: "solver" | "execution" | "dataset" | "rule" | "human",
        method: str,
        summary: str
      }
    },
    ...
  ],
  cut_branch_ids: [str, ...],
  cut_cost: number
}
```

**Regla de forma (freeze §9, sin excepción, validada por el spike §1.4 de trust/07):** el
resultado de partición lleva `verification` **POR ISLA** — un payload de mapa con un único
bloque `verification` a nivel raíz (y no uno por isla) violaría §9 tanto como un resultado sin
bloque `verification` en absoluto.

**[S3 2026-07-30]** Nota: «por isla» es la instancia Reto-1 de la regla, no su enunciado
universal — la formulación GENÉRICA correcta es la de
`docs/specs/confianza-api-sse.md` §Contrato, bala «Regla de forma (freeze §9)» (líneas
31-35 tras el ajuste de header S3): «ningún payload de resultado sin su bloque
`verification`» (por sub-entidad del resultado; «isla» es vocabulario del dominio, no del
contrato — censo §4).

Este payload NO introduce un tipo de evento nuevo al catálogo §14: viaja embebido en el payload
de `verification.completed` (o el `run.step.completed` del paso de partición) tal como trust/07
§1.3 ya lo fijó — esta spec formaliza la FORMA exacta, no inventa wire.

### 5 · Dataviz r vs p

> **[MEJORADO C-9/#106 · 2026-07-30] SUPERSEDIDA la fuente de datos de esta
> sección (divergencia consumada, estampada con causa):** el Studio construyó la
> curva r-vs-p sobre un payload propio (rvsp) y NO sobre `AblationMetric[]` sin
> eje p como esta sección fijó. Resolución C-9: la fuente pasa a ser
> **`GET /runs/{run_id}/rvsp`** (clave POR RUN — el run cita su instancia), que
> entra como fila de `endpoints-studio.md` al implementarse el ítem V3/M20; las
> instancias con `optimo: null` (`ice-*`) quedan declaradas FUERA del endpoint.
> El componente de render (Recharts vía `ChartContainer`) sigue vigente tal cual.

- **Recharts** (ya instalado `^3.8`, R5) vía `ChartContainer` (wrapper shadcn — regla de stack,
  `feedback_stack_definitivo_studio`): `ComposedChart` + `Scatter` con `<ErrorBar>` `[lo, hi]` +
  `<ReferenceLine>` dasheada por baseline (GW/greedy/exacto), colores `--chart-*`. Tabla
  comparativa al lado (shadcn `Table`, estilo W&B Run Comparer).
- Fuente de datos: `AblationMetric[]` — forma YA fijada (trust/07 §1.3 fila "Ablación",
  presente hoy en `apps/studio/src/views/types.ts`); esta spec no cambia esa forma, solo fija
  el componente de render y advierte (R5, riesgo acumulado): mantener `<ErrorBar>` en
  configuración estándar — historial de bugs de Recharts en configs exóticas.

### 6 · Vocabulario: clase + AL, jamás `rung`

`knowledge/trust/18-ux-confianza-componentes-studio.md` es la nota origen de estos componentes
pero **arrastra vocabulario `rung` viejo** en ejemplos históricos (interfaces `Attestation` §2.2
con campo `rung: number`, `TrustCertificateStatement.aggregateRung` — texto anterior a la
supersesión). El freeze **§4** supersede la escalera 1–7 por **clase + AL**; el código YA migró
(ET-9: `assurance.ts`, `AssuranceScale`/`AssuranceBadge`, `apps/studio/src/data/schemas.ts` usa
`assuranceLevelSchema`/`verifierClassSchema`, `apps/studio/src/views/types.ts` usa
`AssuranceLevel`/`VerifierClass`). Toda superficie NUEVA de esta spec (plan-checklist, cards de
aprobación, mapa) usa **exclusivamente clase+AL** — cero `rung`/"escalón" en artefactos nuevos
(regla README §"Cómo trabajamos en paralelo" #4).

### 7 · Contrato Zod (prosa — NO se escribe TS en esta spec)

Convención de fixtures de costura (README "Fixtures de costura — un solo origen"): el origen es
Python (modelos Pydantic del contrato); Fase 1 genera `tests/fixtures/contract/superficie/<caso>.json`
espejado a `apps/studio/src/fixtures/contract/superficie/<caso>.json`, y el par
[fixture generado + Zod espejo a mano] es el contrato — nunca codegen Pydantic→Zod.

El Zod espejo que Fase 1 agrega a `apps/studio/src/data/schemas.ts` (declarado en prosa, no
escrito acá):

- `planCreatedSchema`: `{ plan_id: string, run_id: string, items: array({ id: string, description: string, verification: string, status: enum(pending|running|ok|failed) }) }`.
- `planItemUpdatedSchema`: `{ plan_id: string, run_id: string, item_id: string, status: enum(pending|running|ok|failed), cause: string.optional() }`.
- `approvalRequestedSchema`: `{ run_id: string, approval_id: string, json_schema: record(string, unknown), prompt: string, step_id: string.optional() }`.
- `approvalRespondedSchema`: `{ run_id: string, approval_id: string, response: unknown, authorized_by: string }`.
- `topologySnapshotSchema`: `{ topology_ref: string, islands: array({ id, name, bus_ids: array(string), verification: <mismo shape que attestationSchema, sin evidence> }), cut_branch_ids: array(string), cut_cost: number }`.

**Estado del fixture (Fase 0 → Fase 1, regla README):** el modelo Pydantic origen de
`plan.created`/`plan.item_updated`/`approval.*` NO existe todavía (`harness-agentico.md`, dueño
Dylan+Steven, lo materializa) — el fixture de `contract/superficie/` queda pendiente de Fase 1;
generarlo hoy sería inventar un dato que ningún modelo respalda. Lo que SÍ existe hoy y esta
spec valida en su seed es que la proyección genérica (`project_event`/`sse_frame`) no degrada
estos payloads — ver Tests semilla.

### 8 · Convención de branch-ids y verdict por isla (C-8/#106 · #124 — Fase 0 Mejorado, 2026-07-31)

**Hueco que cierra (cobertura C-8):** `cut_branch_ids` viajaba sin convención versionada en
3 modelos, y la regla de agregación per-isla del verdict no existía escrita.

- **Convención HÍBRIDA de branch-ids (decisión #106 C-8, detalle #124):**
  - Instancias **derivadas de GIS**: el id de rama es el `edge_id_property` del portal
    (FID/OBJECTID), declarado como parámetro de la receta de `geojson_to_graph` — el dato
    del cliente conserva SU identidad; la receta lo estampa.
  - Modelos **sin GIS** (IEEE, sintéticas): id canónico determinista **`L{min}-{max}[-k]`**
    — buses de la rama ordenados ascendente; `k` = índice 1-based de la paralela, presente
    SOLO cuando hay multi-aristas (`L2-5`, `L3-8-2`).
  - **Versionado:** la convención viaja CON la instancia (`recipe.version` +
    `params_digest` de la receta que la generó) — cambiar de convención produce una
    instancia nueva con digest nuevo, jamás un re-etiquetado del dato estampado.
- **Verdict por isla (la regla de agregación que faltaba):** el verdict de la isla `k` =
  `derive_execution_verdict` aplicado al SUBCONJUNTO de checks `island-{k}:*` de esa isla —
  ningún check de otra isla contamina; un check global (`power_balance` de red completa)
  pertenece al resultado, no a una isla. `step_id = island_id` estable (`island-{k}`) — la
  base sobre la que C4/M4 construye `verify_all()` y los badges nativos.
- **Fixture (precondición del merge de V1, letra C-8):**
  `tests/fixtures/contract/superficie/topology-snapshot.json` — generado desde
  `TopologyResponse` (`api/src/chimera_api/reads.py:138`, modelo YA existente) por
  `scripts/gen-contract-fixtures-superficie.py`, espejado al Studio y parseado por el Zod
  NUEVO `topologySnapshotSchema` (entregado en Fase 0 — cierra el «declarado en prosa» del
  §7 para topología). El caso ejemplifica AMBAS formas de branch-id y `verification` POR
  isla (§4).

### 9 · `run.metrics.recorded` extendido y `variant` ×4 (C-4/#106 · #124 — Fase 0 Mejorado, 2026-07-31)

Materializa el supersede (b) del freeze §3 como contrato ejecutable:

- **Payload v2 (aditivo):** los campos de confianza congelados se MANTIENEN
  (`verification_latency_ms`, `attestations_total`, `inconclusive_count`,
  `false_reject_proxy`, `cost_per_verification?`, `ms_por_clase?`); entran **`variant?`**
  (enum de 4: `quantum|classical|mitigated|zne` — cubre M6) y los científicos opcionales
  **`cut_cost?`/`wall_ms?`** (exactamente lo que `AblationMetric` consume — nada más se
  especula). Módulo propuesto: `blite.runtime.metrics` (`RunMetricsRecordedPayload`,
  emisor `service:runtime` al cerrar el run; el evento sigue FUERA del hash, §2).
- **Dos brazos = sub-runs (§13):** cada brazo de ablación es un sub-run que emite SU
  `run.metrics.recorded` en SU stream; las métricas científicas que sean EVIDENCIA van
  además como deliverable con digest citado por el certificado (letra C-4) — el evento
  post-terminal es proyección visual, jamás amparo.
- **Extensión coordinada del enum (jamás catchall):** `AblationMetric.variant`
  (`reads.py:132`), `ablationMetricSchema` (Zod), el tipo TS y el chart pasan de 2 a 4
  valores EN EL MISMO checkpoint que el productor (V2/M19) — misma disciplina que C-15
  fija para `baselines`.
- **Fixture declarado:** `tests/fixtures/contract/superficie/run-metrics-recorded.json`
  (modelo Fase 1 — V2; el generador de superficie gana el caso al existir el modelo). Seed:
  `tests/seeds/test_seed_metrics_variant.py`.

## Fronteras (qué NO decide esta spec)

- **Quién EMITE `plan.created`/`plan.item_updated`/`approval.*`** (A, harness agéntico, dueño
  Dylan+Steven) — `harness-agentico.md` fija el emisor; esta spec solo consume la forma
  pinneada por decisión #66 y le da render.
- **El endpoint HTTP** por el cual el Studio postea `approval.responded` — vive en
  `endpoints-studio.md` o en `harness-agentico.md` (costura A↔E); esta spec no fija esa ruta,
  solo el payload que viaja por el stream una vez que la respuesta se registró.
- **Hosting de tiles/glyphs de MapLibre** (compose, Geovanni).
- **El modelo Pydantic de `plan.created`/`approval.*`** — Fase 1, `harness-agentico.md`.

## Interfaces con otros dominios

| Interfaz                                                                                    | Dominio afectado             | Estado                                                               |
| ------------------------------------------------------------------------------------------- | ---------------------------- | -------------------------------------------------------------------- |
| Consume `plan.created`/`plan.item_updated`/`approval.requested`/`approval.responded` (wire) | D↔A (`harness-agentico.md`)  | SPEC — wire pinneado por decisión #66; emisor pendiente Fase 1       |
| Consume la proyección SSE genérica (`project_event`/`sse_frame`)                            | D↔E (`confianza-api-sse.md`) | VERDE — validado por el seed de esta spec (proyección type-agnostic) |
| Payload de mapa/partición (verification por isla, embebido en `verification.completed`)     | D↔E                          | Forma congelada por trust/07 §1.3; esta spec la formaliza            |

## Eventos/payloads nuevos (wire dotted-lowercase → ● catálogo §14)

| Wire                 | ● catálogo §14 | Nota                                                                                                                                                                              |
| -------------------- | -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `plan.created`       | `●PlanCreated` | ya en el catálogo (§14)                                                                                                                                                           |
| `plan.item_updated`  | —              | progreso incremental del mismo `●PlanCreated`; sin ● propio en el catálogo — aditivo (ver "Discrepancia" abajo)                                                                   |
| `approval.requested` | —              | sin ● propio en §14 — el catálogo tiene `●HumanOverrideRecorded` (posterior al hecho, para overrides ya aplicados) pero NADA para una solicitud de aprobación PENDIENTE; ver nota |
| `approval.responded` | —              | idem — candidato natural sería sumarlo al catálogo §14 en la próxima actualización del freeze, fuera del alcance de esta spec (que no lo edita)                                   |

**Nota (discrepancia a resolver, no bloqueante):** `plan.item_updated` y el par
`approval.requested`/`approval.responded` no tienen un ● homólogo explícito en el catálogo §14
tal como está escrito hoy. Esto NO es una contradicción del freeze (§14 no se declara conjunto
cerrado por escrito) pero sí es una laguna de nomenclatura que un futuro delta de freeze debería
cerrar — se deja registrada aquí, no se resuelve unilateralmente en una spec de costura (regla 3
del freeze: cambios post-freeze son supersesión con causa, no edición silenciosa).

## Tests semilla

- `tests/seeds/test_seed_superficie_plan_aprobacion.py` — **VERDE** (import a nivel de módulo,
  como `tests/unit/api/test_projection.py`): construye eventos `Event` de tipo `plan.created`,
  `approval.requested` y un `verification.completed` con `verification` por isla, y confirma que
  `chimera_api.projection.project_event` los deja pasar íntegros (payload completo, incluido el
  bloque `verification`) — la proyección es genérica por diseño (spec `confianza-api-sse.md`),
  así que este contrato NO depende de que `harness-agentico.md` exista todavía.
