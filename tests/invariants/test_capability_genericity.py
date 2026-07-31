"""
ADR-029 enforcement: all registered CapabilityManifests must use generic terms.

Loads every capability registered under the "blite.capabilities" entry-point
group and fails if any manifest field contains a scenario-specific term from
tests/invariants/scenario_denylist.txt.
"""

from __future__ import annotations

import dataclasses
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
    """Serialize the COMPLETE manifest to a lowercase JSON string (S-E/#127).

    `dataclasses.asdict` covers every field — including `required_permission`,
    `tags`, `version` and the 4 v2 fields: a permission or tag with scenario
    vocabulary is the same leak as a schema with it (ADR-029).
    """
    if dataclasses.is_dataclass(manifest) and not isinstance(manifest, type):
        return json.dumps(dataclasses.asdict(manifest), default=str).lower()
    return json.dumps(vars(manifest), default=str).lower()


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
        if isinstance(cap, type):
            # Entry points register classes (ADR-008); reading `.manifest` on
            # the CLASS returns the property object — the pre-S-E gate did
            # exactly that and silently scanned empty text. Instantiate first.
            cap = cap()
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


def test_manifest_text_covers_the_complete_manifest() -> None:
    """S-E/#127: el gate serializa el manifest COMPLETO — un permiso o tag con
    vocabulario de escenario es la misma fuga que un schema con él (ADR-029)."""
    from blite_capability.manifest import CapabilityManifest

    manifest = CapabilityManifest(
        id="blite.example.echo",
        description="generic echo",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        side_effects="pure",
        required_permission="capability:invoke:marker-permission",
        interaction="request_response",
        version="9.9.9-marker",
        tags=("marker-tag",),
    )
    text = _manifest_text(manifest)
    assert "marker-permission" in text
    assert "marker-tag" in text
    assert "9.9.9-marker" in text
    assert "request_response" in text
    assert "pure" in text
    assert "in-process" in text
