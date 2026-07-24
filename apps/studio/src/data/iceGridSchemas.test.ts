import { describe, expect, test } from 'vitest';

import {
  normalizeProvincia,
  substationCollectionSchema,
  transmissionLineCollectionSchema
} from './iceGridSchemas';

/**
 * Frontera de datos (F3) para el GeoJSON del ICE (D4): estos schemas son la
 * validación real, no un tipo cast — un archivo mal formado debe rechazarse
 * acá, con un mensaje claro, antes de llegar a GridMap.
 */

const VALID_SUBSTATION_COLLECTION = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [-85.36, 10.76] },
      properties: {
        Subestacio: 'Pailas',
        Provincia: 'Guanacaste',
        Canton: 'Liberia',
        Distrito: 'Curubande'
      }
    }
  ]
};

const VALID_LINE_COLLECTION = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      geometry: {
        type: 'LineString',
        coordinates: [
          [-85.44, 10.61],
          [-85.43, 10.6]
        ]
      },
      properties: { Voltaje: 230, Circuito: 'Liberia-Papagayo' }
    },
    {
      type: 'Feature',
      geometry: {
        type: 'MultiLineString',
        coordinates: [
          [
            [-83.1, 9.9],
            [-83.2, 9.8]
          ]
        ]
      },
      properties: { Voltaje: 138 }
    }
  ]
};

describe('substationCollectionSchema', () => {
  test('acepta un FeatureCollection real de subestaciones (geometría Point)', () => {
    expect(() => substationCollectionSchema.parse(VALID_SUBSTATION_COLLECTION)).not.toThrow();
  });

  test('rechaza una geometría que no sea Point', () => {
    const bad = {
      ...VALID_SUBSTATION_COLLECTION,
      features: [
        {
          ...VALID_SUBSTATION_COLLECTION.features[0],
          geometry: { type: 'Polygon', coordinates: [] }
        }
      ]
    };
    expect(() => substationCollectionSchema.parse(bad)).toThrow();
  });

  test('rechaza coordenadas fuera de rango lon/lat (no confía a ciegas en el archivo)', () => {
    const bad = {
      ...VALID_SUBSTATION_COLLECTION,
      features: [
        {
          ...VALID_SUBSTATION_COLLECTION.features[0],
          geometry: { type: 'Point', coordinates: [999, 10.76] }
        }
      ]
    };
    expect(() => substationCollectionSchema.parse(bad)).toThrow();
  });

  test('rechaza un feature sin nombre de subestación', () => {
    const bad = {
      ...VALID_SUBSTATION_COLLECTION,
      features: [
        {
          ...VALID_SUBSTATION_COLLECTION.features[0],
          properties: { ...VALID_SUBSTATION_COLLECTION.features[0].properties, Subestacio: '' }
        }
      ]
    };
    expect(() => substationCollectionSchema.parse(bad)).toThrow();
  });

  test('rechaza una colección vacía (min 1 feature)', () => {
    expect(() =>
      substationCollectionSchema.parse({ type: 'FeatureCollection', features: [] })
    ).toThrow();
  });
});

describe('transmissionLineCollectionSchema', () => {
  test('acepta LineString y MultiLineString en el mismo dataset (el real del ICE mezcla ambos)', () => {
    expect(() => transmissionLineCollectionSchema.parse(VALID_LINE_COLLECTION)).not.toThrow();
  });

  test('rechaza un Voltaje fuera del vocabulario {230, 138}', () => {
    const bad = {
      ...VALID_LINE_COLLECTION,
      features: [{ ...VALID_LINE_COLLECTION.features[0], properties: { Voltaje: 500 } }]
    };
    expect(() => transmissionLineCollectionSchema.parse(bad)).toThrow();
  });

  test('rechaza una geometría distinta a LineString/MultiLineString', () => {
    const bad = {
      ...VALID_LINE_COLLECTION,
      features: [
        {
          ...VALID_LINE_COLLECTION.features[0],
          geometry: { type: 'Point', coordinates: [-85, 10] }
        }
      ]
    };
    expect(() => transmissionLineCollectionSchema.parse(bad)).toThrow();
  });
});

describe('normalizeProvincia — limpieza de acentuación (nota de limpieza de datos)', () => {
  test('normaliza "Limon" (sin tilde) a "Limón"', () => {
    expect(normalizeProvincia('Limon')).toBe('Limón');
  });

  test('deja "Limón" (ya con tilde) intacto', () => {
    expect(normalizeProvincia('Limón')).toBe('Limón');
  });

  test('normaliza "San Jose" a "San José"', () => {
    expect(normalizeProvincia('San Jose')).toBe('San José');
  });

  test('deja "San José" (ya con tilde) intacto', () => {
    expect(normalizeProvincia('San José')).toBe('San José');
  });

  test('deja pasar sin cambios una provincia sin ambigüedad de acento', () => {
    expect(normalizeProvincia('Guanacaste')).toBe('Guanacaste');
    expect(normalizeProvincia('Puntarenas')).toBe('Puntarenas');
  });
});
