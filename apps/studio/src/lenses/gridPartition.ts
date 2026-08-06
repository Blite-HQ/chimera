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
 */

import {
  ICE_DERIVED_INSTANCE,
  isDerivedFromIceInstance,
  normalizeNodeName
} from '../data/iceInstance';

import type { TopologySnapshot } from '../data/schemas';
import type { GridPartitionOverlay } from '../views/GridMap';

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
