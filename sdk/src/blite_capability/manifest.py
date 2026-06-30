"""
CapabilityManifest.

Describes a generic capability. Schemas must use domain-agnostic
terms (ADR-029). The manifest is frozen (immutable) by design.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CapabilityManifest:
    """Immutable descriptor for a generic capability.

    Both `input_schema` and `output_schema` must use generic terminology
    (ADR-029). Terms like "islanding", "grid", "water quality", or specific
    molecule names belong in the agent's knowledge base, not here.

    Example (correct — generic):
        id="blite.solvers.qubo"
        input_schema={"type": "object", "properties": {"matrix": {"type": "array"}}}

    Example (wrong — scenario-specific):
        id="blite.solvers.islanding-partitioner"  # ← violates ADR-029
    """

    id: str
    """Unique capability identifier in reverse-domain notation."""

    description: str
    """Short generic description (no scenario terms — ADR-029)."""

    input_schema: dict[str, Any]
    """JSON-Schema-compatible dict describing the generic input structure."""

    output_schema: dict[str, Any]
    """JSON-Schema-compatible dict describing the generic output structure."""

    version: str = "0.1.0"
    """Semantic version of this capability implementation."""

    tags: tuple[str, ...] = field(default_factory=tuple)
    """Optional classification tags (e.g., "solver", "quantum", "simulation")."""
