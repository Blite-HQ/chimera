# Security Policy

Chimera / Blite Engine handles research data and, eventually, credentials for
model providers and scientific tooling. Report suspected vulnerabilities
responsibly — do not open a public issue.

## Reporting a Vulnerability

- Email: <dylanchavesa@gmail.com> (repo maintainer) with subject `[SECURITY] Chimera — <short summary>`.
- Include: affected component/path, reproduction steps, and impact.
- We will acknowledge within 72 hours and follow up with a remediation plan.
- Please allow us to fix and release before any public disclosure.

## Supported Versions

Pre-release / hackathon-stage project — only the `main` branch is supported.
There are no tagged releases yet.

## Scope

In scope: this repository (`engine/`, `sdk/`, `capabilities/*`, `apps/studio/`,
CI/tooling config). Out of scope: third-party dependencies (report upstream)
and infrastructure not committed to this repo (e.g. cloud deployment config).

## What We Check For

CI enforces secret scanning (gitleaks), dependency auditing (pip-audit,
`pnpm audit`), and Python SAST (Ruff's `S` rule set). See
[`docs/invariants.md`](docs/invariants.md) for the architectural invariants
(e.g. egress governed only by authorization, verifier is never a model) that
exist specifically to contain the blast radius of a compromised component or
a malicious/prompt-injected input.
