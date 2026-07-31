# Research

> **Estado: VIGENTE (2026-07-30).** Frontera knowledge↔research vigente; los
> registros de proceso de la era del evento se archivaron (#112 — ver abajo);
> la «Suggested structure» quedó marcada como propuesta no materializada.

The academic home for Chimera: framing, methodology, and bibliography for the ideas
enforced in [`../invariants.md`](../invariants.md) and explored in
[`../../knowledge/`](../../knowledge/).

## What goes here vs. `knowledge/`

- **`knowledge/trust/`, `knowledge/quantum/`, etc.** — applied research notes, working
  documents written while deciding a specific contract or method (e.g. "which event-sourcing
  shape fits Postgres for this project"). Fast-moving, problem-scoped, may cite papers inline.
- **`docs/research/`** — the academic framing that sits above those notes: the paper draft
  (if/when one exists), the consolidated bibliography, and the methodology section
  describing how claims in this project are validated (e.g. the assurance calculus —
  classes + AL0–AL4 + criticality — and what "confiable ≠ plausible" means formally).

## Process records — moved to the archive (S3, #112)

The event-era process records were archived with `git mv` (history preserved) on
2026-07-30 — see [`../archivo/research/`](../archivo/research/):
`ratificacion-real-sf.md` (audit of the REAL S-F ratifications),
`convergencia-simulada-real-sf.md` (simulated↔real convergence matrix, verdict
CONVERGEN — its protocol entered the live backlog as a tool, decision #116),
`gap-analysis-reto1.md` and `plan-espejo.md` (challenge-1 event planning).
What remains here is only what is still live:

## Design proposals

- [`arquitectura-ingesta-kg-fase2.md`](arquitectura-ingesta-kg-fase2.md) — **design proposal,
  not implemented.** Multi-modal ingestion (video/image/paper/repo) + knowledge base/graph with
  verifiable provenance, tying into the DSSE/certificate layer. Explicitly out of hackathon scope;
  written to preserve the design after a personal exercise concluded the cheap version (a triage
  index over `knowledge/quantum/`, see `knowledge/quantum/_triage-map.md` and `INDEX.md`) covers
  the near-term need instead.

## Suggested structure (create as content arrives)

> **[S3 2026-07-30]** Propuesta NO materializada: `paper-draft.md`, `bibliography.md` y
> `methodology.md` nunca se crearon — el árbol real de `docs/research/` contiene solo los
> registros de proceso y las propuestas de diseño listados arriba. Se conserva como
> propuesta, no como descripción del directorio.

```
docs/research/
├─ README.md          this file
├─ paper-draft.md      (or a proper LaTeX/Typst source tree, if the venue requires it)
├─ bibliography.md     consolidated references (dedupe citations already scattered
│                      across knowledge/trust/*.md — Chen et al., AVA, arXiv refs, etc.)
└─ methodology.md      how the assurance calculus (classes + AL0–AL4 + criticality) and the
                       adaptive-policy trade-offs (knowledge/trust/05) are evaluated
```
