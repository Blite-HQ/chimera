"""Smoke tests for the blite-capability SDK."""

from __future__ import annotations

from blite_capability import Capability, CapabilityManifest, discover_capabilities


def test_imports_work() -> None:
    """All public SDK symbols are importable."""
    assert Capability is not None
    assert CapabilityManifest is not None
    assert discover_capabilities is not None


def test_capability_manifest_creation() -> None:
    """CapabilityManifest can be created with required fields."""
    m = CapabilityManifest(
        id="blite.test.capability",
        description="A generic test capability",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
    )
    assert m.id == "blite.test.capability"
    assert m.version == "0.1.0"
    assert m.tags == ()


def test_registry_returns_dict() -> None:
    """discover_capabilities() returns a dict (even if empty)."""
    caps = discover_capabilities()
    assert isinstance(caps, dict)
