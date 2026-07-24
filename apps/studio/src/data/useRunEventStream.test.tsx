import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { runEventsQueryOptions } from './queries';
import * as runStream from './runStream';
import { appendEvent, useRunEventStream } from './useRunEventStream';

import type { RunStreamHandlers, RunStreamSubscription } from './runStream';
import type { ProjectedEvent } from '../views/types';
import type { ReactNode } from 'react';

vi.mock('./runStream', () => ({
  subscribeToRunEvents: vi.fn()
}));

const EVENT_1: ProjectedEvent = {
  globalSeq: 1,
  type: 'run.started',
  actorId: 'service:runtime',
  occurredAt: '2026-07-22T12:00:01.000000Z',
  resumen: 'Run iniciado'
};

const EVENT_2: ProjectedEvent = {
  globalSeq: 2,
  type: 'capability.job.invoked',
  actorId: 'service:runtime',
  occurredAt: '2026-07-22T12:00:02.000000Z',
  resumen: 'Invocando el solver'
};

describe('appendEvent (helper puro)', () => {
  it('agrega un evento nuevo a un stream vacío', () => {
    expect(appendEvent([], EVENT_1)).toEqual([EVENT_1]);
  });

  it('descarta un evento duplicado por globalSeq (idempotencia ante reconexión SSE)', () => {
    const duplicate: ProjectedEvent = { ...EVENT_1, resumen: 'resumen distinto, mismo seq' };
    expect(appendEvent([EVENT_1], duplicate)).toEqual([EVENT_1]);
  });

  it('mantiene el orden ascendente por globalSeq aunque lleguen desordenados', () => {
    expect(appendEvent([EVENT_2], EVENT_1)).toEqual([EVENT_1, EVENT_2]);
  });

  it('nunca muta el arreglo recibido (inmutabilidad)', () => {
    const prev = [EVENT_1];
    const result = appendEvent(prev, EVENT_2);
    expect(result).not.toBe(prev);
    expect(prev).toEqual([EVENT_1]);
  });
});

function wrapper(queryClient: QueryClient): ({ children }: { children: ReactNode }) => ReactNode {
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('useRunEventStream', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.mocked(runStream.subscribeToRunEvents).mockReset();
  });

  it('no-op en modo fixtures/demo (VITE_API_URL ausente) — no se suscribe', () => {
    vi.stubEnv('VITE_API_URL', undefined);
    const queryClient = new QueryClient();

    renderHook(() => useRunEventStream('8f2c1a9b'), { wrapper: wrapper(queryClient) });

    expect(runStream.subscribeToRunEvents).not.toHaveBeenCalled();
  });

  it('en modo live suscribe y alimenta el cache de runEventsQueryOptions en orden', () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const close = vi.fn();
    vi.mocked(runStream.subscribeToRunEvents).mockImplementation(
      (_runId: string, _options: unknown, handlers: RunStreamHandlers): RunStreamSubscription => {
        handlers.onEvent(EVENT_2);
        handlers.onEvent(EVENT_1);
        return { close };
      }
    );

    const queryClient = new QueryClient();
    const { unmount } = renderHook(() => useRunEventStream('8f2c1a9b'), {
      wrapper: wrapper(queryClient)
    });

    expect(runStream.subscribeToRunEvents).toHaveBeenCalledWith(
      '8f2c1a9b',
      {},
      expect.objectContaining({ onEvent: expect.any(Function) })
    );

    const cached = queryClient.getQueryData(runEventsQueryOptions('8f2c1a9b').queryKey);
    expect(cached).toEqual([EVENT_1, EVENT_2]);

    unmount();
    expect(close).toHaveBeenCalledTimes(1);
  });
});
