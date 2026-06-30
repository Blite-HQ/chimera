"""
Enforced anchor resolution tests.

Parses docs/invariants.md, extracts all <!-- enforced: path::symbol -->
anchors, and verifies that each anchor points to an existing file
(and optionally a symbol/string within that file).

Format:
    <!-- enforced: path/to/file.py::SymbolName -->
    <!-- enforced: path/to/file.toml::string_to_find -->
    <!-- enforced: path/to/file.py -->  (file existence only)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

INVARIANTS_DOC = Path(__file__).parents[2] / "docs" / "invariants.md"
ANCHOR_PATTERN = re.compile(r"<!--\s*enforced:\s*([^\s>]+)\s*-->")


def _parse_anchors() -> list[str]:
    """Extract all enforced anchors from docs/invariants.md."""
    if not INVARIANTS_DOC.exists():
        return []
    return ANCHOR_PATTERN.findall(INVARIANTS_DOC.read_text())


def _resolve_anchor(anchor: str) -> tuple[bool, str]:
    """Return (resolved, reason) for an anchor string."""
    if "::" in anchor:
        file_part, symbol = anchor.rsplit("::", 1)
    else:
        file_part, symbol = anchor, None

    root = Path(__file__).parents[2]
    full_path = root / file_part

    if not full_path.exists():
        return False, f"File not found: {file_part}"

    if symbol:
        content = full_path.read_text()
        if symbol not in content:
            return False, f"Symbol {symbol!r} not found in {file_part}"

    return True, "ok"


_ANCHORS = _parse_anchors()


@pytest.mark.skipif(not INVARIANTS_DOC.exists(), reason="docs/invariants.md not found")
@pytest.mark.skipif(
    not _ANCHORS, reason="No enforced anchors found in docs/invariants.md"
)
@pytest.mark.parametrize("anchor", _ANCHORS)
def test_enforced_anchor_resolves(anchor: str) -> None:
    """Each <!-- enforced: ... --> anchor in docs/invariants.md must resolve."""
    resolved, reason = _resolve_anchor(anchor)
    assert resolved, (
        f"Anchor <!-- enforced: {anchor} --> in docs/invariants.md does not resolve: {reason}\n"
        f"Update the anchor or add the missing file/symbol."
    )


def test_invariants_doc_exists() -> None:
    """docs/invariants.md must exist — it is the frozen constitution."""
    assert INVARIANTS_DOC.exists(), (
        "docs/invariants.md is missing. "
        "This file is the frozen constitution of Chimera — recreate it."
    )
