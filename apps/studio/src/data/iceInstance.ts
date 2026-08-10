/**
 * V1/M18 — el puente índice↔nombre que el overlay de partición necesita.
 *
 * El payload de partición (`superficie-visual.md` §4) cita `bus_ids`: índices
 * de la instancia derivada. El mapa pinta features geográficas nombradas. El
 * puente es el mapa `nodos` que la instancia YA estampó junto con su digest;
 * `scripts/gen-studio-ice-instance.py` lo proyecta acá y un test anti-drift
 * falla si el corpus cambia y esta copia no (`test_studio_ice_instance.py`).
 *
 * Vive en data/** por la misma razón que `iceGrid.ts` (regla F3): las vistas
 * consumen datos SOLO desde acá, nunca importando fixtures directo.
 */

import { z } from 'zod';

import instanciaRaw from '../fixtures/ice/instancia.json';

const derivedInstanceSchema = z.object({
  slug: z.string().min(1),
  instancia: z.string().min(1),
  convencion: z.string().min(1),
  digest: z.string().length(64),
  n_nodos: z.number().int().positive(),
  /** índice de bus (string, como viaja en `bus_ids`) → nombre del nodo. */
  nodos: z.record(z.string(), z.string().min(1))
});

export type DerivedInstance = z.infer<typeof derivedInstanceSchema>;

/**
 * La instancia derivada de la red real, validada una sola vez al importar
 * este módulo (un archivo corrupto explota acá, no en un render).
 */
export const ICE_DERIVED_INSTANCE: DerivedInstance = derivedInstanceSchema.parse(instanciaRaw);

/**
 * Normalización de nombres para casar dos datasets: NFKD → ASCII (descarta
 * diacríticos) → minúsculas → trim. Es la MISMA que usó la derivación
 * (`geojson_to_graph._normalize_name`) — casar con otra regla produciría
 * emparejamientos que la instancia estampada nunca hizo.
 */
export function normalizeNodeName(value: string): string {
  return value
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

/**
 * `topology_ref` del payload ↔ esta instancia. El run cita su instancia; si
 * no es esta, el overlay NO pinta: reconciliar índices de otra red contra
 * estas subestaciones sería inventar una partición.
 */
export function isDerivedFromIceInstance(topologyRef: string | null): boolean {
  if (topologyRef === null) return false;
  const slug = topologyRef.split('@')[0];
  return slug === ICE_DERIVED_INSTANCE.slug || slug === ICE_DERIVED_INSTANCE.instancia;
}

/** Nombre de la subestación de un `bus_id`, o `undefined` si el índice no existe. */
export function nodeNameOf(busId: string): string | undefined {
  return ICE_DERIVED_INSTANCE.nodos[busId];
}
