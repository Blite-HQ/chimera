/**
 * Frontera de validación (F3 "validar en la frontera") para el subconjunto
 * de GeoJSON del ICE que GridMap (D4) consume: solo los tipos de geometría
 * y las propiedades que esta vista lee. El resto (FID, OBJECTID,
 * SHAPE_STLe, Shape__Length, ...) están en los archivos reales pero son
 * irrelevantes acá — Zod los descarta al parsear (`z.object` es "strip" por
 * default), así que nunca se confía en más de lo que se valida.
 *
 * Hallazgo real del dataset: `lineas.geojson` mezcla geometrías LineString
 * (72 features) y MultiLineString (30 features) para líneas individuales —
 * NO solo MultiLineString como sugiere una primera lectura del nombre del
 * layer. d3-geo's geoPath dibuja ambas exactamente igual, así que el schema
 * las modela como unión en vez de forzar una a la otra.
 */

import { z } from 'zod';

const LONGITUDE_MIN = -180;
const LONGITUDE_MAX = 180;
const LATITUDE_MIN = -90;
const LATITUDE_MAX = 90;

const positionSchema = z.tuple([
  z.number().min(LONGITUDE_MIN).max(LONGITUDE_MAX),
  z.number().min(LATITUDE_MIN).max(LATITUDE_MAX)
]);

const pointGeometrySchema = z.object({
  type: z.literal('Point'),
  coordinates: positionSchema
});

const lineStringGeometrySchema = z.object({
  type: z.literal('LineString'),
  coordinates: z.array(positionSchema).min(2)
});

const multiLineStringGeometrySchema = z.object({
  type: z.literal('MultiLineString'),
  coordinates: z.array(z.array(positionSchema).min(2)).min(1)
});

const transmissionLineGeometrySchema = z.union([
  lineStringGeometrySchema,
  multiLineStringGeometrySchema
]);

/** Props del layer "Subestaciones" (portal ICE) que esta vista lee. */
const substationPropertiesSchema = z.object({
  Subestacio: z.string().min(1),
  Provincia: z.string().min(1),
  Canton: z.string().min(1),
  Distrito: z.string().min(1)
});

/** Props del layer "LineasDeTransmision" — solo el voltaje importa acá. */
const transmissionLinePropertiesSchema = z.object({
  Voltaje: z.union([z.literal(230), z.literal(138)]),
  Circuito: z.string().min(1).optional()
});

const substationFeatureSchema = z.object({
  type: z.literal('Feature'),
  geometry: pointGeometrySchema,
  properties: substationPropertiesSchema
});

const transmissionLineFeatureSchema = z.object({
  type: z.literal('Feature'),
  geometry: transmissionLineGeometrySchema,
  properties: transmissionLinePropertiesSchema
});

export const substationCollectionSchema = z.object({
  type: z.literal('FeatureCollection'),
  features: z.array(substationFeatureSchema).min(1)
});

export const transmissionLineCollectionSchema = z.object({
  type: z.literal('FeatureCollection'),
  features: z.array(transmissionLineFeatureSchema).min(1)
});

export type SubstationFeature = z.infer<typeof substationFeatureSchema>;
export type SubstationCollection = z.infer<typeof substationCollectionSchema>;
export type TransmissionLineFeature = z.infer<typeof transmissionLineFeatureSchema>;
export type TransmissionLineCollection = z.infer<typeof transmissionLineCollectionSchema>;

/**
 * D4 — el dataset que consume el router de formatos cuando `format ===
 * 'geojson'`: la red nacional REAL del ICE (70 subestaciones + 102
 * líneas), NO la instancia benchmark del run (ieee6/ieee14) — son dos
 * redes distintas (honestidad, ver GridMap.tsx).
 */
export interface GeoJsonGridDataset {
  readonly format: 'geojson';
  readonly substations: SubstationCollection;
  readonly lines: TransmissionLineCollection;
  readonly attribution: string;
}

const PROVINCIA_CANONICAL: Readonly<Record<string, string>> = {
  'san jose': 'San José',
  limon: 'Limón'
};

/**
 * Normaliza inconsistencias de acentuación en `Provincia` (nota de limpieza
 * de datos del dataset real): el portal del ICE mezcla "Limón"/"Limon" y
 * "San José"/"San Jose" en filas distintas del mismo archivo. Compara sin
 * tildes (NFD + strip de diacríticos) para no depender de qué variante
 * llegó, y deja pasar sin cambios cualquier provincia fuera del mapa (las
 * otras cinco provincias de Costa Rica no llevan tilde en su nombre).
 */
export function normalizeProvincia(rawProvincia: string): string {
  const key = rawProvincia
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase();
  return PROVINCIA_CANONICAL[key] ?? rawProvincia.trim();
}
