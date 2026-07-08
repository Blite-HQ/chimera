"""
AnchorKind — the closed set of non-model anchors a Verifier may rest on.

PR2/ADR-027 (base logica): the verifier is never a model. "model" has no
value in this Literal by construction — see
tests/invariants/test_verifier_contract.py for the negative pyright test.
"""

from __future__ import annotations

from typing import Literal

AnchorKind = Literal["solver", "execution", "dataset", "rule", "human"]
