import { describe, expect, it } from 'vitest';

import { ABLATION_METRICS } from '../fixtures/ablationMetrics';
import { EXAMPLE_CERTIFICATE_WIRE } from '../fixtures/certificate';
import { RUN_EVENTS } from '../fixtures/runEvents';
import { STEP_EVIDENCE } from '../fixtures/stepEvidence';
import {
  ablationMetricSchema,
  projectedEventSchema,
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

  it('parsea el wire SSE del api y lo mapea a camelCase con verdict embebido', () => {
    const wire = sseProjectedEventSchema.parse({
      global_seq: 4,
      type: 'verification.completed',
      actor_id: 'service:verifier',
      occurred_at: '2026-07-22T12:00:04.000000Z',
      resumen: 'Verificación formal exacta (AL3)',
      payload: { verification: { verdict: 'pass' } }
    });
    const projected = toProjectedEvent(wire);
    expect(projected.globalSeq).toBe(4);
    expect(projected.actorId).toBe('service:verifier');
    expect(projected.verdict).toBe('pass');
    expect('payload' in projected).toBe(false);
  });
});
