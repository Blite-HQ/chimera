# Chimera — Constitution: Logical Invariants

> **Status: FROZEN.**
> These invariants define the logical core of Chimera.
> They are not subject to revision. Enforcement mechanisms may be added or improved, never weakened.
>
> _"Lo cuántico propone, las anclas no-modelo verifican; confiable ≠ plausible."_

---

## Invariant 1 — Gateway is the only chokepoint

**Statement:** Every request from outside the system — capability invocations, model calls, and egress protocols — must pass through the `gateway` module. No component may elude the gateway to reach `serving`, `runtime`, or external services directly.

**Rationale:** The gateway is where identity verification, authorization, rate limiting, and audit logging converge. Bypassing it breaks provenance.

**Gate:** import-linter (Python boundary) + dependency-cruiser (Studio egress)

<!-- enforced: apps/studio/.dependency-cruiser.cjs::INV-1 -->
<!-- enforced: apps/studio/src/gatewayClient.ts::GatewayResponse -->

> **Nota de ancla (P-rt, 2026-08-02 · hallazgo 7).** El ancla del lado Studio apuntaba a
> `invokeCapability`, la función que posteaba a la ruta FANTASMA `POST /invoke` (el
> Studio la llamaba, nginx la proxeaba, ningún servidor la servía; ningún componente la
> usaba salvo su propio test). Se mató en vez de implementarla: una segunda vía de
> invocar capabilities habría evadido run/claim/verificación — resultado sin evidencia
> ni certificado, contra la doctrina fail-closed. El ancla pasa a `GatewayResponse`, el
> tipo que TODAS las funciones de egress del módulo devuelven: el invariante lo sostiene
> que todo egress cruce ESTE módulo, no una función en particular.

---

## Invariant 2 — Verifier is never a model

**Statement:** The `verification` module must not import from `serving`, `model_router`, or any LLM library. Verification is deterministic, non-model computation only.

**Rationale:** "Confiable ≠ plausible." If verification uses a model, it becomes opinion, not proof. This is also **PR2** in the frozen base lógica: `AnchorKind` is `solver | execution | dataset | rule | human` — `model` is not a representable anchor by construction.

**Gate:** import-linter contract `INV-2` (extended to forbid direct LLM-client imports, not only `serving`)

<!-- enforced: pyproject.toml::INV-2 -->
<!-- enforced: pyproject.toml::PR2 -->

---

## Axiom AX3 — Model mediation (a model never touches the world directly)

**Statement:** `blite.serving` (the model/model-router layer) must not import `blite.protocols`, `blite.gateway`, `blite.runtime`, `blite.authz`, or any HTTP/socket client (`httpx`, `requests`, `aiohttp`, `urllib3`, `socket`). A model's output only reaches the world by being _called through_ the gateway port — it cannot reach out on its own.

**Rationale:** Base lógica AX3 (inviolable axiom, not a relaxable principle): every model-performed action passes through a port, sandboxed. This is what makes sandboxing and mediation enforceable rather than aspirational.

**Gate:** import-linter contract `AX3`

<!-- enforced: pyproject.toml::AX3 -->

---

## Principle Inv-E — Egress is governed only by authorization, never by verification

**Statement:** `blite.protocols` and `blite.authz` must not import `blite.verification` or `blite.guardrails`. No egress decision may be justified by a verification or guardrail outcome — only by `authz`.

**Rationale:** Base lógica Inv-E: _"el egreso lo gobierna SOLO la autorización... ninguna otra propiedad, en particular la verificación, satisface el antecedente de un egreso."_ This is the structural defense against prompt injection: no instruction embedded in model context can force egress by fabricating a "verification". When an output cannot be verified and the owner has not authorized egress, it is never exported — it is marked unverified or blocked, not sent out.

**Gate:** import-linter contract `Inv-E` (complements INV-3, which forbids the reverse direction: guardrails importing authz/protocols)

<!-- enforced: pyproject.toml::Inv-E -->

---

## Invariant 3 — Guardrail is not a decision-maker for egress

**Statement:** The `guardrails` module enforces policy constraints but does not make authorization decisions for egress. Authorization belongs to `authz`. Guardrails must not import `authz` or `protocols`.

**Rationale:** Separating policy enforcement from authorization prevents guardrail escalation.

**Gate:** import-linter contract `INV-3`

<!-- enforced: pyproject.toml::INV-3 -->

---

## Invariant 4 — Every override is recorded before execution

**Statement:** Any component that bypasses a default (force-override a guardrail, escalate permissions) must emit an `Event` record with a timestamp _before_ executing the override.

**Rationale:** Post-hoc logging can be dropped or tampered. Pre-execution recording is a hard causality guarantee.

**Gate:** type-test + invariant-reviewer checklist

<!-- enforced: tests/invariants/test_types.py::test_event_append_produces_immutable_event -->

---

## Invariant 5 — Event log is append-only

**Statement:** The `events` module exposes only append and read operations. No update or delete. Non-events modules are forbidden from importing `blite.events.writer`.

**Rationale:** The event log is the single source of truth for provenance and certificate generation.

**Gate:** import-linter contract `INV-5` + type-test

<!-- enforced: pyproject.toml::INV-5 -->
<!-- enforced: tests/invariants/test_types.py::test_event_log_is_append_only -->

---

## Invariant 6 — Egress only by authorization

**Statement:** Any module that sends data outside the system boundary (`protocols.*`) must import and check `blite.authz`. No unauthorized data leaves the system.

**Rationale:** Sovereign platforms guarantee all egress is authorized.

**Gate:** import-linter layers contract `INV-6` + invariant-reviewer

<!-- enforced: pyproject.toml::INV-6 -->

---

## ADR-008 — Science capabilities are outside the engine core

**Statement:** The engine (`blite`) must not import any capability package (`blite_cap_*`). Capabilities are plugins discovered at runtime via entry points. The only shared interface is the SDK (`blite_capability`).

**Rationale:** Coupling the engine to specific capabilities defeats the plugin architecture.

**Gate:** import-linter contract `ADR-008` + smoke test

<!-- enforced: pyproject.toml::ADR-008 -->
<!-- enforced: tests/smoke/test_plugin_mechanism.py::test_registry_does_not_crash -->

---

## ADR-029 — Capability manifests are generic

**Statement:** Every `CapabilityManifest` must use generic, domain-agnostic terms. Scenario knowledge lives in the agent and the knowledge base.

**Examples:**

- ✅ `"Solve a QUBO matrix → binary assignment"`
- ❌ `"Partition an electrical grid → islands"` — scenario term belongs in KB

**Gate:** genericity test over all registered manifests

<!-- enforced: tests/invariants/test_capability_genericity.py::test_all_manifests_are_generic -->
<!-- enforced: tests/invariants/scenario_denylist.txt -->

---

## ADR-029b — The generic layers stay generic (multi-layer gate, O11)

**Statement:** Scenario vocabulary must not appear in the **production code of the
generic layers** — `sdk/` · `engine/` · `api/` · the Studio shell and views ·
`packages/` — beyond what `agnosticism_exceptions.toml` **declares**. Every
exception states its class (`doctrina` — the rule quoting itself · `contrato` —
an identifier already stamped in emitted evidence, so renaming it re-digests and
needs ceremony · `deuda` — a real leak, which must cite the backlog item that
closes it).

**Rationale:** ADR-029 alone is one gate over one surface (four manifest fields).
Every leak the design census found (`docs/mejorado/07-censo-documental.md` §8.3)
sits in the surfaces with **no** gate — so each new leak was undetectable by CI.
This is the item that makes the others irreversible: without it, generality won
by G/P/C/V erodes silently, one hardcoded instance id at a time.

**Where the domain DOES belong:** `capabilities/` (ADR-008), the Studio's
`lenses/` (P13 — a lens is the declared plug-in point for a domain),
`distributions/` policies, `knowledge/`, `challenges/`, fixtures (labelled data)
and tests. None of those are scanned.

**The ratchet:** a new undeclared leak fails the gate, and so does an exception
that no longer matches anything — the list can only shrink.

**Gate:** multi-layer scan over the generic layers with declared exceptions

<!-- enforced: tests/invariants/test_agnosticism_layers.py::TestElTrinquete -->
<!-- enforced: tests/invariants/agnosticism_exceptions.toml -->
<!-- enforced: tests/invariants/scenario_denylist.txt -->

---

## Axiom AX1 — Identity (ENFORCED)

**Statement:** Every action must be attributable to exactly one actor. Every `Event` must carry a required, non-empty `actor_id`.

**Rationale:** Base lógica AX1 (inviolable axiom). `Event.actor_id` is a required Pydantic field and the gateway crossing stamps the VERIFIED identity end-to-end: the api resolves the actor from the JWT session cookie (freeze §9 P1-9, `chimera_api.auth`), the crossing's identity stage guards its coherence, and the provenance stages write `identity.id` on every `capability.job.*` event (freeze §8 «Ruta del flip AX1»). Events outside a request keep `service:*` actors (freeze §13 cascada).

**History:** born as an `xfail` placeholder (2026-07 freeze — the identity module did not exist); flipped to a hard assertion in C2/M2 (Fase 1 Mejorado, 2026-07-31) with the assertion HARDENED to actor provenance — the test verifies a real crossing stamps the gateway-verified actor, and is never deleted.

**Gate:** hard test (actor required by type + provenance through a real crossing)

<!-- enforced: tests/invariants/test_types.py::test_event_has_non_null_actor_id -->

---

## Principle — Sub-agent permission intersection

**Statement:** A Claude sub-agent definition (`tools/claude/agents/*.md`) may only declare tools that are a subset of an explicit allowed superset (`Read`, `Grep`, `Glob`, `Bash`). A sub-agent may only ever _reduce_ the permission surface it inherits, never expand it.

**Rationale:** Maps to the OWASP Agentic Top 10 (Excessive Agency / Privilege Compromise). Widening a sub-agent's tool access (e.g. adding `Edit`/`Write`/`Task`) must be a visible, reviewed decision — not something that slips in via an unreviewed prompt file.

**Gate:** pytest parsing every agent's frontmatter `tools:` list

<!-- enforced: tests/invariants/test_subagent_permissions.py::test_subagent_tools_are_subset_of_allowed_superset -->
