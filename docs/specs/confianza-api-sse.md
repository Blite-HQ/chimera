# Spec — `chimera_api`: el API del walking skeleton + SSE (plano confianza)

**Gobernada por:** freeze **§9** (contrato SSE Studio↔Engine) ·
**Dueño:** Dylan · **Estado:** VERDE (2026-07-22) ·
**Insumo:** `knowledge/trust/07` §1.2–1.3 — **[S3 2026-07-30]** slot normalizado: la nota de
knowledge estaba en «Gobernada por:»; knowledge es insumo, jamás autoridad (#108).

> **Alcance (2026-07-24):** la frontera «solo el puerto EventStore» aplica al carril SSE
> de esta spec. El arranque de runs (`runs.py`, MVP Nivel-1) compone
> `blite.runtime`/`blite.verification` por DI — permitido por import-linter; ver
> `docs/mvp/01-runtime-api.md`.

## Contrato

- Paquete **`chimera_api`** (miembro `api/` del workspace). Consume el puerto
  `EventStore` (`blite.events`) — jamás la tabla cruda ni internals de
  `gateway/runtime/serving`. El factory `create_event_store(dsn=None)` decide
  la implementación: con DSN (argumento o **`CHIMERA_DATABASE_URL`**) entrega
  el **`PostgresEventStore`** durable (`blite/events/postgres.py`, sobre la
  tabla `events` de init_v2.sql — concurrencia optimista en el UNIQUE, mismas
  reglas post-terminal de `rules.py`); sin DSN, el in-memory de Fase 1. Los
  callers no cambian con el swap (nota 01 §1.5).
- **`GET /health`** → `{"status": "ok"}` (healthcheck del compose).
- **`GET /runs/{run_id}/events`** (SSE): cada mensaje lleva `id:` =
  `global_seq` · `event:` = `type` del evento · `data:` = JSON del evento
  **proyectado para UI** (subset del Event: sin hashes; `{global_seq, type,
actor_id, occurred_at, step_id?, resumen, payload}`). Reanudación con
  `Last-Event-ID: <global_seq>` → catch-up desde el cursor y luego tail por
  polling del puerto (notify-then-catchup llega con el store PG). El stream
  filtra por `run_id`: el Studio nunca ve eventos de otros streams.
- **Regla de forma (freeze §9):** ningún payload de resultado sin su bloque
  `verification` — la proyección NO recorta el payload: el bloque viaja
  intacto tal como el emisor lo estampó. `resumen` sale de
  `payload["resumen"]` si el emisor lo trae; si no, degrada al `type`
  (convención UI adaptable, nota 18 §5 — no es letra del wire).
- Cabeceras anti-buffering: `Cache-Control: no-cache` +
  `X-Accel-Buffering: no` (la pata `proxy_buffering off` del reverse proxy
  vive en el compose — frontera Geovanni).

## Fronteras (qué NO decide esta spec)

- **Autenticación**: JWT en cookie ya está DECIDIDO (freeze §9 P1-9); su
  implementación es la sesión de seguridad del API (carril Steven +
  auditoría) — este paquete no inventa auth bajo presión.
- **Compose/reverse proxy** (Geovanni): perfiles, healthchecks, proxy.
- **Emisores de eventos** (Steven): qué estampa cada payload; esta spec solo
  garantiza que el API no lo degrada.

## Tests semilla

- `tests/unit/api/test_projection.py` — proyección + forma exacta del frame
  SSE. **VERDE**.
- `tests/unit/api/test_app_sse.py` — health, catch-up por `Last-Event-ID`,
  aislamiento por stream, cabeceras. **VERDE**.
- `tests/integration/test_postgres_event_store.py` — contrato del puerto
  contra Postgres real (schema efímero + init_v2.sql, gated por
  `CHIMERA_TEST_DATABASE_URL`, mismo patrón del probe del esquema). **VERDE**
  (corrida real 2026-07-22: 8/8 passed).
