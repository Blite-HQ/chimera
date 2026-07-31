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
    side_effects="pure",
    required_permission="capability:invoke",
    interaction="request_response",
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


_MAXCUT_MANIFEST = CapabilityManifest(
    id="blite.graphs.maxcut",
    description=(
        "Approximate the maximum of a symmetric QUBO matrix using cut-relaxation "
        "heuristics (SDP rounding or greedy); returns a binary assignment and its "
        "objective value."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "matrix": {
                "type": "array",
                "description": "Symmetric QUBO coefficient matrix (list of lists of numbers)",
            },
            "method": {
                "type": "string",
                "enum": ["gw", "greedy"],
                "default": "greedy",
            },
            "seed": {
                "type": "integer",
                "default": 1,
                "description": "Seed for randomized rounding (method='gw')",
            },
        },
        "required": ["matrix"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "assignment": {
                "type": "array",
                "description": "Binary assignment vector (list of 0 or 1 integers)",
            },
            "energy": {
                "type": "number",
                "description": "Objective value of the solution (xᵀQx)",
            },
            "method": {"type": "string"},
            "seed": {"type": "integer"},
            "sdp_upper_bound": {
                "type": ["number", "null"],
                "description": (
                    "SDP relaxation value before rounding (method='gw' only; "
                    "null for 'greedy') — a rigorous upper bound on the true "
                    "max-cut, same units as 'energy'."
                ),
            },
        },
        "required": ["assignment", "energy"],
    },
    tags=("graphs", "maxcut", "approximation", "classical"),
    side_effects="pure",
    required_permission="capability:invoke",
    interaction="request_response",
)


class MaxCutBaseline:
    """Generic capability: approximate the max-cut of a symmetric QUBO matrix
    using classical cut-relaxation heuristics (SDP rounding or greedy)."""

    @property
    def manifest(self) -> CapabilityManifest:
        return _MAXCUT_MANIFEST

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Invoke the capability. Heavy deps loaded lazily on first call."""
        return self._run(inputs)

    def _run(self, inputs: dict[str, Any]) -> dict[str, Any]:
        # Lazy import of heavy dependency
        try:
            return self._invoke_impl(inputs)
        except ImportError as exc:
            raise ImportError(
                f"MaxCutBaseline: optional dependency missing. "
                f"Install blite-cap-graphs[gw]: {exc}"
            ) from exc

    def _invoke_impl(self, inputs: dict[str, Any]) -> dict[str, Any]:
        from blite_cap_graphs.maxcut import solve_maxcut

        seed = inputs.get("seed", 1)
        if isinstance(seed, bool) or not isinstance(seed, int):
            msg = f"MaxCutBaseline: seed debe ser entero, no {seed!r}"
            raise ValueError(msg)
        return solve_maxcut(
            inputs.get("matrix"), method=inputs.get("method", "greedy"), seed=seed
        )
