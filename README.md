# Chimera

> Open platform for trustworthy agentic scientific research.
>
> _"Lo cuántico propone, las anclas no-modelo verifican; confiable ≠ plausible."_

Chimera is a sovereign, open-source AI substrate with anchored verification and provenance. It powers verified scientific research by combining quantum and classical computation tools with a deterministic verification layer.

The MVP Nivel-1 (closed 2026-07-24) ships that thesis end to end: a runtime API (`POST /runs` → SSE event stream → verifiable DSSE certificate), real anchor verifiers (CP-SAT exact solver + pandapower execution), a React Studio, and a docker-compose walking skeleton — exercised live by the reto-1 deliverable in `challenges/reto1/`.

## Monorepo layout

```
chimera/
├─ sdk/                  blite-capability SDK (Capability port + CapabilityManifest + registry)
├─ engine/               Chimera engine core (gateway, runtime, serving, verification, events, certificate, …)
│  └─ sql/               Frozen event-store schema (init_v2.sql, anti-drift gated)
├─ api/                  chimera_api — runtime API: POST /runs, SSE /runs/{id}/events, certificate
├─ capabilities/         Generic tool packages — discovered at runtime via entry points (ADR-008)
│  ├─ solvers/           QUBO/MILP solvers (OR-Tools CP-SAT) — anchor
│  ├─ graphs/            Graph algorithms (Max-Cut baselines: Goemans-Williamson, greedy)
│  ├─ numeric/           Numerical utilities (numpy, scipy, pandas)
│  ├─ sim/               Physics simulators (pandapower) — anchor
│  ├─ ml/                Classical ML (scikit-learn, XGBoost) — baseline
│  ├─ smt/               Formal verification (Z3) — anchor (stub, not yet implemented)
│  └─ quantum/           Quantum tools (Qiskit QAOA proposer)
├─ apps/studio/          Chimera Studio — React/Vite research UI
├─ packages/             Shared web packages (@chimera/assurance-ui)
├─ challenges/reto1/     Reto-1 deliverable: run_all.py reproducible entry point + report
├─ knowledge/            Shared operational knowledge base (per area, versioned)
├─ docs/                 Authority index in docs/README.md — frozen constitution (invariants.md),
│                        contract freeze, architecture set, specs, MVP closure record
├─ docker/ + compose.yaml  Walking skeleton: postgres + api + worker + studio (file-based secrets)
├─ tests/                unit / integration / invariants / seeds / smoke suites
├─ tools/claude/agents/  invariant-reviewer agent template (install via scripts/install-dev.sh)
└─ scripts/              install-dev.sh, smoke_infra.sh, verify-bundle.py, exp_r_vs_p.py, …
```

## Quick start

```bash
# 1. Install dev environment (uv + pnpm + Husky + invariant-reviewer agent)
bash scripts/install-dev.sh

# 2. Run all tests + invariant gates
uv run pytest

# 3. Check architecture boundaries
uv run lint-imports

# 4. Run Studio
pnpm -C apps/studio run dev

# 5. Live end-to-end smoke of the compose stack (postgres + api + studio)
bash scripts/smoke_infra.sh

# 6. Reproduce the reto-1 deliverable: figures + a real run that emits a
#    DSSE certificate verified 7/7 offline
uv run python challenges/reto1/run_all.py
```

## Architecture gates

These gates enforce the frozen invariants in CI and locally:

| Gate                 | Tool                    | What it enforces                                                                                                                                    |
| -------------------- | ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Import boundaries    | `import-linter`         | Engine ⊥ capabilities (ADR-008); verification ⊥ serving (INV-2); guardrails ⊥ authz (INV-3); events.writer isolation (INV-5); egress layers (INV-6) |
| Manifest genericity  | `pytest` (ADR-029 test) | No scenario terms in any CapabilityManifest                                                                                                         |
| Anchor resolution    | `pytest` (anchor test)  | Every `<!-- enforced: -->` in invariants.md points to existing code                                                                                 |
| Studio egress        | `dependency-cruiser`    | All Studio outbound calls go via `gatewayClient.ts` (INV-1)                                                                                         |
| Type invariants      | `pyright` + pytest      | Manifests are frozen; event log has no update/delete                                                                                                |
| Conventional commits | `commitlint` + Husky    | Commit message format                                                                                                                               |
| Secrets              | `gitleaks`              | No credentials in git history                                                                                                                       |

## Adding a capability

1. Create `capabilities/<name>/` with `pyproject.toml` declaring a `blite.capabilities` entry point.
2. Implement `CapabilityManifest` with **generic** schemas (see ADR-029 in `docs/invariants.md`).
3. Install: `uv sync --all-packages --all-extras`.
4. Verify: `uv run pytest tests/invariants/` — ADR-029 test will catch scenario terms.

See `CONTRIBUTING.md` for the full recipe.

## Constitution

The logical invariants are **frozen**. See [`docs/invariants.md`](docs/invariants.md).
