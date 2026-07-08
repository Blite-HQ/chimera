"""
derive() — permission intersection, guaranteed by construction.

knowledge/trust/08-identidad-lite-kagenti.md SS1.3 (ADR-018): a delegate can
only attenuate a parent identity's permissions, never expand them. This is a
pure function — intersection is set algebra, not a policy decision to get
wrong — proven by property test in
tests/unit/identity/test_derive_property.py.
"""

from __future__ import annotations

from blite.identity.identity import Identity


def derive(parent: Identity, requested: frozenset[str]) -> Identity:
    """Attenuate `parent` to the intersection of its permissions and `requested`."""
    return parent.model_copy(update={"permissions": parent.permissions & requested})
