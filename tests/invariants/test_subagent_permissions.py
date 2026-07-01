"""
Sub-agent permission intersection (Agentic Top 10 — Excessive Agency /
Privilege Compromise).

Base lógica principle (soberanía + no-elusión applied to delegation): a
sub-agent may only ever *reduce* the tool/permission surface of the system
it runs in, never expand it. This test parses the YAML frontmatter `tools:`
list of every Claude sub-agent definition under tools/claude/agents/ and
asserts it is a subset of an explicit allowed superset.

If a new sub-agent legitimately needs a tool outside the superset (e.g. Edit,
Write for a fixer agent), add it to ALLOWED_SUPERSET deliberately — this test
exists so that expansion is a visible, reviewed decision, not something that
slips in unnoticed.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

AGENTS_DIR = Path(__file__).parents[2] / "tools" / "claude" / "agents"

# The maximum tool surface any sub-agent in this repo may declare today.
# Read-only + shell (Bash) — no Edit/Write/Task/Agent (no self-replication,
# no autonomous file mutation) unless explicitly widened here.
ALLOWED_SUPERSET = frozenset({"Read", "Grep", "Glob", "Bash"})

FRONTMATTER_PATTERN = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
TOOLS_LINE_PATTERN = re.compile(r"^tools:\s*(.+)$", re.MULTILINE)


def _agent_files() -> list[Path]:
    if not AGENTS_DIR.exists():
        return []
    return sorted(AGENTS_DIR.glob("*.md"))


def _parse_tools(text: str) -> list[str]:
    """Extract the `tools:` frontmatter value as a list of tool names.

    Supports both `tools: ['A', 'B']` (YAML flow list) and
    `tools: A, B` (bare comma-separated) forms.
    """
    frontmatter_match = FRONTMATTER_PATTERN.match(text)
    assert frontmatter_match, "Agent file has no YAML frontmatter block"

    tools_match = TOOLS_LINE_PATTERN.search(frontmatter_match.group(1))
    assert tools_match, "Agent frontmatter has no `tools:` key"

    raw = tools_match.group(1).strip().strip("[]")
    return [t.strip().strip("'\"") for t in raw.split(",") if t.strip()]


_AGENT_FILES = _agent_files()


@pytest.mark.skipif(not _AGENT_FILES, reason="No sub-agent definitions found")
@pytest.mark.parametrize("agent_path", _AGENT_FILES, ids=lambda p: p.name)
def test_subagent_tools_are_subset_of_allowed_superset(agent_path: Path) -> None:
    """Every sub-agent's declared tools must be a subset of ALLOWED_SUPERSET."""
    tools = set(_parse_tools(agent_path.read_text()))
    excess = tools - ALLOWED_SUPERSET
    assert not excess, (
        f"{agent_path.name} declares tools outside the allowed superset: "
        f"{sorted(excess)}. Sub-agents may only reduce permissions, never "
        f"expand them (Agentic Top 10 — Excessive Agency). If this is "
        f"intentional, widen ALLOWED_SUPERSET here deliberately."
    )
