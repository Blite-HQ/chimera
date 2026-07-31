# Governance

> **Estado: VIGENTE (2026-07-30).** Rewritten by the S3 sanitation to reflect
> the real governance since decision #94 (2026-07-29). The previous version —
> a four-person maintainer council with per-plano ownership — is historical:
> see git history (pre-2026-07-30) and `docs/archivo/ratificaciones/`.

## How decisions get made (#94)

There are no per-person domain owners and no "pending ratification" states.
Every decision — technical, architectural, or documentary — is made by
**analysis of options against the architecture, the context, and the actual
state of the system**, and is **recorded in the append-only decision ledger**
([`docs/mvp/decisiones.md`](docs/mvp/decisiones.md)). The ledger is the single
authority trail: a decision exists when it is written there, and it is reversed
only by a later entry that supersedes it **with cause**.

Two consequences, both deliberate:

- **No person is a gate.** Nothing waits for a specific individual's approval;
  the analysis and the record are the gate. (`PENDIENTE-<persona>` marks are
  dead vocabulary.)
- **No deadlines.** Since the hackathon ended, depth beats speed
  (`docs/mejorado/00-playbook-fase.md`).

## Frozen surfaces

The constitution — [`docs/invariants.md`](docs/invariants.md),
[`docs/base-logica-formal.md`](docs/base-logica-formal.md),
[`docs/contract-freeze.md`](docs/contract-freeze.md) and its annex — changes
only through an explicit supersede ceremony recorded in the ledger. Nothing
stamped (digests, fixtures, canonicalization vectors) is ever re-digested.
Mechanical enforcement: import-linter contracts, invariant tests, and the
enforced-anchor check (`tests/invariants/test_enforced_anchors.py`).

## Review

Every change goes through the gates (pytest, lint-imports, ruff, pyright,
Studio tests/lint, docs lint) before merge — see
[`CONTRIBUTING.md`](CONTRIBUTING.md). `.github/CODEOWNERS` holds a single
catch-all so review requests route somewhere; it does not encode ownership.

## When the repo goes public

Branch protection, required status checks, and external-contributor policy
(DCO bot) are part of the pre-flip OSS checklist (backlog item O2/M26) — they
are declared here so the flip has a governance target, not because they are
active today.
