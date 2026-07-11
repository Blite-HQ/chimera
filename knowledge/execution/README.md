# Knowledge — Execution (plano de ejecución · Steven)

Notas de investigación del plano de ejecución, sesión inicial (2026-07-10, revisión 2026-07-10). Cada
nota tiene los 4 campos obligatorios (patrón/mecanismo · decisión `integrar|portar|inspirar|descartar` ·
licencia · impacto en contrato), agrega alternativas consideradas + "por qué no" + tradeoffs + modos de
falla + implicaciones de test/spec + una recomendación mínima de POC + una dirección later/producción,
marca explícitamente sus supuestos y preguntas abiertas, y cierra con su reconciliación contra
`docs/invariants.md` (la base lógica NO está bajo revisión — ver `CONTRIBUTING.md`: "si `lint-imports` o un
test de invariante falla, se arregla el código, no el test").

**Ninguna de estas notas declara un contrato congelado.** Son insumo para `docs/contract-freeze.md`
(hoy DRAFT, explícitamente pendiente de las correcciones de Steven — plano de ejecución — antes de
congelar), no un reemplazo de ese documento. Ninguna referencia externa citada en estas notas fue
verificada en vivo esta sesión (sin `WebFetch`/`WebSearch`/`gh search`) — se tratan como **patrones de
referencia**, no como verdad del proyecto; cada nota lo marca explícitamente donde aplica.

## Qué es el plano de ejecución

El plano de ejecución es el camino por el que una solicitud entra al sistema, se autoriza, se despacha a
una capability (in-process, servicio, o job remoto) y produce un resultado — todo mediado por el
`gateway` (INV-1, único chokepoint) y sujeto a AX3 (un modelo nunca toca el mundo directo: `blite.serving`
no importa `protocols`, `gateway`, `runtime`, `authz`, ni clientes de red). Corresponde a los módulos
`engine/src/blite/{gateway,runtime,serving}/` (ver `.github/CODEOWNERS`, sección "Plano de ejecución
(Steven + Dylan)").

## Qué entra en el alcance de Steven

- **Gateway / pipeline** — el chokepoint único (INV-1) y el orden de sus etapas.
- **Runtime / agent loop** — el ciclo de ejecución de un run, paso a paso.
- **Durable execution** — cómo un run sobrevive reinicios / jobs de larga duración.
- **Capability Registry y adapters** — descubrimiento de capabilities (ADR-008) y el borde hacia MCP/A2A
  (frontera con el contrato de Dylan en `knowledge/trust/06`).
- **Model router** — selección entre backends de modelo, respetando el aislamiento AX3 de `serving`.
- **Serving** — cómo se despacha `execution_profile` (in-process | service | remote-job).
- **Run lifecycle** — el vocabulario de eventos que agrega runs, steps y jobs de capability en un mismo
  stream.

## Qué NO entra en el alcance de Steven

- `verification`, `events` (el puerto `EventStore` y su esquema), `certificate`, `identity`, `protocols`,
  `guardrails`, `authz`, `sdk/` — todo esto es plano de confianza (Dylan, ver `knowledge/trust/`). Estas
  notas los **consumen** como contratos externos (ej. `EventStore.append`, `capability.job.*`), nunca los
  redefinen.
- La lógica de negocio de `capabilities/*` (ej. solvers, quantum) — el engine se mantiene genérico
  (ADR-029); estas notas no introducen términos de escenario.
- Edición de `docs/invariants.md` (frozen, requiere los cuatro dueños) ni de `docs/contract-freeze.md`
  (draft compartido — ver abajo).

## Índice

| Nota | Tema | Contratos que toca |
|---|---|---|
| [01](01-gateway-chokepoint-pipeline.md) | El gateway como chokepoint único; 7 etapas concretas (identidad→authz→guardrails→policy→despacho→verificación→egreso) | Pipeline de `blite.gateway`; frontera con Inv-E/INV-6 |
| [02](02-runtime-agent-loop.md) | El agent loop: 4 formas comparadas (pipeline fijo/ReAct/plan-execute/jerárquico); vocabulario `run.step.*` | `blite.runtime`; frontera con vocabulario de eventos (trust/06) |
| [03](03-durable-execution.md) | Durabilidad: event replay vs LangGraph checkpointing vs Temporal vs DBOS vs colas | Consume `EventStore` (trust/01); proyección `RunState` |
| [04](04-capability-registry-adapters.md) | Capability vs Tool vs Adapter; descubrimiento tolerante a fallos (caso real pyscf/VQE) | `blite.runtime` registry; frontera con `CapabilityManifest` v2 (trust/06) |
| [05](05-model-router-serving-boundary.md) | AX3 y el router de modelos; 4 diseños de egress comparados, ninguno decidido | `blite.serving`; punto de coordinación obligatorio con Dylan |
| [06](06-serving-execution-profile.md) | `execution_profile` como estrategia de despacho; 4 perfiles comparados | `blite.serving`/`blite.runtime`; consume `CapabilityManifest` v2 (trust/06) |
| [07](07-run-lifecycle-events.md) | Máquina de estados textual de `Run`/`RunStep`; ejemplo de orden de eventos con IDs sintéticos | Consume `EventStore`/`Event` (trust/01); frontera con Studio (trust/18) |

## Orden de lectura sugerido

No es necesario leerlas en orden de número — el orden de dependencia real es:

1. **07** (vocabulario de eventos) primero — fija el lenguaje (`run.*`/`run.step.*`/`capability.job.*`) que
   las notas 01–06 asumen al hablar de "qué evento emite esta etapa".
2. **01** (gateway) — el chokepoint que todo lo demás asume como punto de entrada.
3. **04** (registry) — qué es una capability y cómo se descubre, antes de hablar de cómo se despacha.
4. **02** (runtime/agent loop) — cómo se secuencian los pasos que el gateway despacha vía el registry.
5. **06** (execution_profile) — cómo el runtime decide DÓNDE corre cada paso.
6. **05** (model router/serving) — el caso más difícil de "dónde corre algo": modelos, no capabilities,
   bajo AX3. Depende de haber leído 01 y 06 primero.
7. **03** (durable execution) — asume 07 (vocabulario) y 04 (`side_effects` del manifest) para hablar de
   reintentos seguros; léase al final porque depende de las demás.

## Cómo revisar esto con Dylan

Cada nota marca sus puntos de frontera explícitamente (ver su sección de preguntas abiertas y su tabla de
decisión), pero para una sesión de revisión conjunta, estos son los puntos que requieren su input directo,
en orden de bloqueo:

1. **Nota 07, §5** — ¿es correcto un único `stream_id` por run? Esta pregunta bloquea el resto del
   vocabulario de eventos de las notas 01/02/06; conviene resolverla primero.
2. **Nota 05, completa** — dónde vive la llamada de red real a un proveedor de modelo (`gateway` vs un
   adapter en `protocols` vs algo nuevo). Es la pregunta más grande sin dueño claro entre los dos planos;
   necesita su propia sesión, no solo una revisión de texto.
3. **Nota 04, §5** — ¿el registry debería emitir `registry.loaded`? y la política de manejo de un entry
   point que falla al cargar — ambas tocan el vocabulario de eventos que él posee.
4. **Nota 03, §5** — el mecanismo de idempotencia para pasos `irreversible-external` depende de decisiones
   que tocan `VerificationPolicy` (trust/05) y potencialmente escalamiento a rung 7 (trust/03) — su plano.
5. **Notas 01, 02, 06** — mayormente autocontenidas del lado de ejecución; revisar por completitud, no por
   bloqueo.

**Formato sugerido de la sesión:** repasar la tabla "Decisión" de cada nota primero (son las filas más
rápidas de aprobar/objetar), y dejar las secciones de "preguntas abiertas" para discusión en vivo — no se
espera que Dylan lea las 7 notas completas antes de la sesión.

## Qué queda intencionalmente sin resolver

Esta carpeta es una investigación inicial, no un diseño completo. Lo siguiente es una brecha conocida y
reconocida, no un olvido:

- **El punto de egress de red para modelos (nota 05)** — sin resolver por diseño; requiere una decisión
  conjunta que esta sesión de investigación no tenía mandato para tomar unilateralmente.
- **Mecanismo exacto de idempotencia para reintentos de pasos irreversibles (nota 03)** — se identificó el
  problema y su enganche con `side_effects`, no se diseñó el mecanismo.
- **Forma exacta del objeto de contexto (`ctx`) que viaja por el pipeline del gateway (nota 01)** — se
  fijó qué información necesita cargar, no su tipo/esquema exacto.
- **Órdenes de magnitud reales** (cuántos eventos por run, cuántos backends de modelo, con qué frecuencia
  se necesitaría `execution_profile: remote-job`) — ninguna nota tiene datos de producción; los supuestos
  de Fase 1 son razonamiento desde los invariantes, no medición.
- **Todo lo que depende de `CapabilityManifest` v2 y `DistributionManifest`** — estas notas consumen esos
  contratos como si ya estuvieran congelados del lado de Dylan; `docs/contract-freeze.md` los marca DRAFT,
  así que cualquier cambio ahí puede requerir revisar varias de estas notas.

## Cómo esto alimenta `docs/contract-freeze.md` (más adelante, sin tocarlo ahora)

`docs/contract-freeze.md` ya reserva la etiqueta de dueño `[frontera]` para ítems donde el contrato es de
Dylan y la mecánica es de Steven, y su encabezado dice textualmente: *"pendiente merge con las correcciones
de Steven (plano de ejecución) antes de congelar"*. El flujo previsto (mismo patrón que usó Dylan con
`knowledge/trust/`) es:

1. Estas 7 notas se revisan con Dylan donde tocan un contrato que él ya declaró en el freeze (marcado
   `[frontera]` en cada nota abajo, y priorizado en la sección "Cómo revisar esto con Dylan" arriba).
2. Los puntos sin objeción se incorporan a `docs/contract-freeze.md` como ítems nuevos etiquetados
   `[ejecución]`, o como refinamiento de un ítem `[frontera]` existente — en una edición posterior,
   explícita, no en este pase.
3. Los puntos con desacuerdo o pregunta abierta (ver cada nota, sección de preguntas abiertas, y "Qué queda
   intencionalmente sin resolver" arriba) se resuelven en sesión conjunta antes de tocar el freeze.

Ninguna nota de esta carpeta edita `docs/contract-freeze.md` ni `docs/invariants.md` directamente.
