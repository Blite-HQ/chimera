import { useQuery } from '@tanstack/react-query';
import { Map, Network } from 'lucide-react';
import React, { useMemo, useState } from 'react';

import { EmptyState, ErrorState, LoadingState } from '@/components/feedback/DataState';
import { ToggleButton } from '@/components/layout/ToggleButton';

import { isLiveMode } from '../data/env';
import { isGeospatialMediaType } from '../data/geoJsonSchemas';
import { ICE_DERIVED_INSTANCE } from '../data/iceInstance';
import {
  filesQueryOptions,
  geospatialDatasetQueryOptions,
  topologyQueryOptions
} from '../data/queries';
import GridSpike from '../spike/GridSpike';
import DataFormatRouter from '../views/DataFormatRouter';
import { toGridPartitionOverlay } from './gridPartition';

import type { GeoOverlay } from '../views/GeoMap';
import type { DomainLens, LensContext } from './types';
import type { GridPartitionOverlay } from './gridPartition';

/**
 * Lente de dominio: red eléctrica (P13).
 *
 * Antes esto vivía en `App.tsx` como `RedSlot`, montado incondicionalmente y
 * pasado a `RunDetail` como prop obligatoria — el shell sabía de redes
 * eléctricas. Ahora es una lente registrada: el shell no la nombra, y un run
 * de otro dominio sencillamente no la ve.
 *
 * En réplica ofrece las DOS vistas (D1 task 4 / D4 task 6,
 * `superficie-visual.md` §4.3 «dual diagrama + mapa, no reemplazo»):
 * «Diagrama» (`GridSpike`, la partición benchmark IEEE-14, data estática) y
 * «Mapa» (el render geoespacial GENÉRICO — ver abajo).
 *
 * **O7/#173.2 (directiva de Dylan 2026-08-11).** El mapa dejó de ser un
 * GeoJSON del ICE bundleado en el código de la app: `apps/studio/src/
 * fixtures/ice/{subestaciones,lineas}.geojson` se borraron, junto con los
 * schemas Zod que clavaban sus nombres de campo (`Subestacio`, `Provincia`,
 * `Voltaje`). El renderer (`views/GeoMap.tsx`) es hoy 100% genérico — no sabe
 * qué es una subestación — y el dato geoespacial sale del content store del
 * proyecto (`GET /files`, `data/queries.ts::geospatialDatasetQueryOptions`),
 * exactamente la fuente que Dylan describió: "si la data está en una DB, un
 * knowledge base para testear, o como entrada que un usuario haga, ahí está
 * bien". La lente sigue siendo domain-specific (sabe de capabilities de red,
 * de islas, de `ICE_DERIVED_INSTANCE`) — eso es legítimo, es UNA lente
 * registrada, no el shell; lo que cambió es que el COMPONENTE de render y el
 * DATO que consume ya no están clavados en el código de la plataforma.
 *
 * `appliesTo` gana una tercera vía de reconocimiento: el proyecto OFRECE un
 * dato geoespacial (`LensContext.offeredMediaTypes`), sin importar la
 * capability. Las dos vías previas (capability de red / claim de partición)
 * se CONSERVAN — matan el toggle "Diagrama" (el spike IEEE-14 no tiene nada
 * que ver con archivos geoespaciales) si se reemplazaran por la nueva sola.
 */

type RedViewMode = 'diagrama' | 'mapa';

/**
 * Las capabilities que hacen que este run SEA de este dominio. Es una lista
 * de datos dentro de la lente — la única parte del Studio que puede nombrar
 * capabilities de redes eléctricas, y por eso vive acá y no en el shell.
 */
const GRID_CAPABILITIES: ReadonlySet<string> = new Set([
  'blite.graphs.partition',
  'blite.graphs.maxcut',
  'blite.sim.power_flow',
  'blite.ingesta.geojson.to_graph'
]);

const GRID_CLAIM_PREFIX = 'partition.';

/**
 * Adapta la forma domain-specific de la partición (`GridPartitionOverlay`,
 * `substationNames`/`islands`/`instanceDigest`) a la forma GENÉRICA que
 * `GeoMap` entiende (`GeoOverlay`, `matchKeys`/`groups`/`sourceDigest`). Esta
 * es la única pieza del Studio que sabe traducir entre ambas — ni
 * `gridPartition.ts` (que sigue devolviendo la forma domain-specific, sus
 * tests no cambian) ni `GeoMap.tsx` (que jamás debe conocer "isla" ni
 * "subestación") se tocan para esto.
 */
function toGeoOverlay(overlay: GridPartitionOverlay): GeoOverlay {
  return {
    groups: overlay.islands.map(island => ({
      id: island.id,
      label: island.label,
      matchKeys: island.substationNames,
      verification: island.verification
    })),
    matchedFeatures: overlay.matchedSubstations,
    sourceDigest: overlay.instanceDigest
  };
}

export function GridLensView({ runId }: { readonly runId: string }): React.ReactElement {
  const [viewMode, setViewMode] = useState<RedViewMode>('diagrama');
  const live = isLiveMode();
  const topology = useQuery({ ...topologyQueryOptions(runId), enabled: live });

  const overlay = useMemo(
    () => toGridPartitionOverlay(topology.data, Object.values(ICE_DERIVED_INSTANCE.nodos)),
    [topology.data]
  );

  // O7/#173.2 — la fuente del dato geoespacial es el content store genérico
  // del proyecto, jamás un fixture bundleado. Solo se piden bytes cuando hay
  // algo verificado que pintar (`overlay !== null`): sin partición no hace
  // falta el archivo, y pedirlo antes de tiempo desperdiciaría el fetch.
  const filesQuery = useQuery({ ...filesQueryOptions(), enabled: live && overlay !== null });
  const geoFile = filesQuery.data?.find(file => isGeospatialMediaType(file.media_type));
  const geoDatasetQuery = useQuery({
    ...geospatialDatasetQueryOptions(geoFile?.digest ?? '', geoFile?.filename),
    enabled: live && overlay !== null && geoFile !== undefined
  });

  if (live) {
    if (topology.isError) {
      return (
        <ErrorState
          message={
            topology.error instanceof Error
              ? topology.error.message
              : 'No se pudo leer la topología de este run.'
          }
          onRetry={() => void topology.refetch()}
        />
      );
    }
    if (overlay === null) {
      return (
        <EmptyState
          title="Este run no produjo una partición verificada por isla."
          hint="El mapa se pinta desde `verification.completed`: hace falta una corrida sobre esta instancia cuyo verificador emita constancia POR ISLA. Sin eso no se colorea nada — un color por isla sin veredicto sería un badge inventado."
        />
      );
    }
    if (filesQuery.isError) {
      return (
        <ErrorState
          message={
            filesQuery.error instanceof Error
              ? filesQuery.error.message
              : 'No se pudieron obtener los archivos del proyecto.'
          }
          onRetry={() => void filesQuery.refetch()}
        />
      );
    }
    if (geoFile === undefined) {
      return (
        <EmptyState
          title="Hay una partición verificada, pero el proyecto no tiene un archivo geoespacial para pintarla."
          hint="El mapa es un artifact genérico (O7): sube un GeoJSON al proyecto (`POST /files`) — el componente funciona con cualquier dataset, no solo con el del ICE."
        />
      );
    }
    if (geoDatasetQuery.isPending) {
      return <LoadingState label="Cargando el archivo geoespacial del proyecto" />;
    }
    if (geoDatasetQuery.isError) {
      return (
        <ErrorState
          message={
            geoDatasetQuery.error instanceof Error
              ? geoDatasetQuery.error.message
              : 'No se pudo leer el archivo geoespacial.'
          }
          onRetry={() => void geoDatasetQuery.refetch()}
        />
      );
    }
    return <DataFormatRouter dataset={geoDatasetQuery.data} overlay={toGeoOverlay(overlay)} />;
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end gap-1">
        <ToggleButton
          label="Diagrama"
          icon={<Network data-icon="inline-start" />}
          isActive={viewMode === 'diagrama'}
          onClick={() => setViewMode('diagrama')}
        />
        <ToggleButton
          label="Mapa"
          icon={<Map data-icon="inline-start" />}
          isActive={viewMode === 'mapa'}
          onClick={() => setViewMode('mapa')}
        />
      </div>
      {viewMode === 'diagrama' ? (
        <GridSpike />
      ) : (
        // O7/#173.2 — antes acá vivía el GeoJSON del ICE bundleado
        // (`ICE_GRID_DATASET`). Se borró: en modo réplica no hay servidor al
        // que preguntarle por archivos del proyecto, así que no hay un
        // dataset legítimo que mostrar. Fabricar uno "solo para que se vea
        // algo" sería exactamente el mock silencioso que la regla 1 prohíbe.
        <EmptyState
          title="Sin archivo geoespacial en modo réplica."
          hint="El mapa se sirve desde los archivos del proyecto (`GET /files`) — en modo réplica no hay servidor al que preguntarle, así que no se fabrica un dataset de reemplazo."
        />
      )}
    </div>
  );
}

export const gridLens: DomainLens = {
  id: 'red',
  label: 'Red',
  appliesTo: (context: LensContext) =>
    context.claimTypes.some(type => type.startsWith(GRID_CLAIM_PREFIX)) ||
    context.capabilityIds.some(id => GRID_CAPABILITIES.has(id)) ||
    (context.offeredMediaTypes ?? []).some(isGeospatialMediaType),
  render: (context: LensContext) => <GridLensView runId={context.runId} />
};
