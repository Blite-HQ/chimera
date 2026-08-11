import { render, screen } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';

import DataFormatRouter from './DataFormatRouter';

import type { GenericGeoDataset } from '../data/geoJsonSchemas';

/**
 * D4 — el router de formato dispatchea por `dataset.format`. GeoMap se
 * mockea acá (su propio archivo de test cubre el renderer real) para que
 * este test verifique SOLO la selección de vista, no d3-geo. El fixture es
 * SINTÉTICO (O7/#173.2) — el router no debe depender del shape del ICE.
 */
vi.mock('./GeoMap', () => ({
  default: () => <div data-testid="geo-map-stub" />
}));

const GENERIC_DATASET: GenericGeoDataset = {
  format: 'geojson',
  collection: {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [10, 20] },
        properties: { anyField: 'anyValue' }
      },
      {
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: [
            [10, 20],
            [11, 21]
          ]
        },
        properties: { anotherField: 42 }
      }
    ]
  },
  attribution: 'Fuente sintética de prueba'
};

describe('DataFormatRouter — dispatch por dataset.format (D4)', () => {
  test('format "geojson" renderiza GeoMap', () => {
    render(<DataFormatRouter dataset={GENERIC_DATASET} />);

    expect(screen.getByTestId('geo-map-stub')).toBeInTheDocument();
  });

  test('un formato desconocido cae al fallback etiquetado con el nombre del formato', () => {
    render(<DataFormatRouter dataset={{ format: 'csv' }} />);

    expect(screen.queryByTestId('geo-map-stub')).not.toBeInTheDocument();
    expect(screen.getByText(/formato «csv» sin visualizador todavía/i)).toBeInTheDocument();
  });
});
