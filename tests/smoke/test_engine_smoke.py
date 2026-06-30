"""Smoke tests for the REDACTED skeleton."""

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
    # If any import fails, pytest reports the import error above
    assert blite is not None


def test_runtime_registry_importable() -> None:
    """blite.runtime.registry is importable and exposes load_capabilities."""
    from blite.runtime.registry import load_capabilities

    assert callable(load_capabilities)


def test_events_writer_importable_within_events() -> None:
    """blite.events.writer is importable (for use within events only — INV-5)."""
    from blite.events.writer import Event, append, read_all

    assert Event is not None
    assert callable(append)
    assert callable(read_all)
