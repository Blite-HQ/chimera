"""
CapabilityManifest.

Describes a generic capability. Schemas must use domain-agnostic
terms (ADR-029). The manifest is frozen (immutable) by design.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

SIDE_EFFECTS_VALUES: tuple[str, ...] = (
    "pure",
    "reversible-external",
    "irreversible-external",
)
INTERACTION_VALUES: tuple[str, ...] = ("request_response", "job", "stream")
EXECUTION_PROFILE_VALUES: tuple[str, ...] = ("in-process", "service", "remote-job")


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

    side_effects: Literal["pure", "reversible-external", "irreversible-external"]
    """Risk axis consumed by Policy (freeze §6) and the retry rule (freeze §13).
    Mandatory — no default: a defaulted risk axis would lie (#127)."""

    required_permission: str
    """Permission the gateway's authorization stage checks against the caller's
    effective intersection (freeze §8). The manifest declares; it never grants."""

    interaction: Literal["request_response", "job", "stream"]
    """Invocation shape — validated against execution_profile by the dispatch
    matrix at load time (freeze §1). Mandatory — no default (#127)."""

    version: str = "0.1.0"
    """Semantic version of this capability implementation."""

    tags: tuple[str, ...] = field(default_factory=tuple)
    """Optional classification tags (e.g., "solver", "quantum", "simulation")."""

    execution_profile: Literal["in-process", "service", "remote-job"] = "in-process"
    """Where the capability runs — the only v2 field with a default (§1 letter)."""

    def __post_init__(self) -> None:
        """Fail-closed literal validation (#127): an invalid value explodes at
        load time and the entry point lands in the registry's failed[] —
        visible, never silent."""
        if self.side_effects not in SIDE_EFFECTS_VALUES:
            msg = (
                f"side_effects {self.side_effects!r} not in {SIDE_EFFECTS_VALUES}"
                f" (manifest {self.id!r})"
            )
            raise ValueError(msg)
        if self.interaction not in INTERACTION_VALUES:
            msg = (
                f"interaction {self.interaction!r} not in {INTERACTION_VALUES}"
                f" (manifest {self.id!r})"
            )
            raise ValueError(msg)
        if self.execution_profile not in EXECUTION_PROFILE_VALUES:
            msg = (
                f"execution_profile {self.execution_profile!r} not in "
                f"{EXECUTION_PROFILE_VALUES} (manifest {self.id!r})"
            )
            raise ValueError(msg)
