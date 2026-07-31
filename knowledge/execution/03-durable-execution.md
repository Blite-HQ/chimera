# Nota 03 — Durabilidad por replay del event log, no un motor de workflows nuevo

**Ítem del plan:** plano de ejecución (Steven) — cómo un run sobrevive un reinicio del proceso o un job de
larga duración, apoyándose en lo que el plano de confianza ya congeló para el event log.
**Fecha:** 2026-07-10 · **Estado:** incorporada al contract freeze (S-E, con el endurecimiento del reintento — addendum S-F en §1.4)
**Fuentes:** `knowledge/trust/01-event-sourcing-postgres.md` (especialmente §1.4, proyecciones
regenerables por replay) · `knowledge/trust/06-protocolos-capability-mcp-a2a.md` §4 (campo
`side_effects` del `CapabilityManifest` v2) · `docs/invariants.md` (INV-5, INV-4) ·
`knowledge/execution/02-runtime-agent-loop.md` (forma de `RunStep`) · referencias conceptuales de motores
de ejecución durable, **ninguna verificada en vivo esta sesión**: replay simple sobre Postgres (lo que ya
adopta trust/01), checkpointing tipo LangGraph (guardar snapshots de estado de grafo en cada superstep),
Temporal/Cadence (motor de workflows dedicado con replay de "historia" contra código determinista), DBOS
(runtime que persiste el estado de la función/paso directamente en Postgres, sin motor separado), y colas
de jobs (ej. patrón genérico de cola + workers, sin nombrar un producto concreto)

---

> **[S3 · 2026-07-30] Nota de drift:** la proyección `RunState` que esta nota
> propone (§8.2, §9, §11) no existe con ese nombre — lo real es la proyección de
> runs por replay puro: `project_runs()` → `RunRow` (tabla `runs_projection`) en
> `engine/src/blite/runtime/projection.py`, exactamente el mecanismo que esta nota
> eligió (replay del log, cero estado lateral, idempotente). Las menciones
> «rung 7» del cuerpo quedaron traducidas inline: la escalera quedó supersedida (freeze §4) —
> el escalamiento a humano es hoy la clase `human_expert`, sin número de escalón.

## 1 · Patrón / mecanismo

### 1.1 La pregunta que responde esta nota

Si el proceso del engine muere a mitad de un run — ¿qué hace falta para retomarlo sin perder trabajo ni
duplicar efectos externos? Esta nota compara 5 familias de respuesta, no solo dos.

### 1.2 Cinco opciones de durabilidad — comparadas concretamente

| Opción                                                                                                                                                                       | Dónde vive el estado de ejecución                                                                                          | Qué agrega al stack                                                                                                           | Madurez del patrón (conceptual)                                                                                                                                    | Costo de adoptarlo ahora                                                                                                                |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------- |
| **Replay simple sobre el event log de Postgres** (ya lo que trust/01 adopta)                                                                                                 | El mismo `EventStore` (append-only) — el estado se DERIVA leyendo eventos, no se persiste aparte                           | Nada — reutiliza el puerto `EventStore` ya congelado (trust/01)                                                               | Patrón de event sourcing clásico, ya elegido por el proyecto para otros fines                                                                                      | Ninguno — cero componente nuevo                                                                                                         |
| **Checkpointing tipo LangGraph** (referencia conceptual — guardar un snapshot del estado del grafo de ejecución en cada "superstep")                                         | Un almacén de checkpoints separado del event log (o el mismo Postgres, pero con una tabla/esquema distinto al de `events`) | Un segundo modelo de persistencia paralelo al event log — riesgo de tener DOS fuentes de verdad sobre "en qué paso estábamos" | Framework específico de grafos de agentes — no verificado en vivo, licencia desconocida esta sesión                                                                | Medio-alto — requeriría reconciliar su modelo de checkpoint con el de `RunStep`/`EventStore` ya propuesto                               |
| **Temporal/Cadence-style** (motor de workflows dedicado; referencia conceptual — la "historia" del workflow se replay-ea contra código determinista para reconstruir estado) | Un servicio/cluster separado (el motor de workflows), con su propio almacén de historia                                    | Un componente de infraestructura entero: el motor de workflows, sus workers, su propio protocolo de comunicación              | Patrón maduro en la industria para orquestación de largo plazo — pero como PRODUCTO externo, no como patrón que se pueda "portar" sin adoptar el producto          | Alto — nuevo servicio, nueva dependencia operativa, curva de aprendizaje del equipo                                                     |
| **DBOS-style** (referencia conceptual — runtime que persiste el estado de cada función/paso directamente en Postgres mediante decoradores/anotaciones, sin motor separado)   | Postgres, pero en tablas gestionadas por ese runtime, no necesariamente el mismo esquema `events`                          | Una dependencia de runtime que envuelve las funciones Python — modelo de programación distinto (decoradores)                  | Más liviano que Temporal por diseño (según su propia propuesta de valor, no verificado en vivo), pero sigue siendo un componente externo con su propio modelo      | Medio — no requiere un servicio aparte, pero sí adoptar su modelo de programación en el runtime                                         |
| **Colas de jobs** (patrón genérico de cola + workers, sin producto nombrado)                                                                                                 | Un broker de cola (mensaje) + estado de progreso en donde el worker decida persistirlo                                     | Un broker nuevo (ej. algo tipo Redis/RabbitMQ conceptual) si no se reutiliza Postgres como cola                               | Patrón muy establecido para trabajo asíncrono simple, MENOS adecuado para "secuencias de pasos con estado acumulado" que para "unidades de trabajo independientes" | Medio — encaja bien para `capability.job.*` individuales (trust/06), menos bien para la noción de `Run` completo con pasos dependientes |

### 1.3 Por qué "replay simple sobre Postgres" es la opción de Fase 1, no las otras 4

`knowledge/trust/01` §1.4 ya estableció el principio: "las proyecciones son derivables y regenerables por
replay" — eso es exactamente lo que necesita durabilidad. Si `run.step.*` y `capability.job.*` (notas 02,
07, y trust/06) quedan en el mismo event log append-only, entonces el estado de un run tras un crash se
reconstruye leyendo `EventStore.read_stream(run_stream_id)` desde el principio (o desde el último
checkpoint conocido) — no hace falta un almacén de "estado de workflow" separado. Cada una de las otras 4
opciones introduce una SEGUNDA fuente de verdad sobre el progreso de un run (un checkpoint de grafo, una
historia de motor de workflows, un estado gestionado por decoradores, o el estado de un mensaje en cola) —
que tendría que mantenerse coherente con el event log ya congelado, duplicando trabajo sin necesidad
demostrada en Fase 1.

### 1.4 El problema real no resuelto por el replay solo: reintentos con efectos externos

Reconstruir estado por replay resuelve "¿en qué paso estábamos?", pero no resuelve "¿es seguro reintentar
el paso que estaba a medias?". Aquí es donde `side_effects` del `CapabilityManifest` v2 (trust/06 §4)
importa directamente a este plano: un paso `pure` o `reversible-external` puede reintentarse
automáticamente sin daño; un paso `irreversible-external` (ej. algo que ya envió una notificación externa
real) NO puede reintentarse a ciegas — necesita una estrategia explícita (idempotency key, verificación de
si el efecto ya ocurrió, o escalar a intervención humana — clase `human_expert`, [S3] antes «rung 7»). Esta nota señala el problema y su
enganche con `side_effects`; no propone todavía el mecanismo exacto de idempotencia.

> **ADDENDUM (2026-07-20, S-F — el porqué del cambio que el freeze §13 hizo sobre esta
> sección, estampado acá por la regla de oro de la guía):** el freeze movió
> `reversible-external` del bucket "reintenta libre" al bucket "**sin idempotencia garantizada
> NO hay reintento automático**". Razón: **reversible ≠ idempotente** — re-aplicar una acción
> compensable duele hasta que alguien la compensa (dos cargos reversibles siguen siendo dos
> cargos hasta el refund); el reintento automático solo es gratis cuando re-ejecutar es un
> no-op (`pure`, o external con idempotency key verificada). `pure` se reintenta libre;
> `reversible/irreversible-external` escalan a humano en Fase 1 (override registrado antes,
> INV-4). El mecanismo fino (keys por `step_id`, verificación activa del efecto) es diseño de
> S-G con dueño Steven — la regla del mes es segura sin él. Ratificación final: Steven.

## 2 · Alternativas consideradas

Las 5 filas de §1.2 constituyen las alternativas evaluadas.

## 3 · Por qué no (descartadas)

- **Checkpointing tipo LangGraph — descartado para Fase 1:** el riesgo central es tener dos modelos de
  persistencia (checkpoints de grafo + event log) que pueden divergir; sin verificación en vivo de su
  licencia/madurez esta sesión, adoptarlo sería una dependencia no evaluada además del riesgo estructural.
- **Temporal/Cadence-style — descartado para Fase 1:** el costo de adoptar un motor de workflows dedicado
  (nuevo servicio, nuevos workers, nuevo protocolo) no está justificado sin evidencia de que el replay
  simple sea insuficiente. Es la opción de mayor madurez para orquestación de MUY largo plazo, pero
  también la de mayor costo de adopción — se deja como posible dirección later (§12), no como decisión.
- **DBOS-style — descartado para Fase 1:** aunque conceptualmente más liviano que Temporal (según su
  propia propuesta de valor, no verificada en vivo), adoptar su modelo de decoradores acopla el runtime a
  las convenciones de ese proyecto específico — tensión con mantener el engine genérico (el principio de
  "no acoplar el core a un framework externo" ya aplicado por ADR-008 a capabilities, aplicado aquí por
  analogía al runtime).
- **Colas de jobs — descartado como mecanismo PRINCIPAL de durabilidad de un `Run` completo:** una cola
  encaja bien para una invocación de capability individual (`capability.job.*`, ya el vocabulario de
  trust/06 asume algo cola-like para jobs asíncronos), pero un `Run` con `RunStep`s dependientes entre sí
  necesita más que "encolar y esperar" — necesita reconstrucción de secuencia, que una cola simple no da
  por sí sola sin agregar el mismo event log encima.

## 4 · Decisión

| Referencia                                                                         | Decisión                                                                      | Racional                                                                                                                               |
| ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Replay del event log sobre Postgres como mecanismo de durabilidad (opción 1, §1.2) | **portar**                                                                    | Reutiliza directamente el principio ya congelado en trust/01 §1.4; cero componente nuevo en Fase 1                                     |
| Checkpointing tipo LangGraph (referencia conceptual)                               | **inspirar**                                                                  | Solo la idea de "snapshot de estado de grafo" es relevante si el loop se vuelve dinámico (nota 02 §12) — no se integra el framework    |
| Temporal/Cadence-style (referencia conceptual)                                     | **inspirar**                                                                  | Solo la FORMA del concepto "reconstruir estado por historia contra código determinista" — se descarta como dependencia en Fase 1       |
| DBOS-style (referencia conceptual)                                                 | **inspirar**                                                                  | Solo la idea de "persistir en Postgres sin motor separado" — ya es lo que hace la opción elegida, sin adoptar su modelo de decoradores |
| Colas de jobs (patrón genérico)                                                    | **inspirar** (para `capability.job.*` individuales, ya cubierto por trust/06) | Relevante para la invocación de una capability aislada, no para la durabilidad del `Run` completo                                      |
| Adoptar cualquiera de los 4 productos/frameworks externos como dependencia real    | **descartar**                                                                 | No hay necesidad demostrada aún; cada uno introduce un segundo lugar de verdad sobre el progreso del run, en tensión con trust/01      |
| `side_effects` (trust/06) como eje de decisión de reintento                        | **portar**                                                                    | Ya es parte del contrato de manifest congelado por Dylan; esta nota solo consume el campo, no lo redefine                              |

## 5 · Tradeoffs

| Eje                                       | Replay simple (elegido)             | Checkpointing tipo grafo         | Motor de workflows dedicado                                            | Runtime tipo DBOS                                      | Colas de jobs                                  |
| ----------------------------------------- | ----------------------------------- | -------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------ | ---------------------------------------------- |
| Componentes nuevos                        | Ninguno                             | Un almacén de checkpoints        | Un servicio completo                                                   | Un runtime con modelo propio                           | Un broker (si no se reutiliza Postgres)        |
| Fuentes de verdad sobre el progreso       | Una (el event log)                  | Dos (checkpoints + log)          | Dos (historia del motor + log, si se mantiene el log para otros fines) | Una, pero con esquema propio del runtime               | Una por job individual, ninguna a nivel de Run |
| Madurez para runs MUY largos (horas/días) | Sin datos — no probado a esa escala | Sin datos                        | Alta, por diseño (según referencia conceptual)                         | Sin datos                                              | Media — depende del broker                     |
| Costo de adopción                         | Ninguno                             | Medio-alto                       | Alto                                                                   | Medio                                                  | Medio                                          |
| Coherencia con INV-5                      | Directa (mismo puerto)              | Requiere reconciliar dos modelos | Requiere reconciliar dos modelos                                       | Requiere verificar que su esquema no viole append-only | Depende del broker elegido                     |

La elección prioriza cero-dependencia-nueva y una única fuente de verdad sobre madurez probada para runs
de muy larga duración — un tradeoff razonable para Fase 1 sin evidencia de que se necesiten runs de
horas/días, pero que debería revisarse si esa necesidad aparece (ver §12).

## 6 · Modos de falla

- **Reintento de un paso `irreversible-external` sin idempotencia.** El riesgo central identificado en
  §1.4: un crash a mitad de un paso que ya causó un efecto externo real (ej. una notificación enviada), y
  el mecanismo de reanudación simplemente "vuelve a correr el paso" — duplicando el efecto. Ninguna de las
  5 opciones de §1.2 resuelve esto automáticamente; todas requieren una estrategia explícita de
  idempotencia que esta nota no diseña (pregunta abierta, §10).
- **Replay parcial que no distingue "completado" de "en progreso".** Si el `status` de un `RunStep` (nota
  02 §1.3) no distingue claramente entre "se completó" y "se empezó pero no se sabe si terminó" (ej. el
  proceso murió justo después de la llamada externa pero antes de escribir el evento de finalización), el
  replay no puede decidir con seguridad si reintentar o esperar confirmación — un riesgo estructural de
  cualquier sistema con efectos externos no transaccionales junto al event log.
- **Costo de replay creciente sin límite.** Sin un mecanismo de snapshot/checkpoint (deliberadamente fuera
  de alcance en Fase 1, ver §1.3), un run muy largo obliga a releer TODO su stream desde el inicio en cada
  reanudación — un modo de falla de performance, no de corrección, pero real a partir de cierto volumen de
  eventos (magnitud no medida, ver preguntas abiertas).
- **Divergencia entre dos fuentes de verdad** (si en el futuro se adoptara alguna de las opciones
  descartadas junto con el event log ya existente) — un checkpoint de grafo o una historia de motor de
  workflows que diga algo distinto a lo que el event log registra es, por definición, un estado
  inconsistente que ninguna de las dos fuentes puede resolver por sí sola.

## 7 · Licencias

| Pieza                                                                                          | Licencia                        | Verificado                                                             |
| ---------------------------------------------------------------------------------------------- | ------------------------------- | ---------------------------------------------------------------------- |
| Patrón de replay de historia (genérico, ya usado por trust/01)                                 | N/A — patrón, no producto nuevo | ya adoptado por el proyecto (trust/01), no es una evaluación nueva     |
| Checkpointing tipo LangGraph, Temporal/Cadence, DBOS, colas de jobs (referencias conceptuales) | no verificado                   | **no verificado en vivo esta sesión** — no se propone integrar ninguno |

No se propone ninguna dependencia nueva en esta nota.

## 8 · Impacto en contrato

1. No se propone ningún puerto nuevo — durabilidad es un **patrón de consumo** sobre `EventStore` (ya
   existente, trust/01), no un componente nuevo del plano de ejecución.
2. Se propone una proyección `RunState` (derivable, regenerable por replay, igual que las proyecciones ya
   mencionadas en trust/01 §1.4) que resume el último `RunStep` conocido y su `status` — consumida por el
   runtime al reanudar un run, y potencialmente por el Studio (frontera con trust/18, fuera de esta nota).
3. El campo `side_effects` de `CapabilityManifest` v2 (trust/06) se vuelve una entrada obligatoria de
   cualquier lógica de reintento del runtime — un paso `irreversible-external` no puede reintentarse por
   la misma vía genérica que uno `pure`. El mecanismo exacto queda como pregunta abierta (§10).
4. **Qué debe ser durable AHORA (Fase 1/POC) vs qué se puede posponer:**
   - **Ahora:** que un `RunStep` completado quede en el event log de forma que un replay reconstruya
     "hasta dónde llegó el run" — esto es lo mínimo para que "reiniciar el proceso" no pierda trabajo ya
     hecho.
   - **Puede posponerse:** snapshotting/checkpointing para runs largos (§6, "costo de replay creciente"),
     cualquier mecanismo de idempotencia automática para pasos irreversibles (§10 — hoy exigiría
     intervención manual o simplemente no reintentar automáticamente), y cualquier adopción de un motor de
     workflows dedicado.

## 9 · Implicaciones de test / spec

- **Test de reconstrucción de `RunState` por replay:** dado un stream de eventos de prueba con N
  `run.step.*` completados y uno en progreso, verificar que la proyección `RunState` reconstruida
  identifica correctamente el último paso completado y el paso pendiente.
- **Test de "no reintento automático de `irreversible-external`":** verificar que, dado un `RunStep` con
  `kind` que mapea a una capability `side_effects: irreversible-external` y `status: running` (interrumpido
  a medias), el mecanismo de reanudación NO lo reintenta automáticamente sin una señal explícita —
  cierra, a nivel de test, el modo de falla más grave de §6.
- **Test de idempotencia de proyección:** aplicar el replay dos veces sobre el mismo stream y verificar que
  produce el mismo `RunState` — propiedad básica de cualquier proyección derivada, ya implícita en el
  principio de trust/01 §1.4 pero no verificada específicamente para `RunState`.
- Ninguno de estos tests existe hoy — señalados como trabajo futuro derivado de este diseño.

## 10 · Supuestos y preguntas abiertas

> **[S3 · 2026-07-30 · #116] Registro de valor (§6/§10):** el snapshot/checkpoint
> por volumen de eventos (§6, «costo de replay creciente») y el mecanismo fino de
> idempotencia (§10) quedaron registrados como **KB curada** del censo (#116); el
> mecanismo grueso ya es regla congelada (freeze §13 — sin idempotencia garantizada
> no hay reintento automático; addendum S-F en §1.4).

**Supuestos:**

- El event log (trust/01) es suficientemente rápido de leer/replay-ear para runs de duración razonable en
  Fase 1 — no se hizo ninguna medición ni prueba de carga.
- Un `run` corresponde a un único `stream_id` en el `EventStore` — **CONFIRMADO** (freeze §2/§13, nota 07:
  `stream_id = run_id`, un stream por run, decisión de Dylan). Al momento de escribir esta nota era un
  supuesto pendiente de la nota 07; ya no lo es.

**Preguntas abiertas:**

- ¿Cuál es el mecanismo concreto de idempotencia para pasos `reversible-external`/`irreversible-external`
  tras un crash a medias? (idempotency key por paso, verificación activa contra el sistema externo, o
  escalamiento obligatorio a revisión humana — clase `human_expert` del freeze §4; [S3] antes «rung 7»
  de la escalera, trust/03 SUPERSEDIDA). No
  decidido — este es el modo de falla más grave de §6 y no tiene mitigación diseñada todavía.
- ¿A partir de qué volumen de eventos por run se vuelve necesario un snapshot/checkpoint en vez de replay
  completo desde el inicio del stream? No investigado — depende de datos que no existen todavía.
- ¿Quién dispara la reanudación tras un crash — un proceso de watchdog externo, o el propio runtime al
  arrancar? Fuera del alcance de esta nota.
- Si en el futuro se necesita durabilidad para runs de horas/días (fuera del alcance conocido de Fase 1),
  ¿en qué punto Temporal/Cadence-style deja de ser sobre-ingeniería y se vuelve la opción correcta? No hay
  criterio definido.

## 11 · Recomendación mínima de POC

Replay simple sobre el `EventStore` ya existente (opción 1 de §1.2), sin checkpoint, sin motor dedicado:
(1) escribir `run.step.*` a medida que el pipeline fijo (recomendación de POC de la nota 02) avanza, (2)
implementar `RunState` como una función pura que lee `EventStore.read_stream(run_id)` completo y devuelve
el último `RunStep` conocido, (3) simular un "crash" en el POC deteniendo el proceso a mitad de un run de
prueba y verificar que reiniciar + llamar a `RunState` identifica correctamente dónde continuar. **No
implementar ningún mecanismo de idempotencia automática en el POC** — si el paso de prueba es
`irreversible-external`, el POC debe simplemente NO reintentarlo automáticamente (mitigación manual/no-op
es aceptable para validar el diseño, no para producción).

## 12 · Dirección later / producción

Fuera de alcance de esta nota, como dirección conceptual: si aparece evidencia real de runs de larga
duración (horas/días) o de necesidad de checkpoint por volumen de eventos, Temporal/Cadence-style es la
opción de mayor madurez conceptual para ese caso — pero su adopción implicaría una decisión de
infraestructura mayor, no un cambio incremental, y debería evaluarse con licencias y arquitectura
verificadas en vivo (no como en esta nota). Para el problema de idempotencia (§10, sin resolver), la
dirección más probable es una combinación de idempotency keys por paso (generadas determinísticamente a
partir de `step_id`) y, para el subconjunto de pasos que no puedan garantizar idempotencia por diseño,
escalamiento obligatorio a revisión humana (clase `human_expert`, freeze §4 — [S3] antes «rung 7»,
trust/03) en vez de reintento automático — pero esto
requiere validación con Dylan por su relación con `VerificationPolicy` (trust/05).

## 13 · Reconciliación contra la base lógica (`docs/invariants.md`)

- **INV-5 (event log append-only):** INTACTO y es la base misma del mecanismo propuesto — la durabilidad
  depende de que el log nunca se edite ni borre; si INV-5 se debilitara, este diseño completo dejaría de
  funcionar. Las 4 alternativas descartadas (§3) comparten el riesgo de introducir una segunda fuente de
  verdad que podría, en la práctica, tentar a alguien a "corregir" el checkpoint en vez del log — un
  riesgo indirecto contra el espíritu de INV-5 que el replay simple no tiene.
- **INV-4 (override registrado antes de ejecutar):** relevante para reintentos de pasos irreversibles —
  cualquier decisión de "reintentar de todos modos" un paso `irreversible-external` cuenta como un
  override y debe registrarse ANTES de reintentar, no después. Señalado como requisito de diseño, no
  resuelto todavía (ver pregunta abierta, §10, y modo de falla, §6).
- **PR1 (toda acción emite evento) — referenciado en trust/01 §5:** SOPORTADO — el mecanismo de replay
  depende exactamente de que cada acción relevante ya sea un evento; esta nota no introduce ninguna acción
  que se salte esa regla.
- **Ninguna referencia contradice la base lógica.** Los 4 patrones de referencia comparados en §1.2 son
  coherentes conceptualmente con event sourcing (que es lo que trust/01 ya adoptó) — la decisión de no
  integrarlos es de costo/necesidad, no de conflicto con los invariantes.
