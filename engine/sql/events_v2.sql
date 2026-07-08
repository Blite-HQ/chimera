-- Chimera events v2 — docs/contract-freeze.md SS2 /
-- knowledge/trust/01-event-sourcing-postgres.md.
--
-- 3 changes over the seed schema (docs/esquema-datos.md SS1):
--   1. global_seq BIGINT GENERATED ALWAYS AS IDENTITY — monotonic
--      cross-stream cursor for SSE catch-up and projections (message-db /
--      EventStoreDB pattern). Gaps are permitted; irrelevant in Fase 1 with
--      a single writer.
--   2. REVOKE + a noisy trigger instead of the seed's silent no-op rewrite
--      rules — append-only that fails LOUD (RAISE EXCEPTION), never
--      silently swallows an UPDATE/DELETE.
--   3. expected_seq optimistic-concurrency semantics documented here and
--      enforced by UNIQUE(stream_id, seq): the writer computes
--      seq = expected_seq + 1; a conflicting insert is rejected, the
--      caller rereads the stream and decides (no locks).
--
-- No live Postgres in this ficha (B2 excludes it — session 9's job);
-- tests/invariants/test_events_sql_v2.py checks this file's text.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE events (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stream_id     TEXT NOT NULL,                 -- normally the run_id
    seq           BIGINT NOT NULL,                -- gapless position within the stream
    global_seq    BIGINT GENERATED ALWAYS AS IDENTITY, -- cross-stream cursor (SSE Last-Event-ID)
    type          TEXT NOT NULL,                  -- run.created | tool.invoked | override.applied | ...
    actor_id      TEXT NOT NULL,                  -- AX1: who originated the action
    domain_id     TEXT NOT NULL,                  -- AX1b: trust boundary
    payload       JSONB NOT NULL,
    occurred_at   TIMESTAMPTZ NOT NULL DEFAULT now(),

    prev_hash     TEXT,                           -- Fase 2: hash of the previous event (D14)
    hash          TEXT,                           -- Fase 2: hash-chain (D14/AX2)

    UNIQUE (stream_id, seq)                       -- strict order + idempotency per stream
);

CREATE INDEX idx_events_stream      ON events (stream_id, seq);
CREATE INDEX idx_events_type        ON events (type);
CREATE INDEX idx_events_actor       ON events (actor_id);
CREATE INDEX idx_events_domain      ON events (domain_id);
CREATE INDEX idx_events_occurred    ON events (occurred_at);
CREATE UNIQUE INDEX idx_events_global_seq ON events (global_seq);

-- Append-only that fails LOUD (note 01 SS1.2). A silent no-op rewrite rule
-- lets a buggy UPDATE believe it succeeded — for a system whose thesis is
-- provenance, the rejection must be visible and auditable. Two layers:
-- REVOKE removes the privilege from ordinary roles; the trigger raises
-- regardless of who runs the statement.
REVOKE UPDATE, DELETE ON events FROM PUBLIC;

CREATE OR REPLACE FUNCTION raise_append_only() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'events is append-only (INV-5)';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER events_immutable
    BEFORE UPDATE OR DELETE ON events
    FOR EACH ROW EXECUTE FUNCTION raise_append_only();
