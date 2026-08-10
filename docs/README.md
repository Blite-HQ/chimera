# Documentation Index — the authority map

> **Estado: VIGENTE (2026-07-30).** Rebuilt by the documentation-sanitation
> session S3 as THE single map of documentary authority (decisions #108–#118 in
> the ledger). Every doc under `docs/` and `knowledge/` carries an explicit
> status header (#109); the marks are deliberately **temporary** — they are the
> map for the integral documentation refactoring that happens when the Mejorado
> phase closes (#118), not permanent patches.

## 1 · Authority hierarchy (#108)

Highest to lowest. When two docs seem to disagree, the higher one rules; ties
inside a level are resolved by the explicit rules below.

1. **Constitution** — [`invariants.md`](invariants.md) ·
   [`base-logica-formal.md`](base-logica-formal.md) ·
   [`contract-freeze.md`](contract-freeze.md) ·
   [`contract-freeze-anexo-canonicalizacion.md`](contract-freeze-anexo-canonicalizacion.md).
   Frozen; changes only through explicit supersede ceremony recorded in the
   ledger. Nothing stamped (digests, fixtures, vectors) is ever re-digested.
2. **Global decision ledger** — [`mvp/decisiones.md`](mvp/decisiones.md).
   **VIGENTE, global, append-only** — the record of every decision from MVP
   through Planeado to Mejorado and beyond. It lives under `mvp/` for
   historical reasons; moving it is deferred to the final refactoring
   (#111 as amended by #118). It is the doc third-highest in effective
   authority and the most cited from live code — not a "historical closure
   set".
3. **Seam specs** — [`specs/`](specs/) (one contract per plane/feature).
   A spec never contradicts the freeze; the supersede path is the ledger.
   **Co-authority of the seam specs:**
   [`planeado/03-research-estado-del-arte.md`](planeado/03-research-estado-del-arte.md)
   (the research hub they cite as design basis — #108).
4. **Phase docs** — [`mejorado/`](mejorado/) (the active phase). Earlier phase
   sets (`mvp/`, `planeado/00`) are closed records.
5. **Knowledge** — [`../knowledge/`](../knowledge/) is research **input, never
   authority**. A knowledge note that contradicts a spec or the freeze is data
   about the note. Exception with declared rank: `trust/10`–`trust/12` are
   «internal design cited by code» — code docstrings reference them as design
   criteria; promoting them to real specs is Fase 0 work if needed (#108).
6. **Archive** — [`archivo/`](archivo/) (hackathon-era docs, #112). Never
   authority.

**Tie-break rules (#108):**

- **Freeze ↔ spec-confianza:** the freeze rules;
  [`spec-confianza-v3-2.md`](spec-confianza-v3-2.md) is its **delegated
  vocabulary** (the freeze declares "el vocabulario normativo es el de la
  v3.2" — that delegation is an act of the freeze's authority, not a rival
  claim).
- **The three architecture docs** — single section→doc map:

  | Topic                                                                            | Doc that rules                                                                                                               |
  | -------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
  | Active architecture (stack, packages, pipeline)                                  | `arquitectura-python.md` (mind its [S3] drift marks)                                                                         |
  | arc42/C4 views · ADR registry · invariant→component map                          | `arquitectura-arc42-adrs.md` §5–§6 (rescued extracts in `adr/registro-adr-historico.md`)                                     |
  | Agent/runtime model §2 · QUBO §4 · protocol map §5 · ablation §6 · plan A/B/C §7 | `arquitectura-reconciliada.md` (only the sections its header declares valid; QUBO §4 rescued to `knowledge/islanding/01` §6) |

- **Ledger presentation:** see level 2 above — VIGENTE-global, not historical.

## 2 · Status policy (#109)

Every doc carries a status blockquote under its title:
**VIGENTE** · **VIGENTE-CON-DRIFT** (+ exact delta note) ·
**SUPERSEDIDO-POR-\<x\>** (the supersede marks the OLD doc, not just the
ledger) · **HISTÓRICO** · **CONGELADO** (frozen constitution docs).
Legacy labels from earlier imports (`CERRADA`, `SEMILLA`, `PARCIALMENTE
SUPERSEDIDO`, `EJECUTADA`) remain valid historical vocabulary inside their
headers. Verification seals carry their validity date; a wrong seal is
corrected by a NEW dated note — never by deleting the seal (#109).

## 3 · Index

### Root — constitution and frozen references

| Doc                                                                                      | Estado                        | What it is                                                                                               |
| ---------------------------------------------------------------------------------------- | ----------------------------- | -------------------------------------------------------------------------------------------------------- |
| [`invariants.md`](invariants.md)                                                         | CONGELADO                     | The logical invariants (INV-\*, AX\*) enforced by CI gates                                               |
| [`base-logica-formal.md`](base-logica-formal.md)                                         | CONGELADO                     | The formal logical system (AX/PR/D) that `invariants.md` distills                                        |
| [`tres-planos.md`](tres-planos.md)                                                       | VIGENTE                       | verification ≠ guardrail ≠ evaluation — which plane may decide what (O8)                                 |
| [`protocolo-convergencia.md`](protocolo-convergencia.md)                                 | VIGENTE (método)              | Quadrant audit of two independent passes; refuses an unearned verdict (O9) — tool in `tools/convergence` |
| [`white-box-sep.md`](white-box-sep.md)                                                   | VIGENTE (posición, no código) | Why a closed inference API cannot offer semantic-entropy probes (O10) — detection, never verification    |
| [`contract-freeze.md`](contract-freeze.md)                                               | CONGELADO (+[MEJORADO] marks) | The data contracts. §-map by plane in §4 below                                                           |
| [`contract-freeze-anexo-canonicalizacion.md`](contract-freeze-anexo-canonicalizacion.md) | CONGELADO                     | Byte-level canonicalization (RFC 8785 + DSSE) with test vectors                                          |
| [`spec-confianza-v3-2.md`](spec-confianza-v3-2.md)                                       | CONGELADO                     | Normative kernel spec of the trust layer (delegated vocabulary of the freeze)                            |
| [`perfil-stem-v1-0.md`](perfil-stem-v1-0.md)                                             | CONGELADO                     | STEM Profile v1.0 — Chimera as first distribution of the trust layer                                     |
| [`convergencia-diseno-v32.md`](convergencia-diseno-v32.md)                               | VIGENTE (registro)            | Executed convergence verdict; §2.1 is THE ladder→class+AL translation map                                |
| [`arquitectura-python.md`](arquitectura-python.md)                                       | VIGENTE-CON-DRIFT             | The active architecture (see [S3] marks: layout/stack deltas)                                            |
| [`arquitectura-arc42-adrs.md`](arquitectura-arc42-adrs.md)                               | VIGENTE-CON-DRIFT             | arc42/C4 views + invariant→component map (§6)                                                            |
| [`arquitectura-reconciliada.md`](arquitectura-reconciliada.md)                           | PARCIALMENTE SUPERSEDIDO      | Valid only per its section header (see map in §1)                                                        |
| [`especificacion-contratos-v2.md`](especificacion-contratos-v2.md)                       | VIGENTE-CON-DRIFT             | Historical TS seed; executable truth = Python under the freeze                                           |
| [`esquema-datos-v2.md`](esquema-datos-v2.md)                                             | VIGENTE                       | SQL seed with bidirectional CI lock doc⊆SQL⊆doc                                                          |
| [`deployment.md`](deployment.md)                                                         | VIGENTE (Fase 2 ref)          | BYOC/managed hosting reference design                                                                    |
| [`pre-flip-checklist.md`](pre-flip-checklist.md)                                         | VIGENTE                       | What is already configured for the OSS flip, and what cannot be yet (with the verified cause)            |

### Folders

| Folder                           | Estado                 | What it holds                                                                                                                                                                                                                                                         |
| -------------------------------- | ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`specs/`](specs/)               | VIGENTE (8 docs)       | Seam contracts: `README` (rules + index) · `confianza-api-sse` · `harness-agentico` · `endpoints-studio` · `superficie-visual` (domain-lens §4) · `evidencia-externa` (domain spec) · `capability-ingesta` · `informe-derivado`. Estados per doc in `specs/README.md` |
| [`studio/`](studio/)             | VIGENTE (1 doc)        | [`product-model.md`](studio/product-model.md) — Workspace⊃Project⊃Run doctrine, domain lenses (#78); authority for M1/M15/M17                                                                                                                                         |
| [`mejorado/`](mejorado/)         | VIGENTE — active phase | `00-playbook` · `01-criterio` (#101) · `02-cobertura` · `03-research` · `04-consolidacion` (THE backlog) · `05-plan-paralelo` · `06-saneamiento` (#107) · `07-censo-documental` · `08-handoff-plataforma` (dominio O → control)                                       |
| [`planeado/`](planeado/)         | mixed                  | `00-criterio-niveles` (HISTÓRICO — superseded by mejorado/01) · `03-research-estado-del-arte` (VIGENTE — co-authority of seam specs). The rest moved to `archivo/planeado/`                                                                                           |
| [`mvp/`](mvp/)                   | closure set + 2 live   | Historical MVP records (`00`–`05`, `auditoria-mvp`) + **[`decisiones.md`](mvp/decisiones.md) (VIGENTE — global ledger)** + [`infra-verificacion.md`](mvp/infra-verificacion.md) (VIGENTE — operational runbook)                                                       |
| [`adr/`](adr/)                   | VIGENTE                | ADR-008, ADR-029 (full records) + [`registro-adr-historico.md`](adr/registro-adr-historico.md) (ADR-001–027 registry + invariant→component table, rescued by #112)                                                                                                    |
| [`retos/`](retos/)               | VIGENTE                | The challenges as external contracts (DATA, never logic)                                                                                                                                                                                                              |
| [`research/`](research/)         | VIGENTE (2 docs)       | `README` (knowledge↔research frontier) + `arquitectura-ingesta-kg-fase2.md` (Fase 2 proposal, not implemented). Event-era records moved to `archivo/research/`                                                                                                        |
| [`archivo/`](archivo/)           | HISTÓRICO              | Hackathon-era docs archived by #112 — see [`archivo/README.md`](archivo/README.md)                                                                                                                                                                                    |
| [`../knowledge/`](../knowledge/) | input, never authority | Applied research notes per area (trust/execution/infra/islanding/quantum/nexus) — see `knowledge/README.md`                                                                                                                                                           |

## 4 · Contract-freeze §-map by plane (#110)

The freeze stays mono-doc (#110: option (a)+(c) — modularization rejected with
cause). This map is navigation only; the sections rule, not the map.

| Plane                        | Freeze sections                                             |
| ---------------------------- | ----------------------------------------------------------- |
| Capability manifest/registry | §1 (manifest v2 — pending in SDK, see its [MEJORADO] note)  |
| Events + event store         | §2 · §3 (run vocabulary) · §14 (trust-layer catalog ●)      |
| Verification                 | §4 (classes+AL) · §5 (Signal) · §6 (Policy)                 |
| Certificate / bundle         | §7 (incl. 8-point checklist) · §12 (Artifact)               |
| Identity / gateway           | §8 (8-stage pipeline) · §10 (override)                      |
| SSE / Studio                 | §9                                                          |
| Science (quantum plane)      | §11 · §15.1 · §15.3 (corpus digests) · §15.5 · §15.6        |
| Runs (hierarchy, pinning)    | §13 (+[MEJORADO #102]: agentic loop supersede)              |
| Model serving / egress       | §15.7 (env var reconciliation N12: `CHIMERA_MODEL_BACKEND`) |
| Event-era records            | §15.2 · §15.4 · §15.8 · closing registers                   |

## 5 · Where things live

- **Frozen rules** (enforced by tests/import-linter): `invariants.md` — every
  invariant carries an `<!-- enforced: path::symbol -->` anchor;
  `tests/invariants/test_enforced_anchors.py` fails the build if one stops
  resolving.
- **Frozen vocabulary and contracts:** `contract-freeze.md` + its annex +
  `spec-confianza-v3-2.md` + `perfil-stem-v1-0.md`.
- **Every decision ever made:** `mvp/decisiones.md` (append-only, global).
- **What to build next:** `mejorado/04-consolidacion.md` (backlog by domain,
  extended by #116/#117).
- **Why a rule exists:** `adr/`.
- **Applied research:** `../knowledge/` (input, never authority).
- **What died with the hackathon:** `archivo/`.

## 6 · Conventions

- **Language (#114 as amended by #118):** the corpus converges to English in
  the **final documentation refactoring** at the close of the Mejorado phase —
  new docs SHOULD be born in English; public surfaces already in English stay
  in English; phase working docs remain Spanish until that refactoring. CI-gated
  files (`invariants.md`, `adr/`) are English today.
- **Status headers are mandatory** (#109) for every doc in `docs/` and
  `knowledge/`.
- **Dead vocabulary:** `rung`/escalera, `MODEL_ROUTER_BACKEND`, «5 barras»,
  «pipeline fijo» (as phase architecture), `PENDIENTE-{persona}` and
  hackathon-era logistics terms are dead outside HISTÓRICO docs and the
  polarized statements that declare their death (the translation map lives in
  `convergencia-diseno-v32.md` §2.1).
- **Sanitation marks are temporary** (#118): `[S3 2026-07-30]` and
  `[MEJORADO #n]` marks are the map for the final refactoring, not permanent
  patches.
