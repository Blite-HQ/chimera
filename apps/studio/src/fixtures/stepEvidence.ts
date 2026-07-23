/**
 * Fixture — StepDetail (input/output digests + attestations) for the 3
 * verification steps of the IEEE-14 run in runEvents.ts (solver, execution
 * ×2 islands, dataset). Digests are real sha256 hex (of arbitrary fixture
 * strings, computed with `sha256sum` — not recomputed from the actual
 * event stream, since this is a static frontend fixture, not the engine).
 * Evidence shapes follow nota 18 §2.2 (method-dependent Record<string,
 * unknown>): differential for the solver, power-flow metrics for
 * execution, corpus match for dataset — same verifiers/clases+AL as
 * spike/ieee14.ts (freeze §4).
 */

import type { StepDetail } from '../views/types';

export const STEP_EVIDENCE: Readonly<Record<string, StepDetail>> = {
  'step-solver': {
    stepId: 'step-solver',
    capabilityId: 'capability:ortools-cpsat',
    inputDigest: '6770290ab3a3c377e19708b11d13031356778f63af64a619fe118d11f738d5a5',
    outputDigest: 'b2b332ac13e696d301324cf19c53d97652abbb2d2bdcf02de1f6d300f4ca2661',
    attestations: [
      {
        verifierId: 'ortools-cpsat',
        anchorKind: 'solver',
        verifierClass: 'formal_exact',
        level: 'AL3',
        verdict: 'pass',
        method: 'cpsat-differential',
        summary: 'Corte = óptimo exacto (CP-SAT, status OPTIMAL)',
        evidence: {
          differential: { status: 'OPTIMAL', objective: 3, referenceObjective: 3 }
        }
      }
    ]
  },
  'step-execution-a': {
    stepId: 'step-execution-a',
    capabilityId: 'capability:pandapower-powerflow',
    inputDigest: '585db683cb2ea51dceee5c0a717d5c4f12bc26ac37590f2f63b686072940bf4a',
    outputDigest: '190b0496ab5da84ba0d523685cd01ecbef44b96c674757858b3acceee74aecd1',
    attestations: [
      {
        verifierId: 'pandapower-powerflow',
        anchorKind: 'execution',
        verifierClass: 'execution',
        level: 'AL3',
        verdict: 'pass',
        method: 'pandapower-powerflow',
        summary: 'Flujo de potencia converge en Isla A · balance dentro de límites',
        evidence: { powerflowConverged: true, maxVoltageDeviationPu: 0.018 }
      }
    ]
  },
  'step-execution-b': {
    stepId: 'step-execution-b',
    capabilityId: 'capability:pandapower-powerflow',
    inputDigest: 'c8f18543933d45a7f846810ada23d00648ca54514d1e580c3fd09a1a301d0e5e',
    outputDigest: 'edc693f2afe3084fee206acf0a2e7bd25dcb8793301aa5f4f29eec017593c6c2',
    attestations: [
      {
        verifierId: 'pandapower-powerflow',
        anchorKind: 'execution',
        verifierClass: 'execution',
        level: 'AL3',
        verdict: 'pass',
        method: 'pandapower-powerflow',
        summary: 'Flujo de potencia converge en Isla B · balance dentro de límites',
        evidence: { powerflowConverged: true, maxVoltageDeviationPu: 0.021 }
      }
    ]
  },
  'step-dataset': {
    stepId: 'step-dataset',
    capabilityId: 'capability:corpus-match',
    inputDigest: '8764b583aea77a4786a749efc53c74a23771ae5fca603804fe18337e9b744b26',
    outputDigest: 'd002265bfc17ff59dc558fbcfed3a6b3e3dca99365129886b7d6a282ba6cf590',
    attestations: [
      {
        verifierId: 'ieee14-known-optimum',
        anchorKind: 'dataset',
        verifierClass: 'ground_truth',
        level: 'AL3',
        verdict: 'pass',
        method: 'corpus-match',
        summary: 'Coincide con la partición óptima conocida del corpus IEEE-14',
        evidence: { corpusId: 'ieee14-known-optimum', matched: true }
      }
    ]
  }
};
