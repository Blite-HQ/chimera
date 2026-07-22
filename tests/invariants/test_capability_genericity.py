"""
ADR-029 enforcement: all registered CapabilityManifests must use generic terms.

Loads every capability registered under the "blite.capabilities" entry-point
group and fails if any manifest field contains a scenario-specific term from
tests/invariants/scenario_denylist.txt.
"""

from __future__ import annotations

import json
from importlib.metadata import entry_points
from pathlib import Path

DENYLIST_PATH = Path(__file__).parent / "scenario_denylist.txt"


def _load_denylist() -> list[str]:
    """Return non-empty, non-comment lines from scenario_denylist.txt."""
    return [
        line.strip().lower()
        for line in DENYLIST_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def _manifest_text(manifest: object) -> str:
    """Serialize manifest to a lowercase JSON string for term scanning."""
    return json.dumps(
        {
            "id": getattr(manifest, "id", ""),
            "description": getattr(manifest, "description", ""),
            "input_schema": getattr(manifest, "input_schema", {}),
            "output_schema": getattr(manifest, "output_schema", {}),
        }
    ).lower()


def test_all_manifests_are_generic() -> None:
    """All registered capabilities must have generic manifests (ADR-029).

    Fails with a list of violations if any manifest field contains a
    scenario-specific term from scenario_denylist.txt.
    """
    denylist = _load_denylist()
    eps = entry_points(group="blite.capabilities")

    violations: list[str] = []
    for ep in eps:
        cap = ep.load()
        manifest = getattr(cap, "manifest", None)
        if manifest is None:
            violations.append(f"Capability '{ep.name}' has no .manifest attribute")
            continue

        text = _manifest_text(manifest)
        for term in denylist:
            if term in text:
                violations.append(
                    f"Capability '{ep.name}' manifest contains scenario term {term!r}"
                )

    assert not violations, (
        "ADR-029 violation — capabilities must be generic (no scenario terms):\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


def test_denylist_is_not_empty() -> None:
    """Sanity check: the denylist must contain at least one term."""
    assert _load_denylist(), (
        "scenario_denylist.txt is empty — add scenario terms to enforce ADR-029."
    )
