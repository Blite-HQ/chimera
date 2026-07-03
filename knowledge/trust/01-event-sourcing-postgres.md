# Nota 01 — Event Sourcing sobre Postgres: el event store que aguanta la tesis

**Ítem del plan (§4 Dylan):** Congelar esquema `events` + puerto writer (seq por stream, idempotencia por UNIQUE, LISTEN/NOTIFY u outbox → SSE)
**Fecha:** 2026-07-02 · **Estado:** insumo para el contract freeze del viernes
**Fuentes:** Esquema semilla (interno) · message-db estudiado en vivo 2026-07-02 · EventStoreDB (conceptos) · Revisión Versión Dios ADR-016/ADR-021 · MS Agent Governance Toolkit (audit log tamper-evident, MIT)

---

## 1 · Patrón / mecanismo

### 1.1 Lo que confirman las referencias reales

**message-db (Eventide, MIT — estudiado en vivo):** una sola tabla `messages`; `position` **gapless por stream**; `global_position` **como cursor global (con gaps permitidos)**; `write_message(expected_version)` para concurrencia optimista; lectura por stream y por categoría. **EventStoreDB (estudio de conceptos):** streams + `expectedRevision` + el stream `$all` con posición global para catch-up subscriptions. Ambos convergen en tres cosas que la semilla ya tiene o le faltan:

1. ✅ La semilla ya tiene: `UNIQUE(stream_id, seq)` (orden estricto + idempotencia), append-only, payload JSONB.
2. ❌ Le falta: **cursor global**. Sin una posición global monótona no hay forma limpia de: catch-up de SSE tras reconexión, proyecciones que consumen _todos_ los streams, ni feed del explorador de procedencia. Propuesta: `global_seq BIGINT GENERATED ALWAYS AS IDENTITY` + índice. (Con gaps y anomalía de visibilidad por orden de commit — irrelevante en Fase 1 con writer único; documentado como costura para Fase 2.)
3. ❌ Le falta precisar: **quién asigna `seq`**. Patrón congelado: el caller pasa `expected_seq` (la última que conoce); el writer inserta `seq = expected_seq + 1`; si otro escribió primero, el UNIQUE rechaza → error de concurrencia explícito, el caller relee y decide. Concurrencia optimista sin locks (la forma de message-db/EventStoreDB, simplificada).

### 1.2 Append-only que falla FUERTE, no en silencio

La semilla usa `CREATE RULE ... DO INSTEAD NOTHING` para UPDATE/DELETE. Problema: la regla **traga la operación en silencio** — un bug que intente UPDATE creería que tuvo éxito. Para un sistema cuya tesis es la procedencia, el rechazo debe ser ruidoso y auditable:

```sql
-- En lugar de reglas silenciosas:
REVOKE UPDATE, DELETE ON events FROM app_role;          -- defensa 1: privilegios
CREATE TRIGGER events_immutable BEFORE UPDATE OR DELETE ON events
  FOR EACH ROW EXECUTE FUNCTION raise_append_only();     -- defensa 2: excepción explícita
```

(La función solo hace `RAISE EXCEPTION 'events is append-only (INV-5)'`.) Mismo sello, falla visible.

### 1.3 NOTIFY como campana, la tabla como verdad (la decisión SSE)

`LISTEN/NOTIFY` es transaccional (se emite al commit) pero **efímero**: un listener desconectado pierde la notificación, y el payload tiene límite (~8 KB). Un outbox separado es redundante: **la tabla `events` ES el outbox** (append-only, con cursor global).

**Patrón congelado — "notify-then-catchup":** el NOTIFY lleva solo una pista (`{stream_id, global_seq}`); el consumidor SSE del API, al despertar (o al reconectar), **lee de la tabla desde su último cursor**. Cero eventos perdidos, cero duplicación de fuente de verdad, y el `Last-Event-ID` de SSE mapea 1:1 al `global_seq` (nota 07). Polling con intervalo corto queda como fallback trivial si NOTIFY molesta en Fase 1 — el contrato (cursor) es idéntico.

### 1.4 Separación de concerns (ADR-021) y forma tamper-evident (ADR-016)

- **Tres usos, un sustrato, costuras explícitas:** log de procedencia (inmutable, larga retención) / streams operativos (estado de runs) / read models (`runs_projection`, `attestations`, `trust_certificates` — ya en la semilla). En Fase 1 la misma tabla `events` sirve procedencia + operación (escala de hackathon); el Studio **solo lee proyecciones** (regla ya establecida). La separación física es Fase 2 — la costura queda en que nadie consume eventos crudos salvo los proyectores y el endpoint SSE.
- **Tamper-evident desde el día 1, criptográfico en Fase 2:** columnas `prev_hash`/`hash` presentes y vacías (ya en semilla — se confirma). La forma futura: `hash = H(prev_hash ‖ canónico(evento))` por stream — cadena estilo transparency log (Certificate Transparency/Rekor). El audit log del MS Agent Governance Toolkit (MIT) es la referencia implementable más cercana. **Por qué importa** (hallazgo 4 de la Revisión Versión Dios): una tabla editable contradice la tesis — "cualquiera con acceso a la DB puede editarla silenciosamente"; el hash-chain convierte el registro en prueba. La FORMA se congela hoy; el cálculo se difiere.

### 1.5 El puerto en Python (reemplaza el writer in-memory)

```python
class EventStore(Protocol):
    def append(self, *, stream_id: str, type: str, actor_id: str, domain_id: str,
               payload: dict[str, Any], expected_seq: int | None = None) -> Event: ...
    def read_stream(self, stream_id: str, from_seq: int = 0) -> tuple[Event, ...]: ...
    def read_all(self, from_global_seq: int = 0) -> tuple[Event, ...]: ...  # cursor SSE/proyecciones
```

- `append` genera `id`, `seq`, `occurred_at` (servidor, no caller — igual que hoy el writer asigna timestamp).
- INV-5 intacto: la implementación Postgres vive en `blite.events.writer` (o submódulo), sigue siendo el único escritor; import-linter no cambia.
- El `Event` actual (`type`, `payload`, `timestamp: float`) se reemplaza por el esquema completo; `timestamp` float → `occurred_at` timestamptz.

## 2 · Decisión

| Referencia                          | Decisión                                                                             | Racional                                                                                        |
| ----------------------------------- | ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| message-db                          | **inspirar** (patrones: gapless seq, cursor global, expected_version; NO su esquema) | MIT; su tabla única difiere de nuestra semilla — adoptamos patrones, mantenemos nuestro esquema |
| EventStoreDB                        | **inspirar** (conceptos: $all, catch-up subscriptions)                               | Producto aparte con licencia propia ⚠️ — solo estudio                                           |
| Marten (C#)                         | **inspirar** (validación del enfoque "eventos JSONB en Postgres")                    | Otro lenguaje; confirma viabilidad, no aporta código                                            |
| Esquema semilla propio              | **portar** (TS/SQL → Python/Pydantic + SQL ajustado)                                 | Con 3 ajustes: global_seq, trigger ruidoso, semántica expected_seq                              |
| LISTEN/NOTIFY + catch-up por cursor | **portar** (patrón estándar Postgres)                                                | Cero pérdida, sin outbox redundante, mapea a SSE Last-Event-ID                                  |
| MS AGT audit log tamper-evident     | **inspirar** (forma del hash-chain, Fase 2)                                          | MIT; referencia implementable del ADR-016                                                       |

## 3 · Licencias

| Pieza                       | Licencia                            | Verificado 2026-07-02         |
| --------------------------- | ----------------------------------- | ----------------------------- |
| message-db                  | **MIT**                             | ✅ en vivo                    |
| PostgreSQL                  | PostgreSQL License (permisiva)      | conocida                      |
| EventStoreDB                | licencia propia/source-available ⚠️ | solo estudio, sin dependencia |
| Marten                      | MIT ⚠️ (no verificado en vivo)      | solo estudio                  |
| MS Agent Governance Toolkit | MIT (per compass) ⚠️                | referencia Fase 2             |

Sin dependencias nuevas: la implementación es SQL propio + asyncpg/SQLAlchemy (ya en el stack §8 de Arquitectura-Python).

## 4 · Impacto en contrato

1. **`Event`** (Pydantic, reemplaza el dataclass de `engine/src/blite/events/writer.py`): `id: UUID`, `stream_id: str`, `seq: int`, `global_seq: int`, `type: str`, `actor_id: str` (**obligatorio — la ruta del flip AX1, nota 08**), `domain_id: str`, `payload: dict`, `occurred_at: datetime`, `prev_hash: str | None`, `hash: str | None`.
2. **Esquema SQL `events`** — semilla confirmada con 3 cambios: `+ global_seq BIGINT GENERATED ALWAYS AS IDENTITY` (+ índice), reglas silenciosas → **REVOKE + trigger que lanza excepción**, y documentar la semántica `expected_seq` en el writer.
3. **Puerto `EventStore`** (§1.5) — `append/read_stream/read_all`; el in-memory actual se reemplaza detrás del mismo puerto; INV-5 y sus gates quedan intactos.
4. **Estrategia SSE:** NOTIFY como pista + catch-up por `global_seq`; `Last-Event-ID` = `global_seq` (contrato del API — frontera con Steven, señalado).
5. **Proyecciones:** siguen siendo derivables y regenerables por replay (la semilla ya lo establece); el Studio jamás lee `events` crudo — solo proyecciones/SSE.

## 5 · Reconciliación contra la base lógica

- **INV-5 (log append-only):** REFORZADO — el sello pasa de regla silenciosa a REVOKE+trigger ruidoso; el puerto expone solo append/read.
- **INV-4/AX2 (override registrado ANTES de ejecutar):** SOPORTADO — `override.applied` es una fila más del mismo log (semilla §1); el orden "evento primero, proyección después" se congela como regla de escritura.
- **PR1 (toda acción emite evento):** SOPORTADO — el puerto es la única vía y estampa actor/domain en cada fila.
- **AX1 (actor_id obligatorio):** este esquema es el prerequisito material del flip del xfail — el dataclass actual ni siquiera tiene el campo.
- **Ninguna referencia contradijo la base lógica.** message-db no tiene hash-chain ni actor obligatorio — dato sobre message-db (su dominio es mensajería, no procedencia); nuestra semilla exige más.
