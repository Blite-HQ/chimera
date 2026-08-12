/**
 * Shared prop/data contracts for the trust-UX views (knowledge/trust/18).
 *
 * These are the TypeScript interfaces from nota 18 §2 (RunTimeline,
 * StepInspector, CertificateView, ProvenanceExplorer) migradas al
 * vocabulario clase+AL del freeze §4 y al predicate §7 (reobra ET-9,
 * 2026-07-22), plus the ablation payload shape from nota 07 §1.3.
 * Centralized here (rather than duplicated per component) because several
 * types are shared across more than one view. Component files own their own
 * `*Props` interfaces; this file owns only the data shapes that cross view
 * boundaries.
 *
 * `Verdict`/`AnchorKind` are re-exported from the spike (spike/ieee14.ts)
 * rather than redefined, so the whole Studio shares one definition.
 */

import type { AssuranceLevel, ConclusionVerdict, VerifierClass } from '@chimera/assurance-ui';

import type { AnchorKind, Verdict } from '../spike/ieee14';

export type { AnchorKind, AssuranceLevel, ConclusionVerdict, Verdict, VerifierClass };

/**
 * Nivel-1 task 4 — clase+AL de un evento `verification.completed`, tomado de
 * `payload.attestation.{verifier_class, level}` (wire real del
 * orquestador). Nota 18 §5 permite props de capa UI adaptables además del
 * wire congelado; este campo es aditivo y opcional para no romper eventos
 * sin attestation (p. ej. `claim.emitted`).
 */
export interface EventAssurance {
  readonly verifierClass: VerifierClass | string; // wire crudo; se etiqueta con classLabel()
  readonly level: AssuranceLevel;
}

/** nota 18 §2.1 — consumed by RunTimeline and ProvenanceExplorer. */
export interface ProjectedEvent {
  readonly globalSeq: number;
  readonly type: string;
  readonly actorId: string;
  readonly occurredAt: string; // RFC 3339
  readonly stepId?: string;
  readonly resumen: string;
  readonly verdict?: Verdict; // presente si el evento representa un resultado
  readonly assurance?: EventAssurance; // Nivel-1 task 4 — solo verification.completed
  /**
   * D6 (decisión #93) — el payload ÍNTEGRO del wire SSE (freeze §9: la
   * proyección no recorta lo que el emisor estampó). Opcional y aditivo
   * (nota 18 §5, capa UI adaptable): los fixtures previos a D6 no lo traen.
   * RunThread lo parsea con los Zod de plan.* (schemas.ts) — jamás a mano.
   */
  readonly payload?: Readonly<Record<string, unknown>>;
}

/** nota 18 §2.1 — fixture/demo-only playback simulation for RunTimeline. */
export interface PlaybackControls {
  /**
   * `finished` is distinct from `idle`: `idle` is "never started",
   * `finished` is "ran to completion" — the UI needs to tell them apart to
   * offer "Repetir" instead of re-showing "Reproducir" over an already-full
   * timeline (ficha B5).
   */
  readonly state: 'playing' | 'paused' | 'finished' | 'idle';
  readonly onPlay: () => void;
  readonly onPause: () => void;
  readonly onScrub: (globalSeq: number) => void;
  /**
   * Pragmatic addition beyond the literal nota 18 §2.1 shape: the scrub
   * range input needs an upper bound to let the user "jump directly to a
   * point in the fixture stream" (brief Part 4.1), including points ahead
   * of what has revealed so far. Nota 18 §5 documents these interfaces as
   * adaptable UI-layer props (not a frozen wire contract), so this is a
   * safe, additive, demo-only field.
   */
  readonly maxGlobalSeq: number;
}

/**
 * nota 18 §2.2 — one verifier's attestation for a step (N per step), en
 * vocabulario clase+AL (freeze §4): la clase dice el método, el AL la
 * fuerza. `method`/`summary`/`evidence` son conveniencias de la capa UI
 * (nota 18 §5 — adaptable), no letra del wire.
 */
export interface Attestation {
  readonly verifierId: string;
  readonly verifierClass: VerifierClass;
  readonly anchorKind: AnchorKind;
  readonly level: AssuranceLevel;
  readonly verdict: Verdict;
  readonly method: string;
  readonly summary: string;
  readonly evidence: Record<string, unknown>;
}

/** nota 18 §2.2 — consumed by StepInspector. */
export interface StepDetail {
  readonly stepId: string;
  readonly capabilityId: string;
  readonly inputDigest: string;
  readonly outputDigest: string;
  readonly attestations: readonly Attestation[];
}

/** freeze §7 — una conclusión: el alcance visible antes que el número. */
export interface CertificateConclusion {
  readonly claimDigest: string;
  readonly canonicalStatement: string;
  readonly scope: Readonly<Record<string, string>>;
  readonly verdict: ConclusionVerdict;
  readonly level: AssuranceLevel;
  readonly claimType?: string;
}

/** freeze §7 — `{statement, ref?{name, digest}}`. */
export interface CertificateAssumption {
  readonly statement: string;
  readonly ref?: { readonly name: string; readonly digest: string };
}

/** freeze §7 — `{artifact_ref, digest}` (binding anti-TOCTOU). */
export interface CertificateDeliverable {
  readonly artifactRef: string;
  readonly digest: string;
}

/**
 * freeze §4/§7 — attestation embebida en el payload DSSE (Fase 1: una sola
 * firma ampara certificado + attestations). Solo los campos que la UI
 * presenta; el crudo completo vive en `DsseEnvelope.rawPayload` (nivel 3).
 */
export interface CertificateAttestation {
  readonly verifierId: string;
  readonly verifierClass: string; // wire crudo; se etiqueta con classLabel()
  readonly anchorKind?: string;
  readonly level: AssuranceLevel;
  readonly verdict: Verdict;
  readonly independenceGroup: string;
  readonly claimDigest: string;
  readonly issuedAt: string;
}

/** nota 18 §2.3 / freeze §7 — the TrustCertificate Statement, camelCase. */
export interface TrustCertificateStatement {
  readonly _type: string;
  readonly subject: readonly {
    readonly name: string;
    readonly digest: { readonly sha256: string };
  }[];
  readonly predicateType: string;
  readonly predicate: {
    readonly runId: string;
    readonly actor: string; // URN (freeze §7 — string, ya no objeto)
    readonly provenanceHash: string;
    readonly conclusions: readonly CertificateConclusion[];
    readonly titularLevel: AssuranceLevel;
    readonly assumptions: readonly CertificateAssumption[];
    readonly deliverables: readonly CertificateDeliverable[];
    readonly unanchoredSteps: number;
    readonly policyDigest: string;
    readonly calculusVersion: string;
    readonly validAsOf: string;
    readonly revocation: string; // "none" en Fase 1 (P1-2 — honestidad declarada)
    readonly attestations: readonly CertificateAttestation[];
  };
}

/** nota 18 §2.3 — the decoded DSSE envelope, consumed by CertificateView. */
export interface DsseEnvelope {
  readonly payloadType: string;
  readonly payload: TrustCertificateStatement; // decodificado y mapeado para la UI
  /** Statement decodificado tal cual (nivel 3 — el crudo es crudo). */
  readonly rawPayload: unknown;
  readonly signatures: readonly { readonly keyid: string; readonly sig: string }[];
}

/**
 * dominio Studio F2 — estado de un run en la lista del proyecto. Extensión ADITIVA
 * `fallido`/`cancelado` (auditoría Fase 2, `docs/mvp/decisiones.md`
 * §"Análisis para discusión" punto 3): antes de esto un run terminado en
 * `run.failed`/`run.cancelled` quedaba "en_curso" para siempre en la lista
 * (verificado vivo) — `en_curso`/`completado` conservan su cómputo previo.
 */
export type RunStatus = 'en_curso' | 'completado' | 'fallido' | 'cancelado';

/**
 * F1.1 (ceremonia #176, `docs/studio/projects-workspaces.md`) — fila real de
 * la tabla `projects` (`GET /projects`): lo que el selector del sidebar
 * lista. `domainId` sale de la identidad de quien pregunta, nunca de un
 * parámetro del cliente. El shell (`AppShellProject`) hoy solo consume
 * `id`/`name`; los cuatro campos viajan igual para no fabricar un espejo
 * recortado del wire.
 */
export interface Project {
  readonly id: string;
  readonly domainId: string;
  readonly name: string;
  readonly createdAt: string;
}

/**
 * dominio Studio F2 — fila de la lista de Runs (proyección del certificado + los
 * eventos del run). La confianza (clase + AL) es columna de primera clase:
 * un run jamás se lista sin su badge.
 */
export interface RunSummary {
  readonly runId: string;
  readonly status: RunStatus;
  readonly conclusion: string;
  readonly verdict: ConclusionVerdict;
  readonly titularLevel: AssuranceLevel;
  readonly titularClass: string; // wire crudo; se etiqueta con classLabel()
  readonly eventsCount: number;
  readonly actor: string;
  readonly completedAt?: string;
}

/** dominio Studio F2 — entregable a nivel de proyecto, siempre con su procedencia. */
export interface ProjectArtifact {
  readonly artifactRef: string;
  readonly digest: string;
  readonly runId: string;
  readonly titularLevel: AssuranceLevel;
  readonly titularClass: string;
  readonly verdict: ConclusionVerdict;
  readonly issuedAt: string;
}

/** dominio Studio F2 — conclusión verificada acumulada en Knowledge. */
export interface KnowledgeClaim {
  readonly statement: string;
  readonly scope: Readonly<Record<string, string>>;
  readonly verdict: ConclusionVerdict;
  readonly level: AssuranceLevel;
  readonly titularClass: string;
  readonly runId: string;
  readonly validAsOf: string;
}

/** nota 18 §2.4 — consumed by ProvenanceExplorer. */
export interface ProvenanceFilters {
  readonly type?: string;
  readonly actorId?: string;
}

/** nota 07 §1.3 "Ablación" row — consumed by AblationPanel. */
/**
 * [V2/M19 · C-4] `variant` creció de 2 a 4 valores EN EL MISMO checkpoint que
 * su productor (`blite.runtime.metrics.AblationVariant`) — `mitigated` y `zne`
 * son los brazos de mitigación de M6. Extensión COORDINADA en los 4 espejos
 * (Pydantic, Zod, este tipo y el chart); jamás un catchall que dejaría entrar
 * una variante que ninguna superficie sabe pintar.
 */
export type AblationVariant = 'quantum' | 'classical' | 'mitigated' | 'zne';

export interface AblationMetric {
  readonly variant: AblationVariant;
  readonly cutCost: number;
  readonly wallMs: number;
  readonly verificationLatencyMs: number;
}

/**
 * D5 (dataviz "r vs p") — un baseline clásico/exacto contra el que QAOA se
 * mide: `r = energía / óptimo` (o su análogo de corte), SIN barras de error
 * porque es determinista (un solo run, no N semillas).
 */
export interface RvsPBaseline {
  readonly energy: number;
  readonly r: number;
}

/**
 * D5 — una fila de la curva r-vs-p para un valor de profundidad `p` de
 * QAOA, agregando sobre las semillas del experimento (`config.seeds` de la
 * fuente científica). Dos curvas honestas conviven en la misma fila
 * (decisión #21 — no trivializar con best-of-shots):
 * - `rEsperadoMean`: valor esperado ⟨C⟩ (`r_esperado.mean`) — independiente
 *   de la semilla, por eso NO trae std/min/max (son ≈0 por construcción).
 * - `rMuestralMean`/`rMuestralStd`/`rMuestralMin`/`rMuestralMax`: el
 *   muestreo real (`r_muestral`) — ESTA es la curva con barras de error.
 * - `successRate`: fracción de semillas cuyo mejor shot alcanzó el óptimo
 *   (`success_rate`) — se muestra en la tabla, etiquetado honestamente,
 *   nunca como titular (es trivialmente 1.0 en esta instancia pequeña).
 */
export interface RvsPPoint {
  readonly p: number;
  readonly rEsperadoMean: number;
  readonly rMuestralMean: number;
  readonly rMuestralStd: number;
  readonly rMuestralMin: number;
  readonly rMuestralMax: number;
  readonly successRate: number;
}

/**
 * D5 — el experimento r-vs-p completo de una instancia (fuente: la
 * ciencia real `results/exp_r_vs_p/<instancia>.json`, NO `AblationMetric[]`
 * — divergencia deliberada de spec `superficie-visual.md` §5, registrada en
 * `docs/mvp/decisiones.md`: esa forma no tiene eje `p` ni barras de error,
 * no puede expresar esta curva). Consumido por `RvsPChart`.
 */
export interface RvsPExperiment {
  readonly instance: string;
  readonly optimo: number;
  readonly baselines: {
    readonly cpsat: RvsPBaseline;
    readonly greedy: RvsPBaseline;
    readonly gw: RvsPBaseline;
  };
  readonly points: readonly RvsPPoint[];
}

/**
 * Nivel-1 task 2 — el form de "Nuevo run" (NewRunView), consumido también por
 * `src/data/mutations.ts` (el mapper hacia el contrato plan-01 de
 * `POST /runs`). Vive acá — no en data/mutations.ts — porque es la vista la
 * dueña del shape del formulario (F3: data/** importa tipos de views/**,
 * nunca al revés).
 */
/**
 * Lo que el usuario encarga al abrir un run (P3-D, modo misión).
 *
 * `mission` es TEXTO LIBRE y es lo único obligatorio: es el encargo, escrito
 * por quien lo pide. Las pistas son opcionales a propósito — el harness las
 * resuelve del plan si no vienen, y forzarlas convertiría una conversación en
 * un formulario (que es justo lo que la plantilla vieja hacía).
 */
export interface NewRunInput {
  readonly mission: string;
  /** Pista opcional: instancia del corpus (`instance_id` del contrato). */
  readonly instance?: string;
  /** Pista opcional: proposer preferido (se resuelve a `capability_id`). */
  readonly proposer?: string;
  /**
   * `run_id` del run RAÍZ del hilo (`chat-conversacion.md` §Contrato-4).
   * Es lo que vuelve accionable al 409: un stream terminal no acepta más
   * mensajes, así que continuar la conversación es abrir un run NUEVO que
   * cita al raíz — correlación de lectura, jamás streams anidados.
   */
  readonly threadId?: string;
}
