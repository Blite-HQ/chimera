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
- **Diseño de los adapters (de decisión a diseño, sesión 3):** el freeze define el PUERTO y el contrato; el DISEÑO del adapter detrás del puerto vive en las notas [10](../knowledge/trust/10-spec-exact-solver-verifier-cpsat.md) (`ExactSolverVerifier`/CP-SAT: mapeo status→verdict, determinismo, tolerancias, formulación de referencia + vectores), [11](../knowledge/trust/11-spec-rule-verifier-backend-z3.md) (`RuleVerifier`: backend Python/Z3, unsat core, ruta rung 4→1) y [12](../knowledge/trust/12-spec-execution-verifier-harness-sandbox.md) (`ExecutionVerifier` + puerto `ExecutionHarness`, semilla A7). **A ratificar en el cierre** (§4 de cada nota, operación regla 4): refinamientos ADITIVOS de la unión `evidence` — enum real de CP-SAT en `differential` (`OPTIMAL|FEASIBLE|INFEASIBLE|MODEL_INVALID|UNKNOWN`, con `MODEL_INVALID`/`INFEASIBLE`→error, no verdict), campos del backend formal en `property` (`backend`/`status`/`unsat_core`), y `timed_out` en `execution`; la distinción `error` (falla de proceso, no emite `Attestation`) vs `verdict:"fail"`.

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
- `envelope`: `{payload_type, payload_b64, signatures[{keyid, sig}]}` — **firma Ed25519 local** (lib `cryptography`), PAE de DSSE implementado tal cual; verificable **offline** (air-gap). La firma se pide a través del puerto `KeyProvider` (contrato nuevo, nota [15](../knowledge/trust/15-keyprovider-custodia-llaves.md)): `keyid = "<purpose>:v<version>"`, env hoy → OpenBao (Transit engine) Fase 2, misma forma en ambas fases.
- `aggregate_rung` = el escalón MÁS DÉBIL del camino crítico, nunca promedio; `unanchored_steps` explícito.
- `provenance_hash` = SHA-256 del stream canónico del run; en Fase 2 lo sustituye el head del hash-chain **sin cambiar la forma**. Los BYTES exactos (canonicalización RFC 8785, vista canónica del evento, prefijos de dominio, vectores de prueba): **[anexo de canonicalización](contract-freeze-anexo-canonicalizacion.md)** (G2, nota 09).
- Tabla `trust_certificates`: `+ aggregate_rung`, `+ certificate JSONB`, `+ keyid`.
- Sigstore/Fulcio/Rekor: descartados este mes (rompen air-gap); Rekor como opción de transparencia Fase 2.

## 8 · `Identity` + JWT + intersección de permisos **[confianza / frontera en la etapa 1]** — nota 08

- **`Identity`**: `id` = URN estable estilo SPIFFE (`user:dylan`, `agent:planner-7`, regex validada), `kind`, `domain_id`, `permissions: frozenset[str]`, `spiffe_id?` (Fase 2).
- **JWT** emitido/verificado por el engine con llave local: claims `iss/sub/kind/domain_id/permissions/act/iat/exp`; **`act` (RFC 8693)** = cadena de delegación en el token. Firma **Ed25519/EdDSA** (no HS256 — punto abierto de la nota 08 cerrado por la nota [15](../knowledge/trust/15-keyprovider-custodia-llaves.md)), vía el puerto `KeyProvider` que también firma el certificado (§7).
- **Derivación con intersección garantizada**: `derive(parent, requested)` — el delegado solo atenúa, jamás amplía (mismo principio que el gate de sub-agentes del repo) + property-test.
- **Ruta del flip AX1**: Event.actor_id obligatorio (§2) → etapa identity estampa **[frontera]** → el xfail se voltea a aserción real (nunca se borra). Eventos fuera de request usan `service:*`.

## 9 · Contrato SSE Studio↔Engine **[confianza / frontera en la ruta]** — nota 07

- `GET /runs/{run_id}/events` (SSE): `id = global_seq`, `event = type`, reanudación `Last-Event-ID`; el Studio consume **proyecciones**, jamás la tabla cruda.
- **Payloads por vista** congelados (nota 07 §1.3); regla de forma: **ningún payload de resultado sin su bloque `verification`** (verdict + rung embebidos) — la honestidad como contrato de datos, y en particular el resultado de partición lleva `verification` POR ISLA (validado por el spike).
- Decisión de streaming: **SSE simple** (AG-UI descartado este mes — vocabulario de chat-agente, no de procedencia; candidato Fase 2 para canal interactivo).
- Stack Studio validado por spike: Cytoscape.js (API directa, MIT) + Tailwind v4 + convención shadcn.

## 10 · `OverrideEvent` / `OverridePayload` **[confianza]** — notas 01/05/08 (hueco A8.1 cerrado)

No es tabla nueva: `override.applied` es una fila más de `events` (§2) como cualquier otra — ya reconciliado en nota 01 §5 (INV-4/AX2 soportado). Forma semilla confirmada del `payload`:

- `target: str` — qué se relaja: `"principle:PR2"` | `"guardrail:<name>"` | `"subsystem:logging"`.
- `reason: str`.
- `authorizedBy: str` — URN estilo nota 08, pero **restringido a `user:*`**: un override lo autoriza siempre un humano, nunca un agente ni un servicio (AX2 — la relajación exige responsable identificable fuera del propio sistema que se relaja).
- `scope: Literal["run","domain","global"]`.
- `policy_id: str | None` — referencia opcional a la `VerificationPolicy`/regla que se relaja (§6); cruza con el `policy_id` que ya se estampa en `verification.completed`, de modo que un override sobre una regla de verificación queda enlazado a esa regla, no solo descrito en prosa.

`OverrideEvent` = `Event` (§2) con `type = "override.applied"` y `payload` con la forma de arriba. **Regla dura (AX2):** desactivar el propio registro de overrides es, a su vez, un override — se escribe _antes_ de surtir efecto (mismo `events` append-only con REVOKE+trigger de nota 01 §1.2, sin excepción para este tipo). Sin cambio de esquema SQL: vive en `events.payload` (JSONB), no en tabla aparte.

---

## 11 · `evidence` — campos aditivos del plano cuántico **[confianza / ciencia]** — quantum/03 y quantum/04

> Agregado en la consolidación del knowledge base (2026-07-14) para que estos campos dejen de ser
> contratos fantasma; **pendiente ratificación de Sebas** (autor de las notas que los proponen).

Campos **aditivos** a la unión discriminada de `evidence` (§4) — nunca debilitan lo existente:

- `evidence.circuit_digest: str` — SHA-256 del OpenQASM 3 exacto del circuito ejecutado (`qasm3.dumps` → hash; coherente con la Regla 1 del anexo de canonicalización). El circuito deja de ser anécdota y se vuelve auditable (quantum/03 §1).
- `evidence.differential.approximation_ratio: float` — `r = C(candidato)/C_óptimo`; con CP-SAT en `OPTIMAL` el denominador es exacto ⇒ r es un hecho, no una estimación (quantum/04 §1).
- `evidence.se_estimado: float` — error estándar de la estimación por shots (quantum/04 §2).
- `evidence.exact: bool` — distingue valor por statevector (exacto) de valor por shots (muestral) (quantum/04).
- `evidence.seeds.*` — semillas del proponente (primitive, optimizador, numpy) para replay — el equivalente proponente del `params_digest` del verificador (quantum/04 §8).
- Detalle de `GuardrailSignal` para `self-consistency` (el consenso rung 5 es señal, jamás attestation) — usa la convención `{etapa}.{mecanismo}` de la nota 16; no cambia el contrato de §5.

Ninguno modifica formas existentes; entran como claves opcionales por método.

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
2. Confirmar con Sebas el formato del corpus IEEE (`dataset_id`/versionado — lo consume el ancla rung 3). **Avance (consolidación 2026-07-14):** el corpus v0 ya existe en `knowledge/islanding/corpus/` (6 instancias con óptimos probados, doble ancla, digests SHA-256) — falta su ratificación y el mapeo `dataset_id`↔digest.
3. Traducir este doc a los modelos Pydantic reales en la sesión de construcción (§5.3 del plan maestro) — TDD, gates verdes.
