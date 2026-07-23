# Corpus processing spec — Quantathon knowledge base

Instructions for a model (Sonnet 5, or any Claude) reading the Markdown corpus under
`knowledge/quantathon/`. Goal: turn raw transcripts and slide text into study material.
This spec is model- and tool-agnostic: it works pasted into a Claude Project, handed to
Claude Code / Cowork over the directory, or driven from a script.

## Inputs

Every `sNN.md` has YAML front-matter: `track`, `session`, `title`, `speaker`,
`source_kind`, `content_type` (transcript | slides | document), `language`. The body is
either a timestamped transcript (`[~MM:00]` markers) or per-slide text. Treat any
`_(no extractable text — likely an image/diagram)_` marker as a GAP, not content.

## Task A — per-source notes  → write `sNN.notes.md` beside each source

For each source file, produce study notes **in the same language as the source**:

- **Resumen** (2–3 sentences): what this lecture/deck covers.
- **Conceptos clave**: bullets, each with a one-line explanation.
- **Fórmulas y definiciones**: equations/definitions present, verbatim where possible.
- **Glosario**: jargon → short definition.
- **Huecos**: slides/sections where text was missing (flag for a vision pass).

Rules: never invent content not present in the source. Keep technical terms exact. Anchor
each claim to its session id + timestamp (`[~MM:00]`) or slide number.

## Task B — equation check  → flag inline + collect into `equation-review.md`

Slide decks often mix prose with math, and text extraction mangles the math while leaving
the prose intact — so a broken equation can look fine in the corpus. On every page of each
`content_type: slides` doc, scan the already-extracted text for equations that came out
wrong: stray characters, missing sub/superscripts, `?`/`□`/replacement glyphs, bra-ket or
tensor symbols that dropped, or LaTeX that doesn't parse.

- Flag each suspect spot inline in the source `.md` as `⚠️(verify against slide N)`.
- Collect every flag into `equation-review.md` at the corpus root as a checklist:
  session · slide · what looks wrong. This is the punch-list for a later vision pass.

Don't try to *fix* the math from text alone (you can't see the slide) — only flag it, so a
human or a vision pass can verify against the original via the `source_ref` in front-matter.

## Task C — cross-corpus study guide  → write `study-guide.md` at the corpus root

Synthesize across all `*.notes.md`:

- **Mapa de temas**: which session covers what; group related lectures.
- **Hilo conductor**: how topics connect (e.g. Ising → QUBO → QAOA; QEC → hardware).
- **Glosario unificado**: deduplicated across lectures.
- **Puntos clave / tips**: the 20–30 highest-yield takeaways, each tagged with its session.
- **Lagunas del corpus**: topics referenced but never covered, and decks needing the vision pass.

## Config

- `OUTPUT_LANG` (study guide): `es-AR`  ← change if you prefer another language
- Per-source notes language: match the source
- Idempotent: skip a source if its `.notes.md` already exists
- Equation flags (Task B) append to `equation-review.md`; don't duplicate a flag already listed
