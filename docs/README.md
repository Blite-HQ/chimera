# Documentation Index

## Status legend (imported architecture set)

| Estado                   | Meaning                                                                                                                    |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| CONGELADO                | Frozen — not open for revision. A research note that contradicts it is data about the note, not grounds to change the doc. |
| VIGENTE                  | Current — reflects the active project decision.                                                                            |
| PARCIALMENTE SUPERSEDIDO | Partially superseded — some sections current, others superseded. The doc's own status header states the split.             |
| SEMILLA                  | Seed — an initial-research draft to be translated/adjusted (see `contract-freeze.md`), not implemented as-is.              |

Each imported doc carries its status as a blockquote right under the title — that header is the
authoritative freshness signal, not any internal "state" remark further down (those are kept for
historical record, relabeled "Nota original" where they could otherwise read as current).

## Index

| Doc                                                            | What it is                                                                                                                                                                                                   |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [`invariants.md`](invariants.md)                               | **Frozen constitution.** The logical invariants (INV-_, AX_, ADR-*) enforced by CI gates. Not subject to revision — see status header.                                                                       |
| [`base-logica-formal.md`](base-logica-formal.md)               | CONGELADO. The formal logical system (primitives, axioms, principles, theorems) that `invariants.md` distills into enforceable gates.                                                                        |
| [`arquitectura-python.md`](arquitectura-python.md)             | VIGENTE. The active architecture: Python-dominant core (FastAPI) reconciled with the team's pragmatic build, TypeScript reserved for the Studio.                                                             |
| [`arquitectura-arc42-adrs.md`](arquitectura-arc42-adrs.md)     | VIGENTE salvo ADR-001/002/012. arc42/C4 views, invariant-to-component mapping, and the ADR decision log (the superseded rows are TS-core specific).                                                          |
| [`arquitectura-reconciliada.md`](arquitectura-reconciliada.md) | PARCIALMENTE SUPERSEDIDO. Agent/runtime model, QUBO formulation, protocol map, ablation design, and the Plan A/B/C pivot mechanism are current; its TS-core sections are not (see `arquitectura-python.md`). |
| [`especificacion-contratos.md`](especificacion-contratos.md)   | SEMILLA. Initial-research TypeScript contract shapes — `contract-freeze.md` is the current source of truth for what changes on translation to Pydantic.                                                      |
| [`esquema-datos.md`](esquema-datos.md)                         | SEMILLA. Initial-research PostgreSQL schema — `contract-freeze.md` §2 confirms 3 adjustments on top of it.                                                                                                   |
| [`contract-freeze.md`](contract-freeze.md)                     | DRAFT: data-contract changes proposed by the trust-plane research, pending merge with the execution-plane review before freeze.                                                                              |
| [`deployment.md`](deployment.md)                               | Phase-2 reference design for BYOC/managed hosting on AWS. Not built during the hackathon month — today's code must simply not preclude it.                                                                   |
| [`adr/`](adr/)                                                 | Architecture Decision Records — the "why" behind decisions referenced from `invariants.md` and code.                                                                                                         |
| [`research/`](research/)                                       | Academic home: methodology, bibliography, and paper drafts. Complements the applied notes in [`../knowledge/`](../knowledge/).                                                                               |

## Where things live

- **Frozen rules** (what must always hold, enforced by tests/import-linter): `invariants.md`.
- **Why a rule exists** (context, alternatives considered, consequences): `adr/`.
- **Applied research per problem area** (QUBO mapping, verification methods, protocols): [`../knowledge/`](../knowledge/).
- **Academic framing** (paper draft, related work, methodology): `research/`.
- **Specs** (when introduced): will land under `docs/specs/`, one file per capability/feature, cross-referencing the invariant(s) they must not violate. Not yet created — this is a placeholder convention so future specs have a defined home.

## Conventions

- English for anything CI-gated (`invariants.md`, `adr/`). Root reference docs authored by the trust-plane research (`contract-freeze.md`, the imported architecture set above) keep their original Spanish — translating them isn't planned; add an English summary here if a future contributor needs one. Research notes under `knowledge/` follow the same rule.
- Every frozen invariant in `invariants.md` carries an `<!-- enforced: path::symbol -->` anchor; `tests/invariants/test_enforced_anchors.py` fails the build if an anchor stops resolving.
