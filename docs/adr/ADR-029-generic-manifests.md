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
