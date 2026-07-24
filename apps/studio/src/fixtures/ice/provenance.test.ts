import { describe, expect, test } from 'vitest';

import lineasRaw from './lineas.geojson?raw';
import { LINEAS_PROVENANCE, SUBESTACIONES_PROVENANCE } from './provenance';
import subestacionesRaw from './subestaciones.geojson?raw';

/**
 * Honestidad de dato (D4): la procedencia declarada en provenance.ts no se
 * toma de fe — `featureCount` se cruza acá contra el archivo real en disco
 * (mismo mecanismo `?raw` que usa data/iceGrid.ts), así que si alguien
 * regenera el geojson sin actualizar provenance.ts, este test es el que
 * revienta (RED), no un render silencioso con un conteo mentiroso. El
 * digest sha256 se deja como valor de referencia fijo (computado una vez
 * contra el archivo, ver el brief de D4) — recomputarlo en runtime pediría
 * Node `crypto`, fuera del tsconfig de esta app (browser-only, sin
 * `@types/node`); no aporta honestidad extra que el cruce de featureCount +
 * la validación Zod de iceGridSchemas.test.ts ya no cubran.
 */

function featureCountOf(raw: string): number {
  const parsed: unknown = JSON.parse(raw);
  if (
    typeof parsed !== 'object' ||
    parsed === null ||
    !('features' in parsed) ||
    !Array.isArray((parsed as { features: unknown }).features)
  ) {
    throw new Error('El archivo no tiene un array "features" — no es un FeatureCollection válido.');
  }
  return (parsed as { features: unknown[] }).features.length;
}

describe('SUBESTACIONES_PROVENANCE — procedencia real (ICE datos abiertos)', () => {
  test('featureCount es 70 y coincide con el archivo real en disco', () => {
    expect(SUBESTACIONES_PROVENANCE.featureCount).toBe(70);
    expect(SUBESTACIONES_PROVENANCE.featureCount).toBe(featureCountOf(subestacionesRaw));
  });

  test('digest sha256 (64 hex) y campos de procedencia real del portal ICE', () => {
    expect(SUBESTACIONES_PROVENANCE.digest).toBe(
      '39bd9a3784ba4455cae0e4a07fb5198e4def1be7bb0cba69f43e637ae69afe5c'
    );
    expect(SUBESTACIONES_PROVENANCE.itemId).toBe('f3fceca2659b4ecf8a5c2632e04aff1f');
    expect(SUBESTACIONES_PROVENANCE.sourceUrl).toContain('datos-ice-se.opendata.arcgis.com');
    expect(SUBESTACIONES_PROVENANCE.license).toContain('UsoOpenData');
    expect(SUBESTACIONES_PROVENANCE.retrievedAt).toBe('2026-07-24');
  });
});

describe('LINEAS_PROVENANCE — procedencia real (ICE datos abiertos)', () => {
  test('featureCount es 102 y coincide con el archivo real en disco', () => {
    expect(LINEAS_PROVENANCE.featureCount).toBe(102);
    expect(LINEAS_PROVENANCE.featureCount).toBe(featureCountOf(lineasRaw));
  });

  test('digest sha256 (64 hex) y campos de procedencia real del portal ICE', () => {
    expect(LINEAS_PROVENANCE.digest).toBe(
      '3f7ae3427ef3f619bdf4a27706fa43f7bec10195d0eb4ec457e05851b8720982'
    );
    expect(LINEAS_PROVENANCE.itemId).toBe('1cd1630e16144d3bbccb1bd434dc6866');
    expect(LINEAS_PROVENANCE.sourceUrl).toContain('datos-ice-se.opendata.arcgis.com');
    expect(LINEAS_PROVENANCE.license).toContain('UsoOpenData');
    expect(LINEAS_PROVENANCE.retrievedAt).toBe('2026-07-24');
  });
});
