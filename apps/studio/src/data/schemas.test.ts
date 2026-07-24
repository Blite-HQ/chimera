import { describe, expect, it } from 'vitest';

import { ABLATION_METRICS } from '../fixtures/ablationMetrics';
import { EXAMPLE_CERTIFICATE_WIRE } from '../fixtures/certificate';
import { RUN_EVENTS } from '../fixtures/runEvents';
import { RVSP_EXPERIMENT } from '../fixtures/rvsp';
import { STEP_EVIDENCE } from '../fixtures/stepEvidence';
import {
  ablationMetricSchema,
  projectedEventSchema,
  rvspSchema,
  sseProjectedEventSchema,
  stepDetailSchema,
  toProjectedEvent,
  wireEnvelopeSchema
} from './schemas';

describe('schemas de la frontera (F3)', () => {
  it('valida todos los fixtures vigentes (un fixture corrupto explota acá)', () => {
    expect(() => RUN_EVENTS.map(e => projectedEventSchema.parse(e))).not.toThrow();
    expect(() => Object.values(STEP_EVIDENCE).map(s => stepDetailSchema.parse(s))).not.toThrow();
    expect(() => ABLATION_METRICS.map(m => ablationMetricSchema.parse(m))).not.toThrow();
    expect(() => rvspSchema.parse(RVSP_EXPERIMENT)).not.toThrow();
    expect(() => wireEnvelopeSchema.parse(EXAMPLE_CERTIFICATE_WIRE)).not.toThrow();
  });

  it('rechaza una attestation con vocabulario supersedido o clase "model"', () => {
    const base = Object.values(STEP_EVIDENCE)[0]!.attestations[0]!;
    expect(() =>
      stepDetailSchema.shape.attestations.element.parse({
        ...base,
        verifierClass: 'model'
      })
    ).toThrow();
  });

  it('parsea el wire SSE del api y lo mapea a camelCase con verdict + assurance embebidos (wire real del orquestador)', () => {
    const wire = sseProjectedEventSchema.parse({
      global_seq: 4,
      type: 'verification.completed',
      actor_id: 'service:verifier',
      occurred_at: '2026-07-22T12:00:04.000000Z',
      resumen: 'Verificación formal exacta (AL3)',
      payload: {
        claim_digest: 'sha256:abc',
        verifier_id: 'verifier:cpsat-exact',
        verdict: 'pass',
        attestation: {
          verifier_class: 'formal_exact',
          level: 'AL3',
          verdict: 'pass',
          claim_digest: 'sha256:abc',
          verifier_id: 'verifier:cpsat-exact',
          independence_group: 'solver',
          issued_at: '2026-07-22T12:00:04.000000Z'
        }
      }
    });
    const projected = toProjectedEvent(wire);
    expect(projected.globalSeq).toBe(4);
    expect(projected.actorId).toBe('service:verifier');
    expect(projected.verdict).toBe('pass');
    expect(projected.assurance).toEqual({ verifierClass: 'formal_exact', level: 'AL3' });
    expect('payload' in projected).toBe(false);
  });

  it('un evento claim.emitted no trae verdict ni assurance (el wire no los incluye)', () => {
    const wire = sseProjectedEventSchema.parse({
      global_seq: 3,
      type: 'claim.emitted',
      actor_id: 'service:runtime',
      occurred_at: '2026-07-22T12:00:03.000000Z',
      resumen: 'Claim declarado — corte óptimo propuesto',
      payload: {
        claim_digest: 'sha256:def',
        claim_type: 'partition.optimal_cut',
        is_conclusion: true,
        world: 'ieee14',
        irreversible: false,
        affects_third_party: false
      }
    });
    const projected = toProjectedEvent(wire);
    expect(projected.verdict).toBeUndefined();
    expect(projected.assurance).toBeUndefined();
  });

  it('degrada con gracia (sin assurance) cuando el level de la attestation no es reconocido', () => {
    const wire = sseProjectedEventSchema.parse({
      global_seq: 4,
      type: 'verification.completed',
      actor_id: 'service:verifier',
      occurred_at: '2026-07-22T12:00:04.000000Z',
      resumen: 'Verificación formal exacta',
      payload: {
        claim_digest: 'sha256:abc',
        verifier_id: 'verifier:cpsat-exact',
        verdict: 'pass',
        attestation: {
          verifier_class: 'formal_exact',
          level: 'AL99',
          verdict: 'pass',
          claim_digest: 'sha256:abc',
          verifier_id: 'verifier:cpsat-exact',
          independence_group: 'solver',
          issued_at: '2026-07-22T12:00:04.000000Z'
        }
      }
    });
    const projected = toProjectedEvent(wire);
    expect(projected.verdict).toBe('pass');
    expect(projected.assurance).toBeUndefined();
  });
});

describe('rvspSchema (D5 — dataviz "r vs p")', () => {
  it('rechaza un punto con r fuera de [0, 1] (frontera — un dato corrupto explota acá)', () => {
    const corrupted = {
      ...RVSP_EXPERIMENT,
      points: [{ ...RVSP_EXPERIMENT.points[0]!, rMuestralMean: 1.4 }]
    };
    expect(() => rvspSchema.parse(corrupted)).toThrow();
  });

  it('rechaza p no entero o no positivo', () => {
    const corrupted = { ...RVSP_EXPERIMENT, points: [{ ...RVSP_EXPERIMENT.points[0]!, p: 0 }] };
    expect(() => rvspSchema.parse(corrupted)).toThrow();
  });

  it('rechaza cuando falta un baseline', () => {
    const corrupted = {
      ...RVSP_EXPERIMENT,
      baselines: {
        cpsat: RVSP_EXPERIMENT.baselines.cpsat,
        greedy: RVSP_EXPERIMENT.baselines.greedy
      }
    };
    expect(() => rvspSchema.parse(corrupted)).toThrow();
  });
});
