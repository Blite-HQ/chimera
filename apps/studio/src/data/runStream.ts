/**
 * Seam de stream para S10 (F3, ficha punto 3) — interfaz EventSource-compatible.
 *
 * FIXTURES (VITE_API_URL ausente): emite los eventos del run demo con
 * cadencia, status 'demo' → 'complete' — comportamiento sin cambios. LIVE
 * (VITE_API_URL presente, MVP task 1): delega en
 * `gatewayClient.openRunEventStream` (el único lugar que construye un
 * EventSource real, INV-1) y alimenta el cache vía
 * `queryClient.setQueryData(runEventsQueryOptions(runId).queryKey, ...)`
 * desde `useRunEventStream.ts`. ESTA interfaz no cambió con el swap; el SSE
 * no se fuerza dentro de Query. El contrato de props de nota 18
 * (events/selectedGlobalSeq/onSelectEvent/viewMode) tampoco cambia — solo
 * existe `status` además.
 */

import { RUN_EVENTS } from '../fixtures/runEvents';
import { openRunEventStream } from '../gatewayClient';
import { isLiveMode } from './env';

import type { ProjectedEvent } from '../views/types';

export type RunStreamStatus = 'demo' | 'live' | 'complete';

export interface RunStreamOptions {
  /** Cursor de reanudación (= global_seq, freeze §9); omitido = desde el inicio. */
  readonly lastEventId?: number;
}

export interface RunStreamHandlers {
  readonly onEvent: (event: ProjectedEvent) => void;
  readonly onStatus?: (status: RunStreamStatus) => void;
}

export interface RunStreamSubscription {
  readonly close: () => void;
}

const DEMO_INTERVAL_MS = 400;

export function subscribeToRunEvents(
  runId: string,
  options: RunStreamOptions,
  handlers: RunStreamHandlers
): RunStreamSubscription {
  if (isLiveMode()) {
    handlers.onStatus?.('live');
    const subscription = openRunEventStream(runId, { onEvent: handlers.onEvent });
    return { close: () => subscription.close() };
  }

  const cursor = options.lastEventId ?? 0;
  // Fixture del run demo: un solo stream conocido; el filtro por cursor es
  // el MISMO contrato de reanudación que el SSE real (catch-up, cero
  // eventos perdidos).
  const pending = RUN_EVENTS.filter(event => event.globalSeq > cursor);
  handlers.onStatus?.('demo');

  let index = 0;
  const timer = setInterval(() => {
    if (index >= pending.length) {
      clearInterval(timer);
      handlers.onStatus?.('complete');
      return;
    }
    const event = pending[index];
    index += 1;
    if (event !== undefined) {
      handlers.onEvent(event);
    }
  }, DEMO_INTERVAL_MS);

  return {
    close: () => {
      clearInterval(timer);
    }
  };
}
