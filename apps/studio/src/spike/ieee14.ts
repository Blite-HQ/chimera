/**
 * IEEE 14-bus test system — static spike data.
 *
 * Topology is the standard IEEE 14-bus benchmark (public literature).
 * The partition + verification overlay mirror the event/projection payloads
 * the Studio will eventually receive from the engine API (see
 * knowledge/trust/07-streaming-studio-sse-agui.md). Hardcoded here only for
 * the spike — the real Studio reads projections via gatewayClient (INV-1).
 */

export type Verdict = 'pass' | 'fail' | 'inconclusive';
export type AnchorKind = 'solver' | 'execution' | 'dataset' | 'rule' | 'human';

export interface Bus {
  readonly id: string;
  readonly isGenerator: boolean;
  /** Preset diagram coordinates (model space). */
  readonly x: number;
  readonly y: number;
}

export interface Branch {
  readonly id: string;
  readonly from: string;
  readonly to: string;
}

export interface VerificationBadge {
  readonly verdict: Verdict;
  readonly rung: number;
  readonly anchorKind: AnchorKind;
  readonly method: string;
  readonly summary: string;
}

export interface Island {
  readonly id: string;
  readonly name: string;
  readonly busIds: readonly string[];
  readonly verification: VerificationBadge;
}

export interface PartitionView {
  readonly islands: readonly Island[];
  readonly cutBranchIds: readonly string[];
  readonly cutCost: number;
}

export interface RunAttestation {
  readonly verifierId: string;
  readonly anchorKind: AnchorKind;
  readonly rung: number;
  readonly verdict: Verdict;
  readonly summary: string;
}

export interface RunVerificationSummary {
  readonly aggregateRung: number;
  readonly unanchoredSteps: number;
  readonly attestations: readonly RunAttestation[];
}

export const BUSES: readonly Bus[] = [
  { id: '1', isGenerator: true, x: 60, y: 420 },
  { id: '2', isGenerator: true, x: 200, y: 480 },
  { id: '3', isGenerator: true, x: 480, y: 480 },
  { id: '4', isGenerator: false, x: 420, y: 360 },
  { id: '5', isGenerator: false, x: 240, y: 340 },
  { id: '6', isGenerator: true, x: 240, y: 200 },
  { id: '7', isGenerator: false, x: 500, y: 280 },
  { id: '8', isGenerator: true, x: 620, y: 280 },
  { id: '9', isGenerator: false, x: 500, y: 180 },
  { id: '10', isGenerator: false, x: 430, y: 110 },
  { id: '11', isGenerator: false, x: 320, y: 140 },
  { id: '12', isGenerator: false, x: 120, y: 120 },
  { id: '13', isGenerator: false, x: 240, y: 80 },
  { id: '14', isGenerator: false, x: 440, y: 30 }
];

export const BRANCHES: readonly Branch[] = [
  { id: 'L1-2', from: '1', to: '2' },
  { id: 'L1-5', from: '1', to: '5' },
  { id: 'L2-3', from: '2', to: '3' },
  { id: 'L2-4', from: '2', to: '4' },
  { id: 'L2-5', from: '2', to: '5' },
  { id: 'L3-4', from: '3', to: '4' },
  { id: 'L4-5', from: '4', to: '5' },
  { id: 'L4-7', from: '4', to: '7' },
  { id: 'L4-9', from: '4', to: '9' },
  { id: 'L5-6', from: '5', to: '6' },
  { id: 'L6-11', from: '6', to: '11' },
  { id: 'L6-12', from: '6', to: '12' },
  { id: 'L6-13', from: '6', to: '13' },
  { id: 'L7-8', from: '7', to: '8' },
  { id: 'L7-9', from: '7', to: '9' },
  { id: 'L9-10', from: '9', to: '10' },
  { id: 'L9-14', from: '9', to: '14' },
  { id: 'L10-11', from: '10', to: '11' },
  { id: 'L12-13', from: '12', to: '13' },
  { id: 'L13-14', from: '13', to: '14' }
];

/**
 * Two-island controlled split: each island keeps generation
 * (A: gens 1,2,3 — B: gens 6,8). Cut set = the three tie lines.
 */
export const PARTITION: PartitionView = {
  islands: [
    {
      id: 'island-a',
      name: 'Isla A',
      busIds: ['1', '2', '3', '4', '5'],
      verification: {
        verdict: 'pass',
        rung: 2,
        anchorKind: 'execution',
        method: 'pandapower-powerflow',
        summary: 'Flujo de potencia converge · balance dentro de límites'
      }
    },
    {
      id: 'island-b',
      name: 'Isla B',
      busIds: ['6', '7', '8', '9', '10', '11', '12', '13', '14'],
      verification: {
        verdict: 'pass',
        rung: 2,
        anchorKind: 'execution',
        method: 'pandapower-powerflow',
        summary: 'Flujo de potencia converge · balance dentro de límites'
      }
    }
  ],
  cutBranchIds: ['L4-7', 'L4-9', 'L5-6'],
  cutCost: 3
};

export const RUN_VERIFICATION: RunVerificationSummary = {
  aggregateRung: 3,
  unanchoredSteps: 0,
  attestations: [
    {
      verifierId: 'ortools-cpsat',
      anchorKind: 'solver',
      rung: 1,
      verdict: 'pass',
      summary: 'Corte = óptimo exacto (CP-SAT, status OPTIMAL)'
    },
    {
      verifierId: 'pandapower-powerflow',
      anchorKind: 'execution',
      rung: 2,
      verdict: 'pass',
      summary: 'Ambas islas factibles por ejecución de flujo de potencia'
    },
    {
      verifierId: 'ieee14-known-optimum',
      anchorKind: 'dataset',
      rung: 3,
      verdict: 'pass',
      summary: 'Coincide con la partición óptima conocida del corpus IEEE-14'
    }
  ]
};

export const ISLAND_COLORS: Readonly<Record<string, string>> = {
  'island-a': '#0ea5e9', // sky-500
  'island-b': '#a855f7' // purple-500
};
