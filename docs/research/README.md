# Research

The academic home for Chimera: framing, methodology, and bibliography for the ideas
enforced in [`../invariants.md`](../invariants.md) and explored in
[`../../knowledge/`](../../knowledge/).

## What goes here vs. `knowledge/`

- **`knowledge/trust/`, `knowledge/quantum/`, etc.** — applied research notes, working
  documents written while deciding a specific contract or method (e.g. "which event-sourcing
  shape fits Postgres for this project"). Fast-moving, problem-scoped, may cite papers inline.
- **`docs/research/`** — the academic framing that sits above those notes: the paper draft
  (if/when one exists), the consolidated bibliography, and the methodology section
  describing how claims in this project are validated (e.g. the verification-ladder rungs
  and what "confiable ≠ plausible" means formally).

## Current contents

- [`ratificacion-simulada-sf.md`](ratificacion-simulada-sf.md) — the S-F **simulated
  ratification act** (4 independent reviewers, one per owner + team/completeness, following
  `docs/guia-ratificacion.md` exactly). A counterweight for the real ratification, never its
  substitute.
- [`ratificacion-simulada-sf-validacion.md`](ratificacion-simulada-sf-validacion.md) — the
  **adversarial validation** of that act: 4 verifiers with a refutation posture confirmed
  every finding against primary evidence and swept beyond the guide (including the trust
  plane, which no checklist covered). Its §4 consolidated action list was **applied on
  2026-07-20** as dated `[S-F]` supersessions across the freeze, the v2 seeds, the knowledge
  base and the lockfile — see `contract-freeze.md` → "Registro de cierre (S-F)".
- [`protocolo-auditoria-ratificaciones.md`](protocolo-auditoria-ratificaciones.md) — the
  **replicable protocol** for subjecting the REAL ratifications (Sebas/Steven/Geovanni) to the same
  process as the simulation: intake/normalize → two-pass audit+refutation → convergence matrix
  (sim ↔ real) → dated `[S-F-real]` supersessions with tests → CONVERGE/DIVERGE verdict gating the
  official S-G. Includes copy-paste prompts for the audit and convergence passes.
- [`stress-test-sf-pre-sg.md`](stress-test-sf-pre-sg.md) — the **pre-S-G brutal stress test**: a
  5-attacker adversarial panel (destruction posture) + per-finding refutation, run twice, that tried
  to break the post-S-F design. Verdict **GO** to S-G; 1 P0 + 4 P1 + 4 P2, each with a fix. Its §8
  records the fixes **applied on 2026-07-21** (canonicalization ECMAScript conformance in code;
  verify-bundle 7-point checklist, titular↔verdict coupling and Policy carriers in the frozen spec) —
  marked `[S-F stress]` supersessions.

## Suggested structure (create as content arrives)

```
docs/research/
├─ README.md          this file
├─ paper-draft.md      (or a proper LaTeX/Typst source tree, if the venue requires it)
├─ bibliography.md     consolidated references (dedupe citations already scattered
│                      across knowledge/trust/*.md — Chen et al., AVA, arXiv refs, etc.)
└─ methodology.md      how the assurance calculus (classes + AL0–AL4 + criticality) and the
                       adaptive-policy trade-offs (knowledge/trust/05) are evaluated
```
