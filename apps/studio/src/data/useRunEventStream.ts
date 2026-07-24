/**
 * MVP task 1 (S10) — alimenta el cache de Query con el stream en vivo.
 *
 * Modo live únicamente (`isLiveMode()`): se suscribe a
 * `subscribeToRunEvents` (runStream.ts, que a su vez delega en
 * `gatewayClient.openRunEventStream`) y por cada evento que llega hace un
 * append inmutable, deduplicado por `globalSeq` y ordenado, directo al
 * cache bajo `runEventsQueryOptions(runId).queryKey` — las vistas jamás se
 * enteran de que el dato vino de un SSE en vez de un fetch (F3). En modo
 * fixtures/demo este hook es un no-op: `usePlaybackReveal` sigue siendo la
 * única fuente de progresión del timeline.
 */

import { useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';

import { isLiveMode } from './env';
import { runEventsQueryOptions } from './queries';
import { subscribeToRunEvents } from './runStream';

import type { ProjectedEvent } from '../views/types';

/**
 * Append puro: ignora duplicados por globalSeq (reconexión) y mantiene el
 * orden. Devuelve SIEMPRE un arreglo nuevo (nunca muta `events`) — incluso
 * en el caso duplicado, para que el tipo de retorno case exacto con el
 * TData mutable que espera `queryClient.setQueryData`.
 */
export function appendEvent(
  events: readonly ProjectedEvent[],
  event: ProjectedEvent
): ProjectedEvent[] {
  const alreadySeen = events.some(existing => existing.globalSeq === event.globalSeq);
  if (alreadySeen) {
    return [...events];
  }
  return [...events, event].sort((a, b) => a.globalSeq - b.globalSeq);
}

export function useRunEventStream(runId: string): void {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!isLiveMode()) {
      return undefined;
    }

    const queryKey = runEventsQueryOptions(runId).queryKey;
    if (queryClient.getQueryData(queryKey) === undefined) {
      queryClient.setQueryData(queryKey, []);
    }

    const subscription = subscribeToRunEvents(
      runId,
      {},
      {
        onEvent: event => {
          queryClient.setQueryData(queryKey, (prev: readonly ProjectedEvent[] = []) =>
            appendEvent(prev, event)
          );
        }
      }
    );

    return () => subscription.close();
  }, [runId, queryClient]);
}
