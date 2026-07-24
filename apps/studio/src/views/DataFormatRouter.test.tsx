import { render, screen } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';

import DataFormatRouter from './DataFormatRouter';

import type { GeoJsonGridDataset } from '../data/iceGridSchemas';

/**
 * D4 — el router de formato dispatchea por `dataset.format`. GridMap se
 * mockea acá (su propio archivo de test cubre el renderer real) para que
 * este test verifique SOLO la selección de vista, no d3-geo.
 */
vi.mock('./GridMap', () => ({
  default: () => <div data-testid="grid-map-stub" />
}));

const GEOJSON_DATASET: GeoJsonGridDataset = {
  format: 'geojson',
  substations: {
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
  },
  lines: {
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
        properties: { Voltaje: 230 }
      }
    ]
  },
  attribution: 'Datos: ICE — datos abiertos (datos-ice-se.opendata.arcgis.com)'
};

describe('DataFormatRouter — dispatch por dataset.format (D4)', () => {
  test('format "geojson" renderiza GridMap', () => {
    render(<DataFormatRouter dataset={GEOJSON_DATASET} />);

    expect(screen.getByTestId('grid-map-stub')).toBeInTheDocument();
  });

  test('un formato desconocido cae al fallback etiquetado con el nombre del formato', () => {
    render(<DataFormatRouter dataset={{ format: 'csv' }} />);

    expect(screen.queryByTestId('grid-map-stub')).not.toBeInTheDocument();
    expect(screen.getByText(/formato «csv» sin visualizador todavía/i)).toBeInTheDocument();
  });
});
