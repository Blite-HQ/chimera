import { render, screen } from '@testing-library/react';
import { describe, expect, test } from 'vitest';

import GeoMap from './GeoMap';

import type { GeoOverlay } from './GeoMap';
import type { GenericGeoDataset } from '../data/geoJsonSchemas';

/**
 * GeoMap (O7/#173.2) — proyecta un GeoJSON GENÉRICO a SVG con d3-geo. Este
 * fixture es SINTÉTICO, inventado para esta prueba — nombres de propiedad
 * que NO son los del ICE (`assetCode`/`region`/`linkCode`/`capacity`, nunca
 * `Subestacio`/`Provincia`/`Voltaje`). La genericidad del componente se
 * prueba precisamente con datos que el componente no puede conocer de
 * antemano; un test que solo pasara con campos del ICE no probaría nada de
 * lo que esta migración pide.
 */
const SYNTHETIC_DATASET: GenericGeoDataset = {
  format: 'geojson',
  collection: {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [10, 45] },
        properties: { assetCode: 'north-node', region: 'north', throughput: 12 }
      },
      {
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [12, 44] },
        properties: { assetCode: 'south-node', region: 'south', throughput: 30 }
      },
      {
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: [
            [10, 45],
            [11, 44.5]
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
              [12, 44],
              [13, 43.5]
            ]
          ]
        },
        properties: { linkCode: 'link-b', capacity: 20 }
      }
    ]
  },
  attribution: 'Fuente sintética de prueba'
};

describe('GeoMap — render geoespacial genérico (O7/#173.2)', () => {
  test('renderiza un circle por feature Point y un path por feature de línea, sin importar el dataset', () => {
    const { container } = render(<GeoMap dataset={SYNTHETIC_DATASET} />);

    expect(container.querySelectorAll('svg circle')).toHaveLength(2);
    expect(container.querySelectorAll('svg path')).toHaveLength(2);
  });

  test('usa la propiedad configurada como etiqueta cuando está presente en el feature', () => {
    render(<GeoMap dataset={SYNTHETIC_DATASET} config={{ labelProperty: 'assetCode' }} />);

    expect(screen.getByText(/north-node/)).toBeInTheDocument();
    expect(screen.getByText(/south-node/)).toBeInTheDocument();
  });

  test('sin config, usa el índice del feature — jamás asume una propiedad concreta por default', () => {
    render(<GeoMap dataset={SYNTHETIC_DATASET} />);

    expect(screen.getByText(/Feature 0/)).toBeInTheDocument();
    expect(screen.getByText(/Feature 1/)).toBeInTheDocument();
  });

  test('render honesto: si la propiedad de etiqueta configurada no existe en el feature, cae al índice — nunca "undefined" ni una etiqueta inventada', () => {
    const datasetSinLaPropiedad: GenericGeoDataset = {
      ...SYNTHETIC_DATASET,
      collection: {
        type: 'FeatureCollection',
        features: [SYNTHETIC_DATASET.collection.features[0]!]
      }
    };
    render(
      <GeoMap dataset={datasetSinLaPropiedad} config={{ labelProperty: 'nombreQueNoExiste' }} />
    );

    expect(screen.getByText(/Feature 0/)).toBeInTheDocument();
    expect(screen.queryByText(/undefined/)).not.toBeInTheDocument();
  });

  test('escala el ancho de línea con la propiedad de peso configurada', () => {
    const { container } = render(
      <GeoMap dataset={SYNTHETIC_DATASET} config={{ weightProperty: 'capacity' }} />
    );
    const paths = Array.from(container.querySelectorAll('svg path'));
    const widths = paths.map(path => Number(path.getAttribute('stroke-width')));

    // link-a (capacity 5) es el primer path; link-b (capacity 20) el segundo.
    expect(widths[1]).toBeGreaterThan(widths[0]!);
  });

  test('sin weightProperty configurado, todas las líneas comparten un ancho uniforme', () => {
    const { container } = render(<GeoMap dataset={SYNTHETIC_DATASET} />);
    const paths = Array.from(container.querySelectorAll('svg path'));
    const widths = paths.map(path => Number(path.getAttribute('stroke-width')));

    expect(widths[0]).toBe(widths[1]);
  });

  test('muestra la atribución cuando el dataset la trae', () => {
    render(<GeoMap dataset={SYNTHETIC_DATASET} />);

    expect(screen.getByText('Fuente sintética de prueba')).toBeInTheDocument();
  });

  test('sin atribución, no inventa una', () => {
    const sinAtribucion: GenericGeoDataset = { ...SYNTHETIC_DATASET, attribution: undefined };
    render(<GeoMap dataset={sinAtribucion} />);

    expect(screen.queryByText(/Fuente sintética/)).not.toBeInTheDocument();
  });
});

describe('GeoMap — geojson malformado NUNCA llega acá (la frontera es data/geoJsonSchemas)', () => {
  test('un dataset con 0 features es honesto (sin render a medias) y no explota', () => {
    const vacio: GenericGeoDataset = {
      format: 'geojson',
      collection: { type: 'FeatureCollection', features: [] }
    };
    const { container } = render(<GeoMap dataset={vacio} />);

    expect(container.querySelectorAll('svg circle')).toHaveLength(0);
    expect(container.querySelectorAll('svg path')).toHaveLength(0);
  });
});

describe('GeoMap — overlay de grupo verificado (genérico, jamás "isla"/"subestación")', () => {
  const OVERLAY: GeoOverlay = {
    groups: [
      {
        id: 'group-0',
        label: 'grupo-0',
        matchKeys: ['north-node'],
        verification: {
          verdict: 'pass',
          level: 'AL2',
          verifierClass: 'property_rule',
          method: 'structural-partition-v1',
          summary: 'grupo-0: 2/2 checks pasaron'
        }
      }
    ],
    matchedFeatures: 1,
    sourceDigest: '0078d201ff590345598ab0d7698a724cc642eaec4dca660a4ec66361402485a7'
  };

  test('sin overlay, no colorea ni declara ningún grupo — jamás inventa una agrupación', () => {
    render(<GeoMap dataset={SYNTHETIC_DATASET} config={{ labelProperty: 'assetCode' }} />);

    expect(screen.queryByText('AL2')).not.toBeInTheDocument();
  });

  test('con overlay, muestra un badge por grupo con su clase y su nivel', () => {
    render(
      <GeoMap
        dataset={SYNTHETIC_DATASET}
        config={{ labelProperty: 'assetCode' }}
        overlay={OVERLAY}
      />
    );

    expect(screen.getByText('AL2')).toBeInTheDocument();
    expect(screen.getByText(/structural-partition-v1/)).toBeInTheDocument();
  });

  test('declara cuántos features casaron contra el total — nunca rellena', () => {
    render(
      <GeoMap
        dataset={SYNTHETIC_DATASET}
        config={{ labelProperty: 'assetCode' }}
        overlay={OVERLAY}
      />
    );

    expect(screen.getByText(/1 de 4 features/i)).toBeInTheDocument();
  });

  test('cita el digest de procedencia del overlay', () => {
    render(
      <GeoMap
        dataset={SYNTHETIC_DATASET}
        config={{ labelProperty: 'assetCode' }}
        overlay={OVERLAY}
      />
    );

    expect(screen.getByText('0078d201ff59')).toBeInTheDocument();
  });
});
