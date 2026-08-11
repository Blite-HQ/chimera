# ADR-029 — Capability manifests are generic

**Status:** Accepted

## Context

Capabilities are meant to be reusable, domain-agnostic tools (a QUBO solver, a graph
partitioner). If a manifest's `description`/`input_schema`/`output_schema` bakes in the
name of a specific scenario (e.g. "electrical grid islanding"), the capability stops being
reusable across problems and the abstraction leaks scenario knowledge into the tool layer.

## Decision

Every registered `CapabilityManifest` must use generic, domain-agnostic terms. Example:
`"Solve a QUBO matrix → binary assignment"` (✅ generic) instead of `"Partition an
electrical grid → islands"` (❌ scenario-specific). Scenario-specific knowledge — how to
map a specific problem onto a generic capability — lives in the calling agent and the
knowledge base (`knowledge/`), never in the capability package itself.

## Consequences

- Capabilities can be reused across unrelated research problems without modification.
- Adding scenario knowledge never requires touching `capabilities/*` code — it goes in
  `knowledge/<area>/` instead, keeping the two concerns physically separated.
- A denylist (`tests/invariants/scenario_denylist.txt`) enumerates known scenario terms;
  contributors extend it as new scenario vocabulary appears.
- Enforced by `tests/invariants/test_capability_genericity.py::test_all_manifests_are_generic`,
  which scans every registered manifest against the denylist. See
  `<!-- enforced: tests/invariants/test_capability_genericity.py::test_all_manifests_are_generic -->`
  in `docs/invariants.md`.

## Known blind spot — the gate reads INSTALLED metadata, not source

`test_all_manifests_are_generic` enumerates
`importlib.metadata.entry_points(group="blite.capabilities")`. That call reads
the `dist-info` metadata a package manager (`uv sync`, `pip install`) wrote at
**install time** from each package's `[project.entry-points]` table — it does
not scan the source tree. A capability that is new in the working tree, or
whose manifest just changed, is invisible to the gate until the package is
reinstalled.

Concretely: writing a new `capabilities/<name>/src/.../tool.py` whose manifest
leaks a scenario term (e.g. "islanding", "grid"), and running the full test
suite in the same session without `uv sync --locked --all-packages
--all-extras`, **passes** `test_all_manifests_are_generic` — not because the
manifest is clean, but because the gate never saw it. This is a real,
unfixed limitation of the installed-metadata approach, not a theoretical edge
case; contributors and CI have hit it in practice, which is why the
mitigation below already exists in every capability package's test suite,
ahead of this ADR documenting it.

## Convention — every capability ships its own `TestGenericitySelfCheck`

**Every capability package MUST include a `TestGenericitySelfCheck` class in
its own test suite** (`capabilities/<name>/tests/test_*.py`) that re-runs the
SAME denylist check against the manifest imported directly from source — no
entry points, no installed metadata, so it catches a leak the moment the code
is written:

```python
class TestGenericitySelfCheck:
    """ADR-029: el gate del repo lee entry points INSTALADOS y no verá esta
    capability hasta un reinstall — esta aserción local es la que cubre en
    vivo (ver tests/invariants/test_capability_genericity.py)."""

    def test_manifest_has_no_scenario_vocabulary(self) -> None:
        import dataclasses
        import json
        from pathlib import Path

        from blite_cap_<pkg> import <CapabilityClass>

        denylist_path = (
            Path(__file__).resolve().parents[3]
            / "tests"
            / "invariants"
            / "scenario_denylist.txt"
        )
        denylist = [
            line.strip().lower()
            for line in denylist_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]

        manifest = <CapabilityClass>().manifest
        text = json.dumps(dataclasses.asdict(manifest), default=str).lower()

        violations = [term for term in denylist if term in text]
        assert not violations, (
            f"manifest contiene vocabulario de escenario: {violations}"
        )
```

This mitigation already exists, in this exact shape, in every capability
package's test suite today (`grep -rn "class TestGenericitySelfCheck"
capabilities/*/tests/`) — this ADR ratifies a pattern that was already
load-bearing in practice, rather than proposing a new one. Leaving it as
copy-pasted tribal knowledge means the _next_ capability is the one that
skips it and ships a scenario leak that stays green until someone happens to
reinstall and CI's gate finally sees it — writing it down as MANDATORY is
what turns "everyone happened to copy it" into "reviewers can block a PR
that doesn't have it."

## Honesty about what this does and does not cover

- The local check runs the SAME denylist against the SAME manifest fields as
  the installed-metadata gate, so a capability whose own test suite includes
  a passing `TestGenericitySelfCheck` is provably clean under ADR-029 the
  moment its code is written — not only after the next reinstall.
- It does **not** replace the installed-metadata gate. The local check only
  runs when that specific package's test suite runs; the installed-metadata
  gate is the one CI-wide guarantee that covers every _installed_ capability,
  including ones whose own test suite nobody happened to run this session.
  Losing either one reopens a hole the other does not cover.
- It does **not** close the blind spot itself. A capability that ships
  without its own `TestGenericitySelfCheck` is still invisible to genericity
  enforcement until the next reinstall — this convention lowers the odds by
  making the local check part of what "a capability is done" means, it does
  not make the gap structurally impossible. A stronger guard (e.g. a
  pre-commit or CI check that refuses a new `capabilities/*/src/**/tool.py`
  without a matching `TestGenericitySelfCheck` in the sibling `tests/`
  directory) is not built. This ADR does not claim the gap is closed —
  documenting the limitation honestly is the point of this section.
