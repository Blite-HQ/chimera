# Chimera

> Open platform for trustworthy agentic scientific research.
>
> _"Lo cuántico propone, las anclas no-modelo verifican; confiable ≠ plausible."_

Chimera is the first distribution of **Blite Engine** — a sovereign, open-source AI substrate with anchored verification and provenance. It powers verified scientific research by combining quantum and classical computation tools with a deterministic verification layer.

## Monorepo layout

```
chimera/
├─ sdk/                  blite-capability SDK (Capability port + CapabilityManifest + registry)
├─ engine/               blite-engine core (gateway, runtime, serving, verification, events, …)
├─ capabilities/         Generic tool packages — discovered at runtime via entry points (ADR-008)
│  ├─ solvers/           QUBO/MILP solvers (OR-Tools, Gurobi) — anchor
│  ├─ graphs/            Graph algorithms (NetworkX, igraph) — baseline
│  ├─ numeric/           Numerical utilities (numpy, scipy, pandas)
│  ├─ sim/               Physics simulators (pandapower) — anchor
│  ├─ ml/                Classical ML (scikit-learn, XGBoost) — baseline
│  ├─ smt/               Formal verification (Z3) — anchor
│  └─ quantum/           Quantum tools (Qiskit QAOA, PennyLane VQC, Qiskit Nature VQE, D-Wave)
├─ knowledge/            Shared operational knowledge base (per area, versioned)
├─ apps/studio/          Chimera Studio — React/Vite research UI
├─ docs/
│  └─ invariants.md      FROZEN constitution: 6 invariants + ADR-008 + ADR-029
├─ tools/claude/agents/  invariant-reviewer agent template (install via scripts/install-dev.sh)
└─ scripts/              install-dev.sh, setup-branch-protection.sh
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
