# chimera-otel — the observability projector

A **standalone, read-only consumer** of the event stream that derives OTLP
traces. It lives outside `blite.*` on purpose (resolution C-11): the OTLP
exporter is egress, and egress inside the engine would collide with Inv-E/INV-6.

Contract: [`docs/specs/observabilidad-proyeccion.md`](../../docs/specs/observabilidad-proyeccion.md).

## What makes it different from "add OTel to the app"

- **It does not govern, write, or import the engine.** It parses the wire — the
  same decoupling the Studio has. An import-linter contract enforces both
  directions.
- **Read-only at the database level, not by convention.** Its Postgres user has
  `SELECT` on `events` and nothing else (`docker/otel-projector-grants.sql`).
- **Its cursor lives outside the event store**, so it can crash and re-project
  from anywhere.
- **Deterministic ids and times.** Trace/span ids are hashes of versioned domain
  prefixes over `run_id` and a stable anchor; timestamps come from
  `occurred_at`, never from the projection's clock. Re-projecting the same
  stream — or the stream of a faithful replay — yields byte-identical traces.
- **Digests, never content.** Prompts, responses and artifacts travel as
  digests. Whoever wants the content resolves it against the `ContentStore`
  with _their_ permissions; a trace is not a side channel.

## Run it

```bash
docker compose --profile otel up -d        # collector + projector
```

Standalone:

```bash
CHIMERA_OTEL_DATABASE_URL=postgresql://chimera_otel:...@localhost:5544/chimera \
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 \
uv run python -m chimera_otel --once
```

## Langfuse

Optional profile downstream of the collector — an internal debugging tool for
the proposer, never a "backend" (that degradation is recorded in decision #106).
Point it at the collector's OTLP output; nothing in this package knows it exists.
