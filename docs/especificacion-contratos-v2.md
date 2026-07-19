# El Engine — Especificación de Contratos v2

_Firmas TypeScript de puertos y entidades · Fase 1 · SEMILLA_

> **Estado: SEMILLA v2 (importada 2026-07-18, barrido S-E).** Realización en TypeScript de las
> entidades de la base lógica y de la spec de confianza v3.2 — **la verdad ejecutable sigue
> siendo la traducción a Python/Pydantic gobernada por [`contract-freeze.md`](contract-freeze.md)**
> (misma regla que la semilla v1, hoy supersedida). Importada del working set externo,
> sanitizada ("el Engine") y con las correcciones del veredicto de convergencia aplicadas al
> importar: **C1** (manifest sin `protocol`, con `interaction` + `executionProfile`), **C3/C4**
> (eventos y vocabulario: gana el freeze §2/§3), **P0-2** (letra chica del certificado),
> **P1-2** (`VALID_AS_OF` + revocación autodeclarada), **P1-5** (override con autoridad
> graduada) y la unificación `ModelPort`/`ModelServer` (execution/09). Cada corrección está
> marcada `// [S-E]` en su sitio.
>
> **Propósito.** Define los contratos (interfaces, tipos) que el código debe satisfacer. Cada contrato está anotado con el invariante que materializa.
>
> **Alcance.** Fase 1. Los campos marcados `// Fase 2` se declaran en el tipo pero su implementación puede diferirse. La regla rectora: _el contrato tiene la forma de la arquitectura objetivo; la implementación detrás puede ser la mínima._
>
> **Convención.** Los nombres de tipos, puertos y campos van en inglés (son identificadores de código). Estos contratos viven en `packages/contracts`.

---

## 1 · Identidad y dominio (AX1)

```typescript
// AX1a — toda acción es atribuible a un actor único.
// En Fase 1 la identidad se deriva de un JWT; en Fase 2, de SPIFFE/SVID.
export interface Identity {
  readonly id: string; // URN estable del actor, p.ej. "user:dylan" | "agent:planner-7"
  readonly kind: 'human' | 'agent' | 'service';
  readonly domainId: string; // dominio al que pertenece el actor (AX1b)
  readonly permissions: ReadonlySet<string>; // capacidades que el actor puede invocar
  readonly spiffeId?: string; // Fase 2
}

// AX1b — los dominios son fronteras de confianza selladas.
// Un actor de un dominio no toca datos de otro salvo canal declarado.
export interface Domain {
  readonly id: string;
  readonly ownerId: string; // dueño que autoriza egreso (PR3)
  readonly channels: ReadonlyArray<Channel>; // cruces permitidos hacia otros dominios
}

export interface Channel {
  readonly toDomainId: string;
  readonly allows: ReadonlyArray<'read' | 'invoke' | 'egress'>;
}
```

---

## 2 · Capability (la abstracción central, ADR-013)

```typescript
// Toda integración —nativa, alojada, herramienta o par— es una Capability.
// [S-E · C1] El protocolo (MCP, A2A, HTTP, in-process) es un detalle del ADAPTER, no de la
// capability (ADR-013): el campo `protocol` de la semilla original se ELIMINA del manifest.
// ProtocolKind sobrevive solo como vocabulario del lado adapter.
export type ProtocolKind = 'in-process' | 'mcp' | 'a2a' | 'http' | 'async';

export interface CapabilityManifest {
  readonly id: string; // "solver.qubo" | "simulator.dynamics"
  readonly version: string;
  readonly inputSchema: JSONSchema; // contrato de entrada (validado en el gateway)
  readonly outputSchema: JSONSchema;
  readonly sideEffects: SideEffectClass; // gobierna qué verificación exige (PR2/PR4)
  readonly requiredPermission: string; // permiso que el actor debe tener (AX1)
  // [S-E · C1] Los dos ejes del freeze §1 (validados por execution/06/09):
  readonly interaction: 'request_response' | 'job' | 'stream'; // semántica del contrato: qué maneja el caller
  readonly executionProfile: 'in-process' | 'service' | 'remote-job'; // hint de empaquetado; default "in-process";
  // la distribución puede sobreescribirlo por despliegue
}

// Clasifica el efecto de la acción: determina la ruta de verificación.
export type SideEffectClass =
  | 'pure' // sin efecto externo (cálculo)
  | 'reversible-external' // efecto externo deshacible
  | 'irreversible-external'; // efecto externo que afecta a un tercero (PR4: verificación reforzada)

// El puerto que toda Capability implementa. El adapter traduce el protocolo.
export interface Capability {
  readonly manifest: CapabilityManifest;
  invoke(input: unknown, ctx: InvocationContext): Promise<CapabilityResult>;
}

// SO1 (stress organizacional O1) — anti confused-deputy. Toda invocación lleva la
// cadena de delegación completa; el permiso efectivo es la INTERSECCIÓN de toda la
// cadena, jamás el máximo. Una Capability nunca actúa con más autoridad que el
// Principal menos privilegiado de su cadena (L1 aplicada a la autoridad; ADR-018).
export interface InvocationContext {
  readonly runId: string;
  readonly actor: Identity; // el ejecutor inmediato
  readonly domainId: string;
  readonly invocationChain: ReadonlyArray<string>; // [iniciador, ...delegaciones] — ids de Identity, en orden
  readonly effectivePermissions: ReadonlySet<string>; // ∩ de permissions de toda la chain — el gateway la computa, nadie más
}

export interface CapabilityResult {
  readonly output: unknown;
  readonly producedBy: string; // id de la Capability (para procedencia)
}
```

---

## 3 · Run y eventos (PR1, AX2, Event Sourcing)

```typescript
// Un Run es una ejecución. Su estado se reconstruye por replay de sus eventos.
export interface Run {
  readonly id: string;
  readonly parentRunId?: string; // JERÁRQUICO: ausente = run raíz. El case de confianza y el
  // certificado cuelgan SIEMPRE del run raíz (D5); los sub-runs
  // (formular, QAOA, baseline, verificar) aportan claims al raíz.
  readonly initiatorId: string; // actor que lo inició; la identidad se hereda (restricción 1, Sección 10 arquitectura)
  readonly domainId: string;
  readonly status: 'created' | 'running' | 'awaiting-verification' | 'completed' | 'failed';
  readonly createdAt: string; // ISO 8601

  // SO6 (stress organizacional O7) — pinning: un Run FIJA por digest todo lo que lo definió
  // al iniciar. Editar una definición crea versión nueva y no afecta runs en vuelo (mismo
  // patrón que R-Pol1 para Policy). Es la precondición de reproducibilidad (D16/AX2).
  readonly agentDefinitionDigest?: string;
  readonly workflowDefinitionDigest?: string;
  readonly policyDigest: string; // la Policy del case, fijada al crear el run raíz
}

// PR1 — toda acción emite un evento. El log es la fuente de verdad.
// El campo `seq` ordena dentro del stream; `prevHash`/`hash` son Fase 2 (hash-chain, AX2).
export interface DomainEvent<P = unknown> {
  readonly id: string;
  readonly streamId: string; // = runId (un stream por run — decisión del freeze §2/§13)
  readonly seq: number; // posición dentro del stream
  readonly globalSeq?: number; // [S-E · C3] cursor global (SSE/proyecciones) — lo asigna el store, jamás el caller
  readonly type: EventType;
  readonly actorId: string; // AX1 — quién originó
  readonly domainId: string;
  readonly payload: P;
  readonly occurredAt: string;
  readonly prevHash?: string; // Fase 2 — encadenamiento
  readonly hash?: string; // Fase 2 — integridad (AX2, D14)
}

// [S-E · C4] El vocabulario COMPLETO es el del freeze §3/§14 (gana-freeze):
// run.* / run.step.* / capability.job.* / model.call.* / registry.* + el catálogo ● de la capa
// de confianza (ClaimEmitted, PlanCreated, PolicyPinned, AttestationRecorded, CaseClosed,
// CertificateIssued…). Mapeo de la semilla original: `tool.invoked` ≡ `capability.job.submitted`
// (el evento de provenance:pre del job); `verification.completed` se conserva tal cual.
export type EventType = string; // valores válidos = catálogo del freeze §3/§14 (cerrado por contrato, no por tipo TS)

// El puerto de escritura del log. append() ya tiene la forma a prueba de
// manipulación; en Fase 1 la implementación es una tabla Postgres, en Fase 2
// calcula el hash-chain. Quien consuma este puerto no cambia entre fases.
// [S-E · C3] Forma del freeze §2: concurrencia optimista por `expectedSeq` + lectura global.
export interface EventStore {
  append(
    event: Omit<DomainEvent, 'id' | 'seq' | 'globalSeq' | 'hash' | 'prevHash'>,
    expectedSeq: number
  ): Promise<DomainEvent>;
  readStream(streamId: string, fromSeq?: number): Promise<ReadonlyArray<DomainEvent>>;
  readAll(fromGlobalSeq: number): Promise<ReadonlyArray<DomainEvent>>;
}
```

---

## 3.b · Artifact y content-store (O3/L3 — el sustrato de Evidence y deliverables)

```typescript
// O3 — el contenido se direcciona por IDENTIDAD (digest de su forma canónica), no por
// ubicación. Evidence, deliverables del bundle y payloads del log viven aquí.
// SO2 (stress organizacional O2) — el store está PARTICIONADO POR DOMINIO: un digest es
// visible solo dentro de su dominio salvo Channel con allows:'read'. La deduplicación
// física es optimización interna, JAMÁS un canal de visibilidad (AX1b/Inv-E).
export interface Artifact {
  readonly digest: string; // sha256 de la forma canónica (RFC 8785 JCS + NFC para JSON)
  readonly domainId: string; // SO2 — scope de visibilidad
  readonly mediaType: string;
  readonly sizeBytes: number;
  readonly storageRef: string; // dónde están los bytes (detalle de implementación)
  readonly createdAt: string;
}

export interface ContentStore {
  // put() devuelve el digest: el contenido define su identidad, no al revés.
  put(bytes: Uint8Array, mediaType: string, ctx: InvocationContext): Promise<Artifact>;
  get(digest: string, ctx: InvocationContext): Promise<Uint8Array>; // respeta SO2
  stat(digest: string, ctx: InvocationContext): Promise<Artifact | null>;
}
```

---

## 4 · Override como evento de primera clase (AX2, ADR-022)

```typescript
// AX2 — toda relajación de una Ley/Principio/guardrail es un override, y
// se escribe como evento ANTES de surtir efecto. Desactivar el registro es,
// él mismo, un override que se registra primero.
export interface OverridePayload {
  readonly target: string; // qué se relaja: "principle:PR2" | "guardrail:injection" | "subsystem:logging"
  readonly reason: string;
  readonly authorizedBy: string; // URN humano (AX1) — restringido a "user:*": un override lo
  // autoriza siempre un humano, nunca un agente ni un servicio.
  // [S-E · P1-5] Autoridad graduada: el autorizador debe portar el
  // permiso "override:apply:<scope>" en su intersección efectiva
  // (freeze §8/§10) — sin él, el override se rechaza.
  readonly scope: 'run' | 'domain' | 'global';
  readonly policyId?: string; // regla de VerificationPolicy que se relaja (enlaza con el
  // policy_id estampado en verification.completed)
}

// Conveniencia tipada sobre DomainEvent.
export type OverrideEvent = DomainEvent<OverridePayload> & { type: 'override.applied' };
```

---

## 5 · Verificación y attestation (PR2, D18, ADR-027)

```typescript
// D18/S7 — un Verifier contrasta contra un anchor que NO es un modelo.
// VerifierClass (spec confianza v3.2) excluye 'model' por construcción: no existe el valor.
export type VerifierClass =
  | 'formal_exact' // techo AL4 (con proof-carrying validado; AL3 sin él)
  | 'execution' // techo AL3 (evidence con reproducer obligatorio)
  | 'ground_truth' // techo AL3 (sujeto al tope de autoridad del ancla)
  | 'property_rule' // techo AL2
  | 'consensus_replication' // techo AL2 — SOLO procesos no-modelo (S7)
  | 'human_expert'; // techo AL3 (independiente ∧ en especialidad)

export type AssuranceLevel = 'AL0' | 'AL1' | 'AL2' | 'AL3' | 'AL4';
export type Criticality = 'C0' | 'C1' | 'C2' | 'C3';

export interface Verifier {
  readonly verifierClass: VerifierClass; // nunca 'model' (ADR-027 → S7)
  readonly determinism: 'deterministic' | 'nondeterministic'; // si es nondeterministic, la rerun_policy aplica a ambos veredictos
  verify(claim: unknown, ctx: InvocationContext): Promise<Attestation>;
}

// El resultado de verificar: una constancia, no una opinión.
// Veredicto TRI-ESTADO (D4): "no pude" es un resultado de primera clase, jamás se disfraza.
export interface Attestation {
  readonly verifierId: string;
  readonly verifierClass: VerifierClass;
  readonly verdict: 'pass' | 'fail' | 'inconclusive';
  readonly inconclusiveReason?:
    | 'timeout'
    | 'undecidable'
    | 'ambiguous_formalization'
    | 'conflict'
    | 'undermined_premise'
    | 'no_applicable_anchor'
    | 'anchor_requires_unauthorized_egress'
    | 'budget_exhausted';
  readonly scope: unknown; // ScopeExpr canónico (decidible por construcción)
  readonly claimDigest: string; // binding a 4 digests (L3): qué se verificó,
  readonly verifierBinaryDigest: string; //   con qué binario,
  readonly verifierParamsDigest: string; //   con qué parámetros,
  readonly anchorDigest?: string; //   contra qué ancla exacta
  readonly evidenceDigests: ReadonlyArray<string>; // Artifacts del content-store (§3.b); con reproducer si aporta AL3
  readonly issuedAt: string; // semántica VALID_AS_OF
}

// Guardrails (detección probabilística) — DISTINTO de Verifier.
// Puede usar modelos o heurísticas. Es un pre-filtro que informa, no verifica.
export interface Guardrail {
  readonly name: string; // "prompt-injection" | "sensitive-data"
  detect(input: unknown, ctx: InvocationContext): Promise<GuardrailSignal>;
}

export interface GuardrailSignal {
  readonly name: string;
  readonly flagged: boolean;
  readonly confidence: number; // 0..1 — explícitamente probabilístico
  // S1: tipo DISJUNTO de Attestation — jamás entra al cálculo de veredictos ni niveles.
}
```

---

## 6 · Certificado de confianza (D20, ADR-025)

```typescript
// D20 — la confianza es propiedad del PROCESO: identidad + procedencia + ancla.
// El certificado empaqueta esos tres; el Bundle lo hace verificable OFFLINE por terceros.
// [S-E · P0-2] La letra chica es parte del MÍNIMO: cada conclusión lleva su enunciado canónico
// y su alcance, y el certificado carga sus supuestos — un nivel sin alcance es pasivo, no activo.
export interface TrustCertificate {
  readonly runId: string; // case por run raíz (D5)
  readonly actor: Identity; // identidad (AX1)
  readonly provenanceHash: string; // hash del stream de eventos (D14)
  readonly conclusions: ReadonlyArray<{
    readonly claimDigest: string;
    readonly canonicalStatement: string; // [S-E · P0-2] el enunciado, sin deixis
    readonly scope: unknown; // [S-E · P0-2] ScopeExpr canónico — contra QUÉ se sostiene
    readonly verdict: 'verified' | 'refuted' | 'inconclusive' | 'not_required_declared';
    readonly level: AssuranceLevel;
  }>;
  readonly titularLevel: AssuranceLevel; // MÍNIMO sobre el camino crítico, incluidas derivaciones — jamás promedio
  readonly assumptions: ReadonlyArray<{
    // [S-E · P0-2] los supuestos del case, visibles:
    readonly statement: string; //   p.ej. SC3 verbatim, limitaciones por soberanía (Inv-E)
    readonly ref?: { readonly name: string; readonly digest: string }; // p.ej. modelo del simulador, corpus
  }>;
  readonly deliverables: ReadonlyArray<{ artifactRef: string; digest: string }>; // binding anti-TOCTOU
  readonly attestations: ReadonlyArray<Attestation>; // anclas de verificación (D18/S7)
  readonly policyDigest: string; // Policy fijada por digest al crear el case
  readonly calculusVersion: string; // p. ej. "cal-2.4" (I13)
  readonly validAsOf: string; // [S-E · P1-2] semántica S5: el veredicto vale a este instante;
  //   la vigencia actual exige status online
  readonly revocation: 'none'; // [S-E · P1-2] AUTODECLARADO: sin mecanismo de revocación en
  //   Fase 1 (StatusList/Receipt = Fase 2) — honestidad como campo
}
```

---

## 7 · Model Router (autonomía, ADR-026)

```typescript
// [S-E · execution/09] Unificación de nombres (decidida — ratificación final Steven + Dylan):
//   - `ModelPort` = el PUERTO (Protocol) — vive en `serving` (router puro, cero red; AX3 por
//     construcción). Su forma es la de abajo (la de esta semilla).
//   - `ModelServer` = el ADAPTER que lo implementa — vive en `protocols`, envuelve LiteLLM
//     Router (un solo model_list: cloud + Ollama local), y queda bajo INV-6 (egreso exige authz).
// El modelo es intercambiable. Local-first por autonomía (D19): si se usa una
// API externa, la autonomía se rompe — por eso el puerto trata local como default.
export interface ModelPort {
  readonly id: string; // "ollama:llama3" | "openai:gpt-4"
  readonly local: boolean; // true preserva autonomía (D19)
  complete(prompt: ModelRequest, ctx: InvocationContext): Promise<ModelResponse>;
}

export interface ModelRequest {
  readonly messages: ReadonlyArray<{ role: 'system' | 'user' | 'assistant'; content: string }>;
}

export interface ModelResponse {
  readonly content: string;
}
```

---

## 8 · El gateway: la etapa del pipeline (AX3, ADR-014/024)

```typescript
// El gateway es el punto único de control (chokepoint). Se compone de etapas
// (Chain of Responsibility). Toda invocación pasa por TODAS las etapas en orden.
// Ningún componente puede saltar una etapa (principio de no-elusión).
export interface GatewayStage {
  readonly name: string;
  // Procesa el contexto; puede rechazar (lanzando) o pasar al siguiente.
  process(req: GatewayRequest, next: () => Promise<GatewayResponse>): Promise<GatewayResponse>;
}

export interface GatewayRequest {
  readonly actor: Identity; // estampada en la etapa de identidad (AX1)
  readonly capabilityId: string;
  readonly input: unknown;
  readonly runId: string;
  readonly domainId: string;
}

export interface GatewayResponse {
  readonly output: unknown;
  readonly attestation?: Attestation; // si pasó por verificación (PR2)
  readonly certificate?: TrustCertificate; // al completar el run (D20)
}

// Orden de etapas en Fase 1 (cada una es un GatewayStage) — orden CONGELADO por el freeze §8
// (resolución C2 de la convergencia: 8 etapas; la etapa "policy" no existe — la Policy se fija
// por digest al crear el case, R-Pol1, y la etapa de verificación la lee):
//   1. identity       — verifica y estampa el actor (AX1)
//   2. authorization  — el actor tiene requiredPermission y el dominio permite (AX1b/PR3)
//   3. guardrails     — detección probabilística (informa; no verifica)
//   4. provenance:pre — escribe capability.job.submitted ANTES de ejecutar (PR1/AX2)
//   5. mediation      — invoca la Capability (AX3)
//   6. verification   — contrasta contra anchor no-modelo antes de comprometer (PR2/PR4)
//   7. provenance:post— escribe verification.completed + attestation (PR1)
//   8. egress         — gobernado SOLO por authorization; nunca por verificación (Inv-E)
```

---

> **Estado.** Contratos de Fase 1 completos como SEMILLA v2. Cada puerto y entidad traza a su invariante; las correcciones `[S-E]` provienen del veredicto de convergencia, del stress test S-D y de las notas de ejecución. La traducción a Python/Pydantic (gobernada por `contract-freeze.md`) es la verdad ejecutable. El documento hermano (_Esquema de Datos v2_) realiza estas entidades en PostgreSQL.
