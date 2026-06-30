"""
GraphPartitioner — Partition a graph into balanced components using classical graph algorithms.

Registered as entry point: blite.capabilities["blite.graphs.partition"]
Heavy dependencies are loaded lazily (install via extras):
  uv add blite-cap-graphs[networkx]
"""

from __future__ import annotations

from typing import Any

from blite_capability.manifest import CapabilityManifest

_MANIFEST = CapabilityManifest(
    id="blite.graphs.partition",
    description="Partition a graph into balanced components using classical graph algorithms.",
    input_schema={
        "type": "object",
        "properties": {
            "adjacency": {"type": "array", "description": "Adjacency list or matrix"},
            "num_parts": {"type": "integer", "minimum": 2},
        },
        "required": ["adjacency", "num_parts"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "partition": {
                "type": "array",
                "description": "Component assignment per node (list of integers)",
            }
        },
        "required": ["partition"],
    },
    tags=("graphs", "partitioning", "classical"),
)


class GraphPartitioner:
    """Generic capability: Partition a graph into balanced components using classical graph algorithms."""

    @property
    def manifest(self) -> CapabilityManifest:
        return _MANIFEST

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Invoke the capability. Heavy deps loaded lazily on first call."""
        return self._run(inputs)

    def _run(self, inputs: dict[str, Any]) -> dict[str, Any]:
        # Lazy import of heavy dependency
        try:
            return self._invoke_impl(inputs)
        except ImportError as exc:
            raise ImportError(
                f"GraphPartitioner: optional dependency missing. "
                f"Install blite-cap-graphs[networkx]: {exc}"
            ) from exc

    def _invoke_impl(self, inputs: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(
            "GraphPartitioner: implementation not yet provided. Install blite-cap-graphs[networkx]."
        )
