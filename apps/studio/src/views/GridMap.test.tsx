import { render, screen } from '@testing-library/react';
import { describe, expect, test } from 'vitest';

import GridMap from './GridMap';

import type { GeoJsonGridDataset } from '../data/iceGridSchemas';

/**
 * D4 — GridMap proyecta un GeoJSON real a SVG con d3-geo. Fixture mínimo
 * (2 subestaciones + 2 líneas con kV distinto) para verificar: conteo de
 * elementos, ancho de trazo por Voltaje (230 más grueso que 138), la
 * atribución visible, y el rótulo de honestidad (red real ≠ partición del
 * run).
 */
const DATASET: GeoJsonGridDataset = {
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
      },
      {
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [-83.42, 8.94] },
        properties: {
          Subestacio: 'Palmar',
          Provincia: 'Puntarenas',
          Canton: 'Osa',
          Distrito: 'Palmar'
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
  },
  attribution: 'Datos: ICE — datos abiertos (datos-ice-se.opendata.arcgis.com)'
};

describe('GridMap — proyección d3-geo del grid real del ICE (D4)', () => {
  test('renderiza un circle por subestación', () => {
    const { container } = render(<GridMap dataset={DATASET} />);

    expect(container.querySelectorAll('svg circle')).toHaveLength(2);
    expect(screen.getByText(/Pailas/)).toBeInTheDocument();
    expect(screen.getByText(/Palmar/)).toBeInTheDocument();
  });

  test('renderiza un path por línea, y el ancho de trazo de 230kV es mayor que el de 138kV', () => {
    const { container } = render(<GridMap dataset={DATASET} />);
    const paths = container.querySelectorAll('svg path');
    expect(paths).toHaveLength(2);

    const widths = Array.from(paths).map(path => Number(path.getAttribute('stroke-width')));
    expect(widths[0]).toBeGreaterThan(widths[1]);
  });

  test('muestra la atribución del origen de los datos', () => {
    render(<GridMap dataset={DATASET} />);

    expect(screen.getByText(/datos-ice-se\.opendata\.arcgis\.com/)).toBeInTheDocument();
  });

  test('etiqueta el mapa como la red nacional real, distinta a la partición del run', () => {
    render(<GridMap dataset={DATASET} />);

    expect(screen.getByText(/red real/i)).toBeInTheDocument();
  });

  test('el hover de una subestación muestra su provincia normalizada (sin inconsistencia de tilde)', () => {
    render(<GridMap dataset={DATASET} />);

    expect(screen.getByText('Pailas — Guanacaste, Liberia')).toBeInTheDocument();
  });
});
