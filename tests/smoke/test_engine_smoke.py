"""Smoke tests for the Chimera engine skeleton."""

from __future__ import annotations

import blite
import blite.authz
import blite.certificate
import blite.events
import blite.gateway
import blite.guardrails
import blite.identity
import blite.protocols
import blite.runtime
import blite.serving
import blite.verification


def test_all_engine_subpackages_importable() -> None:
    """All engine subpackages are importable (skeleton check)."""
    # If any import fails, pytest reports the import error above. Referencing
    # each submodule (not just importing it) keeps this a pure importability
    # check while satisfying strict unused-import checking.
    assert blite is not None
    assert blite.authz is not None
    assert blite.certificate is not None
    assert blite.events is not None
    assert blite.gateway is not None
    assert blite.guardrails is not None
    assert blite.identity is not None
    assert blite.protocols is not None
    assert blite.runtime is not None
    assert blite.serving is not None
    assert blite.verification is not None


def test_runtime_registry_importable() -> None:
    """blite.runtime.registry is importable and exposes load_capabilities."""
    from blite.runtime.registry import load_capabilities

    assert callable(load_capabilities)


def test_events_writer_importable_within_events() -> None:
    """blite.events.writer is importable (for use within events only — INV-5)."""
    from blite.events.writer import InMemoryEventStore

    assert InMemoryEventStore is not None
    assert callable(InMemoryEventStore.append)
    assert callable(InMemoryEventStore.read_stream)
    assert callable(InMemoryEventStore.read_all)
