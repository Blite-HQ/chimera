"""Guardrails — policy enforcement (must not import authz or protocols — INV-3)."""

from __future__ import annotations

from blite.guardrails.signal import Signal

__all__ = ["Signal"]
