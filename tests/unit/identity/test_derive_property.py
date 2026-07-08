"""
derive() — guaranteed permission intersection (ficha B2 piece 4).

knowledge/trust/08-identidad-lite-kagenti.md SS1.3 (ADR-018): a delegate can
only attenuate a parent identity's permissions, never expand them —
`permissions(derived) = permissions(parent) ∩ requested`, proven here as a
Hypothesis property over arbitrary permission sets rather than fixed examples.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from blite.identity.derive import derive
from blite.identity.identity import Identity

_PERMISSION_NAMES = st.sampled_from(
    [
        "capability:solver.qubo:invoke",
        "run:create",
        "capability:sim.powerflow:invoke",
        "admin:override",
        "run:read",
    ]
)
_PERMISSION_SETS = st.frozensets(_PERMISSION_NAMES, max_size=5)


def _identity(permissions: frozenset[str]) -> Identity:
    return Identity(
        id="user:dylan", kind="human", domain_id="d-default", permissions=permissions
    )


@given(parent_permissions=_PERMISSION_SETS, requested=_PERMISSION_SETS)
def test_derive_never_grants_a_permission_absent_from_the_parent(
    parent_permissions: frozenset[str], requested: frozenset[str]
) -> None:
    parent = _identity(parent_permissions)
    derived = derive(parent, requested)
    assert derived.permissions.issubset(parent.permissions)


@given(parent_permissions=_PERMISSION_SETS, requested=_PERMISSION_SETS)
def test_derive_is_exactly_the_intersection(
    parent_permissions: frozenset[str], requested: frozenset[str]
) -> None:
    parent = _identity(parent_permissions)
    derived = derive(parent, requested)
    assert derived.permissions == parent_permissions & requested


@given(parent_permissions=_PERMISSION_SETS)
def test_derive_with_full_parent_permissions_requested_returns_parent_permissions(
    parent_permissions: frozenset[str],
) -> None:
    parent = _identity(parent_permissions)
    derived = derive(parent, parent_permissions)
    assert derived.permissions == parent_permissions


def test_derive_preserves_identity_metadata() -> None:
    parent = Identity(
        id="user:dylan",
        kind="human",
        domain_id="d-default",
        permissions=frozenset({"run:create", "capability:solver.qubo:invoke"}),
    )
    derived = derive(parent, frozenset({"run:create"}))
    assert derived.id == parent.id
    assert derived.kind == parent.kind
    assert derived.domain_id == parent.domain_id
    assert derived.permissions == frozenset({"run:create"})
