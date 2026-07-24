/**
 * Fixture — full projected event stream for one IEEE-14 partition run.
 *
 * Simulates the SSE payload nota 07 §1.3 ("Run en vivo") would deliver:
 * run.started → solver capability job → verification (formal_exact) →
 * per-island power-flow capability jobs → verification (execution, ×2
 * islands) → dataset-match capability job → verification (ground_truth)
 * → run.completed. Verdicts/clases/AL/summaries mirror
 * spike/ieee14.ts (RUN_VERIFICATION, PARTITION) so this reads as the SAME
 * run, not unrelated demo data. Static fixture only — no network, no
 * backend (this ficha is 100% frontend on fixtures).
 */

import type { ProjectedEvent } from '../views/types';

export const RUN_EVENTS: readonly ProjectedEvent[] = [
  {
    globalSeq: 1,
    type: 'run.started',
    actorId: 'user:dylan',
    occurredAt: '2026-07-07T17:59:50.100Z',
    resumen: 'Run iniciado — partición controlada IEEE-14'
  },
  {
    globalSeq: 2,
    type: 'capability.job.invoked',
    actorId: 'service:runtime',
    occurredAt: '2026-07-07T17:59:50.400Z',
    stepId: 'step-solver',
    resumen: 'Invocando ortools-cpsat para la partición óptima'
  },
  {
    globalSeq: 3,
    type: 'capability.job.completed',
    actorId: 'service:runtime',
    occurredAt: '2026-07-07T17:59:51.200Z',
    stepId: 'step-solver',
    resumen: 'CP-SAT devolvió corte óptimo (costo 3, status OPTIMAL)'
  },
  {
    globalSeq: 4,
    type: 'verification.completed',
    actorId: 'service:verifier',
    occurredAt: '2026-07-07T17:59:51.500Z',
    stepId: 'step-solver',
    resumen: 'Verificación formal exacta (AL3): corte óptimo confirmado',
    verdict: 'pass',
    assurance: { verifierClass: 'formal_exact', level: 'AL3' }
  },
  {
    globalSeq: 5,
    type: 'capability.job.invoked',
    actorId: 'service:runtime',
    occurredAt: '2026-07-07T17:59:52.000Z',
    stepId: 'step-execution-a',
    resumen: 'Invocando pandapower-powerflow en Isla A'
  },
  {
    globalSeq: 6,
    type: 'capability.job.completed',
    actorId: 'service:runtime',
    occurredAt: '2026-07-07T17:59:53.100Z',
    stepId: 'step-execution-a',
    resumen: 'Flujo de potencia converge en Isla A'
  },
  {
    globalSeq: 7,
    type: 'verification.completed',
    actorId: 'service:verifier',
    occurredAt: '2026-07-07T17:59:53.400Z',
    stepId: 'step-execution-a',
    resumen: 'Verificación por ejecución (AL3): Isla A factible',
    verdict: 'pass',
    assurance: { verifierClass: 'execution', level: 'AL3' }
  },
  {
    globalSeq: 8,
    type: 'capability.job.invoked',
    actorId: 'service:runtime',
    occurredAt: '2026-07-07T17:59:54.000Z',
    stepId: 'step-execution-b',
    resumen: 'Invocando pandapower-powerflow en Isla B'
  },
  {
    globalSeq: 9,
    type: 'capability.job.completed',
    actorId: 'service:runtime',
    occurredAt: '2026-07-07T17:59:55.300Z',
    stepId: 'step-execution-b',
    resumen: 'Flujo de potencia converge en Isla B'
  },
  {
    globalSeq: 10,
    type: 'verification.completed',
    actorId: 'service:verifier',
    occurredAt: '2026-07-07T17:59:55.600Z',
    stepId: 'step-execution-b',
    resumen: 'Verificación por ejecución (AL3): Isla B factible',
    verdict: 'pass',
    assurance: { verifierClass: 'execution', level: 'AL3' }
  },
  {
    globalSeq: 11,
    type: 'capability.job.invoked',
    actorId: 'service:runtime',
    occurredAt: '2026-07-07T17:59:56.200Z',
    stepId: 'step-dataset',
    resumen: 'Comparando partición contra el corpus IEEE-14'
  },
  {
    globalSeq: 12,
    type: 'capability.job.completed',
    actorId: 'service:runtime',
    occurredAt: '2026-07-07T17:59:57.800Z',
    stepId: 'step-dataset',
    resumen: 'Coincide con el óptimo conocido del corpus'
  },
  {
    globalSeq: 13,
    type: 'verification.completed',
    actorId: 'service:verifier',
    occurredAt: '2026-07-07T17:59:58.100Z',
    stepId: 'step-dataset',
    resumen: 'Verificación contra verdad conocida (AL3): coincide con el corpus',
    verdict: 'pass',
    assurance: { verifierClass: 'ground_truth', level: 'AL3' }
  },
  {
    globalSeq: 14,
    type: 'run.completed',
    actorId: 'service:runtime',
    occurredAt: '2026-07-07T17:59:59.900Z',
    resumen: 'Run completado — certificado emitido, nivel titular AL3'
  }
];
