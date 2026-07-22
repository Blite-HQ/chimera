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

## Process records — S-F ratification (2026-07-21/22)

- [`ratificacion-real-sf.md`](ratificacion-real-sf.md) — audit of the REAL S-F ratifications
  (Fase A + pre-B stress test + Fase B application + re-stress, verdict GO).
- [`convergencia-simulada-real-sf.md`](convergencia-simulada-real-sf.md) — the
  simulated↔real convergence matrix (protocol §5), verdict **CONVERGEN**, unified set +
  prioritized S-G list + port table. The simulated-track sources live in the read-only
  exercise branch `ejercicio/sf-ratificacion-simulada`.

Nothing here yet beyond this placeholder — content lands once the group's investigation
(timeboxed research week, see project plan) produces a draft worth structuring.

## Suggested structure (create as content arrives)

```
docs/research/
├─ README.md          this file
├─ paper-draft.md      (or a proper LaTeX/Typst source tree, if the venue requires it)
├─ bibliography.md     consolidated references (dedupe citations already scattered
│                      across knowledge/trust/*.md — Chen et al., AVA, arXiv refs, etc.)
└─ methodology.md      how the verification ladder (knowledge/trust/03) and the
                       adaptive-policy trade-offs (knowledge/trust/05) are evaluated
```
