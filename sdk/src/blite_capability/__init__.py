"""
blite_capability — Capability SDK.

Provides the Capability Protocol, CapabilityManifest data class,
and the entry-point-based registry. This is the only shared interface
between the engine and capability packages (ADR-008).
"""

from .capability import Capability
from .manifest import CapabilityManifest
from .registry import discover_capabilities

__all__ = ["Capability", "CapabilityManifest", "discover_capabilities"]
