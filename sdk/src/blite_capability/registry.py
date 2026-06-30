"""
Capability registry.

Discovers installed capabilities at runtime via Python entry points
(group "blite.capabilities"). The engine uses this function to
load capabilities without importing them directly (ADR-008).

Usage:
    from blite_capability.registry import discover_capabilities

    caps = discover_capabilities()
    result = caps["blite.solvers.qubo"].invoke({"matrix": [...]})
"""

from __future__ import annotations

from importlib.metadata import entry_points
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .capability import Capability


def discover_capabilities() -> dict[str, Capability]:
    """Discover all installed capabilities via entry points.

    Entry points must be registered under the group "blite.capabilities".
    Each entry point name is the capability's unique ID.

    Returns:
        Mapping of capability ID → Capability instance.
        Empty dict if no capabilities are installed.
    """
    caps: dict[str, Capability] = {}
    eps = entry_points(group="blite.capabilities")
    for ep in eps:
        cls = ep.load()
        caps[ep.name] = cls()  # instantiate: entry points register the class
    return caps
