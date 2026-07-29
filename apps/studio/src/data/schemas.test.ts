import { describe, expect, it } from 'vitest';

import { ABLATION_METRICS } from '../fixtures/ablationMetrics';
import { EXAMPLE_CERTIFICATE_WIRE } from '../fixtures/certificate';
import { RUN_EVENTS } from '../fixtures/runEvents';
import { RVSP_EXPERIMENT } from '../fixtures/rvsp';
import { STEP_EVIDENCE } from '../fixtures/stepEvidence';
import {
  ablationMetricSchema,
  ablationWireSchema,
  knowledgeClaimWireSchema,
  projectArtifactWireSchema,
  projectedEventSchema,
  runSummaryWireSchema,
  rvspSchema,
  sseProjectedEventSchema,
  stepDetailSchema,
  stepDetailWireSchema,
  toAblationMetric,
  toKnowledgeClaim,
  toProjectArtifact,
  toProjectedEvent,
  toRunSummary,
  toStepDetail,
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

/**
 * D3 — los 3 wire schemas + mappers nuevos de `docs/specs/endpoints-studio.md`
 * §"Contrato Zod" (runs/artifacts/knowledge) más ablation/step-evidence
 * (reusan shape existente salvo casing). Mismo patrón que
 * sseProjectedEventSchema/toProjectedEvent: el wire snake_case se valida
 * primero, el mapeo a camelCase es una función pura sin re-parse contra el
 * schema de fixtures (ese exige invariantes — p. ej. regex SHA256 — que son
 * el contrato de fixtures, no el wire honesto de un run real).
 */
describe('runSummaryWireSchema / toRunSummary (D3 — GET /runs)', () => {
  const WIRE = {
    run_id: '8f2c1a9b',
    status: 'completado' as const,
    conclusion: 'La partición propuesta de ieee14 es el óptimo exacto del corte',
    verdict: 'verified' as const,
    titular_level: 'AL3' as const,
    titular_class: 'formal_exact',
    events_count: 12,
    actor: 'user:dylan',
    completed_at: '2026-07-22T12:00:06.000000Z'
  };

  it('parsea el wire y lo mapea a camelCase', () => {
    const wire = runSummaryWireSchema.parse(WIRE);
    expect(toRunSummary(wire)).toEqual({
      runId: '8f2c1a9b',
      status: 'completado',
      conclusion: WIRE.conclusion,
      verdict: 'verified',
      titularLevel: 'AL3',
      titularClass: 'formal_exact',
      eventsCount: 12,
      actor: 'user:dylan',
      completedAt: '2026-07-22T12:00:06.000000Z'
    });
  });

  it('un run en curso sin certificado aún: conclusion/verdict/titular_* llegan null (honesto, no error)', () => {
    const wire = runSummaryWireSchema.parse({
      ...WIRE,
      status: 'en_curso',
      conclusion: null,
      verdict: null,
      titular_level: null,
      titular_class: null,
      completed_at: null // E1 lo emite null (no undefined) en un run en curso
    });
    expect(toRunSummary(wire)).toEqual({
      runId: '8f2c1a9b',
      status: 'en_curso',
      conclusion: 'Sin conclusión registrada',
      verdict: 'inconclusive',
      titularLevel: 'AL0',
      titularClass: 'formal_exact',
      eventsCount: 12,
      actor: 'user:dylan'
    });
  });

  it('rechaza un status fuera del vocabulario en_curso/completado', () => {
    expect(() => runSummaryWireSchema.parse({ ...WIRE, status: 'pendiente' })).toThrow();
  });
});

describe('projectArtifactWireSchema / toProjectArtifact (D3 — GET /runs/{id}/artifacts)', () => {
  it('parsea el wire y lo mapea a camelCase', () => {
    const wire = projectArtifactWireSchema.parse({
      artifact_ref: 'partition.json',
      digest: 'a1b751764b2d516ab45b8ac077a0eff0ab49c3d4245e882f3c0bef59de498b93',
      run_id: '8f2c1a9b',
      titular_level: 'AL3',
      titular_class: 'formal_exact',
      verdict: 'verified',
      issued_at: '2026-07-22T12:00:06.000000Z'
    });
    expect(toProjectArtifact(wire)).toEqual({
      artifactRef: 'partition.json',
      digest: 'a1b751764b2d516ab45b8ac077a0eff0ab49c3d4245e882f3c0bef59de498b93',
      runId: '8f2c1a9b',
      titularLevel: 'AL3',
      titularClass: 'formal_exact',
      verdict: 'verified',
      issuedAt: '2026-07-22T12:00:06.000000Z'
    });
  });
});

describe('knowledgeClaimWireSchema / toKnowledgeClaim (D3 — GET /runs/{id}/knowledge)', () => {
  it('parsea el wire y lo mapea a camelCase', () => {
    const wire = knowledgeClaimWireSchema.parse({
      statement: 'La partición propuesta de ieee14 es el óptimo exacto del corte',
      scope: { problem: 'islanding-partition', instance: 'ieee14' },
      verdict: 'verified',
      level: 'AL3',
      titular_class: 'formal_exact',
      run_id: '8f2c1a9b',
      valid_as_of: '2026-07-22T12:00:06.000000Z'
    });
    expect(toKnowledgeClaim(wire)).toEqual({
      statement: 'La partición propuesta de ieee14 es el óptimo exacto del corte',
      scope: { problem: 'islanding-partition', instance: 'ieee14' },
      verdict: 'verified',
      level: 'AL3',
      titularClass: 'formal_exact',
      runId: '8f2c1a9b',
      validAsOf: '2026-07-22T12:00:06.000000Z'
    });
  });
});

describe('ablationWireSchema / toAblationMetric (D3 — GET /runs/{id}/ablation)', () => {
  it('parsea el wire snake_case y lo mapea a camelCase', () => {
    const wire = ablationWireSchema.parse({
      variant: 'quantum',
      cut_cost: 3,
      wall_ms: 820,
      verification_latency_ms: 410
    });
    expect(toAblationMetric(wire)).toEqual({
      variant: 'quantum',
      cutCost: 3,
      wallMs: 820,
      verificationLatencyMs: 410
    });
  });
});

describe('stepDetailWireSchema / toStepDetail (D3 — GET /runs/{id}/steps/{id}/evidence)', () => {
  it('parsea el wire y lo mapea a camelCase, con attestations bien formadas', () => {
    const wire = stepDetailWireSchema.parse({
      step_id: 'step-solver',
      capability_id: 'capability:ortools-cpsat',
      input_digest: '6770290ab3a3c377e19708b11d13031356778f63af64a619fe118d11f738d5a5',
      output_digest: 'b2b332ac13e696d301324cf19c53d97652abbb2d2bdcf02de1f6d300f4ca2661',
      attestations: [
        {
          verifier_id: 'ortools-cpsat',
          verifier_class: 'formal_exact',
          anchor_kind: 'solver',
          level: 'AL3',
          verdict: 'pass',
          method: 'cpsat-differential',
          summary: 'Corte = óptimo exacto (CP-SAT, status OPTIMAL)',
          evidence: { status: 'OPTIMAL' }
        }
      ]
    });
    expect(toStepDetail(wire)).toEqual({
      stepId: 'step-solver',
      capabilityId: 'capability:ortools-cpsat',
      inputDigest: '6770290ab3a3c377e19708b11d13031356778f63af64a619fe118d11f738d5a5',
      outputDigest: 'b2b332ac13e696d301324cf19c53d97652abbb2d2bdcf02de1f6d300f4ca2661',
      attestations: [
        {
          verifierId: 'ortools-cpsat',
          verifierClass: 'formal_exact',
          anchorKind: 'solver',
          level: 'AL3',
          verdict: 'pass',
          method: 'cpsat-differential',
          summary: 'Corte = óptimo exacto (CP-SAT, status OPTIMAL)',
          evidence: { status: 'OPTIMAL' }
        }
      ]
    });
  });

  it('capability_id/input_digest/output_digest null (E1 aún no los atribuye): mapea a string vacío, nunca fabrica un digest', () => {
    const wire = stepDetailWireSchema.parse({
      step_id: 'step-solver',
      capability_id: null,
      input_digest: null,
      output_digest: null,
      attestations: []
    });
    expect(toStepDetail(wire)).toEqual({
      stepId: 'step-solver',
      capabilityId: '',
      inputDigest: '',
      outputDigest: '',
      attestations: []
    });
  });

  it('descarta (sin explotar) una attestation cruda que no matchea el shape esperado', () => {
    const wire = stepDetailWireSchema.parse({
      step_id: 'step-solver',
      capability_id: null,
      input_digest: null,
      output_digest: null,
      attestations: [{ some: 'payload sin forma de attestation' }]
    });
    expect(toStepDetail(wire).attestations).toEqual([]);
  });
});
