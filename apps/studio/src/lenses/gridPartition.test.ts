/**
 * Reconciliación partición ↔ mapa (V1/M18) — las tres formas honestas de
 * decir «no», y la forma de decir «sí» con el conteo declarado.
 */

import { describe, expect, test } from 'vitest';

import { ICE_DERIVED_INSTANCE } from '../data/iceInstance';
import { toGridPartitionOverlay } from './gridPartition';

import type { TopologySnapshot } from '../data/schemas';

const VERIFICATION = {
  verdict: 'pass',
  verifier_class: 'property_rule',
  level: 'AL2',
  anchor_kind: 'rule',
  method: 'structural-partition-v1',
  summary: 'island-0: 2/2 checks pasaron'
} as const;

/** Índices reales de la instancia estampada — nada inventado. */
const BUS_IDS = Object.keys(ICE_DERIVED_INSTANCE.nodos);
const NOMBRES = Object.values(ICE_DERIVED_INSTANCE.nodos);

function snapshot(over: Partial<TopologySnapshot> = {}): TopologySnapshot {
  return {
    topology_ref: 'ice-uniforme',
    islands: [
      {
        id: 'island-0',
        name: 'island-0',
        bus_ids: BUS_IDS.slice(0, 3),
        verification: { ...VERIFICATION }
      },
      {
        id: 'island-1',
        name: 'island-1',
        bus_ids: BUS_IDS.slice(3, 6),
        verification: { ...VERIFICATION, verdict: 'fail' }
      }
    ],
    cut_branch_ids: ['L0-5'],
    cut_cost: 1,
    ...over
  };
}

describe('toGridPartitionOverlay — cuándo NO se pinta', () => {
  test('sin snapshot no hay overlay', () => {
    expect(toGridPartitionOverlay(null, NOMBRES)).toBeNull();
    expect(toGridPartitionOverlay(undefined, NOMBRES)).toBeNull();
  });

  test('un run que corrió pero no produjo islas tampoco pinta', () => {
    expect(toGridPartitionOverlay(snapshot({ islands: [] }), NOMBRES)).toBeNull();
  });

  test('una partición de OTRA instancia no se pinta sobre estas subestaciones', () => {
    const ajena = snapshot({ topology_ref: 'sintetica-4bus' });
    expect(toGridPartitionOverlay(ajena, NOMBRES)).toBeNull();
  });

  test('sin `topology_ref` tampoco — no se adivina de qué red habla', () => {
    expect(toGridPartitionOverlay(snapshot({ topology_ref: null }), NOMBRES)).toBeNull();
  });
});

describe('toGridPartitionOverlay — lo que sí pinta, con su conteo', () => {
  test('traduce bus_ids a nombres de subestación del mapa', () => {
    const overlay = toGridPartitionOverlay(snapshot(), NOMBRES);

    expect(overlay).not.toBeNull();
    expect(overlay?.islands).toHaveLength(2);
    expect(overlay?.islands[0]?.substationNames).toEqual(
      BUS_IDS.slice(0, 3).map(id => ICE_DERIVED_INSTANCE.nodos[id])
    );
  });

  test('cada isla conserva SU constancia — jamás una global compartida', () => {
    const overlay = toGridPartitionOverlay(snapshot(), NOMBRES);

    expect(overlay?.islands.map(i => i.verification.verdict)).toEqual(['pass', 'fail']);
    expect(overlay?.islands[0]?.verification.level).toBe('AL2');
    expect(overlay?.islands[0]?.verification.verifierClass).toBe('property_rule');
  });

  test('cita el digest de la instancia que reconcilió (procedencia)', () => {
    const overlay = toGridPartitionOverlay(snapshot(), NOMBRES);
    expect(overlay?.instanceDigest).toBe(ICE_DERIVED_INSTANCE.digest);
  });

  test('una subestación fuera del mapa se omite y baja el conteo — nunca se rellena', () => {
    const overlay = toGridPartitionOverlay(snapshot(), NOMBRES.slice(0, 4));

    expect(overlay?.matchedSubstations).toBe(4);
    expect(overlay?.islands.reduce((total, isla) => total + isla.substationNames.length, 0)).toBe(
      4
    );
  });

  test('un bus_id que la instancia no conoce se omite en vez de romper', () => {
    const conBasura = snapshot();
    const sucio: TopologySnapshot = {
      ...conBasura,
      islands: [
        { ...conBasura.islands[0]!, bus_ids: [...conBasura.islands[0]!.bus_ids, '99999'] },
        conBasura.islands[1]!
      ]
    };

    const overlay = toGridPartitionOverlay(sucio, NOMBRES);
    expect(overlay?.islands[0]?.substationNames).toHaveLength(3);
  });
});
