# Knowledge Base

Shared operational knowledge versioned alongside the code.
Each subdirectory covers a research area or scenario.

**Rule:** Knowledge goes here, not in capability packages.
Capabilities are generic tools (ADR-029); knowledge is how to
use those tools for a specific problem.

| Directory    | Owner    | Content                                                                                             |
| ------------ | -------- | --------------------------------------------------------------------------------------------------- |
| `islanding/` | Sebas    | Grid partitioning: benchmark corpus with proven optima (IEEE 9/14/30, dual-anchor, digests)         |
| `quantum/`   | Sebas    | Quantum theory foundations, per-challenge formulation recipes, stack idioms, evidence statistics    |
| `trust/`     | Dylan    | Verification protocols, certificate/attestation shapes, identity, guardrails, Studio trust UX       |
| `execution/` | Steven   | Gateway pipeline, runtime loop, durable execution, registry, serving/execution profiles             |
| `infra/`     | Geovanni | Provision-isolate-operate method: control/data plane, isolation ladder, IaC (Pulumi/Automation API) |

## Note template (the defined structure)

Every research note follows the structure set by the week-1 research plan (reference
implementation: `trust/`):

- Filename `NN-tema.md`, indexed in the directory's `README.md` (columns: Nota · Tema ·
  Contratos que toca).
- Header: title + `**Fecha:**` / `**Estado:**` metadata lines.
- The 4 mandatory fields, as sections or as a closing "Template de nota" block:
  **patrón/mecanismo** · **decisión** (`integrar|portar|inspirar|descartar`) · **licencias** ·
  **impacto en contrato**.
- Closes with its **reconciliación** against `docs/invariants.md` (the frozen constitution is
  never under review — a note that contradicts it is data about the note).
- Gaps are marked **PENDIENTE** explicitly, never silently omitted.
