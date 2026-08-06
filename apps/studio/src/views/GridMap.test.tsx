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

/**
 * [V1/M18] El overlay de partición: lo que se pinta sale del run, y lo que
 * no casa se DECLARA. Estos tests fijan la parte de CP6 que vive del lado D —
 * badges por isla sobre el mapa y reconciliación honesta a la vista.
 */
describe('GridMap — overlay de partición (V1/M18)', () => {
  const OVERLAY = {
    islands: [
      {
        id: 'island-0',
        label: 'island-0',
        substationNames: ['Pailas'],
        verification: {
          verdict: 'pass' as const,
          level: 'AL2' as const,
          verifierClass: 'property_rule',
          method: 'structural-partition-v1',
          summary: 'island-0: 2/2 checks pasaron'
        }
      }
    ],
    matchedSubstations: 1,
    instanceDigest: '0078d201ff590345598ab0d7698a724cc642eaec4dca660a4ec66361402485a7'
  };

  test('sin partición dice que no hay nada que colorear — jamás colorea igual', () => {
    render(<GridMap dataset={DATASET} />);

    expect(screen.getByText(/no produjo una partición verificada por isla/i)).toBeInTheDocument();
  });

  test('con partición muestra un badge por isla con su clase y su nivel', () => {
    render(<GridMap dataset={DATASET} partition={OVERLAY} />);

    expect(screen.getByText('AL2')).toBeInTheDocument();
    expect(screen.getByText(/structural-partition-v1/)).toBeInTheDocument();
  });

  test('declara la reconciliación: cuántas subestaciones casaron y cuántas no', () => {
    render(<GridMap dataset={DATASET} partition={OVERLAY} />);

    expect(screen.getByText(/1 de 2 subestaciones reconciliadas/i)).toBeInTheDocument();
    expect(screen.getByText(/1 sin isla/i)).toBeInTheDocument();
  });

  test('cita el digest de la instancia reconciliada — procedencia, no adorno', () => {
    render(<GridMap dataset={DATASET} partition={OVERLAY} />);

    expect(screen.getByText('0078d201ff59')).toBeInTheDocument();
  });

  test('el hover de una subestación asignada nombra su isla y su nivel', () => {
    render(<GridMap dataset={DATASET} partition={OVERLAY} />);

    expect(screen.getByText('Pailas — Guanacaste, Liberia — island-0 (AL2)')).toBeInTheDocument();
  });

  test('una subestación que la partición no cubre se dice «sin isla», no se rellena', () => {
    render(<GridMap dataset={DATASET} partition={OVERLAY} />);

    expect(screen.getByText(/Palmar — Puntarenas, Osa — sin isla/)).toBeInTheDocument();
  });
});
