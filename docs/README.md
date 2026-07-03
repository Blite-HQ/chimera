# Documentation Index

| Doc                                        | What it is                                                                                                                             |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| [`invariants.md`](invariants.md)           | **Frozen constitution.** The logical invariants (INV-_, AX_, ADR-*) enforced by CI gates. Not subject to revision — see status header. |
| [`contract-freeze.md`](contract-freeze.md) | DRAFT: data-contract changes proposed by the trust-plane research, pending merge with the execution-plane review before freeze.        |
| [`adr/`](adr/)                             | Architecture Decision Records — the "why" behind decisions referenced from `invariants.md` and code.                                   |
| [`research/`](research/)                   | Academic home: methodology, bibliography, and paper drafts. Complements the applied notes in [`../knowledge/`](../knowledge/).         |

## Where things live

- **Frozen rules** (what must always hold, enforced by tests/import-linter): `invariants.md`.
- **Why a rule exists** (context, alternatives considered, consequences): `adr/`.
- **Applied research per problem area** (QUBO mapping, verification methods, protocols): [`../knowledge/`](../knowledge/).
- **Academic framing** (paper draft, related work, methodology): `research/`.
- **Specs** (when introduced): will land under `docs/specs/`, one file per capability/feature, cross-referencing the invariant(s) they must not violate. Not yet created — this is a placeholder convention so future specs have a defined home.

## Conventions

- English for anything CI-gated or repo-facing (`invariants.md`, `adr/`, root docs). Research notes under `knowledge/` may be in Spanish where that is the working language of the author.
- Every frozen invariant in `invariants.md` carries an `<!-- enforced: path::symbol -->` anchor; `tests/invariants/test_enforced_anchors.py` fails the build if an anchor stops resolving.
