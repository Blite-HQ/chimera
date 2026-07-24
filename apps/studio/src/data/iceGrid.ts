/**
 * D4 — carga y valida el GeoJSON REAL del ICE (F3 "frontera de datos"): los
 * archivos viven en fixtures/ice/*.geojson (bundleados, NUNCA un fetch —
 * INV-1 + "sin red/sin tiles" del mapa, ver GridMap.tsx) y se importan como
 * texto crudo (`?raw`, soportado por Vite para cualquier extensión) porque
 * `.geojson` no es una extensión que el resolvedor JSON nativo de Vite
 * reconozca — `JSON.parse` + los schemas Zod de `iceGridSchemas.ts` SON la
 * frontera de validación real acá, nunca se confía en el archivo a ciegas.
 *
 * Import eager a nivel de módulo (mismo patrón que fixtures/certificate.ts):
 * un archivo corrupto explota al importar este módulo, no en un render.
 *
 * Vive en data/** (no en fixtures/ ni en views/) porque F3 exige que las
 * vistas (views/components/spike/App.tsx) consuman datos SOLO vía
 * src/data/** — depcruise (INV F3) bloquea a las vistas de importar
 * src/fixtures directo; este módulo es el único punto que sí lo hace.
 */

import subestacionesRaw from '../fixtures/ice/subestaciones.geojson?raw';
import lineasRaw from '../fixtures/ice/lineas.geojson?raw';
import {
  substationCollectionSchema,
  transmissionLineCollectionSchema,
  type GeoJsonGridDataset
} from './iceGridSchemas';

const ATTRIBUTION = 'Datos: ICE — datos abiertos (datos-ice-se.opendata.arcgis.com)';

function parseJson(raw: string): unknown {
  return JSON.parse(raw);
}

/**
 * La red nacional REAL del ICE (70 subestaciones + 102 líneas de
 * transmisión), construida y validada una sola vez al importar este
 * módulo. Consumida por DataFormatRouter/GridMap vía props — NUNCA
 * importada directo por una vista (F3).
 */
export const ICE_GRID_DATASET: GeoJsonGridDataset = {
  format: 'geojson',
  substations: substationCollectionSchema.parse(parseJson(subestacionesRaw)),
  lines: transmissionLineCollectionSchema.parse(parseJson(lineasRaw)),
  attribution: ATTRIBUTION
};
