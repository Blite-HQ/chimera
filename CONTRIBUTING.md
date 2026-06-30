# Contributing to Chimera

## Development setup

```bash
bash scripts/install-dev.sh
```

This installs: Python workspace (uv), Node deps (pnpm), Husky git hooks, and the invariant-reviewer agent.

## Trunk-based development

- All work on short-lived feature branches from `main`.
- Open a PR; CI must be green before merge.
- 1 CODEOWNERS review required.
- No force-push to `main`.

## Commit messages (Conventional Commits)

```
feat: add quantum QAOA capability
fix: correct QUBO matrix normalization in solvers
docs: update invariants.md anchor for INV-3
chore: bump uv to 0.12
```

Types: `feat` `fix` `refactor` `docs` `test` `chore` `ci` `build` `perf` `revert`

## Adding a capability

1. **Create the package:**

   ```bash
   mkdir -p capabilities/<name>/src/blite_cap_<name>
   ```

2. **Write `pyproject.toml`** with:
   - `name = "blite-cap-<name>"`
   - `dependencies = ["blite-capability"]`
   - `[project.entry-points."blite.capabilities"]` pointing to your class
   - Optional deps for heavy libraries (extras)
   - `[tool.uv.sources] blite-capability = { workspace = true }`

3. **Implement the Capability:**
   - `manifest` property returns a `CapabilityManifest` with **generic** schemas (ADR-029)
   - `invoke(inputs)` loads heavy deps lazily
   - Scenario-specific knowledge goes in `knowledge/`, not in the capability

4. **Run the invariant tests:**

   ```bash
   uv sync --all-packages --all-extras
   uv run pytest tests/invariants/ -v
   ```

   The ADR-029 test will fail if your manifest contains scenario-specific terms.

5. **Open a PR** — check the PR template invariant checklist.

## The frozen constitution

The logical invariants in `docs/invariants.md` are not subject to revision.
If `lint-imports` or an invariant test fails, fix the code, not the test.
