"""
PowerFlowSim — Run a generic power-flow simulation over a network topology and return electrical quantities.

Registered as entry point: blite.capabilities["blite.sim.power_flow"]
Heavy dependencies are loaded lazily (install via extras):
  uv add blite-cap-sim[pandapower]
"""

from __future__ import annotations

from typing import Any

from blite_capability.manifest import CapabilityManifest

_MANIFEST = CapabilityManifest(
    id="blite.sim.power_flow",
    description="Run a generic power-flow simulation over a network topology and return electrical quantities.",
    input_schema={
        "type": "object",
        "properties": {
            "topology": {
                "type": "object",
                "description": "Network topology (buses, branches, loads as generic dicts)",
            },
            "parameters": {"type": "object"},
        },
        "required": ["topology"],
    },
    output_schema={
        "type": "object",
        "properties": {"converged": {"type": "boolean"}, "metrics": {"type": "object"}},
        "required": ["converged"],
    },
    tags=("simulation", "physics", "classical", "anchor"),
)


class PowerFlowSim:
    """Generic capability: Run a generic power-flow simulation over a network topology and return electrical quantities."""

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
                f"PowerFlowSim: optional dependency missing. "
                f"Install blite-cap-sim[pandapower]: {exc}"
            ) from exc

    def _invoke_impl(self, inputs: dict[str, Any]) -> dict[str, Any]:
        from blite_cap_sim.power_flow import run_power_flow

        topology = inputs.get("topology")
        if not isinstance(topology, dict):
            msg = "PowerFlowSim: input 'topology' (object) is required"
            raise ValueError(msg)
        return run_power_flow(topology)
