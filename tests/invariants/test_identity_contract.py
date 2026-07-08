"""
Identity contract tests (ficha B2 piece 4 — docs/contract-freeze.md SS8).

knowledge/trust/08-identidad-lite-kagenti.md SS1.3: id is a stable URN in the
SPIFFE-shaped form `(user|agent|service):[a-z0-9-]+`.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from blite.identity.identity import Identity


def test_identity_accepts_a_well_formed_urn() -> None:
    identity = Identity(
        id="user:dylan",
        kind="human",
        domain_id="d-default",
        permissions=frozenset({"run:create"}),
    )
    assert identity.id == "user:dylan"


@pytest.mark.parametrize(
    "bad_id",
    [
        "User:dylan",  # kind must be lowercase
        "admin:dylan",  # kind must be user|agent|service
        "user:",  # empty suffix
        "user: dylan",  # whitespace
        "user:Dylan",  # suffix must be lowercase
        "userx",  # missing colon
    ],
)
def test_identity_rejects_a_malformed_urn(bad_id: str) -> None:
    with pytest.raises(ValidationError):
        Identity(
            id=bad_id, kind="human", domain_id="d-default", permissions=frozenset()
        )


def test_identity_is_frozen() -> None:
    identity = Identity(
        id="user:dylan", kind="human", domain_id="d-default", permissions=frozenset()
    )
    with pytest.raises(ValidationError):
        identity.domain_id = "d-other"


def test_identity_permissions_coerces_a_list_into_a_frozenset() -> None:
    identity = Identity.model_validate(
        {
            "id": "agent:planner-7",
            "kind": "agent",
            "domain_id": "d-default",
            "permissions": ["a", "b", "a"],
        }
    )
    assert identity.permissions == frozenset({"a", "b"})
    assert isinstance(identity.permissions, frozenset)
