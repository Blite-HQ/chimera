# Spec de costura — Proyector de observabilidad OTel (consumer standalone)

**Gobernada por:** freeze **§2** (event store append-only; notify-then-catchup; hash-first —
digests, jamás contenido) + **§3/§14** (vocabulario de eventos que se proyecta) + la
resolución **C-11/#106** (`docs/mejorado/04-consolidacion.md` §3: consumer standalone FUERA
de `blite.*` — el exportador OTLP es egress y no puede vivir dentro del engine sin chocar
Inv-E/INV-6).
**Costura:** stream→observabilidad (solo-lectura) · **Estado:** SPEC (Fase 0 Mejorado,
2026-07-31, decisión #127) · **Consume:** O3/M9.

> El valor de M9 es exportar el rastro del run (incluida la verificación) a cualquier
> collector OTLP sin tocar la frontera de confianza. La resolución C-11 lo vuelve posible:
> el proyector es un PROCESO aparte que deriva spans del stream — no gobierna, no escribe,
> no importa el engine. Esta spec fija el mapeo, la derivación determinista de IDs y las
> reglas de frontera; la implementación es O3.

## Contrato

**1 · Home y frontera.** Miembro nuevo del workspace **`projectors/otel/`** (paquete
`chimera_otel`), FUERA de `blite.*`: **no importa el engine** — parsea los eventos como
JSON del wire (el wire ES el contrato; mismo desacople que el Studio). Corre como servicio
del compose bajo el **perfil `otel`** (junto a un `otel-collector`); el camino por defecto
del stack NO lo incluye. **Langfuse = perfil OPCIONAL aguas abajo** (consumidor OTLP,
herramienta interna de debugging del proposer) — jamás «backend» (la degradación ya
registrada en #106).

**2 · Fuente de datos (solo-lectura).** Usuario Postgres **SOLO-SELECT sobre `events`**
(cero permisos de escritura — el append-only ni se roza) + catch-up por `global_seq` con
**cursor propio persistido FUERA del event store** (archivo/tabla propia del proyector).
Misma doctrina notify-then-catchup de §2: NOTIFY como pista, la tabla como verdad. El
proyector puede caerse y reproyectar desde cualquier cursor — el resultado es idéntico
(punto 4).

**3 · Mapeo evento→span (la tabla).** Un **trace por run**; spans y span-events derivados:

| Evento(s) del stream                                                                   | Span / anclaje                                    | Atributos clave                                                                  |
| -------------------------------------------------------------------------------------- | ------------------------------------------------- | -------------------------------------------------------------------------------- |
| `run.created` → terminal                                                               | span RAÍZ `run` (ancla: `run`)                    | `run_id`, `domain_id`, `actor_id`, `policy_digest`, `max_steps`, status final    |
| `run.step.started/completed/failed`                                                    | span hijo `step` (ancla: `step_id`)               | `step_id`, `kind`, `input_digest`, `output_digest`, `status`                     |
| `capability.job.submitted/…/failed`                                                    | span hijo del step `capability` (ancla: `job_id`) | `capability_id`, digests — semconv de tool execution                             |
| `model.call.requested/completed/failed`                                                | span `gen_ai` (ancla: `prompt_digest`)            | `backend_id`, `local`, `prompt_digest`, `response_digest` — JAMÁS contenido      |
| `●VerificationStarted/Completed`                                                       | span `verification` (ancla: `step_id` o posición) | verdict, `verifier_class`, AL, `policy_id` — la verificación ES parte del rastro |
| `plan.*`, `approval.*`, `mission.message`, `replay.divergence`, `run.metrics.recorded` | span-EVENTS sobre el span raíz                    | payload plano como atributos (digests/ids; texto solo si ya es wire público)     |
| `system:*` streams                                                                     | FUERA — el proyector solo proyecta streams de run | (los streams de sistema no son rastro de un run)                                 |

Regla dura (hash-first §2 + soberanía §15.1): **el proyector exporta digests e IDs, jamás
payloads en claro de contenido grande** — prompts/respuestas/artefactos viajan como digest;
quien quiera el contenido lo resuelve contra el `ContentStore` con SUS permisos, nunca vía
la traza.

**4 · IDs y tiempos DETERMINISTAS (replay ⇒ trazas idénticas).**

```
trace_id = SHA-256("blite/otel-trace/v1\n" ‖ run_id)            [primeros 16 bytes]
span_id  = SHA-256("blite/otel-span/v1\n" ‖ run_id ‖ ":" ‖ ancla) [primeros 8 bytes]
```

— `ancla` = la columna «ancla» de la tabla (estable en el stream, jamás aleatoria);
timestamps de los spans = `occurred_at` de los eventos (jamás el reloj de la proyección).
Consecuencia (la propiedad que O3 demuestra): **re-proyectar el mismo stream — o el stream
de un replay fiel — produce trazas byte-idénticas**; una divergencia de traza sin
`replay.divergence` en el stream es un bug del proyector, no del run. Prefijos de dominio
versionados: cambiar el mapeo o el esquema de derivación = bump (`.../v2`), misma
disciplina que el anexo de canonicalización.

**5 · Semconv GenAI pinneada y ESTAMPADA.** La versión exacta de la convención semántica
GenAI la PINNEA O3 al implementar (con registro en el ledger — las semconv de OTel siguen
incubando y el pin es una decisión fechada); la REGLA es contrato desde ya: cada span porta
**`chimera.semconv_version`** y **`chimera.projector_version`** — dos proyecciones con
convenciones distintas jamás se confunden, y el consumidor sabe QUÉ dialecto lee.

## Eventos / payloads nuevos

Ninguno. El proyector es consumidor puro — no emite eventos al stream, no introduce wire
nuevo; su salida es OTLP hacia el collector del perfil.

## Interfaces con otros dominios

| Interfaz                                        | Dominio         | Estado                                                                                            |
| ----------------------------------------------- | --------------- | ------------------------------------------------------------------------------------------------- |
| Lectura solo-SELECT de `events` + cursor propio | infra (compose) | SPEC — usuario/GRANT los define O3                                                                |
| Tabla de mapeo evento→span                      | observabilidad  | SPEC — fixture golden declarado                                                                   |
| Perfil `otel` (+ Langfuse opcional) en compose  | infra           | SPEC — O3                                                                                         |
| `model.call.*` (los emite P4/M31)               | A↔E             | El proyector los mapea CUANDO existan — sin ellos el span gen_ai simplemente no aparece (honesto) |

## Fronteras (qué NO decide esta spec)

- **El pin concreto de la semconv** y las versiones de SDK/collector — O3 con registro.
- **Dashboards/queries** sobre el collector — fuera del contrato.
- **La emisión de `model.call.*`** — P4/M31 (sesión P-rt); el proyector no los inventa.
- **Métricas/alertas OTel** (solo trazas en v1; métricas = extensión futura con bump).

## Tests de contrato (fixtures de costura)

Declarado (el proyector no existe — Fase 1 O3):
`tests/fixtures/contract/observabilidad/trace-example.json` — el **golden trace** que el
proyector produce sobre un stream fixture conocido (ids deterministas ⇒ el golden es
estable por construcción); espejo Studio no aplica (el consumidor es el collector, no el
Studio).

## Tests semilla

- `tests/seeds/test_seed_observabilidad_proyector.py` — **SEED, xfail(strict=False)**: la
  derivación de `trace_id`/`span_id` del punto 4 recomputada de forma INDEPENDIENTE
  (hashlib en el test) contra `chimera_otel.projection`; determinismo (misma entrada ⇒
  mismos ids); y que el módulo NO importe `blite` (frontera C-11 como aserción).
