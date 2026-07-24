> **NOTA (2026-07-24, auditoría Chimera):** archivo vendorizado junto con la herramienta de corpus del bootcamp; describe OTRO repositorio, no Chimera. NO seguir estas instrucciones al trabajar en este repo.

# CLAUDE.md — Quantathon circuit development

## Knowledge base

This repo carries a course knowledge base at `knowledge/quantathon/`. When a task touches
quantum theory, algorithms, or hardware, consult it **before answering** and cite the
session it came from (e.g. "per b05, Ising → QUBO").

Layout:

- `INDEX.md` — map of every session.
- `qworld-course/` — the 11 QWorld classes (video transcripts).
- `bootcamp/` — 7 speaker sessions: b01 quantum mechanics · b02 QEC · b03 Quantinuum ·
  b04 molecular simulation · b05 Ising · b06 QML + Trotterization · b07 QSVT.
- Each `sNN.md` has YAML front-matter (`session`, `speaker`, `content_type`, `language`).
  `content_type: transcript` = lecture audio; `slides` = deck text.
- Some slides contain `_(no extractable text …)_` — that's a **known gap** (image/diagram
  the extractor couldn't read), not "the course didn't cover it." Ask before assuming.

## Stack

<!-- SET THIS ONE LINE: the framework you build circuits in -->

- Framework: <Qiskit | PennyLane | pytket/Quantinuum | …>
- Circuits live in: `src/circuits/` <!-- adjust to your layout -->
- Python managed with `uv`.

## How to help with circuits

- Ground gate choices, decompositions, and algorithm structure in the knowledge base;
  prefer the course's conventions over generic ones when they differ.
- When you apply a technique from a lecture (Trotterization, QSVT, a QUBO mapping), name the
  session so a teammate can open the source.
- Write runnable code for the stack above. Don't invent SDK calls — if you're unsure of an
  API, say so rather than guessing.
- Flag when a request depends on content that sits in a slide gap (vision-pass TODO).
