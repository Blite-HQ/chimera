"""
Classifier — Classify a set of feature vectors using a classical ML model.

Registered as entry point: blite.capabilities["blite.ml.classify"]
Heavy dependencies are loaded lazily (install via extras):
  uv add blite-cap-ml[sklearn]
"""

from __future__ import annotations

from typing import Any

from blite_capability.manifest import CapabilityManifest

_MANIFEST = CapabilityManifest(
    id="blite.ml.classify",
    description="Classify a set of feature vectors using a classical ML model.",
    input_schema={
        "type": "object",
        "properties": {
            "features": {"type": "array", "description": "List of feature vectors"},
            "model": {
                "type": "string",
                "enum": ["svm", "xgboost", "random_forest"],
                "default": "svm",
            },
        },
        "required": ["features"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "labels": {"type": "array", "description": "Predicted class labels"},
            "probabilities": {"type": "array"},
        },
        "required": ["labels"],
    },
    tags=("ml", "classification", "classical"),
    side_effects="pure",
    required_permission="capability:invoke",
    interaction="request_response",
)


class Classifier:
    """Generic capability: Classify a set of feature vectors using a classical ML model."""

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
                f"Classifier: optional dependency missing. "
                f"Install blite-cap-ml[sklearn]: {exc}"
            ) from exc

    def _invoke_impl(self, inputs: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(
            "Classifier: implementation not yet provided. Install blite-cap-ml[sklearn]."
        )
