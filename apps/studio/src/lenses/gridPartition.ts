/**
 * Reconciliación partición ↔ mapa (V1/M18) — lógica pura, testeable sin DOM.
 *
 * El payload de partición cita `bus_ids` (índices de la instancia derivada);
 * el mapa dibuja subestaciones nombradas. Este módulo hace el único puente
 * honesto entre ambos: el `nodos` que la instancia estampó, con su digest.
 *
 * Las tres formas de decir «no» que tiene esta función, y por qué importan:
 * - la partición viene vacía ⇒ el run no produjo islas verificadas;
 * - `topology_ref` no es esta instancia ⇒ pintar índices de otra red sobre
 *   estas subestaciones sería inventar una partición;
 * - un bus sin nombre en el mapa ⇒ se omite y el conteo lo declara (los 2 de
 *   70 que ningún circuito resuelve nunca entraron a la instancia derivada).
 *
 * O7/#173.2 — el tipo `GridPartitionOverlay` vivía en `views/GridMap.tsx`,
 * que ahora es `views/GeoMap.tsx` (GENÉRICO, cero vocabulario de dominio).
 * Este módulo es la pieza de la lente "Red" que SÍ sabe de subestaciones e
 * islas (legítimo — es un dominio registrado, `product-model.md`
 * §"Superficies de plataforma vs dominio"), así que el tipo se queda acá,
 * no en el componente genérico. `gridLens.tsx` adapta esta forma a la
 * `GeoOverlay` genérica de `GeoMap` antes de pasarla al render.
 */

import {
  ICE_DERIVED_INSTANCE,
  isDerivedFromIceInstance,
  normalizeNodeName
} from '../data/iceInstance';

import type { AssuranceLevel } from '@chimera/assurance-ui';
import type { TopologySnapshot } from '../data/schemas';

export interface IslandVerificationView {
  readonly verdict: 'pass' | 'fail' | 'inconclusive';
  readonly level: AssuranceLevel;
  readonly verifierClass: string;
  readonly method: string;
  readonly summary: string;
}

/**
 * Una isla lista para pintarse: qué subestaciones la componen (por nombre YA
 * reconciliado) y con qué constancia — freeze §9: `verification` POR isla,
 * sin excepción.
 */
export interface GridIslandOverlay {
  readonly id: string;
  readonly label: string;
  readonly substationNames: readonly string[];
  readonly verification: IslandVerificationView;
}

export interface GridPartitionOverlay {
  readonly islands: readonly GridIslandOverlay[];
  /** Subestaciones del mapa que la partición cubre. */
  readonly matchedSubstations: number;
  /** Digest de la instancia derivada que se reconcilió (procedencia). */
  readonly instanceDigest: string;
}

/**
 * Traduce el snapshot del run a overlay del mapa, o `null` cuando no hay
 * nada honesto que pintar.
 *
 * `substationNames` son los nombres TAL COMO aparecen en el GeoJSON (el mapa
 * hace lookup exacto): el matching normalizado ocurre acá, una sola vez.
 */
export function toGridPartitionOverlay(
  snapshot: TopologySnapshot | null | undefined,
  substationNames: readonly string[]
): GridPartitionOverlay | null {
  if (!snapshot || snapshot.islands.length === 0) {
    return null;
  }
  if (!isDerivedFromIceInstance(snapshot.topology_ref)) {
    return null;
  }

  const byNormalized = new Map<string, string>();
  for (const name of substationNames) {
    byNormalized.set(normalizeNodeName(name), name);
  }

  let matched = 0;
  const islands = snapshot.islands.map(island => {
    const names: string[] = [];
    for (const busId of island.bus_ids) {
      const nodeName = ICE_DERIVED_INSTANCE.nodos[busId];
      if (nodeName === undefined) continue;
      const mapped = byNormalized.get(normalizeNodeName(nodeName));
      if (mapped === undefined) continue;
      names.push(mapped);
    }
    matched += names.length;
    return {
      id: island.id,
      label: island.name,
      substationNames: names,
      verification: {
        verdict: island.verification.verdict,
        level: island.verification.level,
        verifierClass: island.verification.verifier_class,
        method: island.verification.method,
        summary: island.verification.summary
      }
    };
  });

  return {
    islands,
    matchedSubstations: matched,
    instanceDigest: ICE_DERIVED_INSTANCE.digest
  };
}
