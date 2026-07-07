# Chimera — Esquema de Datos

_PostgreSQL · Fase 1_

> **Estado: SEMILLA.** Esquema PostgreSQL de la investigación inicial (Fase 1). [`contract-freeze.md`](contract-freeze.md) §2 confirma 3 ajustes sobre esta base (`global_seq`, REVOKE+trigger en vez de reglas silenciosas `DO INSTEAD NOTHING`, semántica de concurrencia optimista `expected_seq`) — no implementar directo de este documento. Ver [`README.md`](README.md).
>
> **Propósito.** Realiza en PostgreSQL las entidades definidas en _Especificación de Contratos_. El principio rector es Event Sourcing: la tabla `events` es la **única fuente de verdad** (append-only); todo lo demás son proyecciones derivables por replay.
>
> **Forma a prueba de manipulación desde el inicio.** En Fase 1 `events` es una tabla append-only con `seq` monótono. En Fase 2 se añaden `prev_hash`/`hash` para el hash-chain (AX2/D14). La forma de la tabla no cambia entre fases; solo se llenan columnas que ya existen.
>
> **Extensiones.** `pgcrypto` (hashes, Fase 2), `pgvector` (memoria/RAG, cuando aplique).

---

## 1 · La fuente de verdad: tabla de eventos (PR1, AX2)

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Append-only. Nadie hace UPDATE ni DELETE sobre esta tabla.
-- Es el log inmutable del que se reconstruye todo el estado.
CREATE TABLE events (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stream_id     TEXT NOT NULL,                 -- normalmente el run_id
    seq           BIGINT NOT NULL,               -- posición dentro del stream
    type          TEXT NOT NULL,                 -- run.created | tool.invoked | override.applied | ...
    actor_id      TEXT NOT NULL,                 -- AX1: quién originó la acción
    domain_id     TEXT NOT NULL,                 -- AX1b: frontera de confianza
    payload       JSONB NOT NULL,
    occurred_at   TIMESTAMPTZ NOT NULL DEFAULT now(),

    prev_hash     TEXT,                          -- Fase 2: hash del evento anterior del stream
    hash          TEXT,                          -- Fase 2: hash(este evento) — encadenamiento (D14)

    UNIQUE (stream_id, seq)                      -- orden estricto e idempotencia por stream
);

CREATE INDEX idx_events_stream   ON events (stream_id, seq);
CREATE INDEX idx_events_type     ON events (type);
CREATE INDEX idx_events_actor    ON events (actor_id);
CREATE INDEX idx_events_domain   ON events (domain_id);
CREATE INDEX idx_events_occurred ON events (occurred_at);

-- Refuerzo de append-only a nivel de base (Fase 1 ya lo deja sellado):
CREATE RULE events_no_update AS ON UPDATE TO events DO INSTEAD NOTHING;
CREATE RULE events_no_delete AS ON DELETE TO events DO INSTEAD NOTHING;
```

El evento `override.applied` (AX2/ADR-022) no es una tabla aparte: es una fila de `events` con `type = 'override.applied'` y el `payload` con la forma `OverridePayload`. Así toda relajación queda en el mismo log inmutable que todo lo demás.

---

## 2 · Dominios y canales (AX1b)

```sql
CREATE TABLE domains (
    id         TEXT PRIMARY KEY,
    owner_id   TEXT NOT NULL,                    -- PR3: quién autoriza egreso
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Cruces permitidos entre dominios. Sin una fila aquí, no hay cruce (AX1b).
CREATE TABLE channels (
    from_domain_id TEXT NOT NULL REFERENCES domains (id),
    to_domain_id   TEXT NOT NULL REFERENCES domains (id),
    allows         TEXT[] NOT NULL,              -- {read, invoke, egress}
    PRIMARY KEY (from_domain_id, to_domain_id)
);
```

En Fase 1 existe un solo dominio; el constructo está presente aunque el dominio sea único.

---

## 3 · Identidades y permisos (AX1)

```sql
CREATE TABLE identities (
    id          TEXT PRIMARY KEY,                -- "user:dylan" | "agent:planner-7"
    kind        TEXT NOT NULL CHECK (kind IN ('human', 'agent', 'service')),
    domain_id   TEXT NOT NULL REFERENCES domains (id),
    permissions TEXT[] NOT NULL DEFAULT '{}',    -- capacidades invocables (intersección AX1)
    spiffe_id   TEXT,                            -- Fase 2
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## 4 · Catálogo de capabilities (ADR-013)

```sql
-- El catálogo de lo que el Engine sabe invocar. TH1 (integridad del catálogo):
-- toda Capability registrada tiene manifest válido y permiso requerido.
CREATE TABLE capabilities (
    id                  TEXT NOT NULL,
    version             TEXT NOT NULL,
    protocol            TEXT NOT NULL CHECK (protocol IN ('in-process','mcp','a2a','http','async')),
    input_schema        JSONB NOT NULL,
    output_schema       JSONB NOT NULL,
    side_effects        TEXT NOT NULL CHECK (side_effects IN ('pure','reversible-external','irreversible-external')),
    required_permission TEXT NOT NULL,
    registered_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id, version)
);
```

---

## 5 · Proyecciones (CQRS-lite, derivables del log)

Estas tablas son **lecturas materializadas**; se reconstruyen aplicando los eventos. Si se borraran, un replay de `events` las regenera. Son optimización, no fuente de verdad (restricción 5, arquitectura).

```sql
-- Proyección de Runs (estado actual, derivado de run.created / run.completed / ...).
CREATE TABLE runs_projection (
    id           TEXT PRIMARY KEY,
    initiator_id TEXT NOT NULL,                  -- la identidad se hereda del iniciador
    domain_id    TEXT NOT NULL,
    status       TEXT NOT NULL CHECK (status IN
                   ('created','running','awaiting-verification','completed','failed')),
    created_at   TIMESTAMPTZ NOT NULL,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Attestations producidas por los Verifiers (D18). Audit-ready.
CREATE TABLE attestations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id      TEXT NOT NULL,
    verifier_id TEXT NOT NULL,
    anchor_kind TEXT NOT NULL CHECK (anchor_kind IN ('solver','execution','dataset','rule','human')),
    verdict     TEXT NOT NULL CHECK (verdict IN ('pass','fail')),
    evidence    JSONB NOT NULL,                  -- qué anchor, qué regla, qué traza
    issued_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_attestations_run ON attestations (run_id);

-- Certificados de confianza emitidos (D20/ADR-025). Salida de primera clase.
CREATE TABLE trust_certificates (
    run_id          TEXT PRIMARY KEY,
    actor_id        TEXT NOT NULL,
    provenance_hash TEXT NOT NULL,               -- hash del stream del run (D14)
    issued_at       TIMESTAMPTZ NOT NULL DEFAULT now()
    -- las attestations del certificado se leen de la tabla attestations por run_id
);
```

---

## 6 · El flujo de escritura (cómo se usan juntas)

Un `tool.invoked` siempre se escribe en `events` _antes_ de ejecutar la Capability (PR1/AX2); la proyección `runs_projection` se actualiza _después_, leyendo el evento. El orden es siempre: **escribir el evento inmutable primero, derivar la proyección después.** Nunca al revés. Esto garantiza que la fuente de verdad (el log) jamás vaya por detrás de lo que el sistema ya hizo.

```sql
-- Pseudo-secuencia de una invocación (en una transacción):
-- 1) INSERT INTO events (type='tool.invoked', actor_id, domain_id, payload, ...)
-- 2)  [ejecutar la Capability mediada por el gateway]
-- 3) INSERT INTO events (type='verification.completed', payload=attestation, ...)
-- 4) INSERT INTO attestations (...)            -- proyección
-- 5) UPDATE runs_projection SET status=...     -- proyección
```

---

## 7 · Nota sobre snapshots (Fase 2, restricción 5)

Cuando los streams crezcan, un `snapshots` table acelera la reconstrucción (guarda el estado de un Run en un `seq` dado, para no reproducir desde cero). Es **optimización de lectura**: el log completo se conserva siempre como fuente de verdad. No se introduce en Fase 1.

```sql
-- Fase 2:
-- CREATE TABLE snapshots (
--     stream_id  TEXT NOT NULL,
--     at_seq     BIGINT NOT NULL,
--     state      JSONB NOT NULL,
--     created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
--     PRIMARY KEY (stream_id, at_seq)
-- );
```

---

> **Nota original.** Esquema de Fase 1 completo. `events` es la fuente de verdad append-only, con la forma a prueba de manipulación ya presente (las columnas `prev_hash`/`hash` existen; se llenan en Fase 2). Las proyecciones son derivables. El siguiente documento (_Orden de Construcción_) define en qué secuencia se construye todo esto.
