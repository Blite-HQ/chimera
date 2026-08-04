import { Map, Network } from 'lucide-react';
import React, { useState } from 'react';

import { EmptyState } from '@/components/feedback/DataState';
import { ToggleButton } from '@/components/layout/ToggleButton';

import { isLiveMode } from '../data/env';
import { ICE_GRID_DATASET } from '../data/iceGrid';
import GridSpike from '../spike/GridSpike';
import DataFormatRouter from '../views/DataFormatRouter';

import type { DomainLens, LensContext } from './types';

/**
 * Lente de dominio: red eléctrica (P13).
 *
 * Antes esto vivía en `App.tsx` como `RedSlot`, montado incondicionalmente y
 * pasado a `RunDetail` como prop obligatoria — el shell sabía de redes
 * eléctricas. Ahora es una lente registrada: el shell no la nombra, y un run
 * de otro dominio sencillamente no la ve.
 *
 * El contenido no cambió (D1 task 4 / D4 task 6, `superficie-visual.md` §4.3
 * «dual diagrama + mapa, no reemplazo»): en réplica ofrece las DOS vistas —
 * «Diagrama» (`GridSpike`, la partición benchmark IEEE-14, data estática) y
 * «Mapa» (la red nacional REAL del ICE, 70 subestaciones + 102 líneas). Son
 * dos redes distintas: el mapa nunca sustituye al diagrama, lo complementa
 * (no existe todavía un mapeo determinista entre la instancia benchmark y el
 * grid real). En vivo sigue faltando el productor de partición sobre esa red
 * (decisión #88), así que anuncia «pendiente» en vez de mostrar cualquiera.
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

export function GridLensView(): React.ReactElement {
  const [viewMode, setViewMode] = useState<RedViewMode>('diagrama');

  if (isLiveMode()) {
    return (
      <EmptyState
        title="Topología en vivo — pendiente"
        hint="El mapa ICE-70 real y las rutas de lectura ya existen — falta el productor real de partición sobre esa red (decisión #88), sin fecha prometida."
      />
    );
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
  render: () => <GridLensView />
};
