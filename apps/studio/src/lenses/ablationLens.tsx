import { useQuery } from '@tanstack/react-query';
import React from 'react';

import { EmptyState, ErrorState, LoadingState } from '@/components/feedback/DataState';

import { ablationQueryOptions, rvspQueryOptions } from '../data/queries';
import AblationPanel from '../views/AblationPanel';
import RvsPChart from '../views/RvsPChart';

import type { DomainLens, LensContext } from './types';

/**
 * Lente de dominio: ablación de optimización combinatoria (P13).
 *
 * Comparar «cuántico vs. clásico» y la curva r-vs-p solo SIGNIFICAN algo en
 * un run de optimización: en un run de, digamos, evolución temporal de un
 * hamiltoniano, una tab «Ablación» sería una promesa vacía. Por eso la lente
 * declara qué capabilities la hacen aplicable en vez de estar siempre.
 *
 * Las queries viven ACÁ y no en el shell (como antes): una lente que necesita
 * datos los pide ella misma — si no, agregar un dominio nuevo obligaría a
 * cablear sus queries en `App.tsx`, que es exactamente el acoplamiento que
 * P13 viene a romper.
 */

const OPTIMIZATION_CAPABILITIES: ReadonlySet<string> = new Set([
  'blite.quantum.qaoa',
  'blite.graphs.maxcut',
  'blite.graphs.partition',
  'blite.solvers.qubo'
]);

export function AblationLensView({ runId }: { readonly runId: string }): React.ReactElement {
  const rvspQuery = useQuery(rvspQueryOptions(runId));
  const ablationQuery = useQuery(ablationQueryOptions(runId));

  // D5 — la curva r-vs-p real de la ciencia es el contenido PRIMARIO
  // (divergencia deliberada de superficie-visual.md §5, supersedida por C-9).
  const rvspSection = rvspQuery.isPending ? (
    <LoadingState label="Cargando la curva r vs p" />
  ) : rvspQuery.isError ? (
    <ErrorState message={rvspQuery.error.message} onRetry={() => void rvspQuery.refetch()} />
  ) : rvspQuery.data === null ? (
    <EmptyState
      title="Sin curva r vs p todavía."
      hint="Esta vista solo existe en modo réplica hoy — el endpoint en vivo llega con un run comparativo real."
    />
  ) : (
    <RvsPChart experiment={rvspQuery.data} />
  );

  const ablationSection = ablationQuery.isPending ? (
    <LoadingState label="Cargando las métricas de ablación" />
  ) : ablationQuery.isError ? (
    <ErrorState
      message={ablationQuery.error.message}
      onRetry={() => void ablationQuery.refetch()}
    />
  ) : ablationQuery.data.length === 0 ? (
    <EmptyState
      title="Sin métricas de ablación todavía."
      hint="Ejecute un run comparativo (cuántico vs. clásico) para poblar esta vista."
    />
  ) : (
    <AblationPanel metrics={ablationQuery.data} />
  );

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-8">
      {rvspSection}
      <div className="flex flex-col gap-4 border-t border-border pt-6">
        <h3 className="text-sm font-medium text-muted-foreground">
          Ablación — cuántico vs. clásico
        </h3>
        {ablationSection}
      </div>
    </div>
  );
}

export const ablationLens: DomainLens = {
  id: 'ablacion',
  label: 'Ablación',
  appliesTo: (context: LensContext) =>
    context.capabilityIds.some(id => OPTIMIZATION_CAPABILITIES.has(id)) ||
    (context.offeredAblationVariants ?? []).length > 0,
  render: (context: LensContext) => <AblationLensView runId={context.runId} />
};
