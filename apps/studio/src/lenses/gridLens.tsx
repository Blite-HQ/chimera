import { useQuery } from '@tanstack/react-query';
import { Map, Network } from 'lucide-react';
import React, { useMemo, useState } from 'react';

import { EmptyState, ErrorState } from '@/components/feedback/DataState';
import { ToggleButton } from '@/components/layout/ToggleButton';

import { isLiveMode } from '../data/env';
import { ICE_GRID_DATASET } from '../data/iceGrid';
import { topologyQueryOptions } from '../data/queries';
import GridSpike from '../spike/GridSpike';
import DataFormatRouter from '../views/DataFormatRouter';
import { toGridPartitionOverlay } from './gridPartition';

import type { DomainLens, LensContext } from './types';

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
 * «Mapa» (la red nacional REAL del ICE). Son dos redes distintas: el mapa
 * nunca sustituye al diagrama, lo complementa.
 *
 * **[V1/M18] En vivo el honest-empty se acabó DONDE hay productor.** Antes
 * esta lente anunciaba «pendiente» siempre, con causa (decisión #88: no
 * existía productor de partición sobre esta red). Ahora consulta
 * `GET /runs/{id}/topology` y, si el run produjo una partición verificada POR
 * ISLA sobre ESTA instancia, la pinta con sus badges. Si no la produjo, sigue
 * diciéndolo — y dice cuál de las dos cosas pasó, que no son la misma.
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

const SUBSTATION_NAMES: readonly string[] = ICE_GRID_DATASET.substations.features.map(
  feature => feature.properties.Subestacio
);

export function GridLensView({ runId }: { readonly runId: string }): React.ReactElement {
  const [viewMode, setViewMode] = useState<RedViewMode>('diagrama');
  const live = isLiveMode();
  const topology = useQuery({ ...topologyQueryOptions(runId), enabled: live });

  const overlay = useMemo(
    () => toGridPartitionOverlay(topology.data, SUBSTATION_NAMES),
    [topology.data]
  );

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
    return <DataFormatRouter dataset={ICE_GRID_DATASET} partition={overlay} />;
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
      {viewMode === 'diagrama' ? <GridSpike /> : <DataFormatRouter dataset={ICE_GRID_DATASET} />}
    </div>
  );
}

export const gridLens: DomainLens = {
  id: 'red',
  label: 'Red',
  appliesTo: (context: LensContext) =>
    context.claimTypes.some(type => type.startsWith(GRID_CLAIM_PREFIX)) ||
    context.capabilityIds.some(id => GRID_CAPABILITIES.has(id)),
  render: (context: LensContext) => <GridLensView runId={context.runId} />
};
