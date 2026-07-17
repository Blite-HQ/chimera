# Governance

Chimera is maintained by a small maintainer council — four people, each owning
one "plano" (domain), the same split already encoded in
[`.github/CODEOWNERS`](.github/CODEOWNERS):

| Plano                                                                                                     | Maintainer |
| --------------------------------------------------------------------------------------------------------- | ---------- |
| Execution (`engine/src/blite/{gateway,runtime,serving}/`, `apps/studio/`)                                 | Steven     |
| Trust (`engine/src/blite/{verification,events,certificate,identity,protocols,guardrails,authz}/`, `sdk/`) | Dylan      |
| Quantum (`capabilities/quantum/`)                                                                         | Sebastián  |
| Repo setup & CI (`.github/`, `scripts/`)                                                                  | Geovanni   |

This mirrors what CNCF calls a maintainer council: a small group of equal
maintainers, no single decision-maker, decisions made by consensus rather
than a vote.

## How decisions get made

**Ownership is advisory, not a gate.** A plano's maintainer is
auto-requested for review on any PR touching their area (via CODEOWNERS) and
is the preferred reviewer — but their approval is never _required_ to merge.
The reason is deliberate, not an oversight: during the hackathon, if the
owner of a domain is unavailable, the team cannot afford to be blocked
waiting for them. Concretely, this means:

- **Normal changes** — one approving review from **any** maintainer is
  enough to merge, whether or not they own the touched plano.
- **Changes to the constitution** (`docs/invariants.md`) — require consensus
  from all four maintainers. This is the one deliberate exception:
  `docs/invariants.md` defines Chimera's frozen logical invariants (the
  contract that `import-linter` and `dependency-cruiser` mechanically
  enforce), and changing it changes what every other contribution is judged
  against.

This is a Node.js-style consensus-seeking model ("does anyone object?"), not
a BDFL or a formal voting body — appropriate for a team this size. See
[`CONTRIBUTING.md`](CONTRIBUTING.md#5-review) for exactly which of this is
enforced by GitHub today versus convention, and for the plan to make review
and branch protection mechanically enforced once the repo is public.

## Endurecimiento gradual — how this tightens later

Advisory-only ownership is the right shape for four trusted maintainers
moving fast. It is **not** the end state. As the project gains external
contributors, the plan is:

1. Add a **backup maintainer** per plano in CODEOWNERS, so "the owner" is
   never a single person.
2. Only then turn on GitHub's "require review from Code Owners" rule — with
   two people per plano, that rule stops being a single-point-of-block.
3. Introduce a lightweight contributor ladder (contributor → reviewer →
   maintainer), in the spirit of Kubernetes' OWNERS model, once there's a
   real pipeline of external contributions to grow into it.

None of this is needed yet, and it is intentionally not built ahead of time
(YAGNI) — but the CODEOWNERS structure and this document are written so the
tightening is additive, not a rewrite.

## Scope

This document governs decision-making and review policy for the Chimera
repository. It does not replace [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)
(behavioral expectations) or [`SECURITY.md`](SECURITY.md) (vulnerability
disclosure) — see those files for those topics.
