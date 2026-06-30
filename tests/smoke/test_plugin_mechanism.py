"""
Smoke test: the plugin mechanism (entry-point discovery) works end to end.

This test validates the ADR-008 architecture:
  - capabilities/ packages register entry points
  - the engine discovers them via blite_capability.registry
  - the engine never imports capabilities directly
"""

from __future__ import annotations

from blite.runtime.registry import load_capabilities
from blite_capability.registry import discover_capabilities


def test_registry_does_not_crash() -> None:
    """Registry discovery runs without errors (even if no capabilities installed)."""
    caps = discover_capabilities()
    assert isinstance(caps, dict)


def test_engine_registry_uses_sdk() -> None:
    """Engine's load_capabilities delegates to the SDK (no direct imports)."""
    caps = load_capabilities()
    assert isinstance(caps, dict)


def test_all_discovered_caps_have_manifests() -> None:
    """Every discovered capability exposes a valid manifest."""
    caps = discover_capabilities()
    for name, cap in caps.items():
        manifest = cap.manifest
        assert manifest.id, f"Capability {name!r}: manifest.id is empty"
        assert manifest.description, (
            f"Capability {name!r}: manifest.description is empty"
        )
        assert isinstance(manifest.input_schema, dict), (
            f"Capability {name!r}: input_schema is not a dict"
        )
        assert isinstance(manifest.output_schema, dict), (
            f"Capability {name!r}: output_schema is not a dict"
        )


def test_all_discovered_caps_are_invocable() -> None:
    """Every discovered capability has an invoke() method."""
    caps = discover_capabilities()
    for name, cap in caps.items():
        assert hasattr(cap, "invoke") and callable(cap.invoke), (
            f"Capability {name!r} does not implement invoke()"
        )
