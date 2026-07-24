# blite-cap-ingesta

Ingestion capabilities: raw snapshot capture and schema-validated derivation
of generic graph topology from geospatial feature collections.

Two capabilities, registered under entry-point group `blite.capabilities`:

- `blite.ingesta.snapshot.fetch` — wraps `ContentStore.put(bytes, media_type,
  ctx) -> Artifact` and produces an external-source provenance record. Does
  **not** perform network I/O itself: it receives bytes already retrieved by
  the caller (the concrete HTTP client is out of scope — see
  `docs/specs/capability-ingesta.md` §Fronteras).
- `blite.ingesta.geojson.to_graph` — pure. Derives a generic graph topology
  (`{aristas, n_nodos, nodos}`) from a pair of GeoJSON `FeatureCollection`s
  (nodes + edges), validating shape (RFC 7946 geometry, tabular attributes)
  before declaring the derived instance valid; the validation outcomes travel
  as `assertions` on the returned derivation provenance.

## Architecture note (ADR-008)

This package never imports `blite.*` (the engine). Both capabilities exchange
plain dicts shaped like `blite.verification.provenance.{ExternalSourceProvenance,
DerivationProvenance}` without importing those classes — the engine-side
caller is responsible for validating/canonicalizing/storing the returned
provenance dict through the single canonicalization gate
(`blite.certificate.canonical.canonicalize`). See `docs/specs/capability-ingesta.md`.
