# Documentation Index

## Status legend (imported architecture set)

| Estado                   | Meaning                                                                                                                    |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| CONGELADO                | Frozen — not open for revision. A research note that contradicts it is data about the note, not grounds to change the doc. |
| VIGENTE                  | Current — reflects the active project decision.                                                                            |
| PARCIALMENTE SUPERSEDIDO | Partially superseded — some sections current, others superseded. The doc's own status header states the split.             |
| SUPERSEDIDO              | Fully superseded by a newer doc (named in its status header). Kept as historical record only.                              |
| SEMILLA                  | Seed — an initial-research draft to be translated/adjusted (see `contract-freeze.md`), not implemented as-is.              |

Each imported doc carries its status as a blockquote right under the title — that header is the
authoritative freshness signal, not any internal "state" remark further down (those are kept for
historical record, relabeled "Nota original" where they could otherwise read as current).

## Index

| Doc                                                                                      | What it is                                                                                                                                                                                                    |
| ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`invariants.md`](invariants.md)                                                         | **Frozen constitution.** The logical invariants (INV-_, AX_, ADR-*) enforced by CI gates. Not subject to revision — see status header.                                                                        |
| [`base-logica-formal.md`](base-logica-formal.md)                                         | CONGELADO. The formal logical system (primitives, axioms, principles, theorems) that `invariants.md` distills into enforceable gates.                                                                         |
| [`spec-confianza-v3-2.md`](spec-confianza-v3-2.md)                                       | CONGELADO. **Normative kernel spec of the trust layer** (v3.2 · `cal-2.4`): decision classes + AL0–AL4 + criticality, the nine entities, the calculus, Certificate/Bundle. Imported sanitized in S-E.         |
| [`perfil-stem-v1-0.md`](perfil-stem-v1-0.md)                                             | CONGELADO. **STEM Profile v1.0** — Chimera as the first distribution of the trust layer: claim schemas, curated capabilities (params by digest), research Policy templates, methodology doctrine.             |
| [`contract-freeze.md`](contract-freeze.md)                                               | **CONGELADO (2026-07-18, S-E).** The month's data contracts: trust-plane + execution-plane research merged, v3.2 vocabulary, §12–§15 (Artifact/ContentStore, hierarchical Run, event catalog, S-E decisions). |
| [`contract-freeze-anexo-canonicalizacion.md`](contract-freeze-anexo-canonicalizacion.md) | CONGELADO (annex to the freeze): exact byte-level canonicalization for `provenance_hash`/`claim_digest`/`policy_digest` (RFC 8785 + DSSE rules) with test vectors.                                            |
| [`convergencia-diseno-v32.md`](convergencia-diseno-v32.md)                               | VIGENTE (executed). The S-B convergence verdict — kept as the ladder→classes translation map (§2.1) and conflict-resolution record (§3). Its §6 actions were applied in S-E.                                  |
| [`guia-ratificacion.md`](guia-ratificacion.md)                                           | VIGENTE (process — expires once ratification closes). Per-owner ratification guide over the frozen design: project context + exact checklists for Sebas/Steven/Geovanni, deadline 23-jul.                     |
| [`especificacion-contratos-v2.md`](especificacion-contratos-v2.md)                       | SEMILLA v2. TypeScript contract shapes aligned to spec v3.2, with the convergence corrections applied at import (`[S-E]` marks). Executable truth = the Pydantic translation governed by the freeze.          |
| [`esquema-datos-v2.md`](esquema-datos-v2.md)                                             | SEMILLA v2. PostgreSQL schema aligned to spec v3.2 (hardened `events`, `artifacts`, hierarchical `runs_projection`, certificate fine print). Executable truth = the translation governed by the freeze.       |
| [`arquitectura-python.md`](arquitectura-python.md)                                       | VIGENTE. The active architecture: Python-dominant core (FastAPI) reconciled with the team's pragmatic build, TypeScript reserved for the Studio. S-E corrections: 8-stage pipeline, TFIM/C3, cvxpy.           |
| [`arquitectura-arc42-adrs.md`](arquitectura-arc42-adrs.md)                               | VIGENTE salvo ADR-001/002/012. arc42/C4 views, invariant-to-component mapping, and the ADR decision log (the superseded rows are TS-core specific).                                                           |
| [`arquitectura-reconciliada.md`](arquitectura-reconciliada.md)                           | PARCIALMENTE SUPERSEDIDO. Agent/runtime model, QUBO formulation (Max-Cut oficial since S-E), protocol map, ablation design, and the Plan A/B/C pivot mechanism (Plan B = C3/TFIM since S-E) are current.      |
| [`especificacion-contratos.md`](especificacion-contratos.md)                             | SUPERSEDIDO by `especificacion-contratos-v2.md` (S-E). Historical record of the initial-research contract shapes.                                                                                             |
| [`esquema-datos.md`](esquema-datos.md)                                                   | SUPERSEDIDO by `esquema-datos-v2.md` (S-E). Historical record of the initial-research schema.                                                                                                                 |
| [`deployment.md`](deployment.md)                                                         | Phase-2 reference design for BYOC/managed hosting on AWS. Not built during the hackathon month — today's code must simply not preclude it. Backend fact corrected in S-E (Quantinuum H2).                     |
| [`adr/`](adr/)                                                                           | Architecture Decision Records — the "why" behind decisions referenced from `invariants.md` and code.                                                                                                          |
| [`research/`](research/)                                                                 | Academic home: methodology, bibliography, and paper drafts. Complements the applied notes in [`../knowledge/`](../knowledge/).                                                                                |

## Where things live

- **Frozen rules** (what must always hold, enforced by tests/import-linter): `invariants.md`.
- **Frozen vocabulary and contracts** (the month's data shapes): `contract-freeze.md` + `spec-confianza-v3-2.md` + `perfil-stem-v1-0.md`.
- **Why a rule exists** (context, alternatives considered, consequences): `adr/`.
- **Applied research per problem area** (QUBO mapping, verification methods, protocols): [`../knowledge/`](../knowledge/).
- **Academic framing** (paper draft, related work, methodology): `research/`.
- **Specs** (when introduced): will land under `docs/specs/`, one file per capability/feature, cross-referencing the invariant(s) they must not violate. Not yet created — this is a placeholder convention so future specs have a defined home (seeded in S-G).

## Conventions

- English for anything CI-gated (`invariants.md`, `adr/`). Root reference docs authored by the trust-plane research (`contract-freeze.md`, the imported architecture set above) keep their original Spanish — translating them isn't planned; add an English summary here if a future contributor needs one. Research notes under `knowledge/` follow the same rule.
- Every frozen invariant in `invariants.md` carries an `<!-- enforced: path::symbol -->` anchor; `tests/invariants/test_enforced_anchors.py` fails the build if an anchor stops resolving.
