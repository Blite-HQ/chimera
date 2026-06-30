"""
Runtime capability registry.

This module is the ONLY place in the engine that bridges to capabilities.
It uses the SDK discovery function (blite_capability.registry) and never
imports any concrete capability package directly (ADR-008).
"""

from __future__ import annotations

from blite_capability.capability import Capability
from blite_capability.registry import discover_capabilities


def load_capabilities() -> dict[str, Capability]:
    """Discover and return all registered capabilities at runtime.

    Capabilities are discovered via Python entry points
    (group="blite.capabilities") — never via direct imports.
    This preserves the engine ⊥ capabilities boundary (ADR-008).

    Returns:
        Mapping of capability ID → Capability instance.
    """
    return discover_capabilities()
