# Chimera — Especificación de Contratos

_Firmas TypeScript de puertos y entidades · Fase 1_

> **Estado: HISTÓRICO (2026-07-30, archivado por #112).** Se conserva la marca SUPERSEDIDO
> de abajo. Rescate previo al archivo: el concepto `ModelServer.local: boolean` («true
> preserva autonomía», D19/ADR-026) fue rescatado a `docs/adr/registro-adr-historico.md`
> antes de archivar; la única cita viva desde código
> (`engine/src/blite/verification/context.py:4`) se actualiza en el barrido #115 de esta
> misma sesión.
>
> **Estado: SUPERSEDIDO (2026-07-18, barrido S-E) por [`especificacion-contratos-v2.md`](../especificacion-contratos-v2.md).** Se conserva como registro histórico de la investigación inicial. La fuente de verdad de la traducción a Python/Pydantic es [`contract-freeze.md`](../contract-freeze.md) — no implementar de este documento. Ver [`README.md`](../README.md).
>
> **Propósito.** Define los contratos (interfaces, tipos) que el código debe satisfacer. Es la realización en TypeScript de las entidades de la base lógica y de los puertos de la arquitectura. Cada contrato está anotado con el invariante que materializa.
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
// El protocolo (MCP, A2A, HTTP, in-process) es un detalle del adapter.
export type ProtocolKind = 'in-process' | 'mcp' | 'a2a' | 'http' | 'async';

export interface CapabilityManifest {
  readonly id: string; // "solver.qubo" | "chemistry.vqe"
  readonly version: string;
  readonly protocol: ProtocolKind;
  readonly inputSchema: JSONSchema; // contrato de entrada (validado en el gateway)
  readonly outputSchema: JSONSchema;
  readonly sideEffects: SideEffectClass; // gobierna qué verificación exige (PR2/PR4)
  readonly requiredPermission: string; // permiso que el actor debe tener (AX1)
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

export interface InvocationContext {
  readonly runId: string;
  readonly actor: Identity;
  readonly domainId: string;
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
  readonly initiatorId: string; // actor que lo inició; la identidad se hereda (restricción 1, Sección 10 arquitectura)
  readonly domainId: string;
  readonly status: 'created' | 'running' | 'awaiting-verification' | 'completed' | 'failed';
  readonly createdAt: string; // ISO 8601
}

// PR1 — toda acción emite un evento. El log es la fuente de verdad.
// El campo `seq` ordena dentro del stream; `prevHash`/`hash` son Fase 2 (hash-chain, AX2).
export interface DomainEvent<P = unknown> {
  readonly id: string;
  readonly streamId: string; // normalmente el runId
  readonly seq: number; // posición dentro del stream
  readonly type: EventType;
  readonly actorId: string; // AX1 — quién originó
  readonly domainId: string;
  readonly payload: P;
  readonly occurredAt: string;
  readonly prevHash?: string; // Fase 2 — encadenamiento
  readonly hash?: string; // Fase 2 — integridad (AX2, D14)
}

export type EventType =
  | 'run.created'
  | 'tool.invoked'
  | 'verification.completed'
  | 'override.applied' // AX2 — ver Sección 4
  | 'run.completed'
  | 'run.failed';

// El puerto de escritura del log. append() ya tiene la forma a prueba de
// manipulación; en Fase 1 la implementación es una tabla Postgres, en Fase 2
// calcula el hash-chain. Quien consuma este puerto no cambia entre fases.
export interface EventStore {
  append(event: Omit<DomainEvent, 'id' | 'seq' | 'hash' | 'prevHash'>): Promise<DomainEvent>;
  readStream(streamId: string): Promise<ReadonlyArray<DomainEvent>>;
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
  readonly authorizedBy: string; // actor humano que lo autoriza (AX1)
  readonly scope: 'run' | 'domain' | 'global';
}

// Conveniencia tipada sobre DomainEvent.
export type OverrideEvent = DomainEvent<OverridePayload> & { type: 'override.applied' };
```

---

## 5 · Verificación y attestation (PR2, D18, ADR-027)

```typescript
// D18 — un Verifier contrasta contra un anchor que NO es un modelo.
// El tipo `anchorKind` excluye 'model' por construcción: no existe el valor.
export type AnchorKind = 'solver' | 'execution' | 'dataset' | 'rule' | 'human';

export interface Verifier {
  readonly anchorKind: AnchorKind; // nunca 'model' (ADR-027)
  verify(claim: unknown, ctx: InvocationContext): Promise<Attestation>;
}

// El resultado de verificar: una constancia, no una opinión.
export interface Attestation {
  readonly verifierId: string;
  readonly anchorKind: AnchorKind;
  readonly verdict: 'pass' | 'fail';
  readonly evidence: unknown; // qué anchor, qué regla, qué traza (audit-ready)
  readonly issuedAt: string;
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
}
```

---

## 6 · Certificado de confianza (D20, ADR-025)

```typescript
// D20 — la confianza es propiedad del PROCESO: identidad + procedencia + ancla.
// El certificado empaqueta esos tres como salida de primera clase de cada resultado.
export interface TrustCertificate {
  readonly runId: string;
  readonly actor: Identity; // identidad (AX1)
  readonly provenanceHash: string; // hash del stream de eventos (D14)
  readonly attestations: ReadonlyArray<Attestation>; // anclas de verificación (D18)
  readonly issuedAt: string;
}
```

---

## 7 · Model Router (autonomía, ADR-026)

```typescript
// El modelo es intercambiable. Local-first por autonomía (D19): si se usa una
// API externa, la autonomía se rompe — por eso el puerto trata local como default.
export interface ModelServer {
  readonly id: string; // "ollama:llama3" | "openai:gpt-4"
  readonly local: boolean; // true preserva autonomía
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

// Orden de etapas en Fase 1 (cada una es un GatewayStage):
//   1. identity       — verifica y estampa el actor (AX1)
//   2. authorization  — el actor tiene requiredPermission y el dominio permite (AX1b/PR3)
//   3. guardrails     — detección probabilística (informa; no verifica)
//   4. provenance:pre — escribe tool.invoked ANTES de ejecutar (PR1/AX2)
//   5. mediation      — invoca la Capability (AX3)
//   6. verification   — contrasta contra anchor no-modelo antes de comprometer (PR2/PR4)
//   7. provenance:post— escribe verification.completed + attestation (PR1)
//   8. egress         — gobernado SOLO por authorization; nunca por verificación (Inv-E)
```

---

> **Nota original.** Contratos de Fase 1 completos. Cada puerto y entidad traza a su invariante. Los `packages/contracts` no dependen de ninguna implementación: son la frontera entre la lógica y el código. El siguiente documento (_Esquema de Datos_) realiza estas entidades en PostgreSQL; el de _Orden de Construcción_ las secuencia.
