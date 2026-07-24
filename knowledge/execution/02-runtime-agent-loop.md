# Nota 02 — El runtime como máquina de estados explícita: forma del agent loop

**Ítem del plan:** plano de ejecución (Steven) — dar forma de dato al ciclo de ejecución detrás de
`engine/src/blite/runtime/registry.py`, hoy solo un stub de registro sin loop de ejecución.
**Fecha:** 2026-07-10 · **Estado:** insumo para contract freeze — **parcialmente cerrada** (S-E 2026-07-18):
(1) la relación `RunStep`↔`capability.job` quedó confirmada **1:1 en Fase 1** (freeze §3) — cierra la
pregunta abierta de §10; (2) `max_steps` a nivel de `Run` es **obligatorio**, viaja en el payload de
`run.created` (freeze) — cierra el mecanismo de límite del modo de falla "loop infinito" (§6/§10). Sigue
**abierta** la pregunta de en qué punto se necesitaría ReAct-style/plan-execute (sin evidencia de producto
todavía). El proyector de `RunStep`/`RunRow` que esta nota anticipa (§1.3) es ahora el seed activo
`tests/seeds/test_seed_ejecucion_runs_projection.py` [S-G Etapa 0] — sin implementar todavía.
**Fuentes:** `docs/invariants.md` (INV-2, INV-5, INV-4) · `engine/src/blite/runtime/registry.py` ·
`knowledge/trust/06-protocolos-capability-mcp-a2a.md` §1.3 (vocabulario `capability.job.*`) ·
`knowledge/execution/07-run-lifecycle-events.md` (vocabulario `run.*`) · patrones generales de loop de
agente (referencia conceptual, **no verificados en vivo esta sesión**): pipeline fijo (secuencia estática
de pasos), ReAct (Yao et al. 2022 — reason+act intercalado, referenciado por nombre únicamente, no leído
esta sesión), plan-execute (plan completo primero, luego ejecución), y loops jerárquicos/sub-agente
(orquestador que delega en sub-loops)

---

## 1 · Patrón / mecanismo

### 1.1 Un run como secuencia de pasos, no una función que corre de un tirón

El riesgo de un "agent loop" implementado como un solo bucle `while` con estado en variables locales es
que no sobrevive un reinicio del proceso y no es observable desde afuera. El patrón de referencia
(genérico, visto en runtimes de agentes y en motores de workflow-as-code) es modelar el loop como una
secuencia de **pasos discretos y nombrados**, cada uno con entrada/salida serializable, en vez de estado
implícito en el stack de llamadas. Esto es un patrón de forma, no una librería — no se propone integrar
ningún framework de agentes externo.

### 1.2 Cuatro formas de loop — comparadas concretamente

| Forma                                                                                                                                                             | Cómo decide el siguiente paso                                                                                                               | Encaja con replay (nota 03)                                                                                                                                                      | Complejidad de implementación | Cuándo tendría sentido                                                                                                                                    |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Pipeline fijo** — secuencia estática de N pasos conocidos de antemano (ej. "resolver identidad → elegir capability → invocar → listo")                          | No decide — el orden está harcodeado en el código del loop                                                                                  | Trivial — replay = re-ejecutar los mismos N pasos en el mismo orden                                                                                                              | Muy baja                      | Cuando el flujo del run es siempre el mismo (ej. una única capability invocada una vez)                                                                   |
| **ReAct-style** (referencia conceptual — razonar, luego actuar, observar, repetir)                                                                                | Un modelo decide en cada iteración qué acción tomar según la observación anterior                                                           | Media — cada decisión del modelo debe registrarse como parte del `RunStep` para ser replay-able (si no se registra el input exacto dado al modelo, el replay no es determinista) | Media                         | Cuando el número y orden de pasos no se conoce de antemano y depende del resultado de cada paso                                                           |
| **Plan-execute** — un paso de "planificación" produce una lista completa de pasos futuros, luego se ejecutan en orden (con posible replanificación si algo falla) | El plan se decide una vez (o se recalcula explícitamente), no en cada iteración                                                             | Alta — el plan en sí es un artefacto serializable (`{plan_id, steps: [...]}`), fácil de guardar como evento y reconstruir                                                        | Media-alta                    | Cuando el costo de planificar es alto y se prefiere pagarlo una vez, o cuando se necesita mostrar el plan al usuario antes de ejecutar (auditoría previa) |
| **Jerárquico / sub-agente** — un loop orquestador delega sub-tramos completos a loops hijos (cada uno con su propia secuencia de `RunStep`)                       | El orquestador decide QUÉ sub-loop invocar; cada sub-loop decide sus propios pasos internamente (con cualquiera de las 3 formas anteriores) | Depende del sub-loop; agrega una capa de anidamiento a la correlación de eventos (relevante para nota 07 — ¿un sub-run es un `run_id` distinto o un `step_id` anidado?)          | Alta                          | Cuando distintos sub-tramos necesitan aislamiento (ej. límites de permiso distintos, o quieren poder verificarse/cancelarse independientemente)           |

### 1.3 Un `RunStep` como unidad mínima, y qué significa "serializable y replay-friendly" en concreto

Cada iteración del loop (cualquiera de las 4 formas de §1.2 se reduce, en el evento log, a una secuencia
de estos) se modela como un `RunStep`: `{step_id, run_id, kind, input_digest, output_digest?, status}`.
Para que sea replay-friendly de verdad (no solo "serializable" en el sentido superficial de "se puede
convertir a JSON"), un `RunStep` debe cumplir:

- **El input debe ser un digest de algo que se pueda recuperar íntegramente**, no un resumen con pérdida.
  Si el paso invoca un modelo (vía nota 05), el `input_digest` debe corresponder a un prompt/contexto
  reconstruible byte a byte — de lo contrario el replay reconstruye el ORDEN de los pasos pero no puede
  verificar que el CONTENIDO fue el mismo (relevante para el modo de falla "replay no determinista", §6).
- **El `kind` debe ser suficiente para saber, sin ejecutar nada, qué tipo de efecto tuvo el paso** —
  esto es lo que conecta con `side_effects` del `CapabilityManifest` v2 (trust/06, consumido en la nota 03) para decidir si un replay puede simplemente "saltarse" un paso ya completado (`pure`,
  seguro de re-derivar) o debe tratarlo como un hecho consumado que no se repite (`irreversible-external`).
- **El `status` debe ser un valor de un conjunto cerrado** (ej. `pending|running|completed|failed`), no
  texto libre — un replay que lee `status` para decidir "¿retomo desde aquí?" necesita poder hacer un
  `match` exhaustivo, no interpretar prosa.

### 1.4 Relación con el vocabulario de eventos de capability (trust/06) y run (nota 07)

`knowledge/trust/06` ya congeló el vocabulario `capability.job.submitted/progress/completed/failed` para
una invocación de capability individual. Un `RunStep` del runtime normalmente ENVUELVE una invocación de
capability, pero no es necesariamente 1:1 — un paso de "planificación" (elegir qué capability llamar, o
en la forma plan-execute, producir el plan completo) no dispara ningún evento `capability.job.*`. Este
runtime necesita su propio vocabulario `run.step.*` (nota 07) que sea distinto pero componible con
`capability.job.*`, no un reemplazo.

## 2 · Alternativas consideradas

Las 4 formas de §1.2 son las alternativas centrales de esta nota. Además:

- **(E) Loop sin pasos discretos, estado en memoria/stack de llamadas.** El "estado actual" (§1.1) —
  técnicamente ya es una opción disponible, es lo que ocurre si no se diseña nada explícito.
- **(F) Delegar el loop completo a un framework externo** (referencia conceptual — la forma de un grafo
  de estados tipo LangGraph, o un framework de agentes con su propio runtime de ejecución).

## 3 · Por qué no (descartadas)

- **(E) descartada:** ya está cubierta como el riesgo central de §1.1 — sin pasos discretos, ni
  durabilidad (nota 03) ni observabilidad son posibles sin reescribir el loop.
- **(F) descartada para Fase 1:** adoptar el runtime de ejecución de un framework externo acopla el motor
  de pasos del engine a las convenciones de ese framework (su propio formato de estado, su propio
  mecanismo de checkpointing) — en tensión directa con ADR-008 (mantener el engine genérico y no acoplado
  a librerías de terceros para su núcleo) y con INV-2 (si el framework decide internamente cómo y cuándo
  verificar, eso podría colisionar con que la verificación nunca sea un modelo). Además, ningún framework
  de este tipo fue verificado en vivo esta sesión — su licencia, madurez y modelo de checkpointing son
  desconocidos, no solo no-elegidos.
- **Plan-execute descartada como forma ÚNICA para Fase 1** (aunque no se descarta como forma futura): el
  costo de implementar re-planificación cuando un paso falla es mayor que lo que un POC necesita
  demostrar — ver recomendación de POC (§11).
- **Jerárquico/sub-agente descartada para Fase 1:** el anidamiento de runs complica directamente la
  pregunta abierta de la nota 07 (§5, "¿un único `stream_id` por run?") — resolver jerarquía y
  correlación de eventos a la vez es más de lo que esta pasada de investigación puede comprometer.

## 4 · Decisión

| Referencia                                                                                   | Decisión                                                | Racional                                                                                                                                                      |
| -------------------------------------------------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Loop como máquina de estados de pasos explícitos (patrón general, base común a las 4 formas) | **inspirar**                                            | Informa la FORMA (pasos serializables, nombrados) — no se adopta ningún motor concreto                                                                        |
| Pipeline fijo (forma más simple, §1.2) como forma inicial de implementación                  | **portar**                                              | Mínimo riesgo, mínimo código, valida el mecanismo de `RunStep` sin comprometerse a lógica de decisión dinámica                                                |
| ReAct-style / plan-execute / jerárquico (referencia conceptual)                              | **inspirar** (como dirección futura, no implementación) | Formas de razonamiento sobre PRÓXIMO paso — relevantes cuando el flujo deje de ser fijo, no en Fase 1                                                         |
| Adoptar un framework de agentes externo como dependencia del runtime                         | **descartar**                                           | Fuera de alcance de Fase 1; el engine se mantiene genérico (ADR-008) y sin dependencia nueva pesada — pendiente de verificación de licencia si se reconsidera |
| Vocabulario `run.step.*` compuesto sobre `capability.job.*` (trust/06)                       | **portar**                                              | Reutiliza la forma ya congelada para jobs de capability, evita vocabulario duplicado                                                                          |

## 5 · Tradeoffs

| Eje                                 | Pipeline fijo                       | ReAct-style                                                          | Plan-execute                                                   | Jerárquico           |
| ----------------------------------- | ----------------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------- | -------------------- |
| Predictibilidad del run             | Alta                                | Baja (decisión por iteración)                                        | Media (el plan es visible antes de ejecutar)                   | Depende del sub-loop |
| Costo de implementación             | Bajo                                | Medio-alto (requiere lógica de decisión + registro de cada decisión) | Medio-alto (requiere representación de plan + replanificación) | Alto                 |
| Auditabilidad previa a ejecución    | Alta (se sabe el flujo de antemano) | Baja (no hay "plan" que auditar antes de correr)                     | Alta (el plan es auditable antes de ejecutar)                  | Depende              |
| Adecuado para runs largos/complejos | Bajo                                | Alto                                                                 | Alto                                                           | Alto                 |
| Riesgo de loop infinito (§6)        | Ninguno (N pasos fijos)             | Alto si no hay límite explícito                                      | Bajo (el plan tiene longitud fija una vez generado)            | Depende del sub-loop |

## 6 · Modos de falla

- **Loop infinito.** En cualquier forma donde el "siguiente paso" se decide dinámicamente (ReAct-style,
  y en menor medida jerárquico), sin un límite explícito de pasos o un criterio de terminación
  verificable, el loop puede no converger nunca — consumiendo recursos indefinidamente y, en el peor
  caso, generando facturación/costo sin límite si cada paso invoca un modelo (nota 05). **Mitigación no
  implementada:** un `max_steps` obligatorio a nivel de `Run` (relacionado con la pregunta abierta de la
  nota 07 sobre `run.cancelled`), y/o un timeout de wall-clock.
- **Estado oculto.** Si el loop retiene información relevante en variables Python locales que NO se
  serializa en ningún `RunStep` (ej. un acumulador que solo vive en el stack de llamadas), un replay
  (nota 03) reconstruye los pasos pero no ese estado — produciendo un resultado distinto al original de
  forma silenciosa. Este es el motivo central detrás del requisito de §1.3: TODO lo que afecta la
  decisión del siguiente paso debe estar en el `input_digest` de algún `RunStep`, no en memoria no
  registrada.
- **Llamada a tool no registrada (`unlogged tool call`).** Si una capability se invoca sin pasar por el
  Registry (nota 04) — ej. un atajo de código que la importa directamente para "ahorrar una vuelta" — no
  se genera ningún `capability.job.*` ni `run.step.*`, rompiendo tanto la propiedad de que "toda acción
  emite un evento" (PR1, referenciado en trust/01 §5) como la posibilidad de replay: ese efecto queda
  invisible para cualquier reconstrucción futura del run.
- **Replay no determinista.** Incluso con pasos bien registrados, si el `input_digest` de un paso que
  invoca un modelo no captura TODO lo que influyó en la respuesta (ej. un parámetro de temperatura no
  registrado, o un contexto que incluye la hora actual del sistema), reproducir el run desde el log puede
  producir una secuencia de pasos distinta a la original — el replay converge en estructura (mismos
  `step_id` en el mismo orden) pero no necesariamente en contenido. Esto es una limitación conocida y
  general de cualquier sistema que mezcle componentes no deterministas (modelos) con event sourcing — no
  es específico de este diseño, pero el diseño debe reconocerlo explícitamente en vez de asumir replay
  perfecto.

## 7 · Licencias

| Pieza                                                                                             | Licencia                | Verificado                                                                             |
| ------------------------------------------------------------------------------------------------- | ----------------------- | -------------------------------------------------------------------------------------- |
| Patrón de loop como máquina de estados                                                            | N/A — patrón, no código | conocimiento general, **no verificado en vivo esta sesión**                            |
| ReAct (nombre de patrón, Yao et al.), frameworks de agentes/workflows mencionados como referencia | no verificado           | **no verificado en vivo esta sesión** — no se propone integrar ningún paquete concreto |

No se propone ninguna dependencia nueva en esta nota.

## 8 · Impacto en contrato

1. Propuesta: `RunStep` como forma de dato (§1.3) — no reemplaza `Event`, se transporta COMO payload de
   eventos `run.step.*` (nota 07) sobre el `EventStore` ya existente (trust/01), sin nuevo almacén.
2. El runtime despacha a capabilities exclusivamente vía el Registry (nota 04) — nunca importa
   `blite_cap_*` directamente (ADR-008 ya lo exige a nivel de import-linter, esta nota no lo cambia, solo
   lo hereda como restricción de diseño del loop). Este requisito es también la mitigación directa del
   modo de falla "llamada a tool no registrada" (§6).
3. El runtime no debe convertirse en un segundo lugar donde se decida verificación o egreso — su única
   responsabilidad es secuenciar pasos y registrar eventos; cualquier decisión de "¿este resultado es
   válido?" se delega, no se resuelve dentro del loop.
4. Cualquiera de las 4 formas de §1.2 debe producir `RunStep`s que cumplan los 3 requisitos de
   serializabilidad de §1.3 — este requisito es transversal a la forma elegida, no específico del
   pipeline fijo.

## 9 · Implicaciones de test / spec

- **Test de "todo paso es un evento":** para cualquier implementación de loop, un test de integración que
  ejecute un run de prueba contra un `EventStore` en memoria/test y verifique que el número de
  `run.step.*` emitidos corresponde exactamente al número de decisiones tomadas por el loop — cierra
  (parcialmente, a nivel de test) el modo de falla de "llamada no registrada".
- **Test de límite de pasos:** para formas dinámicas (ReAct-style), un test que fuerce un escenario donde
  el criterio de terminación nunca se cumple y verifique que el loop se corta en `max_steps` en vez de
  colgarse — cierra el modo de falla "loop infinito".
- **Test de replay-igualdad estructural:** dado un `run_id` con eventos ya escritos, reconstruir la
  secuencia de `RunStep`s por replay y verificar que el ORDEN y los `step_id` coinciden con lo esperado —
  no puede garantizar igualdad de CONTENIDO si hay modelos involucrados (ver §6), pero sí de estructura.
- Ninguno de estos tests existe hoy — señalados como trabajo futuro derivado de este diseño.

## 10 · Supuestos y preguntas abiertas

**Supuestos:**

- Un run tiene un único loop de pasos secuenciales en Fase 1 (no ramificación paralela de pasos ni grafo
  de dependencias, ni forma jerárquica) — no se investigó si esto es suficiente para los casos de uso
  reales del equipo.
- El runtime corre in-process, igual que el supuesto de la nota 01 sobre el gateway.

**Preguntas abiertas:**

- ¿Un `RunStep` puede disparar más de un `capability.job` (ej. llamadas en paralelo dentro de un mismo
  paso), o la relación es siempre 1:1? Afecta directamente el diseño de vocabulario de la nota 07.
- ¿Quién decide cuándo el loop termina — una condición explícita del step, un límite de pasos, o ambos?
  Relacionado directamente con el modo de falla "loop infinito" (§6) — no se investigó ningún mecanismo
  concreto de límite/timeout en esta pasada.
- ¿El runtime retiene estado en memoria entre pasos, o reconstruye todo desde el event log en cada paso
  (relevante para durable execution, nota 03)? Esta nota no lo resuelve, lo señala como dependencia directa
  de la nota 03.
- ¿En qué punto (si alguno) del roadmap se necesita ReAct-style o plan-execute en vez del pipeline fijo?
  No hay evidencia de producto real que lo determine todavía.

## 11 · Recomendación mínima de POC

**El pipeline fijo (§1.2, primera fila) es la recomendación explícita para el POC** — no ReAct-style, no
plan-execute, no jerárquico. Justificación: el POC necesita validar 3 cosas independientes de la forma de
decisión de "siguiente paso" — (1) que un `RunStep` se puede serializar y transportar como payload de
evento, (2) que el runtime despacha exclusivamente vía el Registry (nota 04), (3) que un replay reconstruye
la misma secuencia de pasos (nota 03). Ninguna de las tres necesita razonamiento dinámico. Un pipeline fijo
de 2-3 pasos harcodeados (ej. "resolver qué capability invocar" → "invocarla" → "reportar resultado") ya
ejercita el contrato de `RunStep` de punta a punta con la complejidad mínima posible. Las formas
dinámicas (ReAct-style/plan-execute) se dejan para cuando exista un caso de uso real que las requiera.

## 12 · Dirección later / producción

Fuera de alcance de esta nota, como dirección conceptual: si el pipeline fijo resulta insuficiente (un
caso de uso real necesita que el número/orden de pasos dependa del resultado de pasos anteriores),
ReAct-style es la extensión más directa — mantiene la unidad `RunStep` sin cambios, solo cambia CÓMO se
decide el siguiente `kind` de paso. Plan-execute sería la elección si el equipo prioriza auditabilidad
previa a ejecución (mostrar el plan completo antes de correr, valioso para casos de alto riesgo/rung 7).
Jerárquico/sub-agente queda como la extensión de mayor costo, condicionada a resolver primero la pregunta
abierta de correlación de streams de la nota 07. Ninguna de estas rutas se compromete aquí — todas
requieren revisión conjunta antes de implementarse, dado que tocan vocabulario de eventos compartido con
Dylan.

## 13 · Reconciliación contra la base lógica (`docs/invariants.md`)

- **INV-2 (el verificador nunca es un modelo):** INTACTO — el runtime explícitamente no verifica, en
  ninguna de las 4 formas comparadas; el diseño propuesto no le da al loop ninguna vía para producir un
  `Attestation`.
- **INV-5 (event log append-only):** INTACTO — `RunStep` viaja como payload de eventos vía el puerto
  `EventStore` ya existente; no se propone ningún almacén nuevo ni escritura fuera de ese puerto. El modo
  de falla "estado oculto" (§6) es precisamente un riesgo de VIOLAR esta garantía en la práctica si el
  loop no se disciplina — la nota lo marca como riesgo activo, no como brecha ya resuelta.
- **INV-4 (override registrado antes de ejecutar):** el diseño de pasos discretos hace más fácil
  cumplirlo (cada paso es un punto natural para registrar antes de actuar), pero esta nota no define el
  mecanismo exacto — queda como trabajo de diseño posterior, no como brecha conocida contra el invariante.
- **Ninguna referencia contradice la base lógica.** Los patrones de loop mencionados (ReAct, plan-execute,
  jerárquico, y los frameworks de agentes/workflows citados como referencia) son solo inspiración de
  forma; no se adopta código ni licencia de ninguno.
