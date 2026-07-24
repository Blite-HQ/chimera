# Contributing to Chimera

## Development setup

```bash
bash scripts/install-dev.sh
```

This installs: Python workspace (uv), Node deps (pnpm), Husky git hooks, and the invariant-reviewer agent.

## How this repo works (read this first)

Trunk-based development on a single `main` — no long-lived `dev`/`staging`/`demo` branches.
Quality is enforced in layers: local git hooks catch formatting/commit-style/architecture
issues before anything leaves your machine, CI re-checks everything on every PR, and a
GitHub branch-protection Ruleset is drafted and staged to make the CI checks and review
actually mandatory. For who decides what and why review is shaped the way it is, see
[`GOVERNANCE.md`](GOVERNANCE.md).

**Important right now:** the Ruleset (and the reviewer-gate on the `demo` environment,
see "Promotion to demo" below) cannot be turned on yet — Blite-HQ is on GitHub Free, and
private-repo branch protection requires GitHub Team. The exact policy is fully written and
ready in `scripts/setup-branch-protection.sh` (kept as documentation/reference — see the
header comment in that file); it activates the moment the org upgrades. Until then, several
things below are **convention**, not a technical block — this doc marks each one explicitly
so nobody assumes more enforcement exists than actually does.

## The workflow, step by step

### 1. Start a change

Branch off `main`. Keep it short-lived — the longer a branch lives, the more it drifts from
`main` and the worse the eventual merge. There's no enforced branch-naming pattern; a loose
`type/short-topic` (matching the commit types below) is a reasonable convention but nothing
checks it.

### 2. Commit — this is a real, local gate today

Two Husky hooks run on every `git commit` and can reject it outright:

- **`pre-commit`** → `lint-staged`, auto-fixes what you staged, per file type:

  | Files                              | Runs                                                                                                                   |
  | ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
  | `*.py`                             | `ruff format` → `ruff check --fix`                                                                                     |
  | `*.{json,yml,yaml}`                | `prettier --write`                                                                                                     |
  | `*.md`                             | `markdownlint --fix` → `prettier --write` (this order matters — prettier must run last so its formatting isn't undone) |
  | `apps/studio/**/*.{ts,tsx,js,jsx}` | `eslint --fix` → `prettier --write`                                                                                    |

- **`commit-msg`** → `commitlint` (rules in `commitlint.config.cjs`, extends
  `@commitlint/config-conventional`). Your message must be **Conventional Commits**:

  ```
  feat: add quantum QAOA capability
  fix: correct QUBO matrix normalization in solvers
  docs: update invariants.md anchor for INV-3
  chore: bump uv to 0.12
  ```

  Allowed types: `feat` `fix` `docs` `style` `refactor` `perf` `test` `chore` `ci` `build`
  `revert`. Header ≤ 100 chars, subject not sentence/start/pascal/upper-case. Commits from
  `dependabot[bot]` are exempt (its auto-generated changelog bodies routinely exceed the
  line-length rule and that's not something we can reformat).

- **Sign off your commits (DCO).** Every commit should carry a
  `Signed-off-by: Your Name <you@example.com>` trailer, certifying you have the right to
  submit the change under the project's license (the standard [Developer Certificate of
  Origin](https://developercertificate.org/)). Add it automatically with:

  ```bash
  git commit -s -m "feat: add quantum QAOA capability"
  ```

  This is **convention today, not bot-enforced** — see the enforced-vs-convention table below.
  It becomes an actual PR gate (a DCO check bot) once the project starts taking outside
  contributions; documenting and practicing it now avoids a painful retrofit later.

If a hook rejects your commit, **fix the code/message, don't bypass it** — see "Don't" below.

### 3. Push — another real, local gate

**`pre-push`** runs a lightweight architecture check before your commits leave your machine
(the full gate runs in CI, this is a fast local approximation):

1. `uv run lint-imports` — the 12 architecture contracts (ADR-008 ×2, S-G ×2 — "api
   consumes engine ports, never capability packages" / "engine and capabilities never
   import the api" —, INV-2, INV-3, AX3, AX3-b — "model client SDKs are imported only by
   the protocols adapter (ModelServer)" —, Inv-E, INV-5, INV-6, SDK-standalone).
2. `pnpm -C apps/studio exec tsc --noEmit` — TypeScript typecheck.
3. `uv run pytest tests/invariants -q` — invariant tests.

### 4. Open a PR

CI (`.github/workflows/ci.yml`) runs nine jobs on every PR:

| Job (exact name)                   | What it checks                                                           | Blocking?                                    |
| ---------------------------------- | ------------------------------------------------------------------------ | -------------------------------------------- |
| **Python**                         | ruff lint/format, pyright, pytest+coverage, `lint-imports`               | Yes                                          |
| **Web (Studio)**                   | eslint, tsc, vitest, dependency-cruiser (INV-1)                          | Yes                                          |
| **Commit messages**                | commitlint on every commit in the PR                                     | Yes                                          |
| **PR title (Conventional Commit)** | the PR title follows Conventional Commits (same type-enum as commitlint) | Yes                                          |
| **Security**                       | gitleaks (full history), pip-audit, `pnpm audit --audit-level=high`      | Yes                                          |
| **Semgrep (advisory)**             | custom + registry SAST rules                                             | **No** — `continue-on-error`, annotates only |
| **Docs**                           | `markdownlint` + `prettier --check .` (whole repo, not just staged)      | Yes                                          |

The other two jobs are plumbing: **Detect changes** (path filter that decides whether
Python/Web need to run) and **CI gate** (aggregates the required jobs into a single
pass/fail status).

Fill out the PR template's invariant checklist (`.github/pull_request_template.md`).

### 5. Review

See [`GOVERNANCE.md`](GOVERNANCE.md) for the full policy and why it's shaped this way — in
short (and per the "enforced vs. convention" table below, still convention today): 1
approving review from **any** maintainer is enough to merge, and if your change touches a
path listed in `.github/CODEOWNERS` that owner is auto-requested as the preferred reviewer,
but their approval is never a hard requirement — ownership is advisory on purpose, so the
team is never blocked by one person's availability. Current owners by plano: **Steven**
(`engine/src/blite/{gateway,runtime,serving}/`, `apps/studio/`), **Dylan**
(`engine/src/blite/{verification,events,certificate,identity,protocols,
guardrails,authz}/`, `sdk/`), **Sebastián** (`capabilities/quantum/`), **Geovanni**
(`.github/`, `scripts/`). `docs/invariants.md` is the one exception — changes there need
consensus from all four.

**Known gap, left as-is on purpose:** CODEOWNERS has no catch-all rule. `knowledge/`, most
of `docs/`, and most root configs have no required reviewer today (the enforcement files
`pyproject.toml`, `semgrep.yml`, `package.json` and `.husky/` do have owners in
`.github/CODEOWNERS`) — a deliberate hackathon-speed tradeoff (rigid per-person ownership
doesn't fit the current pace), not an oversight.

### 6. Merge

Squash or rebase only — merge commits are disabled at the repo level
(`allow_merge_commit=false`), matching the linear-history rule already in the staged
Ruleset. The branch auto-deletes on merge (`delete_branch_on_merge=true`).

### 7. After merge — what runs automatically on `main`

- **`direct-push-guard.yml`** — advisory, never blocks. Checks whether the commit that just
  landed on `main` came from a merged PR; if not, it leaves a visible warning (Actions
  annotation + step summary). Pure traceability today, since nothing yet _prevents_ a direct
  push.
- **`promote-demo.yml`** — runs the `dev` job automatically, then the `demo` job (`needs:
dev`). Both `dev` and `demo` are real GitHub Environments, but their steps are
  **placeholders** (`TODO` echoes) — there is no real deploy target yet. `knowledge/infra/03`
  designs the demo infrastructure (Dockerfiles, air-gapped compose, Fargate) but is still
  pending ratification; don't wire up a real deploy before that note is ratified.

## Promotion to demo (interim convention)

Until the `demo` Environment has a real required-reviewer rule (same GitHub Team upgrade as
the Ruleset), promoting anything meaningful to the hackathon demo is a **human** step: post
in the team channel and get an explicit OK from someone else before you treat a `demo` run
as "the thing we're showing." The workflow won't stop you either way — that's the point of
calling this out.

## What's an enforced gate today vs. convention

| Layer                                 | Today                                               | Activates when                                  |
| ------------------------------------- | --------------------------------------------------- | ----------------------------------------------- |
| Local formatting/lint (`lint-staged`) | **Real** — blocks the commit                        | already                                         |
| Commit message format (`commitlint`)  | **Real** — blocks the commit (unless `--no-verify`) | already                                         |
| Architecture/types/tests (`pre-push`) | **Real** — blocks the push                          | already                                         |
| CI on PRs (9 jobs)                    | **Informational** — red/green, doesn't stop a merge | GitHub Team upgrade (Ruleset)                   |
| 1 approving + CODEOWNERS review       | Convention                                          | GitHub Team upgrade (Ruleset)                   |
| No force-push / no deleting `main`    | Convention (technically possible today)             | GitHub Team upgrade (Ruleset)                   |
| Manual gate before `demo`             | Convention (team channel OK)                        | GitHub Team upgrade (Environment reviewer rule) |
| DCO sign-off (`git commit -s`)        | Convention — documented, not checked                | A DCO check bot, once there are outside PRs     |

## Do / Don't

**Do:**

- Use the Conventional Commit types listed above; let `lint-staged` auto-fix formatting
  instead of fighting it manually.
- Sign off your commits (`git commit -s`) — see the DCO note in step 2.
- Keep branches short-lived and rebase/merge `main` in often if a branch lives more than a
  day or two.
- Ask the relevant plano owner (CODEOWNERS) for review when touching their area, even
  though nothing technically requires it yet.
- Mark unresolved gaps explicitly as `PENDIENTE` in `knowledge/` notes (established
  convention) instead of silently guessing.
- Treat `docs/invariants.md` as frozen: if `lint-imports` or an invariant test fails, **fix
  the code, not the test.**

**Don't:**

- Don't bypass hooks with `--no-verify` without a genuinely good reason — and say so in the
  PR description if you do; the "Commit messages" CI job and `direct-push-guard` exist
  precisely because a hook bypass on someone's machine is invisible otherwise.
- Don't push directly to `main` outside a PR. Nothing blocks it today, but
  `direct-push-guard` will flag it, and once the Ruleset activates it stops working
  entirely.
- Don't edit `docs/invariants.md` without all four CODEOWNERS signing off.
- Don't invent scenario-specific terms in a capability's `manifest` — the ADR-029 test will
  fail (capabilities stay generic; scenario knowledge belongs in `knowledge/`).
- Don't merge a Dependabot PR without at least skimming the diff — `dependabot.yml` is
  explicit that these are advisory, no-auto-merge by design.
- Don't wire up real deploy logic in `promote-demo.yml` before `knowledge/infra/03` is
  ratified — the placeholders are intentional.

## Dependency updates (Dependabot)

Weekly, grouped by minor/patch per ecosystem (`uv`, `npm`, `github-actions`) — see
`.github/dependabot.yml`. No auto-merge: every Dependabot PR goes through the same flow as
anything else (review + green CI). Cooldowns (`pnpm-workspace.yaml`,
`minimumReleaseAge`) quarantine brand-new releases; **security updates bypass cooldowns**.
`automated-security-fixes` is enabled repo-wide, so a patch for a currently-unfixable CVE
(e.g. `diskcache`/CVE-2025-69872, tracked as an accepted risk in `ci.yml`'s `pip-audit
--ignore-vuln` and dismissed on the Security tab as `tolerable_risk`) will open its own PR
automatically once one exists — no manual re-checking needed.

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

The logical invariants in `docs/invariants.md` are not subject to revision without all four
CODEOWNERS. If `lint-imports` or an invariant test fails, fix the code, not the test.
