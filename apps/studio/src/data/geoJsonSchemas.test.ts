import { describe, expect, test } from 'vitest';

import {
  geoFeatureCollectionSchema,
  geospatialDatasetSchema,
  isGeospatialMediaType
} from './geoJsonSchemas';

/**
 * Frontera de validación (F3) para el subconjunto de GeoJSON que el
 * artifact geoespacial GENÉRICO consume (O7/#173.2, `docs/mejorado/`
 * directiva 2026-08-11): el componente no puede saber de antemano qué
 * dataset le van a integrar, así que el fixture de este archivo usa
 * nombres de propiedad SINTÉTICOS, inventados para esta prueba — nunca los
 * del ICE (`Subestacio`/`Provincia`/`Voltaje`). Un test que solo pasara con
 * campos del ICE no probaría genericidad.
 *
 * Hallazgo real conservado del dataset original (mezcla LineString +
 * MultiLineString en la misma colección) se prueba acá también, sobre datos
 * sintéticos: d3-geo's geoPath dibuja ambas formas igual, así que el schema
 * las modela como unión en vez de forzar una a la otra.
 */

const SYNTHETIC_COLLECTION = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [10.5, 45.2] },
      properties: { assetCode: 'north-node', region: 'north', throughputMw: 42 }
    },
    {
      type: 'Feature',
      geometry: {
        type: 'LineString',
        coordinates: [
          [10.5, 45.2],
          [11.1, 44.8]
        ]
      },
      properties: { linkCode: 'link-a', capacity: 5 }
    },
    {
      type: 'Feature',
      geometry: {
        type: 'MultiLineString',
        coordinates: [
          [
            [12.0, 44.0],
            [13.0, 43.5]
          ]
        ]
      },
      properties: { linkCode: 'link-b', capacity: 20 }
    }
  ]
};

describe('geoFeatureCollectionSchema — genericidad (ADR-029, cero vocabulario del ICE)', () => {
  test('acepta un FeatureCollection con nombres de propiedad ARBITRARIOS', () => {
    expect(() => geoFeatureCollectionSchema.parse(SYNTHETIC_COLLECTION)).not.toThrow();
  });

  test('acepta Point, LineString y MultiLineString mezclados en la misma colección', () => {
    const parsed = geoFeatureCollectionSchema.parse(SYNTHETIC_COLLECTION);
    expect(parsed.features.map(feature => feature.geometry.type)).toEqual([
      'Point',
      'LineString',
      'MultiLineString'
    ]);
  });

  test('conserva las propiedades arbitrarias íntegras, sin descartar claves desconocidas', () => {
    const parsed = geoFeatureCollectionSchema.parse(SYNTHETIC_COLLECTION);
    expect(parsed.features[0]?.properties).toEqual({
      assetCode: 'north-node',
      region: 'north',
      throughputMw: 42
    });
  });

  test('acepta una colección vacía — un layer sin features es GeoJSON válido', () => {
    expect(() =>
      geoFeatureCollectionSchema.parse({ type: 'FeatureCollection', features: [] })
    ).not.toThrow();
  });

  test('rechaza coordenadas fuera de rango lon/lat — no confía a ciegas en el archivo', () => {
    const bad = {
      ...SYNTHETIC_COLLECTION,
      features: [
        {
          ...SYNTHETIC_COLLECTION.features[0],
          geometry: { type: 'Point', coordinates: [999, 45.2] }
        }
      ]
    };
    expect(() => geoFeatureCollectionSchema.parse(bad)).toThrow();
  });

  test('rechaza una geometría no soportada (Polygon)', () => {
    const bad = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          geometry: {
            type: 'Polygon',
            coordinates: [
              [
                [0, 0],
                [1, 0],
                [1, 1],
                [0, 0]
              ]
            ]
          },
          properties: {}
        }
      ]
    };
    expect(() => geoFeatureCollectionSchema.parse(bad)).toThrow();
  });

  test('rechaza un FeatureCollection sin "features" — geojson malformado, error en la frontera', () => {
    expect(() => geoFeatureCollectionSchema.parse({ type: 'FeatureCollection' })).toThrow();
  });

  test('rechaza cuando "type" no es "FeatureCollection"', () => {
    expect(() => geoFeatureCollectionSchema.parse({ type: 'Feature', features: [] })).toThrow();
  });
});

describe('geospatialDatasetSchema — el dataset genérico que consume DataFormatRouter/GeoMap', () => {
  test('acepta {format: "geojson", collection}', () => {
    expect(() =>
      geospatialDatasetSchema.parse({ format: 'geojson', collection: SYNTHETIC_COLLECTION })
    ).not.toThrow();
  });

  test('attribution es opcional', () => {
    const parsed = geospatialDatasetSchema.parse({
      format: 'geojson',
      collection: SYNTHETIC_COLLECTION
    });
    expect(parsed.attribution).toBeUndefined();
  });

  test('cuando trae attribution, se conserva', () => {
    const parsed = geospatialDatasetSchema.parse({
      format: 'geojson',
      collection: SYNTHETIC_COLLECTION,
      attribution: 'Fuente sintética de prueba'
    });
    expect(parsed.attribution).toBe('Fuente sintética de prueba');
  });

  test('rechaza un format distinto de "geojson"', () => {
    expect(() =>
      geospatialDatasetSchema.parse({ format: 'csv', collection: SYNTHETIC_COLLECTION })
    ).toThrow();
  });
});

describe('isGeospatialMediaType — el criterio de disparo por TIPO de dato (O7/#173.2)', () => {
  test('reconoce el media type IANA de GeoJSON (RFC 7946)', () => {
    expect(isGeospatialMediaType('application/geo+json')).toBe(true);
  });

  test('reconoce el media type con parámetros adicionales (charset)', () => {
    expect(isGeospatialMediaType('application/geo+json; charset=utf-8')).toBe(true);
  });

  test('reconoce el media type histórico application/vnd.geo+json', () => {
    expect(isGeospatialMediaType('application/vnd.geo+json')).toBe(true);
  });

  test('NO reconoce un tipo ajeno — el criterio es el TIPO de dato, no el dominio', () => {
    expect(isGeospatialMediaType('application/pdf')).toBe(false);
    expect(isGeospatialMediaType('text/csv')).toBe(false);
    expect(isGeospatialMediaType('application/octet-stream')).toBe(false);
  });
});
