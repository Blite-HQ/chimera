# Knowledge — Trust (plano de confianza e integración · Dylan)

Notas de la investigación de semana 1 (2026-07-02/03). Cada nota tiene los 4 campos obligatorios
(patrón/mecanismo · decisión `integrar|portar|inspirar|descartar` · licencia · impacto en contrato)
y cierra con su reconciliación contra `docs/invariants.md` (la base lógica NO está bajo revisión).
La consolidación de todas: **`docs/contract-freeze.md`** (DRAFT para el freeze del viernes).

## Índice

| Nota                                                   | Tema                                                                                                                 | Contratos que toca                                  |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| [01](01-event-sourcing-postgres.md)                    | Event Sourcing sobre Postgres (message-db/EventStoreDB, notify-then-catchup, ADR-016/021)                            | `Event`, esquema `events`, puerto `EventStore`      |
| [02](02-trust-certificate-attestation.md)              | Certificado con forma in-toto Statement + DSSE firmado Ed25519 (Sigstore descartado: air-gap)                        | `TrustCertificate`, `provenance_hash`               |
| [03](03-escalera-verificacion-metodos.md)              | La escalera 1–7 formalizada + métodos (property/diferencial/metamórfico/PRM) + verdict tri-estado                    | `Verifier`, `Attestation` (rung/verdict/evidence)   |
| [04](04-anclas-duras-mapa-oraculos.md)                 | Mapa de oráculos duros (CP-SAT/pandapower/corpus/Z3/Lean) + el hueco de AWS AR + guardrail ≠ verificación            | adapters de `Verifier`, `GuardrailSignal`           |
| [05](05-verificacion-adaptativa-politica-tradeoffs.md) | Verificación adaptativa por riesgo + policy-as-code (OPA/Cedar → lite) + trade-offs (Goodhart/collapse/over-refusal) | `VerificationPolicy` (nuevo), métricas por run      |
| [06](06-protocolos-capability-mcp-a2a.md)              | Capability universal (ADR-013); MCP/A2A/AsyncAPI como adapters; job asíncrono                                        | `CapabilityManifest` v2, eventos `capability.job.*` |
| [07](07-streaming-studio-sse-agui.md)                  | SSE simple vs AG-UI + contrato de eventos por vista + hallazgos del spike Cytoscape                                  | endpoint SSE, payloads por vista                    |
| [08](08-identidad-lite-kagenti.md)                     | Identidad lite: forma SPIFFE + RFC 8693 (`act`) + intersección de permisos; ruta del flip AX1                        | `Identity`, JWT, `Event.actor_id`                   |

## El spike (código)

`apps/studio/src/spike/` — IEEE-14 en Cytoscape con partición coloreada, aristas de corte y
overlay de badges de verificación (Tailwind v4 + convención shadcn). Verificado: build + lint +
dependency-cruiser (INV-1) verdes. Correr: `pnpm -C apps/studio dev`.
