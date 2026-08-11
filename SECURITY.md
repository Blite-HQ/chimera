# Security Policy

Chimera handles research data and, eventually, credentials for
model providers and scientific tooling. Report suspected vulnerabilities
responsibly — do not open a public issue.

## Reporting a Vulnerability

- Email: <dylanchavesa@gmail.com> (repo maintainer) with subject `[SECURITY] Chimera — <short summary>`.
  (This is the route **while the repository is private**: GitHub's private
  vulnerability reporting is not available on a private repo — verified
  2026-08-06, `PUT /private-vulnerability-reporting` returns 404. It gets
  enabled the day the repo goes public and becomes the preferred route;
  step 3 of `docs/pre-flip-checklist.md` §5.)
- Include: affected component/path, reproduction steps, and impact.
- We will acknowledge within 72 hours and follow up with a remediation plan.
- Please allow us to fix and release before any public disclosure.

## Supported Versions

Pre-release / hackathon-stage project — only the `main` branch is supported.
There are no tagged releases yet.

## Scope

In scope: this repository (`engine/`, `api/`, `sdk/`, `packages/`, `capabilities/*`,
`apps/studio/`, CI/tooling config). Out of scope: third-party dependencies (report upstream)
and infrastructure not committed to this repo (e.g. cloud deployment config).

## What We Check For

CI enforces secret scanning (gitleaks), dependency auditing (pip-audit,
`pnpm audit`), Python SAST (Ruff's `S` rule set), and Semgrep (custom
base-lógica rules + `p/python` + `p/secrets` registry packs). See
[`docs/invariants.md`](docs/invariants.md) for the architectural invariants
(e.g. egress governed only by authorization, verifier is never a model) that
exist specifically to contain the blast radius of a compromised component or
a malicious/prompt-injected input.
