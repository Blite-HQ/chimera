# Nota 02 — La cola de jobs en Python: Postgres ya es la cola

**Ítem del plan (§4, Geovanni):** re-mapear el patrón cola→worker al stack vigente. La nota 01 (y el documento de infraestructura original) asumían BullMQ sobre NestJS/Redis — supersedido por el core Python/FastAPI (`docs/arquitectura-python.md`). Esta nota compara los candidatos reales en Python y cierra el pendiente #1 del README de infra.
**Fecha:** 2026-07-14 · **Estado:** investigación de consolidación (Dylan) — pendiente validación y ratificación de Geovanni
**Fuentes:** verificado en vivo 2026-07-14: `procrastinate-org/procrastinate` (repo + docs readthedocs, sección de mecanismo interno) · `python-arq/arq` (repo, aviso maintenance-only #510) · `celery/celery` (repo; discusión #9049 sobre asyncio) · `Bogdanp/dramatiq` (repo + `COPYING.LESSER`) · `tobymao/saq` (repo + changelog) · `rq/rq` (repo + `LICENSE`) · guía oficial de uv para Docker (contexto nota 03) · artículo "Postgres LISTEN/NOTIFY does not scale" (recall.ai) y referencias de campo del patrón `SELECT ... FOR UPDATE SKIP LOCKED`. Internas: `knowledge/trust/01-event-sourcing-postgres.md`, `knowledge/execution/03-durable-execution.md`, `knowledge/execution/06-serving-execution-profile.md`, `knowledge/trust/06-protocolos-capability-mcp-a2a.md`, `docs/invariants.md`.

---

## 1 · Patrón / mecanismo

### 1.1 Qué tiene que hacer la cola este mes (y qué no)

Los jobs del mes son exactamente dos familias, ambas "unidades de trabajo independientes" — el caso donde `knowledge/execution/03` §1.2 ya dijo que una cola de jobs encaja bien (a diferencia del `Run` completo, cuya fuente de verdad es el event log, no la cola):

1. **Capabilities con `execution_profile = remote-job`** (`trust/06` §1.2, `execution/06` §1.3): invocaciones que tardan minutos u horas, despachadas por el `Dispatcher` como `JobRef`, con progreso reportado vía eventos `capability.job.*` en el event store.
2. **Provisioning con Automation API** (nota 01 §3, §6): `stack.up()`/`destroy` como jobs — el patrón canónico API → cola → worker → Automation API que la nota 01 ya adoptó, con la pieza concreta por definir.

El perfil de carga es **baja frecuencia, larga duración**: decenas de jobs por día en el demo, no miles por segundo. Lo que sí es innegociable: retries con backoff, recuperación tras crash del worker, cancelación (para abortar un run), y observabilidad básica (qué job está en qué estado).

### 1.2 El mecanismo de fondo: es el mismo patrón que trust/01 ya congeló

Una cola sobre Postgres se construye con dos primitivas estándar:

- **`SELECT ... FOR UPDATE SKIP LOCKED`** — el worker toma la siguiente fila de jobs disponible saltándose las que otro worker ya bloqueó; concurrencia segura sin coordinación externa (patrón de campo bien documentado; docs de PostgreSQL, cláusula de bloqueo de `SELECT`).
- **`LISTEN/NOTIFY`** — la campana que despierta al worker cuando hay job nuevo, con polling de fallback.

Eso es **literalmente el patrón "notify-then-catchup" que `trust/01` §1.3 ya congeló para SSE**: NOTIFY como campana, la tabla como verdad. La cola de jobs y el event store usan la misma primitiva del mismo Postgres — un solo mecanismo mental para el equipo.

**Procrastinate implementa exactamente esto** (verificado en vivo en sus docs): "PostgreSQL's LISTEN allows us to be notified whenever a task is available", el fetch usa "a `SELECT FOR UPDATE` that will lock the impacted rows", y hay polling de fallback configurable (`fetch_job_polling_interval`). Su racional publicado para "por qué Postgres como cola" es el nuestro: mantener una sola base robusta es preferible a operar un broker aparte (Redis/RabbitMQ) con sus propios backups, disponibilidad y monitoreo. _(Matiz: sus docs citan `SELECT FOR UPDATE`; el uso exacto de `SKIP LOCKED` en su PLpgSQL no se citó textual — el ~11% del repo es PLpgSQL; confirmar en el código al integrar. No cambia la decisión.)_

### 1.3 Los siete candidatos, comparados en vivo

| Candidato                                    | Broker / almacén                                                                      | Async nativo (FastAPI)                                                                                               | Licencia (LICENSE real) | Versión · actividad (2026-07-14)                                 | Pieza nueva en el compose   |
| -------------------------------------------- | ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ----------------------- | ---------------------------------------------------------------- | --------------------------- |
| **Procrastinate**                            | **Postgres 13+ (el que ya existe)**                                                   | ✅ sí — async es "the recommended way"; sync también                                                                 | MIT ✅                  | v3.9.0 (jun 2026), 112 releases, activo, 1.3k★                   | **ninguna**                 |
| **SAQ**                                      | Redis **o Postgres** (`saq[postgres]`)                                                | ✅ sí (asyncio puro)                                                                                                 | MIT ✅                  | v0.26.4 (may 2026), activo, ~0.9k★                               | **ninguna** (modo postgres) |
| **arq**                                      | Redis                                                                                 | ✅ sí                                                                                                                | MIT ✅                  | v0.28.0 (abr 2026) — **maintenance-only mode** (issue #510), 3k★ | Redis                       |
| **Celery**                                   | RabbitMQ / Redis / SQS / Pub/Sub (SQLAlchemy **solo** como result backend, no broker) | ❌ no — sin soporte para `async def` tasks (discusión #9049 abierta; solo terceros: aio-celery, celery-pool-asyncio) | BSD-3 ("New BSD") ✅    | v5.6.3 (mar 2026), muy activo, 28.7k★                            | Redis o RabbitMQ            |
| **Dramatiq**                                 | RabbitMQ / Redis                                                                      | ⚠️ no de primera clase (existe middleware asyncio — no verificado en vivo, PENDIENTE)                                | **LGPL-3.0** ⚠️         | v2.2.0 (jun 2026), activo, 5.3k★                                 | Redis o RabbitMQ            |
| **RQ**                                       | Redis ≥ 5 / Valkey ≥ 7.2                                                              | ❌ no                                                                                                                | BSD-2 ✅                | v2.10 (jun 2026), activo, 10.7k★                                 | Redis                       |
| **SKIP LOCKED a mano** (detrás de un puerto) | Postgres                                                                              | ✅ sí (asyncpg)                                                                                                      | propia                  | —                                                                | ninguna                     |

### 1.4 Por qué Procrastinate gana en los cinco criterios

1. **Compose mínimo:** usa el Postgres que ya existe. Cuatro de los siete candidatos exigen Redis (o RabbitMQ) — y el compose objetivo del mes es `postgres + api + studio [+ ollama]`, **sin Redis salvo justificación fuerte**. Ninguno de los candidatos Redis aporta algo que justifique el servicio extra en este perfil de carga.
2. **Los jobs del mes:** retries con backoff, tareas periódicas, **locks arbitrarios** (ej. "un solo job de provisioning por workspace a la vez" — exactamente lo que Automation API necesita para no pisar stacks), prioridades y **cancelación de jobs** (mapea al abort de un run). Todo de fábrica, verificado en sus docs.
3. **Async nativo:** async es el modo recomendado; convive con FastAPI/ASGI sin puentes. Celery y RQ fallan este criterio de plano; arq lo cumple pero está en modo mantenimiento declarado por su autor.
4. **Madurez/licencia:** MIT verificada en vivo, v3.9.0 con release el mes pasado, Python 3.10+ (nuestro pyproject exige ≥3.12), desarrollo activo. No es el proyecto más estrellado de la lista — pero es el único activo que cumple los criterios 1–3 simultáneamente.
5. **Coherencia con event sourcing:** los jobs viven en el **mismo Postgres** que los eventos del run (Procrastinate soporta correr en la misma base, con schema propio). Encolar un job y appendear el evento que lo anuncia puede compartir transacción — la propiedad "outbox transaccional" gratis, sin segundo sistema de estado que pueda divergir del event log (el riesgo que `execution/03` §1.3 señaló para cualquier persistencia paralela). _(La forma exacta del defer transaccional compartiendo conexión con nuestro `EventStore` es detalle de implementación — PENDIENTE de spike al construir `apps/api`.)_

### 1.5 El puerto propio: la opción "a mano" sobrevive como forma, no como implementación

La opción "SELECT FOR UPDATE SKIP LOCKED a mano detrás de un puerto" pierde como implementación — reimplementar retries, backoff, heartbeats, jobs perdidos, scheduling y cancelación es reconstruir un motor que Procrastinate ya trae probado. Pero **gana como forma**: el engine no debe acoplarse a Procrastinate. Se define un puerto propio y Procrastinate es su primer adaptador:

```python
class JobQueue(Protocol):
    async def enqueue(self, *, task: str, payload: dict[str, Any],
                      lock: str | None = None, priority: int = 0) -> JobRef: ...
    async def cancel(self, ref: JobRef) -> None: ...
    async def status(self, ref: JobRef) -> JobStatus: ...
```

El `JobRef` es el mismo que el `DispatchStrategy` de `execution/06` §1.4 ya devuelve para `remote-job`. Si Procrastinate decepciona, se cambia el adaptador (SAQ-postgres es el plan B natural, misma licencia y mismo backend), no el contrato.

### 1.6 El límite conocido, anotado para Fase 2

`LISTEN/NOTIFY` de Postgres adquiere un lock global en la fase de commit bajo carga alta de escritores (hallazgo publicado por recall.ai, 2025: "Postgres LISTEN/NOTIFY does not scale"). A la escala del demo (decenas de jobs/día, un writer) es irrelevante; a escala real, Procrastinate ya trae el modo `listen_notify=False` + polling, y la evolución a durable execution (Temporal-style) ya está mapeada en nota 01 y `execution/03` como dirección de Fase 2, no como reemplazo. Se registra para que la decisión de hoy no se lea como ignorancia del límite.

## 2 · Decisión

| Candidato                       | Decisión                                                                   | Racional                                                                                                                                                                    |
| ------------------------------- | -------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Procrastinate**               | **integrar** — la cola del mes, detrás del puerto `JobQueue`               | Único candidato activo que cumple los 5 criterios: cero piezas nuevas en compose, async-first, MIT, features exactas de los jobs del mes, mismo Postgres que el event store |
| **SKIP LOCKED a mano (puerto)** | **inspirar** — la forma del puerto es propia; la implementación no         | No reimplementar retries/heartbeats/scheduling; el patrón subyacente es el mismo que Procrastinate ejecuta                                                                  |
| **SAQ**                         | **inspirar** — plan B documentado si Procrastinate tropieza en la práctica | MIT, asyncio puro, `PostgresQueue` disponible; comunidad menor (~0.9k★) y backend Postgres más joven que el de Procrastinate                                                |
| **arq**                         | **descartar**                                                              | Requiere Redis y está en maintenance-only mode declarado (#510) — dos strikes                                                                                               |
| **Celery**                      | **descartar**                                                              | Sin soporte nativo `async def` (postura mantenida por años, #9049); broker extra obligatorio; su madurez no compensa dos criterios fallados                                 |
| **Dramatiq**                    | **descartar**                                                              | Broker extra obligatorio (Redis/RabbitMQ); LGPL-3.0 pesa más en la postura open-core; async no de primera clase                                                             |
| **RQ**                          | **descartar**                                                              | Requiere Redis; sin async nativo                                                                                                                                            |

**Supersede formalmente a BullMQ:** el patrón cola→worker de la nota 01 §6 queda igual; la pieza pasa de "NestJS + BullMQ + Redis" a "FastAPI + Procrastinate + el Postgres existente". El trace del run queda: API → **Procrastinate** → worker Python → _(si aplica: Automation API)_ → … — un lenguaje, un almacén.

## 3 · Licencias

| Pieza         | Licencia                       | Verificado 2026-07-14                      |
| ------------- | ------------------------------ | ------------------------------------------ |
| Procrastinate | **MIT**                        | ✅ en vivo (repo)                          |
| SAQ           | **MIT**                        | ✅ en vivo (repo)                          |
| arq           | MIT                            | ✅ en vivo (repo) — descartado             |
| Celery        | BSD-3 ("New BSD")              | ✅ en vivo (repo) — descartado             |
| Dramatiq      | **LGPL-3.0** ⚠️                | ✅ en vivo (`COPYING.LESSER`) — descartado |
| RQ            | BSD-2                          | ✅ en vivo (`LICENSE`) — descartado        |
| PostgreSQL    | PostgreSQL License (permisiva) | conocida (ya en el stack)                  |

Dependencia nueva del mes: solo `procrastinate` (MIT). Cero servicios nuevos.

## 4 · Impacto en contrato

- **No toca** `Event`, `Verifier` ni `CapabilityManifest`: la cola es mecanismo de despacho, no contrato. El `JobRef` que devuelve `DispatchStrategy` (`execution/06` §1.4) gana una implementación concreta; su forma ya estaba propuesta allí.
- **Vocabulario `capability.job.*`** (`trust/06`): los eventos de progreso del job siguen viviendo en el event store — la tabla de jobs de Procrastinate es **estado operativo, no procedencia**. Nadie lee la tabla de jobs para reconstruir un run; se lee el event log (`execution/03` §1.3 intacto).
- **INV-5 intacto:** las tablas de Procrastinate (schema propio) conviven en la misma base pero no son `events`; el único escritor de eventos sigue siendo `blite.events.writer`. El worker que quiera appendear eventos pasa por el puerto `EventStore`, jamás por SQL directo a `events`.
- **Nuevo deployable lógico: el worker.** Mismo código base que el api, proceso distinto (`procrastinate worker`). Impacta el compose y las task definitions de Fargate — resuelto en la nota 03.
- **Punto de encuentro con Steven** (nota 01 §I): `execution_profile: remote-job` ↔ esta cola. El hint de despacho del manifest aterriza aquí.

## 5 · Reconciliación contra la base lógica

1. **Resuelve el drift #1 del README de infra** (BullMQ/NestJS → stack vigente): el patrón cola→worker se conserva, la pieza se re-mapea a Procrastinate sobre el Postgres existente. La nota 01 no se edita — este documento la supersede en ese punto; ratificación de Geovanni pendiente.
2. **INV-1 (gateway chokepoint):** los jobs se encolan desde el api (detrás del gateway); el worker no expone puertos ni recibe invocaciones externas — consume de Postgres. Ninguna ruta nueva elude el gateway.
3. **AX3 / Inv-E:** el worker ejecuta capabilities y provisioning, no es `serving`; si un job necesita modelo, pasa por el model router como cualquier otro llamador. La cola no crea ningún camino de egress nuevo — el egress de un job sigue gobernado por `authz`.
4. **INV-5 (append-only):** verificado arriba (§4) — la cola no introduce update/delete sobre `events`; su propio estado mutable (jobs) es explícitamente no-procedencia.
5. **Compose objetivo del mes:** `postgres + api + studio [+ ollama]` se sostiene **sin Redis** — este era el criterio con más peso y es el que elimina a 4 de 7 candidatos. La justificación fuerte para Redis no apareció.
6. **Coherencia con `trust/01`:** misma primitiva (NOTIFY como campana, tabla como verdad, polling como fallback) para SSE y para jobs — una sola historia que contar en el pitch de arquitectura.
7. **PENDIENTES:** (a) confirmar `SKIP LOCKED` textual en el PLpgSQL de Procrastinate al integrar; (b) spike del defer transaccional compartiendo conexión con `EventStore`; (c) verificar en vivo el middleware asyncio de Dramatiq solo si alguien reabre ese candidato.
