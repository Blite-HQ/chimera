/**
 * Frontera de validación (F3) para datos geoespaciales GENÉRICOS — O7/#173.2
 * (directiva de Dylan 2026-08-11, `docs/mejorado/`): el artifact de mapa NO
 * conoce el dataset que lo alimenta. Antes este módulo (`iceGridSchemas.ts`)
 * clavaba los nombres de campo del portal del ICE (`Subestacio`, `Provincia`,
 * `Canton`, `Distrito`, `Voltaje ∈ {230,138}`, `Circuito`) directo en el
 * schema Zod — cualquier dataset con OTRO shape rompía en la frontera. Ese
 * acoplamiento era precisamente la data quemada que la directiva pide sacar.
 *
 * Reemplazo: un `FeatureCollection` con geometrías Point/LineString/
 * MultiLineString (hallazgo real conservado: un mismo archivo puede mezclar
 * LineString y MultiLineString — d3-geo's geoPath dibuja ambas igual) y
 * propiedades ARBITRARIAS (`Record<string, unknown>`, ningún nombre de
 * campo asumido). Qué propiedad usar como etiqueta/grupo/peso pasa a ser
 * CONFIGURACIÓN del render (`GeoRenderConfig`, `views/GeoMap.tsx`) — mismo
 * patrón que `blite.ingesta.geojson.to_graph` (`node_match_property`,
 * `endpoint_property`, `weight_property` viajan como PARAMS de invocación,
 * jamás hardcodeados en el manifest; ver
 * `capabilities/ingesta/tests/test_geojson_to_graph.py`
 * ::TestEndpointNameMatchStrategyGenericBehaviour).
 *
 * `normalizeProvincia` (limpieza de acentuación de UN dataset concreto) NO
 * tiene reemplazo genérico acá — era limpieza de dato específica del ICE, no
 * un paso del camino genérico; si algún día hace falta, es una función
 * OPCIONAL que el caller aplica por configuración, nunca incondicional.
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

const geoGeometrySchema = z.union([
  pointGeometrySchema,
  lineStringGeometrySchema,
  multiLineStringGeometrySchema
]);

/** Propiedades ARBITRARIAS — ningún nombre de campo se asume (ADR-029). */
const geoPropertiesSchema = z.record(z.string(), z.unknown());

const geoFeatureSchema = z.object({
  type: z.literal('Feature'),
  geometry: geoGeometrySchema,
  properties: geoPropertiesSchema
});

export const geoFeatureCollectionSchema = z.object({
  type: z.literal('FeatureCollection'),
  features: z.array(geoFeatureSchema)
});

export type GeoGeometry = z.infer<typeof geoGeometrySchema>;
export type GeoFeature = z.infer<typeof geoFeatureSchema>;
export type GeoFeatureCollection = z.infer<typeof geoFeatureCollectionSchema>;

/**
 * El dataset que consume `DataFormatRouter`/`GeoMap` cuando `format ===
 * 'geojson'`. `attribution` es opcional y genérico (citar la fuente es una
 * práctica geoespacial estándar, no algo específico del ICE).
 */
export const geospatialDatasetSchema = z.object({
  format: z.literal('geojson'),
  collection: geoFeatureCollectionSchema,
  attribution: z.string().min(1).optional()
});

export type GenericGeoDataset = z.infer<typeof geospatialDatasetSchema>;

/**
 * Media types que este componente reconoce como "hay un dato geoespacial
 * disponible" — IANA registra `application/geo+json` (RFC 7946); se acepta
 * también el histórico `application/vnd.geo+json` que muchos clientes viejos
 * (y navegadores sin mapeo de `.geojson`) todavía emiten. El criterio es el
 * TIPO de dato, jamás su dominio — ningún capability id ni vocabulario de
 * reto entra acá (O7/#173.2).
 */
const GEOSPATIAL_MEDIA_TYPES: ReadonlySet<string> = new Set([
  'application/geo+json',
  'application/vnd.geo+json'
]);

export function isGeospatialMediaType(mediaType: string): boolean {
  const base = mediaType.split(';')[0]?.trim().toLowerCase() ?? '';
  return GEOSPATIAL_MEDIA_TYPES.has(base);
}
