# El Engine — Esquema de Datos v2

_PostgreSQL · Fase 1 · SEMILLA_

> **Estado: SEMILLA v2 (importada 2026-07-18, barrido S-E).** Realiza en PostgreSQL las
> entidades de la _Especificación de Contratos v2_ — **la verdad ejecutable sigue siendo la
> traducción gobernada por [`contract-freeze.md`](contract-freeze.md)** (misma regla que la
> semilla v1, hoy supersedida). Importada del working set externo, sanitizada ("el Engine") y
> con las correcciones del veredicto de convergencia aplicadas al importar: **C3** (el esquema
> `events` gana-freeze: `global_seq`, append-only que falla fuerte con REVOKE + trigger,
> semántica `expected_seq`) y **C1** (tabla `capabilities` sin `protocol`, con `interaction` +
> `execution_profile`), más la letra chica del certificado (**P0-2/P1-2**). Cada corrección
> está marcada `-- [S-E]` en su sitio.
>
> **Propósito.** El principio rector es Event Sourcing: la tabla `events` es la **única fuente de verdad** (append-only); todo lo demás son proyecciones derivables por replay.
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
    stream_id     TEXT NOT NULL,                 -- = run_id (un stream por run, freeze §2/§13)
    seq           BIGINT NOT NULL,               -- posición dentro del stream
    global_seq    BIGINT GENERATED ALWAYS AS IDENTITY,  -- [S-E · C3] cursor global (SSE/proyecciones)
    type          TEXT NOT NULL,                 -- vocabulario del freeze §3/§14
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

-- [S-E · C3] Refuerzo de append-only a nivel de base — APPEND-ONLY QUE FALLA FUERTE
-- (gana-freeze §2, trust/01): las reglas silenciosas `DO INSTEAD NOTHING` de la semilla
-- original se reemplazan — un UPDATE/DELETE debe EXPLOTAR, jamás no-op silencioso.
REVOKE UPDATE, DELETE ON events FROM PUBLIC;

CREATE OR REPLACE FUNCTION events_immutable() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'events es append-only (INV-5): % prohibido', TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER events_no_update_delete
    BEFORE UPDATE OR DELETE ON events
    FOR EACH ROW EXECUTE FUNCTION events_immutable();

-- [S-E · C3] Concurrencia optimista (freeze §2): el caller pasa `expected_seq`; el INSERT usa
-- seq = expected_seq + 1 y el UNIQUE (stream_id, seq) rechaza el conflicto — sin locks.
```

El evento `override.applied` (AX2/ADR-022) no es una tabla aparte: es una fila de `events` con `type = 'override.applied'` y el `payload` con la forma `OverridePayload`. Así toda relajación queda en el mismo log inmutable que todo lo demás. La regla dura de AX2 (freeze §10) aplica sin excepción: desactivar el propio registro de overrides es, a su vez, un override que se escribe _antes_ de surtir efecto.

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
-- [S-E · C1] Sin columna `protocol` (el protocolo es del adapter, ADR-013); con los dos
-- ejes del freeze §1: `interaction` + `execution_profile`.
CREATE TABLE capabilities (
    id                  TEXT NOT NULL,
    version             TEXT NOT NULL,
    input_schema        JSONB NOT NULL,
    output_schema       JSONB NOT NULL,
    side_effects        TEXT NOT NULL CHECK (side_effects IN ('pure','reversible-external','irreversible-external')),
    required_permission TEXT NOT NULL,
    interaction         TEXT NOT NULL CHECK (interaction IN ('request_response','job','stream')),
    execution_profile   TEXT NOT NULL DEFAULT 'in-process'
                        CHECK (execution_profile IN ('in-process','service','remote-job')),
    registered_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id, version)
);
```

---

## 4.b · Content-store (O3/L3 — sustrato de Evidence y deliverables)

```sql
-- El contenido se direcciona por identidad (digest de la forma canónica), no por ubicación.
-- SO2: particionado por dominio — un digest es visible solo dentro de su dominio salvo
-- Channel con 'read'. La dedup física es optimización interna, jamás canal de visibilidad.
CREATE TABLE artifacts (
    digest      TEXT NOT NULL,                   -- sha256 de la forma canónica
    domain_id   TEXT NOT NULL REFERENCES domains (id),   -- SO2: scope de visibilidad
    media_type  TEXT NOT NULL,
    size_bytes  BIGINT NOT NULL,
    storage_ref TEXT NOT NULL,                   -- dónde viven los bytes (disco/S3/etc.)
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (digest, domain_id)              -- mismo contenido en dos dominios = dos filas, cero fuga
);

CREATE INDEX idx_artifacts_domain ON artifacts (domain_id);
```

---

## 5 · Proyecciones (CQRS-lite, derivables del log)

Estas tablas son **lecturas materializadas**; se reconstruyen aplicando los eventos. Si se borraran, un replay de `events` las regenera. Son optimización, no fuente de verdad (restricción 5, arquitectura).

```sql
-- Proyección de Runs (estado actual, derivado de run.created / run.completed / ...).
CREATE TABLE runs_projection (
    id            TEXT PRIMARY KEY,
    parent_run_id TEXT REFERENCES runs_projection (id),  -- NULL = run raíz; el case/certificado cuelga del raíz (D5)
    initiator_id  TEXT NOT NULL,                 -- la identidad se hereda del iniciador
    domain_id     TEXT NOT NULL,
    status        TEXT NOT NULL CHECK (status IN
                    ('created','running','awaiting-verification','completed','failed')),

    -- SO6: pinning por digest de todo lo que definió el run (reproducibilidad, D16/AX2).
    -- Editar una definición crea versión nueva; los runs en vuelo no cambian.
    agent_definition_digest    TEXT,
    workflow_definition_digest TEXT,
    policy_digest              TEXT NOT NULL,

    created_at    TIMESTAMPTZ NOT NULL,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_runs_parent ON runs_projection (parent_run_id);

-- Attestations producidas por los Verifiers (D18). Audit-ready.
CREATE TABLE attestations (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id                 TEXT NOT NULL,
    verifier_id            TEXT NOT NULL,
    verifier_class         TEXT NOT NULL CHECK (verifier_class IN
                             ('formal_exact','execution','ground_truth',
                              'property_rule','consensus_replication','human_expert')),
    verdict                TEXT NOT NULL CHECK (verdict IN ('pass','fail','inconclusive')),
    inconclusive_reason    TEXT,                  -- tri-estado (D4): timeout | undecidable | conflict | undermined_premise | ...
    scope                  JSONB NOT NULL,        -- ScopeExpr canónico (decidible)
    claim_digest           TEXT NOT NULL,         -- binding a 4 digests (L3):
    verifier_binary_digest TEXT NOT NULL,         --   binario del verificador,
    verifier_params_digest TEXT NOT NULL,         --   parámetros de invocación,
    anchor_digest          TEXT,                  --   ancla exacta usada
    evidence_digests       TEXT[] NOT NULL,       -- refs a artifacts(digest); audit-ready, reproducer si aporta AL3
    issued_at              TIMESTAMPTZ NOT NULL DEFAULT now()  -- semántica VALID_AS_OF
);
CREATE INDEX idx_attestations_run ON attestations (run_id);

-- Certificados de confianza emitidos (D20/ADR-025). Salida de primera clase.
-- [S-E · P0-2/P1-2] La letra chica es parte del mínimo: conclusiones con enunciado+alcance,
-- supuestos visibles, VALID_AS_OF y revocación autodeclarada. El sobre DSSE completo se
-- persiste (verificación offline = bytes exactos, Regla 1 del anexo de canonicalización).
CREATE TABLE trust_certificates (
    run_id           TEXT PRIMARY KEY,            -- case por run raíz (D5)
    actor_id         TEXT NOT NULL,
    provenance_hash  TEXT NOT NULL,               -- hash del stream del run (D14)
    titular_level    TEXT NOT NULL CHECK (titular_level IN ('AL0','AL1','AL2','AL3','AL4')),
    conclusions      JSONB NOT NULL,              -- [{claim_digest, canonical_statement, scope, verdict, level}]
                                                  --   mínimo del camino crítico, jamás promedio
    assumptions      JSONB NOT NULL,              -- [S-E · P0-2] [{statement, ref?: {name, digest}}]
    deliverables     JSONB NOT NULL,              -- [{artifact_ref, digest}] — binding anti-TOCTOU
    policy_digest    TEXT NOT NULL,               -- Policy fijada por digest al crear el case
    calculus_version TEXT NOT NULL,               -- p. ej. 'cal-2.4' (I13)
    certificate      JSONB NOT NULL,              -- [S-E] el envelope DSSE completo (payload_b64 + firmas)
    keyid            TEXT NOT NULL,               -- [S-E] "<purpose>:v<version>" — puerto KeyProvider (freeze §7)
    valid_as_of      TIMESTAMPTZ NOT NULL DEFAULT now(),  -- [S-E · P1-2] semántica S5
    revocation       TEXT NOT NULL DEFAULT 'none' -- [S-E · P1-2] Fase 1 autodeclarada sin revocación
    -- las attestations se leen de la tabla attestations por run_id; el Bundle las empaqueta para verificación offline
);
```

---

## 6 · El flujo de escritura (cómo se usan juntas)

Un `capability.job.submitted` siempre se escribe en `events` _antes_ de ejecutar la Capability (PR1/AX2 — etapa provenance:pre); la proyección `runs_projection` se actualiza _después_, leyendo el evento. El orden es siempre: **escribir el evento inmutable primero, derivar la proyección después.** Nunca al revés. Esto garantiza que la fuente de verdad (el log) jamás vaya por detrás de lo que el sistema ya hizo.

```sql
-- Pseudo-secuencia de una invocación (en una transacción):
-- 1) INSERT INTO events (type='capability.job.submitted', actor_id, domain_id, payload, ...)
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

> **Estado.** Esquema de Fase 1 completo como SEMILLA v2. `events` es la fuente de verdad append-only **que falla fuerte** (REVOKE + trigger), con cursor global y concurrencia optimista por `expected_seq`. Las proyecciones son derivables. La traducción a `infra/init.sql` real la gobierna `contract-freeze.md`.
