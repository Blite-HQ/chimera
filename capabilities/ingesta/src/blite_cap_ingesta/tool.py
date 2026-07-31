"""
Ingestion capabilities — manifests + wrappers `Capability` finos sobre la
lógica pura (`snapshot_fetch.py`/`geojson_to_graph.py`).

Registrados como entry points:
  blite.capabilities["blite.ingesta.snapshot.fetch"]
  blite.capabilities["blite.ingesta.geojson.to_graph"]

DISCREPANCIA FLAGGEADA (docs/specs/capability-ingesta.md §Dos capabilities
nuevas): el freeze §1 congela un `CapabilityManifest` v2 con 4 campos
adicionales — `side_effects`/`required_permission`/`interaction`/
`execution_profile` — que `sdk/src/blite_capability/manifest.py` (el
`@dataclass` v1 hoy instalado) NO tiene. Se programa aquí contra el v1
EXISTENTE (no se reescribe el SDK — la migración al manifest v2 es trabajo
pendiente del SDK, compartido por TODAS las capabilities nuevas del plan,
no exclusivo de ingesta); los 4
campos v2 quedan documentados en la `description`/tabla de abajo y en
`tags`, listos para migrar cuando el manifest v2 llegue:

| id                             | side_effects        | required_permission                | interaction        | execution_profile |
| ------------------------------- | -------------------- | ------------------------------------ | ------------------ | ------------------ |
| blite.ingesta.snapshot.fetch    | reversible-external  | capability:ingest:external-source    | job                | in-process (hint)  |
| blite.ingesta.geojson.to_graph  | pure                 | capability:ingest:derive             | request_response   | in-process (hint)  |

ADR-029: schemas genéricos — cero término de escenario ("islanding"/"ICE"/
"subestación") en `id`/`description`/schema. Los datos REALES que fluyen por
estas capabilities (p. ej. el corpus ICE-70) sí traen esos términos — eso es
DATO, no forma; el manifest no lo sabe.
"""

from __future__ import annotations

from typing import Any

from blite_cap_ingesta.geojson_to_graph import derive_graph
from blite_cap_ingesta.snapshot_fetch import fetch_snapshot
from blite_capability.manifest import CapabilityManifest

_SNAPSHOT_FETCH_MANIFEST = CapabilityManifest(
    id="blite.ingesta.snapshot.fetch",
    description=(
        "Store an already-retrieved external byte payload as a "
        "content-addressed artifact and record its external-source "
        "provenance. v2 manifest fields (not yet on CapabilityManifest — "
        "module docstring): side_effects=reversible-external, "
        "required_permission=capability:ingest:external-source, "
        "interaction=job, execution_profile=in-process (hint)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "content_base64": {
                "type": "string",
                "description": "Base64-encoded raw bytes already retrieved by the caller",
            },
            "media_type": {
                "type": "string",
                "description": "MIME type of the content",
            },
            "source_uri": {
                "type": "string",
                "description": "Locator the bytes were retrieved from (recorded, never re-fetched)",
            },
            "retrieved_at": {
                "type": "string",
                "format": "date-time",
                "description": "Timestamp of retrieval",
            },
            "http_status": {
                "type": "integer",
                "description": "Status code of the retrieval, if applicable",
            },
            "domain_id": {
                "type": "string",
                "description": "Caller's visibility domain for the content store",
            },
        },
        "required": [
            "content_base64",
            "media_type",
            "source_uri",
            "retrieved_at",
            "domain_id",
        ],
    },
    output_schema={
        "type": "object",
        "properties": {
            "artifact": {
                "type": "object",
                "description": "Content-addressed descriptor of the stored bytes",
            },
            "provenance": {
                "type": "object",
                "description": "External-source provenance record for the stored artifact",
            },
        },
        "required": ["artifact", "provenance"],
    },
    tags=("ingestion", "snapshot", "external-source"),
)


class SnapshotFetch:
    """Generic capability: persist externally-retrieved bytes as a
    content-addressed artifact plus its external-source provenance.

    `inputs["content_store"]` is a live dependency (a `ContentSink`,
    `ports.py`) injected at invocation time by whoever dispatches the job —
    it is NOT part of `input_schema` (not JSON-representable). See
    `snapshot_fetch.fetch_snapshot`.
    """

    @property
    def manifest(self) -> CapabilityManifest:
        return _SNAPSHOT_FETCH_MANIFEST

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return fetch_snapshot(inputs)


_GEOJSON_TO_GRAPH_MANIFEST = CapabilityManifest(
    id="blite.ingesta.geojson.to_graph",
    description=(
        "Derive a generic graph topology from a pair of GeoJSON feature "
        "collections (nodes + edges), validating geometry (RFC 7946) and "
        "tabular attribute shape before declaring the derived instance "
        "valid; validation outcomes travel as assertions on the returned "
        "derivation provenance. v2 manifest fields (not yet on "
        "CapabilityManifest — module docstring): side_effects=pure, "
        "required_permission=capability:ingest:derive, "
        "interaction=request_response, execution_profile=in-process (hint)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "nodes_content_base64": {
                "type": "string",
                "description": "Base64-encoded GeoJSON FeatureCollection of point features (graph nodes)",
            },
            "edges_content_base64": {
                "type": "string",
                "description": "Base64-encoded GeoJSON FeatureCollection of line features (graph edges)",
            },
            "node_id_property": {
                "type": "string",
                "default": "FID",
                "description": "Property name carrying each node feature's stable identifier",
            },
            "edge_strategy": {
                "type": "string",
                "default": "nearest-neighbor",
                "enum": ["nearest-neighbor", "endpoint-name-match"],
                "description": (
                    "How to resolve which two nodes each edge feature "
                    "connects. 'nearest-neighbor' snaps each line endpoint "
                    "to the closest node by geometric distance. "
                    "'endpoint-name-match' parses a delimited endpoint-name "
                    "pair from an edge property (endpoint_property, split "
                    "on endpoint_separator) and matches each side against a "
                    "node property (node_match_property) by normalized "
                    "name; only nodes that resolve at least one edge appear "
                    "in the output."
                ),
            },
            "node_match_property": {
                "type": "string",
                "description": (
                    "Node property carrying the name matched against "
                    "parsed edge endpoints — required when "
                    "edge_strategy='endpoint-name-match'"
                ),
            },
            "endpoint_property": {
                "type": "string",
                "description": (
                    "Edge property holding the delimited endpoint-name "
                    "pair — required when edge_strategy='endpoint-name-match'"
                ),
            },
            "endpoint_separator": {
                "type": "string",
                "default": "-",
                "description": (
                    "Delimiter splitting endpoint_property into two "
                    "endpoint names (edge_strategy='endpoint-name-match')"
                ),
            },
            "weight_property": {
                "type": ["string", "null"],
                "default": None,
                "description": (
                    "Edge property summed across aggregated parallel edges "
                    "to compute edge weight (edge_strategy='endpoint-name-"
                    "match'); when omitted/null, weight is instead the "
                    "count of aggregated parallel edges"
                ),
            },
            "run_id": {
                "type": "string",
                "description": "Run identifier this derivation executes under",
            },
            "params_digest": {
                "type": "string",
                "description": (
                    "Digest of this invocation's parameters, computed by the "
                    "caller via the single canonicalization gate"
                ),
            },
            "code_ref": {
                "type": "string",
                "description": "Version-control reference for the recipe code that produced this derivation",
            },
            "inputs": {
                "type": "array",
                "description": "Provenance references for the snapshot artifact(s) this derivation consumed",
                "items": {
                    "type": "object",
                    "properties": {
                        "ref": {"type": "string"},
                        "digest": {"type": "string"},
                    },
                    "required": ["ref", "digest"],
                },
            },
        },
        "required": [
            "nodes_content_base64",
            "edges_content_base64",
            "run_id",
            "params_digest",
            "code_ref",
            "inputs",
        ],
    },
    output_schema={
        "type": "object",
        "properties": {
            "graph": {
                "type": "object",
                "properties": {
                    "n_nodos": {"type": "integer"},
                    "aristas": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "description": "[node_i, node_j, weight]",
                        },
                    },
                    "nodos": {
                        "type": "object",
                        "description": "Node metadata keyed by node index (string)",
                    },
                },
                "required": ["n_nodos", "aristas", "nodos"],
            },
            "provenance": {
                "type": "object",
                "description": "Derivation provenance record — {kind, inputs, recipe, run_id, assertions}",
            },
        },
        "required": ["graph", "provenance"],
    },
    tags=("ingestion", "derivation", "graph", "pure"),
)


class GeojsonToGraph:
    """Generic capability: pure derivation of graph topology from GeoJSON."""

    @property
    def manifest(self) -> CapabilityManifest:
        return _GEOJSON_TO_GRAPH_MANIFEST

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return derive_graph(inputs)
