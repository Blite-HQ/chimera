/**
 * Shared prop/data contracts for the trust-UX views (knowledge/trust/18).
 *
 * These are the TypeScript interfaces from nota 18 §2 (RunTimeline,
 * StepInspector, CertificateView, ProvenanceExplorer), plus the ablation
 * payload shape from nota 07 §1.3. Centralized here (rather than duplicated
 * per component) because several types are shared across more than one view
 * — e.g. `Attestation` appears in both `StepDetail` (§2.2) and
 * `TrustCertificateStatement` (§2.3). Component files own their own
 * `*Props` interfaces; this file owns only the data shapes that cross view
 * boundaries.
 *
 * `Verdict`/`AnchorKind` are re-exported from the spike (spike/ieee14.ts)
 * rather than redefined, so the whole Studio shares one definition.
 */

import type { AnchorKind, Verdict } from '../spike/ieee14';

export type { AnchorKind, Verdict };

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
  readonly state: 'playing' | 'paused' | 'idle';
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

/** nota 18 §2.2 — one verifier's attestation for a step (N per step). */
export interface Attestation {
  readonly verifierId: string;
  readonly anchorKind: AnchorKind;
  readonly rung: number;
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

/** nota 18 §2.3 / nota 02 §1.3 — the TrustCertificate Statement, camelCase. */
export interface TrustCertificateStatement {
  readonly _type: string;
  readonly subject: readonly {
    readonly name: string;
    readonly digest: { readonly sha256: string };
  }[];
  readonly predicateType: string;
  readonly predicate: {
    readonly runId: string;
    readonly actor: { readonly id: string; readonly kind: string; readonly domainId: string };
    readonly aggregateRung: number;
    readonly unanchoredSteps: number;
    readonly attestations: readonly Attestation[];
    readonly policyId: string;
    readonly issuedAt: string;
  };
}

/** nota 18 §2.3 — the decoded DSSE envelope, consumed by CertificateView. */
export interface DsseEnvelope {
  readonly payloadType: string;
  readonly payload: TrustCertificateStatement; // ya decodificado de base64 para la UI
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
