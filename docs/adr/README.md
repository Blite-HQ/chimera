# Architecture Decision Records

> **Estado: VIGENTE-CON-DRIFT (2026-07-30).** The promotion criterion below is current, but
> the "Enforced by" column does not reflect import-linter contracts and invariant gates added
> after this index was written; refresh deferred to the final refactoring pass (backlog #118).

An ADR captures a significant architectural decision: the context that forced it, the
decision itself, and its consequences (trade-offs accepted, alternatives rejected). Format
follows Michael Nygard's original template — see [`adr-template.md`](adr-template.md).

**Naming:** `ADR-<id>-<slug>.md`, where `<id>` matches the identifier already used in
[`../invariants.md`](../invariants.md), code comments, and `import-linter` contract names —
not a separate sequential counter. This keeps one traceable ID across doc, code, and gate.

## Status legend

| Status     | Meaning                                                                                                                                                  |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Accepted   | Decided and reflected in `invariants.md` and/or an enforced gate.                                                                                        |
| Referenced | Cited in research notes ([`../../knowledge/trust/`](../../knowledge/trust/)) as input to a decision still being evaluated — not yet a Chimera-owned ADR. |

## Index

| ID                                        | Title                                                                                           | Status     | Enforced by                                                                                                                      |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------- |
| [ADR-008](ADR-008-capability-boundary.md) | Science capabilities are outside the engine core                                                | Accepted   | `import-linter` contract `ADR-008`; `tests/smoke/test_plugin_mechanism.py`                                                       |
| [ADR-029](ADR-029-generic-manifests.md)   | Capability manifests are generic                                                                | Accepted   | `tests/invariants/test_capability_genericity.py`                                                                                 |
| ADR-013                                   | Universal `Capability` port vs. adopting an external protocol (MCP/A2A) as the core abstraction | Referenced | Not yet formalized — tracked in `knowledge/trust/06-protocolos-capability-mcp-a2a.md`                                            |
| ADR-016                                   | Tamper-evident event log shape (hash-chain)                                                     | Referenced | Not yet formalized — tracked in `knowledge/trust/01-event-sourcing-postgres.md`                                                  |
| ADR-017                                   | Verification policy as a declarative engine, separate from verifier mechanism                   | Referenced | Not yet formalized — tracked in `knowledge/trust/05-verificacion-adaptativa-politica-tradeoffs.md`                               |
| ADR-018                                   | Attenuable capabilities (not boolean allow/deny)                                                | Referenced | Not yet formalized — tracked in `knowledge/trust/08-identidad-lite-kagenti.md`                                                   |
| ADR-021                                   | Event log separation of concerns                                                                | Referenced | Not yet formalized — tracked in `knowledge/trust/01-event-sourcing-postgres.md`                                                  |
| ADR-027                                   | Verifier-never-a-model, reinforced by competitive landscape review                              | Referenced | Overlaps `INV-2`/`PR2` (already Accepted, see `invariants.md`) — the ADR itself covering the landscape review is not yet written |

**Why only two are "Accepted":** ADR-008 and ADR-029 are the only IDs with a full
statement + rationale + enforced gate already frozen in `invariants.md` today. The other six
are cited across `knowledge/trust/*` notes as input from Chimera's own reference
architecture review — still being evaluated for what to formalize, not decisions frozen into
`invariants.md` yet. Listing them as ADR files here would misattribute provenance. Promote a row to
"Accepted" (and add its `ADR-<id>-*.md` file) only once its decision lands in `invariants.md`
with a real enforcement gate — mirrors the rule in [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md):
"if `lint-imports` or an invariant test fails, fix the code, not the test."
