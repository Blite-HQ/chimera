import { describe, expect, test } from 'vitest';

import { ICE_GRID_DATASET } from './iceGrid';

/**
 * D4 — el dataset REAL del ICE, cargado y validado una sola vez al importar
 * el módulo (mismo patrón que fixtures/certificate.ts: un archivo corrupto
 * explota acá, no en un render). Este test asegura que el conteo de
 * features coincide con la procedencia declarada (provenance.ts) y que el
 * shape es el que DataFormatRouter/GridMap esperan.
 */
describe('ICE_GRID_DATASET', () => {
  test('format es "geojson" — el router lo despacha a GridMap', () => {
    expect(ICE_GRID_DATASET.format).toBe('geojson');
  });

  test('70 subestaciones reales, todas Point', () => {
    expect(ICE_GRID_DATASET.substations.features).toHaveLength(70);
    expect(
      ICE_GRID_DATASET.substations.features.every(feature => feature.geometry.type === 'Point')
    ).toBe(true);
  });

  test('102 líneas de transmisión reales, con Voltaje en {230, 138}', () => {
    expect(ICE_GRID_DATASET.lines.features).toHaveLength(102);
    expect(
      ICE_GRID_DATASET.lines.features.every(feature =>
        [230, 138].includes(feature.properties.Voltaje)
      )
    ).toBe(true);
  });

  test('trae attribution visible mencionando ICE y el portal de datos abiertos', () => {
    expect(ICE_GRID_DATASET.attribution).toContain('ICE');
    expect(ICE_GRID_DATASET.attribution).toContain('datos-ice-se.opendata.arcgis.com');
  });
});
