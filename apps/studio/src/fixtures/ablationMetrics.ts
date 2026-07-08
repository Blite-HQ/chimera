/**
 * Fixture — the "Ablación" row from nota 07 §1.3: quantum vs. classical
 * solver for the SAME IEEE-14 partition problem. Both reach the identical
 * optimal cut_cost (3, matching spike/ieee14.ts PARTITION.cutCost) — the
 * point of this fixture is an honest comparison (quantum modestly faster
 * wall time, not a gimmick 10x claim), verification latency near-identical
 * since both runs go through the same non-model anchors afterward.
 */

import type { AblationMetric } from '../views/types';

export const ABLATION_METRICS: readonly AblationMetric[] = [
  {
    variant: 'quantum',
    cutCost: 3,
    wallMs: 820,
    verificationLatencyMs: 410
  },
  {
    variant: 'classical',
    cutCost: 3,
    wallMs: 1140,
    verificationLatencyMs: 425
  }
];
