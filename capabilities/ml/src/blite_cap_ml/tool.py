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


_TABULAR_PREP_MANIFEST = CapabilityManifest(
    id="blite.ml.tabular_prep",
    description=(
        "Prepare tabular rows for binary classification with a leakage-safe "
        "pipeline: stratified fold assignment committed before any fit, then "
        "per-fold median imputation, top-k feature selection by importance, "
        "and min-max scaling — every fit restricted to the train split."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "rows": {
                "type": "array",
                "description": "List of feature rows (numbers or null for missing values)",
            },
            "labels": {
                "type": "array",
                "description": "Binary (0/1) label per row",
            },
            "n_folds": {"type": "integer", "default": 5, "minimum": 2},
            "seed": {"type": "integer", "default": 1},
            "n_features": {
                "type": "integer",
                "default": 4,
                "description": "Number of top features to select by importance",
            },
        },
        "required": ["rows", "labels"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "folds": {"type": "array", "description": "Fold index per row"},
            "n_folds": {"type": "integer"},
            "seed": {"type": "integer"},
            "feature_indices": {
                "type": "array",
                "description": "Selected raw-column indices per fold",
            },
            "prepared": {
                "type": "array",
                "description": "Per-fold prepared train/test feature matrices and labels",
            },
            "fold_sizes": {"type": "array", "description": "Per-fold train/test row counts"},
        },
        "required": [
            "folds",
            "n_folds",
            "seed",
            "feature_indices",
            "prepared",
            "fold_sizes",
        ],
    },
    tags=("ml", "preprocessing", "tabular", "classification"),
    side_effects="pure",
    required_permission="capability:invoke",
    interaction="request_response",
)


class TabularPrep:
    """Generic capability: leakage-safe tabular preprocessing pipeline for
    binary classification (fold-committed, per-fold impute/select/scale)."""

    @property
    def manifest(self) -> CapabilityManifest:
        return _TABULAR_PREP_MANIFEST

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Invoke the capability. Heavy deps loaded lazily on first call."""
        return self._run(inputs)

    def _run(self, inputs: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._invoke_impl(inputs)
        except ImportError as exc:
            raise ImportError(
                f"TabularPrep: optional dependency missing. "
                f"Install blite-cap-ml[sklearn]: {exc}"
            ) from exc

    def _invoke_impl(self, inputs: dict[str, Any]) -> dict[str, Any]:
        from blite_cap_ml.tabular_prep import tabular_prep

        return tabular_prep(inputs)


_SVM_PRECOMPUTED_MANIFEST = CapabilityManifest(
    id="blite.ml.svm_precomputed",
    description=(
        "Fit and evaluate a binary SVM over a precomputed kernel (Gram) "
        "matrix, reporting predictions, dual coefficients and a full metric "
        "set (accuracy alone is documented as insufficient under class "
        "imbalance)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "kernel_train": {"type": "array", "description": "Train-vs-train Gram matrix (m x m)"},
            "kernel_test": {"type": "array", "description": "Test-vs-train Gram matrix (k x m)"},
            "labels_train": {"type": "array", "description": "Binary (0/1) labels, length m"},
            "labels_test": {"type": "array", "description": "Binary (0/1) labels, length k"},
            "seed": {"type": "integer", "default": 1},
            "c": {"type": "number", "default": 1.0, "description": "SVM regularization strength"},
        },
        "required": ["kernel_train", "kernel_test", "labels_train", "labels_test"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "predictions": {"type": "array", "description": "Predicted labels on the test set"},
            "dual_coef": {"type": "array"},
            "intercept": {"type": "array"},
            "support_indices": {"type": "array"},
            "accuracy": {"type": "number"},
            "precision": {"type": "number"},
            "recall": {"type": "number"},
            "f1": {"type": "number"},
            "confusion_matrix": {"type": "array"},
        },
        "required": [
            "predictions",
            "dual_coef",
            "intercept",
            "support_indices",
            "accuracy",
            "precision",
            "recall",
            "f1",
            "confusion_matrix",
        ],
    },
    tags=("ml", "classification", "svm", "kernel"),
    side_effects="pure",
    required_permission="capability:invoke",
    interaction="request_response",
)


class SvmPrecomputed:
    """Generic capability: binary SVM over a precomputed kernel matrix."""

    @property
    def manifest(self) -> CapabilityManifest:
        return _SVM_PRECOMPUTED_MANIFEST

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Invoke the capability. Heavy deps loaded lazily on first call."""
        return self._run(inputs)

    def _run(self, inputs: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._invoke_impl(inputs)
        except ImportError as exc:
            raise ImportError(
                f"SvmPrecomputed: optional dependency missing. "
                f"Install blite-cap-ml[sklearn]: {exc}"
            ) from exc

    def _invoke_impl(self, inputs: dict[str, Any]) -> dict[str, Any]:
        from blite_cap_ml.svm_precomputed import svm_precomputed

        return svm_precomputed(inputs)


_CLASSIFIER_BASELINE_MANIFEST = CapabilityManifest(
    id="blite.ml.classifier_baseline",
    description=(
        "Official cross-validated RBF-SVM baseline for binary tabular "
        "classification: stratified 5-fold CV, out-of-fold predictions, "
        "per-fold and aggregate metrics, and an optional exact McNemar "
        "comparison against a second model's predictions. Optionally fits "
        "over externally prepared per-fold matrices (same shape as another "
        "pipeline's precomputed features) so that a comparison isolates the "
        "kernel/model, not the preprocessing."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "rows": {
                "type": "array",
                "description": "List of feature rows (numbers or null for missing values)",
            },
            "labels": {"type": "array", "description": "Binary (0/1) label per row"},
            "n_folds": {"type": "integer", "default": 5, "minimum": 2},
            "seed": {"type": "integer", "default": 1},
            "c": {"type": "number", "default": 1.0},
            "gamma": {
                "type": ["string", "number"],
                "description": "'scale', 'auto', or a positive number",
                "default": "scale",
            },
            "compare_predictions": {
                "type": "array",
                "description": (
                    "Optional binary predictions from another model, aligned "
                    "row-for-row with 'rows'/'labels' — triggers the McNemar "
                    "comparison in the output"
                ),
            },
            "prepared_folds": {
                "type": "array",
                "description": (
                    "Optional: one entry per fold, each "
                    "{'train': {'features','labels'}, 'test': {'features',"
                    "'labels'}} — same shape as another preprocessing "
                    "pipeline's per-fold output. When given (together with "
                    "'folds'), the model fits directly on these matrices "
                    "instead of recomputing its own split/imputation from "
                    "'rows'."
                ),
            },
            "folds": {
                "type": "array",
                "description": (
                    "Required alongside 'prepared_folds': the row-to-fold "
                    "assignment used to reassemble out-of-fold predictions "
                    "in the same order as 'rows'/'labels'."
                ),
            },
        },
        "required": ["rows", "labels"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "n_folds": {"type": "integer"},
            "seed": {"type": "integer"},
            "predictions": {"type": "array", "description": "Out-of-fold predictions"},
            "fold_metrics": {"type": "array", "description": "Per-fold metrics"},
            "aggregate": {"type": "object", "description": "Metrics over concatenated OOF predictions"},
            "mcnemar": {
                "type": "object",
                "description": "b/c discordant pairs and exact p-value (present only when compare_predictions was supplied)",
            },
        },
        "required": ["n_folds", "seed", "predictions", "fold_metrics", "aggregate"],
    },
    tags=("ml", "classification", "svm", "baseline"),
    side_effects="pure",
    required_permission="capability:invoke",
    interaction="request_response",
)


class ClassifierBaseline:
    """Generic capability: official CV-5 RBF-SVM baseline with optional
    McNemar comparison against another model's predictions; optionally fits
    over externally prepared per-fold matrices so the comparison isolates
    the model, not the preprocessing."""

    @property
    def manifest(self) -> CapabilityManifest:
        return _CLASSIFIER_BASELINE_MANIFEST

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Invoke the capability. Heavy deps loaded lazily on first call."""
        return self._run(inputs)

    def _run(self, inputs: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._invoke_impl(inputs)
        except ImportError as exc:
            raise ImportError(
                f"ClassifierBaseline: optional dependency missing. "
                f"Install blite-cap-ml[sklearn]: {exc}"
            ) from exc

    def _invoke_impl(self, inputs: dict[str, Any]) -> dict[str, Any]:
        from blite_cap_ml.classifier_baseline import classifier_baseline

        return classifier_baseline(inputs)
