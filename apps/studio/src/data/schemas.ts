/**
 * Schemas Zod de la frontera de datos (F3) — espejo de los contratos
 * congelados (freeze §4/§7/§9 + nota 18 §2). Regla global: schema-based
 * validation at boundaries — TODO dato que entra a las vistas pasa por acá,
 * venga de fixtures (hoy) o del gateway real (S10: mismo schema, otra
 * fuente). El wire del SSE (snake_case, proyección de chimera_api) tiene su
 * schema + mapper propios para que S10 sea un swap, no un rewrite.
 */

import { z } from 'zod';

import { ASSURANCE_LEVELS } from '@chimera/assurance-ui';

import type { EventAssurance, ProjectedEvent } from '../views/types';

const SHA256_HEX = /^[0-9a-f]{64}$/;

export const verdictSchema = z.enum(['pass', 'fail', 'inconclusive']);

export const assuranceLevelSchema = z.enum(ASSURANCE_LEVELS);

/** freeze §4 — sin "model" por construcción (INV-2/PR2). */
export const verifierClassSchema = z.enum([
  'formal_exact',
  'execution',
  'ground_truth',
  'property_rule',
  'consensus_replication',
  'human_expert'
]);

export const anchorKindSchema = z.enum(['solver', 'execution', 'dataset', 'rule', 'human']);

/** nota 18 §2.1 — el evento proyectado que consumen las vistas (camelCase). */
export const projectedEventSchema = z.object({
  globalSeq: z.number().int().positive(),
  type: z.string().min(1),
  actorId: z.string().min(1),
  occurredAt: z.string().min(1),
  stepId: z.string().optional(),
  resumen: z.string().min(1),
  verdict: verdictSchema.optional(),
  // MVP task 4 — sin esto Zod lo strippea silenciosamente en
  // `z.array(projectedEventSchema).parse(RUN_EVENTS)` (queries.ts) y el
  // AssuranceBadge nunca se muestra en fixtures/demo mode.
  assurance: z.object({ verifierClass: z.string().min(1), level: assuranceLevelSchema }).optional()
});

/**
 * Espejo del wire SSE del api (freeze §9 · `chimera_api.projection`):
 * `data:` = `{global_seq, type, actor_id, occurred_at, step_id?, resumen,
 * payload}`. S10 parsea cada frame con ESTE schema dentro de gatewayClient.
 */
export const sseProjectedEventSchema = z.object({
  global_seq: z.number().int().positive(),
  type: z.string().min(1),
  actor_id: z.string().min(1),
  occurred_at: z.string().min(1),
  step_id: z.string().optional(),
  resumen: z.string().min(1),
  payload: z.record(z.string(), z.unknown())
});

export type SseProjectedEvent = z.infer<typeof sseProjectedEventSchema>;

/**
 * `payload.attestation` tal como lo emite el orquestador (freeze §4, wire
 * crudo snake_case) — solo los campos que este mapper necesita leer.
 */
const wireAttestationSchema = z.object({
  verifier_class: z.string().min(1),
  level: z.string().min(1)
});

/**
 * Extrae `EventAssurance` de `payload.attestation` cuando su `level` es un
 * `AssuranceLevel` reconocido; degrada a `undefined` (sin throw) si el
 * attestation falta o trae un nivel fuera de vocabulario — la regla del
 * brief es "graceful", no "explota el fixture".
 */
function toEventAssurance(payload: Record<string, unknown>): EventAssurance | undefined {
  const attestation = wireAttestationSchema.safeParse(payload['attestation']);
  if (!attestation.success) {
    return undefined;
  }
  const level = assuranceLevelSchema.safeParse(attestation.data.level);
  if (!level.success) {
    return undefined;
  }
  return { verifierClass: attestation.data.verifier_class, level: level.data };
}

/** Mapper wire→UI (S10 lo usa tal cual; la UI jamás ve snake_case). */
export function toProjectedEvent(wire: SseProjectedEvent): ProjectedEvent {
  // El verdict vive en `payload.verdict` (top level) — NO en
  // `payload.verification.verdict`, que no existe en el wire real del
  // orquestador (decisiones.md #8).
  const verdict = verdictSchema.safeParse(wire.payload['verdict']);
  const assurance = toEventAssurance(wire.payload);
  return {
    globalSeq: wire.global_seq,
    type: wire.type,
    actorId: wire.actor_id,
    occurredAt: wire.occurred_at,
    ...(wire.step_id !== undefined && { stepId: wire.step_id }),
    resumen: wire.resumen,
    ...(verdict.success && { verdict: verdict.data }),
    ...(assurance && { assurance })
  };
}

/** nota 18 §2.2 — attestation de un paso, en clase+AL (freeze §4). */
export const attestationSchema = z.object({
  verifierId: z.string().min(1),
  verifierClass: verifierClassSchema,
  anchorKind: anchorKindSchema,
  level: assuranceLevelSchema,
  verdict: verdictSchema,
  method: z.string().min(1),
  summary: z.string().min(1),
  evidence: z.record(z.string(), z.unknown())
});

export const stepDetailSchema = z.object({
  stepId: z.string().min(1),
  capabilityId: z.string().min(1),
  inputDigest: z.string().regex(SHA256_HEX),
  outputDigest: z.string().regex(SHA256_HEX),
  attestations: z.array(attestationSchema)
});

/** nota 07 §1.3 — fila de ablación. */
export const ablationMetricSchema = z.object({
  variant: z.enum(['quantum', 'classical']),
  cutCost: z.number().nonnegative(),
  wallMs: z.number().nonnegative(),
  verificationLatencyMs: z.number().nonnegative()
});

/** D5 — un baseline clásico/exacto: r ∈ [0, 1] (energía / óptimo). */
const rvspBaselineSchema = z.object({
  energy: z.number().nonnegative(),
  r: z.number().min(0).max(1)
});

/**
 * D5 — espejo de `RvsPExperiment` (views/types.ts): fuente = la ciencia
 * real (`results/exp_r_vs_p/<instancia>.json`), NO `AblationMetric[]`
 * (divergencia de spec §5 registrada en decisiones.md). `p` es la
 * profundidad QAOA (entero positivo); toda razón `r` vive en [0, 1].
 */
export const rvspSchema = z.object({
  instance: z.string().min(1),
  optimo: z.number().positive(),
  baselines: z.object({
    cpsat: rvspBaselineSchema,
    greedy: rvspBaselineSchema,
    gw: rvspBaselineSchema
  }),
  points: z
    .array(
      z.object({
        p: z.number().int().positive(),
        rEsperadoMean: z.number().min(0).max(1),
        rMuestralMean: z.number().min(0).max(1),
        rMuestralStd: z.number().nonnegative(),
        rMuestralMin: z.number().min(0).max(1),
        rMuestralMax: z.number().min(0).max(1),
        successRate: z.number().min(0).max(1)
      })
    )
    .min(1)
});

/** freeze §7 — el envelope DSSE wire (payload base64 + firma): lo descargable. */
export const wireEnvelopeSchema = z.object({
  payloadType: z.string().min(1),
  payload: z.string().min(1),
  signatures: z.array(z.object({ keyid: z.string().min(1), sig: z.string().min(1) })).min(1)
});
