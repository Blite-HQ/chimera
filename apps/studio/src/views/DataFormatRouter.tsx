/**
 * DataFormatRouter (D4) — inspecciona `dataset.format` y despacha al
 * visualizador correspondiente. Hoy solo `geojson` tiene un renderer
 * (GridMap); cualquier otro formato cae a un fallback etiquetado con el
 * nombre del formato — nunca una pantalla en blanco ni un visualizador
 * genérico que finja soportarlo.
 *
 * Extensible por diseño: agregar un formato nuevo es agregar un type guard
 * + una rama acá (el patrón "dispatch table por discriminante" pedido en
 * D4) — este componente no cambia de forma cuando crece el vocabulario de
 * formatos.
 */

import React from 'react';

import { EmptyState } from '@/components/feedback/DataState';

import GridMap, { type GridPartitionOverlay } from './GridMap';

import type { GeoJsonGridDataset } from '../data/iceGridSchemas';

/** Contrato mínimo de cualquier dataset ruteable: el discriminante `format`. */
export interface FormatDataset {
  readonly format: string;
}

export interface DataFormatRouterProps {
  readonly dataset: FormatDataset;
  /** Reenviado tal cual al renderer geojson (ver GridMap — seam B2/R5). */
  readonly partition?: GridPartitionOverlay;
}

function isGeoJsonDataset(dataset: FormatDataset): dataset is GeoJsonGridDataset {
  return (
    dataset.format === 'geojson' &&
    'substations' in dataset &&
    'lines' in dataset &&
    'attribution' in dataset
  );
}

export default function DataFormatRouter({
  dataset,
  partition
}: DataFormatRouterProps): React.ReactElement {
  if (isGeoJsonDataset(dataset)) {
    return <GridMap dataset={dataset} partition={partition} />;
  }

  return (
    <EmptyState
      title={`Formato «${dataset.format}» sin visualizador todavía.`}
      hint="El router de formatos no tiene un renderer registrado para este dataset."
    />
  );
}
