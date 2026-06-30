## Summary

<!-- What does this PR do? 1–3 bullet points. -->

-
-

## Invariant checklist

> The base lógica está congelada — es la constitución, no se revisa.
> If your PR touches any of these areas, confirm the invariant holds.

- [ ] **INV-1 (Gateway chokepoint):** No path bypasses the gateway module to reach `serving`/`runtime` or external services.
- [ ] **INV-2 (Verifier ≠ model):** `verification.*` does NOT import `serving`, `model_router`, or any LLM library.
- [ ] **INV-3 (Guardrail ≠ egress decision):** `guardrails.*` does NOT import `authz` or `protocols`.
- [ ] **INV-4 (Override → event first):** Any override emits an `Event` record _before_ executing.
- [ ] **INV-5 (Event log append-only):** Only `events.writer` writes to the log; all others read only.
- [ ] **INV-6 (Egress by authz):** Any egress adapter in `protocols.*` imports `authz`.
- [ ] **ADR-008 (Capabilities outside core):** `blite` does NOT import any `blite_cap_*` package.
- [ ] **ADR-029 (Generic manifests):** If adding/changing a `CapabilityManifest`, schemas use generic terms — no scenario-specific language.

_N/A — this PR does not touch any of the above areas._

## Test plan

<!-- How was this tested? -->

- [ ]
- [ ]

## Checklist

- [ ] `uv run pytest` passes
- [ ] `uv run lint-imports` passes (architecture gates)
- [ ] `uv run ruff check .` + `uv run pyright` passes
- [ ] `pnpm -C apps/studio run test:run` passes (if Studio changed)
- [ ] No hardcoded secrets or credentials
