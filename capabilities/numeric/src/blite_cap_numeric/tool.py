"""
MatrixOps — Perform generic matrix operations (multiply, invert, decompose, normalize).

Registered as entry point: blite.capabilities["blite.numeric.matrix_ops"]
Heavy dependencies are loaded lazily (install via extras):
  uv add blite-cap-numeric[full]
"""

from __future__ import annotations

from typing import Any

from blite_capability.manifest import CapabilityManifest

_MANIFEST = CapabilityManifest(
    id="blite.numeric.matrix_ops",
    description="Perform generic matrix operations (multiply, invert, decompose, normalize).",
    input_schema={
        "type": "object",
        "properties": {
            "matrix": {"type": "array"},
            "operation": {
                "type": "string",
                "enum": ["multiply", "invert", "normalize", "eigenvalues"],
            },
        },
        "required": ["matrix", "operation"],
    },
    output_schema={
        "type": "object",
        "properties": {"result": {"type": "array"}},
        "required": ["result"],
    },
    tags=("numeric", "linear-algebra", "classical"),
)


class MatrixOps:
    """Generic capability: Perform generic matrix operations (multiply, invert, decompose, normalize)."""

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
                f"MatrixOps: optional dependency missing. "
                f"Install blite-cap-numeric[full]: {exc}"
            ) from exc

    def _invoke_impl(self, inputs: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(
            "MatrixOps: implementation not yet provided. Install blite-cap-numeric[full]."
        )
