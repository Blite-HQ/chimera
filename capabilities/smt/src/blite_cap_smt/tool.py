"""
ConstraintChecker — Check whether a set of logical constraints is satisfiable using an SMT solver.

Registered as entry point: blite.capabilities["blite.smt.check_constraints"]
Heavy dependencies are loaded lazily (install via extras):
  uv add blite-cap-smt[z3]
"""

from __future__ import annotations

from typing import Any

from blite_capability.manifest import CapabilityManifest

_MANIFEST = CapabilityManifest(
    id="blite.smt.check_constraints",
    description="Check whether a set of logical constraints is satisfiable using an SMT solver.",
    input_schema={
        "type": "object",
        "properties": {
            "constraints": {
                "type": "array",
                "description": "List of constraint expressions in SMT-LIB2 format or as dicts",
            },
            "logic": {"type": "string", "default": "QF_LIA"},
        },
        "required": ["constraints"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "satisfiable": {"type": "boolean"},
            "model": {
                "type": "object",
                "description": "Witness model if satisfiable, null otherwise",
            },
        },
        "required": ["satisfiable"],
    },
    tags=("smt", "formal-verification", "anchor", "classical"),
)


class ConstraintChecker:
    """Generic capability: Check whether a set of logical constraints is satisfiable using an SMT solver."""

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
                f"ConstraintChecker: optional dependency missing. "
                f"Install blite-cap-smt[z3]: {exc}"
            ) from exc

    def _invoke_impl(self, inputs: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(
            "ConstraintChecker: implementation not yet provided. Install blite-cap-smt[z3]."
        )
