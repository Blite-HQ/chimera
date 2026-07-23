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

import type { AssuranceLevel, VerifierClass } from '@/components/verification/assurance';

import type { AnchorKind, Verdict } from '../spike/ieee14';

export type { AnchorKind, AssuranceLevel, Verdict, VerifierClass };

/** nota 18 §2.1 — consumed by RunTimeline and ProvenanceExplorer. */
export interface ProjectedEvent {
  readonly globalSeq: number;
  readonly type: string;
  readonly actorId: string;
  readonly occurredAt: string; // RFC 3339
  readonly stepId?: string;
  readonly resumen: string;
  readonly verdict?: Verdict; // presente si el evento representa un resultado
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

/** freeze §7 — veredicto de una conclusión del camino crítico. */
export type ConclusionVerdict = 'verified' | 'refuted' | 'inconclusive' | 'not_required_declared';

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

/** nota 18 §2.4 — consumed by ProvenanceExplorer. */
export interface ProvenanceFilters {
  readonly type?: string;
  readonly actorId?: string;
}

/** nota 07 §1.3 "Ablación" row — consumed by AblationPanel. */
export interface AblationMetric {
  readonly variant: 'quantum' | 'classical';
  readonly cutCost: number;
  readonly wallMs: number;
  readonly verificationLatencyMs: number;
}
