# Contract Freeze — qué cambia en los contratos (DRAFT para el viernes)

> **Estado: DRAFT — investigación de Dylan (plano de confianza + integración) completa; pendiente merge con las correcciones de Steven (plano de ejecución) antes de congelar.**
> Fuente: las 8 notas de `knowledge/trust/` (2026-07-02/03). La semilla de especificación/esquema (interna) se traduce a Python/Pydantic con los cambios de abajo. La base lógica (`docs/invariants.md`) NO cambia — cada nota cierra con su reconciliación.
> Convención de dueño: **[confianza]** = Dylan · **[frontera]** = contrato de Dylan, mecánica de Steven — coordinar, no anticipar.

---

## 1 · `CapabilityManifest` v2 **[frontera]** — nota 06

Al stub actual (`sdk/src/blite_capability/manifest.py`) se agregan:

| Campo                 | Tipo                                                            | Por qué                                                                          |
| --------------------- | --------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `side_effects`        | `Literal["pure","reversible-external","irreversible-external"]` | Eje de riesgo de la verificación (PR2/PR4); lo consume `VerificationPolicy` (§6) |
| `required_permission` | `str`                                                           | AX1/authz; lo chequea la etapa 2 del gateway contra los claims (§8)              |
| `interaction`         | `Literal["request_response","job","stream"]`                    | Semántica del contrato — "execution mode" refinado: qué maneja el caller         |
| `execution_profile`   | `Literal["in-process","service","remote-job"] = "in-process"`   | Hint de empaquetado; la **distribución** puede sobreescribirlo por despliegue    |

El campo `protocol` de la semilla TS **se elimina** del manifest: el protocolo es del adapter, no de la capability (ADR-013). ADR-029 (genericidad) aplica sin cambios a los campos nuevos.

## 2 · `Event` + esquema `events` + puerto `EventStore` **[confianza]** — nota 01

- **`Event`** (reemplaza el dataclass de `engine/src/blite/events/writer.py`): `id: UUID`, `stream_id`, `seq`, `global_seq`, `type`, **`actor_id` obligatorio**, `domain_id`, `payload`, `occurred_at: datetime`, `prev_hash/hash: str | None` (vacíos = semilla del hash-chain Fase 2).
- **Esquema SQL semilla confirmado con 3 cambios:** `+ global_seq BIGINT GENERATED ALWAYS AS IDENTITY` (cursor global para SSE/proyecciones); reglas silenciosas `DO INSTEAD NOTHING` → **REVOKE + trigger que lanza excepción** (append-only que falla fuerte); semántica de concurrencia optimista documentada (`expected_seq` → INSERT `seq = expected_seq + 1`, el UNIQUE rechaza conflictos).
- **Puerto:** `EventStore.append(stream_id, type, actor_id, domain_id, payload, expected_seq) / read_stream(stream_id, from_seq) / read_all(from_global_seq)`. El writer in-memory se reemplaza detrás del mismo puerto; INV-5 y sus gates intactos.
- **SSE:** patrón **notify-then-catchup** (NOTIFY como pista, la tabla como verdad, catch-up por `global_seq`).

## 3 · Job asíncrono: eventos del ciclo de vida **[frontera]** — nota 06

`invoke()` sync-only queda descartado. Vocabulario nuevo de eventos del run (forma alineada al task lifecycle de A2A):
`capability.job.submitted` (ANTES de ejecutar — PR1) → `capability.job.progress`* → `capability.job.completed | capability.job.failed`.
`interaction: request_response` es el caso degenerado que completa de inmediato — mismo rastro.

## 4 · `Verifier` / `Attestation` **[confianza]** — notas 03 y 04

- `AnchorKind = Literal["solver","execution","dataset","rule","human"]` — sin cambios, sin `"model"` (verificado por pyright).
- **`Verifier`** (Protocol): `anchor_kind`, **`rung: int`** (1–7), `verify(claim, ctx) -> Attestation`.
- **`Attestation`** cambia vs semilla TS: `+ rung`, **`verdict: Literal["pass","fail","inconclusive"]`** (tri-estado — la abstención es representable, precedente AWS AR), `evidence` = **unión discriminada por `method`** (differential/execution/known_truth/property/metamorphic/human — formas en nota 03 §1.2), `+ subject {run_id, step_id?, claim_digest}` (verificación de proceso, PRM).
- Tabla `attestations`: `+ rung SMALLINT NOT NULL`, CHECK de verdict tri-estado.
- La **escalera 1–7 queda formalizada como registro**: escalones 5–6 (consenso/detección) NO producen attestation por construcción → §5.
- Adapters hackathon: CP-SAT/fuerza bruta (rung 1), pandapower (rung 2), corpus IEEE (rung 3), Hypothesis/metamórficas (rung 4).

## 5 · `GuardrailSignal` **[confianza]** — nota 04

`{name, flagged, confidence: float, rung: Literal[5,6], detail}` — tipo **disjunto** de `Attestation`, sin conversión posible. Detección probabilística informa; jamás verifica ni satisface egreso (D18/D21/Inv-E hechos tipo).

## 6 · `VerificationPolicy` **[confianza]** — nota 05 (contrato NUEVO)

Política declarativa (Pydantic + YAML versionado en `distributions/chimera/`): `rules[] {match {side_effects, claim_type}, min_rung, required_anchors[], escalation, on_inconclusive: mark|escalate_human|hold_run}`.

- La etapa de verificación del gateway la consume **[frontera]**: la etapa es mecánica, la exigencia es dato.
- `policy_id` + digest se estampan en cada `verification.completed` (procedencia de la exigencia).
- `on_inconclusive` afecta el estado del run, **jamás el egreso** (Inv-E).
- Métricas por run como evento: `{verification_latency_ms, attestations_total, inconclusive_count, false_reject_proxy}`.

## 7 · `TrustCertificate` v0 **[confianza]** — nota 02

De objeto plano (semilla TS §6) a **Statement in-toto + envelope DSSE firmado**:

- `statement`: `subject = [{name: "run:<id>", digest: {sha256: provenance_hash}}]`, `predicate = {run_id, actor, aggregate_rung, unanchored_steps, attestations[], policy_id, issued_at}`, `predicateType` versionado.
- `envelope`: `{payload_type, payload_b64, signatures[{keyid, sig}]}` — **firma Ed25519 local** (lib `cryptography`), PAE de DSSE implementado tal cual; verificable **offline** (air-gap).
- `aggregate_rung` = el escalón MÁS DÉBIL del camino crítico, nunca promedio; `unanchored_steps` explícito.
- `provenance_hash` = SHA-256 del stream canónico del run; en Fase 2 lo sustituye el head del hash-chain **sin cambiar la forma**.
- Tabla `trust_certificates`: `+ aggregate_rung`, `+ certificate JSONB`, `+ keyid`.
- Sigstore/Fulcio/Rekor: descartados este mes (rompen air-gap); Rekor como opción de transparencia Fase 2.

## 8 · `Identity` + JWT + intersección de permisos **[confianza / frontera en la etapa 1]** — nota 08

- **`Identity`**: `id` = URN estable estilo SPIFFE (`user:dylan`, `agent:planner-7`, regex validada), `kind`, `domain_id`, `permissions: frozenset[str]`, `spiffe_id?` (Fase 2).
- **JWT** emitido/verificado por el engine con llave local: claims `iss/sub/kind/domain_id/permissions/act/iat/exp`; **`act` (RFC 8693)** = cadena de delegación en el token.
- **Derivación con intersección garantizada**: `derive(parent, requested)` — el delegado solo atenúa, jamás amplía (mismo principio que el gate de sub-agentes del repo) + property-test.
- **Ruta del flip AX1**: Event.actor_id obligatorio (§2) → etapa identity estampa **[frontera]** → el xfail se voltea a aserción real (nunca se borra). Eventos fuera de request usan `service:*`.

## 9 · Contrato SSE Studio↔Engine **[confianza / frontera en la ruta]** — nota 07

- `GET /runs/{run_id}/events` (SSE): `id = global_seq`, `event = type`, reanudación `Last-Event-ID`; el Studio consume **proyecciones**, jamás la tabla cruda.
- **Payloads por vista** congelados (nota 07 §1.3); regla de forma: **ningún payload de resultado sin su bloque `verification`** (verdict + rung embebidos) — la honestidad como contrato de datos, y en particular el resultado de partición lleva `verification` POR ISLA (validado por el spike).
- Decisión de streaming: **SSE simple** (AG-UI descartado este mes — vocabulario de chat-agente, no de procedencia; candidato Fase 2 para canal interactivo).
- Stack Studio validado por spike: Cytoscape.js (API directa, MIT) + Tailwind v4 + convención shadcn.

---

## Dependencias nuevas que este freeze implica (todas verificadas 2026-07-02/03)

| Dependencia                          | Licencia                              | Rol                                    |
| ------------------------------------ | ------------------------------------- | -------------------------------------- |
| ortools (CP-SAT)                     | Apache-2.0                            | ancla rung 1                           |
| pandapower                           | BSD-3                                 | ancla rung 2                           |
| hypothesis                           | MPL-2.0 (no vendorizar)               | rung 4 + property-tests de contratos   |
| cryptography (Ed25519)               | Apache-2.0/BSD                        | firma del certificado                  |
| PyJWT                                | MIT ⚠️ confirmar                      | identidad lite                         |
| mcp python-sdk                       | MIT — **pinear v1.x** (v2 beta rompe) | adapter MCP de salida (semana 3/bonus) |
| cytoscape 3.34.0 / tailwindcss 4.3.1 | MIT                                   | Studio (ya instaladas)                 |

## Qué NO cambia

- `docs/invariants.md` — congelado; las 8 notas reconcilian contra él sin excepciones.
- `AnchorKind` sin `"model"`; INV-1…6, AX1/AX3, Inv-E, ADR-008/029 y sus gates.
- Tablas semilla `domains`, `channels`, `identities`, `runs_projection` — confirmadas tal cual.
- Nada de SPIRE/OPA/Cedar/in-toto/Sigstore/microVM se integra este mes: **formas estudiadas, lites propios** (decisiones por nota).

## Para cerrar el freeze el viernes

1. Merge con las correcciones de Steven a `Capability`/`GatewayStage`/`Run`/`ModelServer` (los puntos **[frontera]** de arriba son la lista de coordinación).
2. Confirmar con Sebas el formato del corpus IEEE (`dataset_id`/versionado — lo consume el ancla rung 3).
3. Traducir este doc a los modelos Pydantic reales en la sesión de construcción (§5.3 del plan maestro) — TDD, gates verdes.
