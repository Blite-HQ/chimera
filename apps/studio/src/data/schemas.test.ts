import { describe, expect, it } from 'vitest';

import { ABLATION_METRICS } from '../fixtures/ablationMetrics';
import { EXAMPLE_CERTIFICATE_WIRE } from '../fixtures/certificate';
import APPROVAL_REQUESTED_CONTRACT_FIXTURE from '../fixtures/contract/harness/approval-requested.json';
import APPROVAL_RESPONDED_CONTRACT_FIXTURE from '../fixtures/contract/harness/approval-responded.json';
import MISSION_MESSAGE_CONTRACT_FIXTURE from '../fixtures/contract/harness/mission-message.json';
import PLAN_CREATED_CONTRACT_FIXTURE from '../fixtures/contract/harness/plan-created.json';
import PLAN_ITEM_UPDATED_CONTRACT_FIXTURE from '../fixtures/contract/harness/plan-item-updated.json';
import runMetricsFixture from '../fixtures/contract/superficie/run-metrics-recorded.json';
import TOPOLOGY_SNAPSHOT_CONTRACT_FIXTURE from '../fixtures/contract/superficie/topology-snapshot.json';
import { RUN_EVENTS } from '../fixtures/runEvents';
import { RVSP_EXPERIMENT } from '../fixtures/rvsp';
import { STEP_EVIDENCE } from '../fixtures/stepEvidence';
import {
  ablationMetricSchema,
  ablationWireSchema,
  approvalRequestedSchema,
  approvalRespondedSchema,
  knowledgeClaimWireSchema,
  missionMessageSchema,
  planCreatedSchema,
  planItemUpdatedSchema,
  projectArtifactWireSchema,
  projectedEventSchema,
  runSummaryWireSchema,
  rvspSchema,
  sseProjectedEventSchema,
  topologySnapshotSchema,
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
    // D6 (decisión #93) — el payload ahora viaja ÍNTEGRO con el evento
    // proyectado (freeze §9: la proyección no recorta); antes se descartaba.
    expect(projected.payload).toEqual(wire.payload);
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

  it('rechaza un status fuera del vocabulario en_curso/completado/fallido/cancelado', () => {
    expect(() => runSummaryWireSchema.parse({ ...WIRE, status: 'pendiente' })).toThrow();
  });

  /**
   * Auditoría Fase 2 (`docs/mvp/decisiones.md` §"Análisis para discusión"
   * punto 3, extensión aditiva) — antes un run terminado en
   * `run.failed`/`run.cancelled` quedaba "en_curso" para siempre.
   */
  it.each(['fallido', 'cancelado'] as const)('acepta status=%s (extensión aditiva)', status => {
    const wire = runSummaryWireSchema.parse({ ...WIRE, status });
    expect(toRunSummary(wire)).toMatchObject({ status });
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

describe('Zod espejo de plan.* contra los fixtures de costura (D6, contrato D↔A)', () => {
  // superficie-visual.md §7: el contrato es el par [fixture generado desde
  // Pydantic (gen-contract-fixtures-harness.py) + Zod espejo a mano]. Si el
  // engine cambia la forma, el fixture regenerado rompe ESTOS parses.
  it('plan-created.json valida contra planCreatedSchema', () => {
    const parsed = planCreatedSchema.parse(PLAN_CREATED_CONTRACT_FIXTURE);
    expect(parsed.items[0].status).toBe('pending');
  });

  it('plan-item-updated.json valida contra planItemUpdatedSchema (con cause)', () => {
    const parsed = planItemUpdatedSchema.parse(PLAN_ITEM_UPDATED_CONTRACT_FIXTURE);
    expect(parsed.status).toBe('failed');
    expect(parsed.cause).toBe('capability.job.failed');
  });

  it('un status fuera del conjunto cerrado explota (misma disciplina que RunStep.status)', () => {
    expect(() =>
      planItemUpdatedSchema.parse({ ...PLAN_ITEM_UPDATED_CONTRACT_FIXTURE, status: 'bogus' })
    ).toThrow();
  });

  it('toProjectedEvent conserva el payload íntegro (freeze §9 — la proyección no recorta)', () => {
    const projected = toProjectedEvent({
      global_seq: 3,
      type: 'plan.created',
      actor_id: 'service:runtime',
      occurred_at: '2026-07-29T12:00:00Z',
      resumen: 'plan.created',
      payload: PLAN_CREATED_CONTRACT_FIXTURE
    });
    expect(projected.payload).toEqual(PLAN_CREATED_CONTRACT_FIXTURE);
  });
});

describe('Zod espejo de approval.* contra los fixtures de costura (S-A #123, contrato D↔A)', () => {
  // chat-conversacion.md §7: mismo par [fixture generado desde Pydantic
  // (gen-contract-fixtures-harness.py) + Zod espejo a mano] que plan.*.
  // Cierra el lado D del anti-drift de N2 (los fixtures existían sin espejo).
  it('approval-requested.json valida contra approvalRequestedSchema', () => {
    const parsed = approvalRequestedSchema.parse(APPROVAL_REQUESTED_CONTRACT_FIXTURE);
    expect(parsed.approval_id).toBe('approval-1');
    // F1.3: el fixture ahora representa lo que el ÚNICO emisor real produce
    // — la clave AUSENTE (Pydantic omite optativos `None` con
    // `exclude_none=True`), jamás un `"step-1"` inventado.
    expect(parsed.step_id).toBeUndefined();
    expect(parsed.json_schema).toHaveProperty('required');
  });

  it('approval-requested con step_id NULO (la forma literal que emite loop.py) produce un valor parseado, no un descarte', () => {
    // Regresión del bug real: Zod v4 `.optional()` rechaza `null` (solo
    // tolera la clave ausente) — un `safeParse` fallido acá es
    // exactamente lo que hacía que `RunThread` descartara la card en
    // silencio (`if (!parsed.success) continue`).
    const conNulo = { ...APPROVAL_REQUESTED_CONTRACT_FIXTURE, step_id: null };
    const parsed = approvalRequestedSchema.safeParse(conNulo);
    expect(parsed.success).toBe(true);
    if (parsed.success) {
      expect(parsed.data.step_id).toBeNull();
    }
  });

  it('approval-responded.json valida contra approvalRespondedSchema', () => {
    const parsed = approvalRespondedSchema.parse(APPROVAL_RESPONDED_CONTRACT_FIXTURE);
    expect(parsed.authorized_by).toBe('user:dylan');
    expect(parsed.response).toEqual({ aprobado: true });
  });

  it('una respuesta booleana de tope (json_schema={"type":"boolean"}) valida — Any de Pydantic, no solo objeto', () => {
    // El segundo desajuste del diagnóstico: `ApprovalRespondedPayload.
    // response` es `Any` en Pydantic; `z.record()` solo aceptaba objetos y
    // un `true` de tope (justo lo que produce un json_schema booleano)
    // fallaba el espejo.
    const conBooleano = { ...APPROVAL_RESPONDED_CONTRACT_FIXTURE, response: true };
    expect(approvalRespondedSchema.safeParse(conBooleano).success).toBe(true);
  });

  it('una respuesta sin authorized_by explota (AX2: la relajación exige humano identificable)', () => {
    const sinAutor: Record<string, unknown> = { ...APPROVAL_RESPONDED_CONTRACT_FIXTURE };
    delete sinAutor.authorized_by;
    expect(() => approvalRespondedSchema.parse(sinAutor)).toThrow();
  });
});

describe('Zod espejo de mission.message contra el fixture de costura (S-A #123, contrato D↔A)', () => {
  // chat-conversacion.md §Contrato-1: el mensaje del usuario es un evento del
  // MISMO stream del run — por eso entra al provenance_hash. El espejo valida
  // la forma del payload; el `message_id` viaja en el wire (a diferencia de la
  // vista del proposer, que lo excluye para no romper la clave de replay).
  it('mission-message.json valida contra missionMessageSchema', () => {
    const parsed = missionMessageSchema.parse(MISSION_MESSAGE_CONTRACT_FIXTURE);
    expect(parsed.author).toBe('user:dylan');
    expect(parsed.message_id).toBe('msg-1');
    expect(parsed.text).toContain('3 islas');
  });

  it('un mensaje con texto vacío explota (§Contrato-1: no es evidencia de nada)', () => {
    const vacio = { ...MISSION_MESSAGE_CONTRACT_FIXTURE, text: '' };
    expect(() => missionMessageSchema.parse(vacio)).toThrow();
  });

  it('un mensaje sin author explota (la identidad la estampa el request, pero viaja)', () => {
    const sinAutor: Record<string, unknown> = { ...MISSION_MESSAGE_CONTRACT_FIXTURE };
    delete sinAutor.author;
    expect(() => missionMessageSchema.parse(sinAutor)).toThrow();
  });
});

describe('Zod espejo de topología contra el fixture de costura (S-D #125, contrato D↔E)', () => {
  // superficie-visual.md §8: origen = TopologyResponse (chimera_api.reads);
  // el fixture ejercita verification POR isla y la convención C-8 de
  // branch-ids (canónico L{min}-{max}[-k] + edge_id_property de GIS).
  it('topology-snapshot.json valida contra topologySnapshotSchema', () => {
    const parsed = topologySnapshotSchema.parse(TOPOLOGY_SNAPSHOT_CONTRACT_FIXTURE);
    expect(parsed.islands).toHaveLength(2);
    expect(parsed.cut_branch_ids).toEqual(['L3-6', 'L4-8-2', '70143']);
  });

  it('una isla sin bloque verification explota (regla §9, sin excepción)', () => {
    const roto = structuredClone(TOPOLOGY_SNAPSHOT_CONTRACT_FIXTURE) as Record<string, unknown>;
    const islands = roto.islands as Array<Record<string, unknown>>;
    delete islands[0].verification;
    expect(() => topologySnapshotSchema.parse(roto)).toThrow();
  });

  it('cada verification por isla viene en clase+AL (jamás rung)', () => {
    const parsed = topologySnapshotSchema.parse(TOPOLOGY_SNAPSHOT_CONTRACT_FIXTURE);
    for (const island of parsed.islands) {
      expect(island.verification.level).toMatch(/^AL[0-4]$/);
      expect(island.verification.verifier_class).toBe('execution');
    }
  });
});

/**
 * [V2/M19 · C-4] El fixture de costura `run-metrics-recorded` ES el contrato
 * del payload extendido: confianza (congelado) + ciencia (aditivo) en un solo
 * evento. Si el espejo Zod solo soportara uno de los dos grupos, fallaría acá
 * y no en vivo.
 */
describe('ablación — enum de variantes ×4 (C-4) y el fixture del productor', () => {
  it('acepta las cuatro variantes del enum coordinado', () => {
    for (const variant of ['quantum', 'classical', 'mitigated', 'zne'] as const) {
      const parsed = ablationWireSchema.parse({
        variant,
        cut_cost: 1,
        wall_ms: 2,
        verification_latency_ms: 3
      });
      expect(parsed.variant).toBe(variant);
    }
  });

  it('rechaza una variante fuera del enum — jamás un catchall silencioso', () => {
    expect(() =>
      ablationWireSchema.parse({
        variant: 'catchall',
        cut_cost: 1,
        wall_ms: 2,
        verification_latency_ms: 3
      })
    ).toThrow();
  });

  it('el fixture del productor trae confianza Y ciencia en el mismo payload', () => {
    expect(runMetricsFixture.variant).toBe('zne');
    expect(runMetricsFixture.attestations_total).toBe(4);
    expect(runMetricsFixture.cut_cost).toBe(57070);
  });

  it('la fila de ablación se arma con los campos científicos del cierre', () => {
    const fila = toAblationMetric(
      ablationWireSchema.parse({
        variant: runMetricsFixture.variant,
        cut_cost: runMetricsFixture.cut_cost,
        wall_ms: runMetricsFixture.wall_ms,
        verification_latency_ms: runMetricsFixture.verification_latency_ms
      })
    );
    expect(fila).toEqual({
      variant: 'zne',
      cutCost: 57070,
      wallMs: 1240,
      verificationLatencyMs: 812.5
    });
  });
});
