# Nota 07 — Vocabulario `run.*`: máquina de estados y orden de eventos con `run.step.*`/`capability.job.*`

**Ítem del plan:** plano de ejecución (Steven) — el vocabulario de eventos de nivel "run" que agrega los
eventos de paso (nota 02) y de job de capability (`knowledge/trust/06` §1.3) en una línea de tiempo
coherente, consumible por el Studio (frontera con `knowledge/trust/18`).
**Fecha:** 2026-07-10 · **Estado:** incorporada al freeze (S-E 2026-07-18), con la pregunta №1 RESUELTA y un refinamiento de la convergencia (§4.2): (1) **confirmado `stream_id = run_id`, un stream por run** (opción A — decisión de Dylan); (2) **se adopta el `Run` jerárquico** que esta nota no vio: `parent_run_id` en el Run/proyección, case y certificado SIEMPRE del run raíz (D5), sub-runs con **su propio stream** que aportan claims al raíz — la jerarquía viaja por `parent_run_id`, no por streams anidados (las opciones B/C siguen descartadas). El caso §6 (step RUNNING al cancelar el run) quedó cerrado: sin evento terminal propio; la proyección lo reporta `interrupted`. Máquinas de estado y vocabulario `run.*`/`run.step.*` entraron tal cual (freeze §3/§13). **EJECUTADA (2026-07-24)** — el vocabulario `run.*`/`run.step.*`/`capability.job.*` lo emite `runtime/loop.py`; `stream_id = run_id` confirmado en código.
**Fuentes:** `knowledge/trust/01-event-sourcing-postgres.md` (puerto `EventStore`, `stream_id`) ·
`knowledge/trust/06-protocolos-capability-mcp-a2a.md` §1.3 (`capability.job.*`) ·
`knowledge/trust/08-identidad-lite-kagenti.md` (AX1, `actor_id` obligatorio) ·
`knowledge/trust/18-ux-confianza-componentes-studio.md` (`RunTimeline`, consume proyecciones) ·
`docs/invariants.md` (INV-4, INV-5, AX1) · `knowledge/execution/02-runtime-agent-loop.md` (forma de
`RunStep`) · `knowledge/execution/03-durable-execution.md` (proyección `RunState`) · patrón general de
historia de workflow anidada (padre/hijo dentro de una misma traza — referencia conceptual, **no
verificado en vivo esta sesión**)

**Todos los IDs usados en esta nota (`run-7f3a`, `step-01`, `job-9c2b`, etc.) son sintéticos, inventados
para ilustrar orden de eventos — no corresponden a ningún dato real del sistema, que no existe todavía.**

---

## 1 · Patrón / mecanismo

### 1.1 Tres vocabularios que deben componer, no colisionar

Hoy hay (o se propone en esta carpeta) tres niveles de evento relacionados con la ejecución de un run:

1. `run.*` (esta nota) — nivel del run completo: creado, iniciado, completado, fallido, cancelado.
2. `run.step.*` (nota 02, propuesta) — nivel de paso del agent loop dentro de un run.
3. `capability.job.*` (ya congelado en `knowledge/trust/06` §1.3) — nivel de una invocación de capability
   individual, que normalmente ocurre DENTRO de un `run.step`.

Además, existen **eventos del plano de confianza** que pueden intercalarse en la misma línea de tiempo sin
pertenecer a ninguno de los 3 niveles anteriores: `verification.completed` (produce una `Attestation`,
trust/03) y, potencialmente, eventos de `GuardrailSignal` (trust/04) — estos NO son parte del vocabulario
que esta nota define, pero comparten el mismo stream (§1.2) y deben poder intercalarse en el orden
cronológico sin ambigüedad de tipo.

El riesgo de no definir esto explícitamente es que cada nivel termine con su propio esquema de
correlación incompatible con los otros, rompiendo la línea de tiempo que `RunTimeline`
(`knowledge/trust/18`) ya espera poder construir.

### 1.2 Propuesta: un único `stream_id` por run, correlación por campo en el payload

Patrón de referencia (workflow-history-style, genérico): en vez de streams separados por paso/job —lo que
multiplicaría streams en el `EventStore` y complicaría el catch-up por `global_seq` ya diseñado en
trust/01 §1.3— todos los eventos de un run (`run.*`, `run.step.*`, `capability.job.*`, y los eventos de
confianza intercalados de §1.1) se escriben en el **mismo `stream_id`** (el del run), y la relación
padre/hijo se expresa como un campo en el `payload` (`step_id`, y dentro de un step, `job_id`). Esto
reutiliza el contrato `EventStore` de trust/01 sin cambios — es una convención de uso del puerto, no una
extensión del puerto.

**Esta es la asunción de mayor riesgo de toda la nota — ver §10, marcada explícitamente para que Dylan la
confirme o corrija, ya que él es dueño del puerto `EventStore` y del esquema `events`.**

### 1.3 Máquina de estados textual — `Run`

```
                 ┌──────────┐
   run.created   │          │
  ───────────────▶  CREATED │
                 │          │
                 └────┬─────┘
                      │ run.started
                      ▼
                 ┌──────────┐
                 │          │
                 │ RUNNING  │◀────────────┐
                 │          │             │ (ningún evento propio de Run;
                 └────┬─────┘             │  los run.step.* transcurren
                      │                   │  DENTRO de este estado)
        ┌─────────────┼─────────────┐     │
        │             │             │     │
 run.completed   run.failed   run.cancelled
        │             │             │
        ▼             ▼             ▼
  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │COMPLETED │  │  FAILED  │  │CANCELLED │   (estados terminales —
  └──────────┘  └──────────┘  └──────────┘    ninguna transición sale de aquí)
```

Reglas de la máquina: `CREATED → RUNNING` es la única transición de entrada (vía `run.started`); desde
`RUNNING` hay exactamente 3 transiciones de salida, todas a estados terminales — no hay transición de un
estado terminal a otro (ej. un run `FAILED` no puede pasar a `COMPLETED` después). Un `run.cancelled`
puede ocurrir en cualquier momento mientras el run está `RUNNING` (relacionado con el modo de falla "loop
infinito" de la nota 02 §6 — la cancelación es la salida de emergencia).

### 1.4 Máquina de estados textual — `RunStep` (anidada dentro de `RUNNING`)

```
                    ┌──────────┐
   run.step.started │          │
  ──────────────────▶ PENDING  │───┐
                    │          │   │ (transición inmediata a running
                    └──────────┘   │  en la mayoría de implementaciones;
                                   │  PENDING existe como estado nombrado
                                   ▼  por si hay cola/espera de recursos)
                              ┌──────────┐
                              │          │
                              │ RUNNING  │
                              │          │  (aquí es donde ocurren, si
                              └────┬─────┘   aplica, los capability.job.*
                                   │          — ver §1.5)
                    ┌──────────────┼──────────────┐
                    │              │              │
        run.step.completed  run.step.failed  (ningún run.step.cancelled
                    │              │           propuesto — la cancelación
                    ▼              ▼           es a nivel de Run, §1.3)
              ┌──────────┐  ┌──────────┐
              │COMPLETED │  │  FAILED  │
              └──────────┘  └──────────┘
```

### 1.5 Relación entre los tres niveles — quién contiene a quién

- Un `Run` contiene N `RunStep`s (secuenciales en la forma de POC recomendada por la nota 02, §11).
- Un `RunStep`, mientras está en estado `RUNNING`, puede (no necesariamente) envolver la invocación de una
  o más capabilities — cada una generando su propia secuencia `capability.job.submitted → [progress]* →
completed|failed` (trust/06 §1.3). La pregunta de si un `RunStep` puede envolver MÁS de un
  `capability.job` a la vez sigue abierta (ya señalada en la nota 02 §10) — el diagrama de §1.4 la deja
  implícita (la caja `RUNNING` no especifica cardinalidad).
- Un `RunStep` que NO invoca ninguna capability (ej. un paso de "planificación" puro, nota 02 §1.4) pasa
  por `PENDING → RUNNING → COMPLETED|FAILED` sin ningún `capability.job.*` intercalado.
- Eventos de confianza (`verification.completed`, señales de guardrail) pueden ocurrir dentro de la ventana
  temporal de un `RunStep` sin ser hijos formales de él en el sentido de `step_id` — su relación con el
  paso es contextual (ocurrieron "durante"), no necesariamente declarada en el payload del propio evento
  de verificación (esto depende de cómo trust/03 modele `Attestation.subject.step_id`, ya mencionado como
  posible en trust/03 §1.3 — "la Attestation lleva un subject con step_id opcional").

## 2 · Alternativas consideradas

- **(A) Un único `stream_id` por run, correlación por payload (§1.2, propuesta de esta nota).**
- **(B) Un `stream_id` por cada nivel** (uno para el run, uno por cada step, uno por cada job) — máxima
  granularidad, análogo a como algunos sistemas de logging usan un "trace ID" jerárquico con "span IDs"
  hijos completamente independientes.
- **(C) Un `stream_id` por run, pero con eventos de step/job en streams HIJOS con nombre derivado** (ej.
  `run-7f3a`, `run-7f3a/step-01`) — un punto intermedio entre (A) y (B).

## 3 · Por qué no (descartadas)

- **(B) descartada:** multiplicaría streams sin necesidad — el catch-up SSE de trust/01 §1.3
  (`Last-Event-ID = global_seq`) ya funciona sobre UN cursor global independientemente del número de
  streams, pero reconstruir "todo lo que pasó en este run" requeriría consultar N streams distintos y
  fusionarlos por orden temporal en vez de leer un solo `read_stream(run_id)` — más trabajo en el lado de
  lectura sin beneficio claro identificado.
- **(C) descartada, pero con menor confianza que (B):** un esquema de streams jerárquicos por nombre no es
  algo que trust/01 haya diseñado — introducir esa convención unilateralmente sería una extensión de facto
  del puerto `EventStore` sin la revisión de Dylan, algo que esta nota explícitamente evita (ver §10, es la
  pregunta de mayor prioridad de coordinación de toda la carpeta según el `README.md`).

## 4 · Decisión

| Referencia                                                                             | Decisión      | Racional                                                                                                                                                                 |
| -------------------------------------------------------------------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Un único `stream_id` por run, correlación por `step_id`/`job_id` en payload (opción A) | **portar**    | Evita multiplicar streams en el `EventStore` ya congelado (trust/01); reutiliza `global_seq` para catch-up sin cambios — **pendiente de confirmación de Dylan, ver §10** |
| Vocabulario `run.created/started/completed/failed/cancelled`                           | **integrar**  | Composición directa con `capability.job.*` (trust/06) y `run.step.*` (nota 02) — mismo patrón de eventos de ciclo de vida                                                |
| `run.created` como punto de estampado de `actor_id`                                    | **portar**    | Reutiliza directamente el mecanismo de AX1 ya diseñado en trust/08, sin proponer uno nuevo                                                                               |
| Streams separados por paso o por job (opción B)                                        | **descartar** | Multiplicaría streams sin necesidad, complicando el catch-up SSE (`Last-Event-ID` = `global_seq`, trust/01 §1.3)                                                         |
| Streams hijos con nombre derivado (opción C)                                           | **descartar** | Extensión de facto del puerto `EventStore` sin revisión de Dylan                                                                                                         |

## 5 · Tradeoffs

| Eje                                                     | Opción A (elegida)                                                  | Opción B (streams por nivel)                                                                                            | Opción C (streams jerárquicos)                        |
| ------------------------------------------------------- | ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| Complejidad de lectura de "todo el run"                 | Baja — un solo `read_stream(run_id)`                                | Alta — fusionar N streams                                                                                               | Media — requiere conocer la convención de nombres     |
| Presión sobre `global_seq`/catch-up                     | Ninguna nueva                                                       | Cada stream nuevo agrega entradas al cursor global, sin cambiar su semántica pero aumentando volumen de streams activos | Similar a B                                           |
| Coherencia con el diseño ya congelado de trust/01       | Directa — cero cambio de convención                                 | Requiere que trust/01 explique semántica de streams múltiples por unidad lógica (no confirmado que la tenga)            | Requiere una convención nueva no presente en trust/01 |
| Aislamiento de un sub-tramo (ej. cancelar solo un step) | Bajo — todo comparte un stream, aislar requiere filtrar por payload | Alto — cada stream es independiente                                                                                     | Medio                                                 |

## 6 · Modos de falla

- **Confusión de correlación si `step_id`/`job_id` no son únicos dentro del stream del run.** Si dos
  `RunStep`s distintos generan el mismo `step_id` por error de implementación (ej. un contador que se
  reinicia), la reconstrucción de la línea de tiempo (§1.5) mezclaría eventos de pasos distintos bajo la
  misma identidad — un riesgo de corrección, no solo de presentación.
- **Eventos de verificación sin `step_id` cuando deberían tenerlo.** Si `Attestation.subject.step_id`
  (trust/03 §1.3, ya mencionado como opcional) se omite en la práctica, la relación "esta verificación
  correspondía a este paso" se pierde — el Studio (trust/18) no podría anclar el badge de verificación al
  paso correcto en `StepInspector`.
- **Ambigüedad de `run.cancelled` a mitad de un `RunStep` en curso.** Si el evento de cancelación del run
  se escribe mientras un `RunStep` sigue en estado `RUNNING` (§1.4), la máquina de estados de `RunStep` no
  tiene una transición formal a un estado terminal propio — queda "colgado" en `RUNNING` para siempre en
  términos de su propia máquina de estados, aunque el `Run` que lo contiene ya esté `CANCELLED`. Este es un
  caso no resuelto de la interacción entre las dos máquinas de estado de §1.3/§1.4.

## 7 · Licencias

| Pieza                                                       | Licencia      | Verificado                                                     |
| ----------------------------------------------------------- | ------------- | -------------------------------------------------------------- |
| Patrón de historia de workflow anidada (referencia general) | no verificado | **no verificado en vivo esta sesión** — no se propone integrar |

No se propone ninguna dependencia nueva en esta nota.

## 8 · Impacto en contrato

1. Vocabulario nuevo propuesto: `run.created {run_id, actor_id, domain_id}`, `run.started`,
   `run.completed {output_digest?}`, `run.failed {error_kind}`, `run.cancelled {reason}` — todos como
   filas del mismo `stream_id` = `run_id` (o un id derivado, a confirmar — ver §10).
2. Ningún campo nuevo se propone para el puerto `EventStore` en sí (trust/01) — esta nota consume la forma
   ya congelada (`append(stream_id, type, actor_id, domain_id, payload, expected_seq)`).
3. Requisito derivado para el Studio (frontera, `knowledge/trust/18`): cualquier vista `RunTimeline` que
   ya asuma un `stream_id` por run debe poder distinguir `run.*` de `run.step.*` de `capability.job.*` y de
   eventos de confianza intercalados (§1.1) únicamente por el campo `type` del evento — no se introduce
   ninguna estructura de payload incompatible con lo que esa nota ya especificó, hasta donde esta nota pudo
   revisar (no confirmado con Dylan).
4. `docs/contract-freeze.md` §9 (atribuido a nota 07) fija la regla "ningún payload de resultado sin su
   bloque `verification`" para el contrato SSE Studio↔Engine — aplica igual a `run.completed` si ese
   evento carga un resultado; este vocabulario no la redefine, la hereda. (`knowledge/trust/07` en sí no
   fue leído directamente esta sesión — esta cita viene del resumen en contract-freeze.md.)
5. La máquina de estados de §1.3/§1.4 es la base para cualquier validación futura de "transición válida"
   (ej. un test que rechace un `run.completed` después de un `run.failed` ya escrito) — no se implementa
   aquí, solo se documenta la forma que tal validación debería seguir.

## 9 · Implicaciones de test / spec

- **Test de transición válida de `Run`:** dado un stream de prueba, verificar que la secuencia de eventos
  `run.*` respeta la máquina de estados de §1.3 (ej. rechazar/detectar una secuencia donde
  `run.completed` aparece después de `run.failed`).
- **Test de unicidad de `step_id`/`job_id` dentro de un stream:** cierra, a nivel de test, el modo de falla
  de correlación (§6, primer punto).
- **Test de ejemplo de orden de eventos (§11):** el ejemplo con IDs sintéticos de §11 puede convertirse
  directamente en un fixture de test — una secuencia de eventos esperada que cualquier implementación real
  del runtime/gateway debería producir para el mismo escenario.
- Ninguno de estos tests existe hoy — señalados como trabajo futuro derivado de este diseño.

## 10 · Supuestos y preguntas abiertas

**Supuestos:**

- `run_id` puede usarse directamente como `stream_id` (relación 1:1) — no confirmado contra el esquema SQL
  real de `events` (trust/01), que no especifica de dónde sale el valor de `stream_id` en la práctica.
  **Pregunta directa para Dylan: ¿`stream_id` en el esquema real de `events` tiene alguna restricción de
  formato o unicidad que choque con usar un `run_id` (ej. UUID) directamente como su valor?**
- Cancelación (`run.cancelled`) es siempre un evento explícito disparado por una decisión de un actor, no
  un timeout automático — si existe un mecanismo de timeout, necesitaría su propio `actor_id` sintético de
  la forma `service:<nombre>` (ej. `service:runtime`, patrón ya usado en trust/08 §1.4).

**Preguntas abiertas — candidatas a revisión conjunta con Dylan (toca el puerto `EventStore`, su plano —
esta es, según el `README.md` de la carpeta, la pregunta de mayor prioridad de bloqueo de toda la
investigación):**

- ¿Es correcto asumir un único `stream_id` por run (§1.2), o `knowledge/trust/01` ya tiene una convención
  distinta de qué constituye un "stream" que esta nota no vio? Esta es la pregunta más importante de la
  nota — el resto del diseño (incluyendo las máquinas de estado de §1.3/§1.4, que asumen lectura de un solo
  stream) depende de la respuesta.
- ¿Puede un `capability.job` disparado dentro de un `run.step` pertenecer a MÁS de un run a la vez (ej.
  una capability compartida invocada por dos runs concurrentes)? Si sí, la correlación por `stream_id`
  único de esta nota no alcanza y hace falta un `run_id` explícito también en el payload del job, no solo
  el `stream_id` que ya lo implica.
- ¿`RunTimeline` (trust/18) ya asume una forma de correlación distinta a la propuesta aquí? Esta nota no
  pudo confirmarlo — se marca como riesgo de incompatibilidad con el Studio hasta que se revise.
- ¿Cómo se resuelve el caso de §6 (tercer modo de falla) de un `RunStep` que queda `RUNNING` cuando el
  `Run` que lo contiene pasa a `CANCELLED`? No resuelto — candidato a definir junto con la máquina de
  estados si se valida en código.

## 11 · Ejemplo de orden de eventos esperado (IDs sintéticos)

Escenario de ejemplo: un run con 2 `RunStep`s, el segundo de los cuales invoca una capability.
**Todos los valores (`run-7f3a`, `step-01`, `step-02`, `job-9c2b`, `cap-echo`) son sintéticos e inventados
para este ejemplo — no representan datos reales del sistema.**

```
seq  type                      payload (resumido)
---  ------------------------  -----------------------------------------------
1    run.created               {run_id: "run-7f3a", actor_id: "user:steven", domain_id: "poc"}
2    run.started               {run_id: "run-7f3a"}
3    run.step.started          {run_id: "run-7f3a", step_id: "step-01", kind: "plan"}
4    run.step.completed        {run_id: "run-7f3a", step_id: "step-01"}
5    run.step.started          {run_id: "run-7f3a", step_id: "step-02", kind: "invoke_capability"}
6    capability.job.submitted  {run_id: "run-7f3a", step_id: "step-02", job_id: "job-9c2b", capability_id: "cap-echo"}
7    capability.job.completed  {run_id: "run-7f3a", step_id: "step-02", job_id: "job-9c2b", output_digest: "sha256:..."}
8    run.step.completed        {run_id: "run-7f3a", step_id: "step-02"}
9    run.completed             {run_id: "run-7f3a", output_digest: "sha256:..."}
```

Puntos a notar del ejemplo: (a) `step-01` (un paso de planificación puro, nota 02 §1.4) nunca genera un
`capability.job.*` — pasa directo de `started` a `completed`; (b) `step-02` SÍ envuelve un
`capability.job`, y el orden es estrictamente `run.step.started → capability.job.submitted →
capability.job.completed → run.step.completed` — el job siempre transcurre DENTRO de la ventana de su
step contenedor, nunca antes ni después; (c) todos los eventos comparten `run_id: "run-7f3a"`, consistente
con el supuesto de un único `stream_id` por run (§1.2) — si Dylan corrige ese supuesto (§10), este ejemplo
tendría que rehacerse con streams distintos por nivel.

## 12 · Reconciliación contra la base lógica (`docs/invariants.md`)

- **INV-5 (event log append-only):** INTACTO — no se propone ningún mecanismo de escritura fuera del
  puerto `EventStore` ya existente; el vocabulario nuevo son solo valores nuevos de `type`.
- **AX1 (actor_id obligatorio):** REFORZADO — `run.created` da un punto único y temprano donde estampar
  `actor_id` para todo el run, consistente con la ruta del flip AX1 ya trazada en trust/08. El ejemplo de
  §11 lo ilustra explícitamente en el primer evento.
- **INV-4 (override registrado antes de ejecutar):** relevante para `run.cancelled` — una cancelación que
  interrumpe pasos en curso debe registrarse ANTES de que el runtime detenga efectivamente la ejecución,
  no después. El modo de falla de §6 (tercer punto, `RunStep` colgado en `RUNNING`) es precisamente un
  caso donde este requisito es difícil de cumplir limpiamente sin una transición formal definida — señalado
  como requisito de diseño para quien implemente `run.cancelled`, no resuelto en detalle aquí.
- **Ninguna referencia contradice la base lógica.** El patrón de correlación padre/hijo por payload es una
  convención de uso sobre un puerto ya congelado, no una extensión de la base lógica ni de INV-5 — pero
  esta nota reconoce explícitamente (§10) que la convención en sí no ha sido confirmada por el dueño del
  puerto.
