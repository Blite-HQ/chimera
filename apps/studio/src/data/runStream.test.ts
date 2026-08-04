import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { RUN_EVENTS } from '../fixtures/runEvents';
import * as gatewayClient from '../gatewayClient';
import { subscribeToRunEvents, type RunStreamStatus } from './runStream';

import type { RunEventStreamHandlers, RunEventStreamSubscription } from '../gatewayClient';
import type { ProjectedEvent } from '../views/types';

vi.mock('../gatewayClient', () => ({
  openRunEventStream: vi.fn()
}));

describe('subscribeToRunEvents (seam de S10)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('emite los eventos en orden y cierra con status complete', () => {
    const events: ProjectedEvent[] = [];
    const statuses: RunStreamStatus[] = [];
    subscribeToRunEvents(
      '8f2c1a9b',
      {},
      { onEvent: e => events.push(e), onStatus: s => statuses.push(s) }
    );

    vi.advanceTimersByTime(RUN_EVENTS.length * 400 + 400);

    expect(events.map(e => e.globalSeq)).toEqual(RUN_EVENTS.map(e => e.globalSeq));
    expect(statuses).toEqual(['demo', 'complete']);
  });

  it('reanuda desde lastEventId — el contrato de catch-up del freeze §9', () => {
    const events: ProjectedEvent[] = [];
    const cursor = RUN_EVENTS[2]!.globalSeq;
    subscribeToRunEvents('8f2c1a9b', { lastEventId: cursor }, { onEvent: e => events.push(e) });

    vi.advanceTimersByTime(RUN_EVENTS.length * 400 + 400);

    expect(events.length).toBe(RUN_EVENTS.filter(e => e.globalSeq > cursor).length);
    expect(events.every(e => e.globalSeq > cursor)).toBe(true);
  });

  it('close() detiene la emisión (desconexión limpia)', () => {
    const events: ProjectedEvent[] = [];
    const subscription = subscribeToRunEvents('8f2c1a9b', {}, { onEvent: e => events.push(e) });

    vi.advanceTimersByTime(400 * 2);
    subscription.close();
    const seen = events.length;
    vi.advanceTimersByTime(400 * 5);

    expect(events.length).toBe(seen);
  });
});

describe('subscribeToRunEvents — modo live', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.mocked(gatewayClient.openRunEventStream).mockReset();
  });

  it('delega en gatewayClient.openRunEventStream, reenvía eventos y emite status live', () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const close = vi.fn();
    let capturedHandlers: RunEventStreamHandlers | undefined;
    vi.mocked(gatewayClient.openRunEventStream).mockImplementation(
      (_runId: string, handlers: RunEventStreamHandlers): RunEventStreamSubscription => {
        capturedHandlers = handlers;
        return { close };
      }
    );

    const events: ProjectedEvent[] = [];
    const statuses: RunStreamStatus[] = [];

    // Act
    const subscription = subscribeToRunEvents(
      '8f2c1a9b',
      {},
      { onEvent: e => events.push(e), onStatus: s => statuses.push(s) }
    );

    // Assert
    expect(gatewayClient.openRunEventStream).toHaveBeenCalledWith(
      '8f2c1a9b',
      expect.objectContaining({ onEvent: expect.any(Function) })
    );
    expect(statuses).toEqual(['live']);

    const fakeEvent = RUN_EVENTS[0]!;
    capturedHandlers?.onEvent(fakeEvent);
    expect(events).toEqual([fakeEvent]);

    subscription.close();
    expect(close).toHaveBeenCalledTimes(1);
  });
});
