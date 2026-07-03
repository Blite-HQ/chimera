# ADR-008 — Science capabilities are outside the engine core

**Status:** Accepted

## Context

Chimera combines a small, stable execution core (gateway, runtime, verification, events,
authz) with a growing, heterogeneous set of scientific tools — QUBO solvers, graph
algorithms, physics simulators, quantum backends. These tools have very different
dependency footprints (OR-Tools, Qiskit, pandapower, scikit-learn) and different rates of
change. Coupling the engine to any one of them would force every engine change to consider
every tool's API, and every tool upgrade to risk the core.

## Decision

The engine package (`blite`) must not import any capability package (`blite_cap_*`).
Capabilities are plugins, discovered at runtime via Python entry points
(`blite.capabilities`), never imported directly. The only interface shared between the
engine and capabilities is the SDK (`blite_capability`): `Capability` protocol +
`CapabilityManifest` + registry.

## Consequences

- New capabilities can be added, removed, or reworked without touching engine code.
- The engine stays free of heavy scientific dependencies (Qiskit, pandapower, etc.) —
  smaller attack surface, faster core test suite.
- A capability cannot reach into engine internals to bypass the gateway/authz/verification
  boundary, even by accident — the import graph makes it structurally impossible, not just
  discouraged by convention.
- Enforced by `import-linter` contract `ADR-008` (forbidden-import, both directions) and
  `tests/smoke/test_plugin_mechanism.py::test_registry_does_not_crash`. See
  `<!-- enforced: pyproject.toml::ADR-008 -->` in `docs/invariants.md`.
