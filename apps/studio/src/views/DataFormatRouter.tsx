/**
 * DataFormatRouter (D4) — inspecciona `dataset.format` y despacha al
 * visualizador correspondiente. Hoy solo `geojson` tiene un renderer
 * (GeoMap, GENÉRICO — O7/#173.2); cualquier otro formato cae a un fallback
 * etiquetado con el nombre del formato — nunca una pantalla en blanco ni un
 * visualizador genérico que finja soportarlo.
 *
 * Extensible por diseño: agregar un formato nuevo es agregar un type guard
 * + una rama acá (el patrón "dispatch table por discriminante" pedido en
 * D4) — este componente no cambia de forma cuando crece el vocabulario de
 * formatos.
 */

import React from 'react';

import { EmptyState } from '@/components/feedback/DataState';

import GeoMap, { type GeoOverlay } from './GeoMap';

import type { GenericGeoDataset } from '../data/geoJsonSchemas';

/** Contrato mínimo de cualquier dataset ruteable: el discriminante `format`. */
export interface FormatDataset {
  readonly format: string;
}

export interface DataFormatRouterProps {
  readonly dataset: FormatDataset;
  /** Reenviado tal cual al renderer geojson (ver GeoMap — seam B2/R5). */
  readonly overlay?: GeoOverlay;
}

function isGeoJsonDataset(dataset: FormatDataset): dataset is GenericGeoDataset {
  return dataset.format === 'geojson' && 'collection' in dataset;
}

export default function DataFormatRouter({
  dataset,
  overlay
}: DataFormatRouterProps): React.ReactElement {
  if (isGeoJsonDataset(dataset)) {
    return <GeoMap dataset={dataset} overlay={overlay} />;
  }

  return (
    <EmptyState
      title={`Formato «${dataset.format}» sin visualizador todavía.`}
      hint="El router de formatos no tiene un renderer registrado para este dataset."
    />
  );
}
