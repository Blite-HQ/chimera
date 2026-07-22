-- Chimera — init v2 (Fase 1). Traducción ejecutable de docs/esquema-datos-v2.md
-- (SEMILLA v2, gobernada por docs/contract-freeze.md). Los statements se copian
-- VERBATIM de los bloques ```sql del doc — tests/invariants/test_esquema_migration.py
-- explota ante drift en CUALQUIER dirección (doc⊆init e init⊆doc).
-- [S-G Etapa 0] Supersede engine/sql/events_v2.sql: ese archivo conservaba el
-- índice duplicado (stream_id, seq) que [S-F · N6] eliminó, un índice extra en
-- global_seq sin respaldo en la letra, y nombres de trigger pre-S-F.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Append-only. Nadie hace UPDATE ni DELETE sobre esta tabla.
-- Es el log inmutable del que se reconstruye todo el estado.
CREATE TABLE events (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stream_id     TEXT NOT NULL,                 -- = run_id (un stream por run, freeze §2/§13);
                                                 -- [S-F · N2] eventos sin run: "system:<componente>"
                                                 -- (registry/policy/trust-registry) — jamás entran
                                                 -- al provenance_hash de un certificado
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

-- [S-F · N6] sin índice (stream_id, seq) aparte: el UNIQUE de arriba ya lo materializa.
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

CREATE TABLE identities (
    id          TEXT PRIMARY KEY,                -- "user:dylan" | "agent:planner-7"
    kind        TEXT NOT NULL CHECK (kind IN ('human', 'agent', 'service')),
    domain_id   TEXT NOT NULL REFERENCES domains (id),
    permissions TEXT[] NOT NULL DEFAULT '{}',    -- capacidades invocables (intersección AX1)
    spiffe_id   TEXT,                            -- Fase 2
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

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

-- Proyección de Runs (estado actual, derivado de run.created / run.completed / ...).
CREATE TABLE runs_projection (
    id            TEXT PRIMARY KEY,
    parent_run_id TEXT REFERENCES runs_projection (id),  -- NULL = run raíz; el case/certificado cuelga del raíz (D5)
    initiator_id  TEXT NOT NULL,                 -- la identidad se hereda del iniciador
    domain_id     TEXT NOT NULL,
    -- [S-F] 'cancelled' faltaba (freeze §3 lo congela terminal — un run.cancelled era
    -- improyectable); 'awaiting-verification' e 'interrupted' (steps) son sub-estados de
    -- PROYECCIÓN derivados de eventos, no estados de la máquina de eventos.
    status        TEXT NOT NULL CHECK (status IN
                    ('created','running','awaiting-verification','completed','failed','cancelled')),
    max_steps     INTEGER NOT NULL,               -- [S-F] "contrato, no cortesía" (freeze §3/§13)

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
    anchor_kind            TEXT CHECK (anchor_kind IN      -- [S-F stress · SF-P1-2] KIND del ancla:
                             ('solver','execution','dataset','rule','human')),  -- Policy required_anchors
    verdict                TEXT NOT NULL CHECK (verdict IN ('pass','fail','inconclusive')),
    inconclusive_reason    TEXT,                  -- tri-estado (D4): timeout | undecidable | conflict | undermined_premise | ...
    scope                  JSONB NOT NULL,        -- ScopeExpr canónico (decidible)
    independence_group     TEXT NOT NULL,         -- [S-F · T5] el conteo de patas C3 es POR GRUPO
    claim_digest           TEXT NOT NULL,         -- binding a 4 digests (L3):
    verifier_binary_digest TEXT NOT NULL,         --   binario del verificador,
    verifier_params_digest TEXT NOT NULL,         --   parámetros de invocación,
    anchor_digest          TEXT,                  --   ancla exacta usada
    predicate              JSONB NOT NULL DEFAULT '{}',  -- [S-F · T4] por clase: proof∅ (AL4), coverage, reruns
    evidence_digests       TEXT[] NOT NULL,       -- refs a artifacts(digest); audit-ready, reproducer si aporta AL3
    issued_at              TIMESTAMPTZ NOT NULL DEFAULT now(),  -- semántica VALID_AS_OF

    -- [S-F · T3] un 'pass' sin ancla es irrepresentable (D10); el nullable de anchor_digest
    -- es legítimo SOLO para 'inconclusive' (p.ej. no_applicable_anchor).
    -- [stress-final · 2026-07-22] el CHECK se alinea a la letra: nullable SOLO inconclusive
    -- (antes solo cubría 'pass' — un 'fail' sin ancla era representable contra el comentario).
    CONSTRAINT attestations_pass_requiere_ancla
        CHECK (verdict = 'inconclusive' OR anchor_digest IS NOT NULL)
);
CREATE INDEX idx_attestations_run ON attestations (run_id);

-- Certificados de confianza emitidos (D20/ADR-025). Salida de primera clase.
-- [S-E · P0-2/P1-2] La letra chica es parte del mínimo: conclusiones con enunciado+alcance,
-- supuestos visibles, VALID_AS_OF y revocación autodeclarada. El sobre DSSE completo se
-- persiste (verificación offline = bytes exactos, Regla 1 del anexo de canonicalización).
CREATE TABLE trust_certificates (
    run_id           TEXT PRIMARY KEY,            -- case por run raíz (D5);
                                                  -- [S-F · T14] Fase 1 = UNA emisión por run
                                                  -- (●CertificateReissued/Revoked = Fase 2)
    actor_id         TEXT NOT NULL,
    provenance_hash  TEXT NOT NULL,               -- hash del stream del run (D14)
    titular_level    TEXT NOT NULL CHECK (titular_level IN ('AL0','AL1','AL2','AL3','AL4')),
                                                  -- [S-F · T2] := mín(conclusions[].level_efectivo); vacío ⇒ AL0
                                                  -- [stress-final] level_efectivo := AL0 si verdict ∈
                                                  --   {refuted, inconclusive, not_required_declared} (SF-P2-4)
    conclusions      JSONB NOT NULL,              -- [{claim_digest, canonical_statement, scope, verdict, level}]
                                                  --   mínimo del camino crítico, jamás promedio
    unanchored_steps INTEGER NOT NULL DEFAULT 0,  -- [S-F · N1] predicate mínimo del mes (freeze §7)
    coverage_stats   JSONB NOT NULL DEFAULT '{}', -- [S-F · N1/T13] cobertura/gap por conclusión
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
