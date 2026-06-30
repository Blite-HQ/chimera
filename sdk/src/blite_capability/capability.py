"""
Capability port.

All capability packages implement this Protocol. The engine
uses this interface exclusively — it never imports concrete
capability implementations (ADR-008).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .manifest import CapabilityManifest


@runtime_checkable
class Capability(Protocol):
    """Generic capability port — all capability packages implement this."""

    @property
    def manifest(self) -> CapabilityManifest:
        """Return the capability manifest (generic, no scenario terms — ADR-029)."""
        ...

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Invoke the capability with generic inputs; return generic outputs."""
        ...
