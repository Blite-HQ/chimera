import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { getCertificate, invokeCapability, openRunEventStream, postRun } from './gatewayClient';

import type { CreateRunBody } from './gatewayClient';
import type { ProjectedEvent } from './views/types';

describe('gatewayClient', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('sends POST to /invoke with the correct payload', async () => {
    // Arrange
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, data: { result: 42 }, error: null })
    } as Response);

    // Act
    const result = await invokeCapability({
      capability: 'blite.solvers.qubo',
      inputs: {
        matrix: [
          [0, 1],
          [1, 0]
        ]
      }
    });

    // Assert
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/invoke'),
      expect.objectContaining({ method: 'POST' })
    );
    expect(result.success).toBe(true);
    expect(result.data).toEqual({ result: 42 });
  });

  it('returns error response when gateway returns non-OK status', async () => {
    // Arrange
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 503,
      statusText: 'Service Unavailable'
    } as Response);

    // Act
    const result = await invokeCapability({ capability: 'blite.solvers.qubo', inputs: {} });

    // Assert
    expect(result.success).toBe(false);
    expect(result.error).toContain('503');
    expect(result.data).toBeNull();
  });

  it('returns error response when network request fails', async () => {
    // Arrange
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('ERR_NETWORK'));

    // Act
    const result = await invokeCapability({ capability: 'blite.solvers.qubo', inputs: {} });

    // Assert
    expect(result.success).toBe(false);
    expect(result.error).toContain('ERR_NETWORK');
  });
});

describe('postRun', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  const BODY: CreateRunBody = {
    capability_id: 'blite.solvers.qaoa',
    inputs: { instance: 'ieee14' },
    claim: {
      canonical_statement: 'Partición controlada óptima de ieee14',
      scope: { instance: 'ieee14' },
      claim_type: 'optimality'
    }
  };

  it('envía POST a {VITE_API_URL}/runs con el body del contrato y devuelve run_id', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, data: { run_id: 'run-123' }, error: null })
    } as Response);

    // Act
    const result = await postRun(BODY);

    // Assert
    expect(mockFetch).toHaveBeenCalledWith('http://api.test/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(BODY)
    });
    expect(result.success).toBe(true);
    expect(result.data).toEqual({ run_id: 'run-123' });
  });

  it('devuelve error cuando la respuesta no es OK', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 503,
      statusText: 'Service Unavailable'
    } as Response);

    // Act
    const result = await postRun(BODY);

    // Assert
    expect(result.success).toBe(false);
    expect(result.error).toContain('503');
    expect(result.data).toBeNull();
  });

  it('devuelve error cuando la petición de red falla', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('ERR_NETWORK'));

    // Act
    const result = await postRun(BODY);

    // Assert
    expect(result.success).toBe(false);
    expect(result.error).toContain('ERR_NETWORK');
  });
});

describe('getCertificate', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('envía GET a {VITE_API_URL}/runs/{id}/certificate y devuelve el wire crudo como data', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const wire = {
      payloadType: 'application/vnd.blite.trust-certificate+json',
      payload: 'e30=',
      signatures: [{ keyid: 'certificate:v1-example', sig: 'abc' }]
    };
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => wire
    } as Response);

    // Act
    const result = await getCertificate('8f2c1a9b');

    // Assert
    expect(mockFetch).toHaveBeenCalledWith('http://api.test/runs/8f2c1a9b/certificate');
    expect(result).toEqual({ success: true, data: wire, error: null });
  });

  it('encodea el runId en la url', async () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({})
    } as Response);

    await getCertificate('run/with slash');

    expect(mockFetch).toHaveBeenCalledWith('http://api.test/runs/run%2Fwith%20slash/certificate');
  });

  it('devuelve error cuando la respuesta no es OK', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found'
    } as Response);

    // Act
    const result = await getCertificate('8f2c1a9b');

    // Assert
    expect(result.success).toBe(false);
    expect(result.error).toContain('404');
    expect(result.data).toBeNull();
  });

  it('devuelve error cuando la petición de red falla', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('ERR_NETWORK'));

    // Act
    const result = await getCertificate('8f2c1a9b');

    // Assert
    expect(result.success).toBe(false);
    expect(result.error).toContain('ERR_NETWORK');
    expect(result.data).toBeNull();
  });
});

/** Fake EventSource — captura los listeners registrados por tipo + close(). */
class FakeEventSource {
  static instances: FakeEventSource[] = [];
  readonly url: string;
  readonly listenersByType = new Map<string, ((event: MessageEvent<string>) => void)[]>();
  onerror: (() => void) | null = null;
  closed = false;

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: (event: MessageEvent<string>) => void): void {
    const existing = this.listenersByType.get(type) ?? [];
    this.listenersByType.set(type, [...existing, listener]);
  }

  close(): void {
    this.closed = true;
  }

  dispatch(type: string, data: string): void {
    const listeners = this.listenersByType.get(type) ?? [];
    for (const listener of listeners) {
      listener({ data } as unknown as MessageEvent<string>);
    }
  }
}

describe('openRunEventStream', () => {
  beforeEach(() => {
    FakeEventSource.instances = [];
    vi.stubGlobal('EventSource', FakeEventSource);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it('abre el EventSource contra {VITE_API_URL}/runs/{id}/events y mapea un frame nombrado', () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const events: ProjectedEvent[] = [];

    // Act
    const subscription = openRunEventStream('8f2c1a9b', { onEvent: e => events.push(e) });
    const source = FakeEventSource.instances[0];

    // Assert
    expect(source?.url).toBe('http://api.test/runs/8f2c1a9b/events');

    source?.dispatch(
      'verification.completed',
      JSON.stringify({
        global_seq: 4,
        type: 'verification.completed',
        actor_id: 'service:verifier',
        occurred_at: '2026-07-22T12:00:04.000000Z',
        resumen: 'Verificación formal exacta (AL3)',
        // Wire real del orquestador: el verdict vive en payload.verdict
        // (top level), no en payload.verification.verdict.
        payload: { verdict: 'pass' }
      })
    );

    expect(events).toHaveLength(1);
    expect(events[0]).toEqual({
      globalSeq: 4,
      type: 'verification.completed',
      actorId: 'service:verifier',
      occurredAt: '2026-07-22T12:00:04.000000Z',
      resumen: 'Verificación formal exacta (AL3)',
      verdict: 'pass'
    });

    subscription.close();
    expect(source?.closed).toBe(true);
  });

  it('encodea el runId en la url', () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');

    openRunEventStream('run/with slash', { onEvent: () => {} });

    expect(FakeEventSource.instances[0]?.url).toBe(
      'http://api.test/runs/run%2Fwith%20slash/events'
    );
  });

  it('llama a onError (nunca lanza) cuando un frame no parsea', () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const onError = vi.fn();

    openRunEventStream('8f2c1a9b', { onEvent: () => {}, onError });
    const source = FakeEventSource.instances[0];

    expect(() => source?.dispatch('run.started', 'not-json')).not.toThrow();
    expect(onError).toHaveBeenCalledTimes(1);
  });

  it('llama a onError cuando el EventSource subyacente reporta un error', () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const onError = vi.fn();

    openRunEventStream('8f2c1a9b', { onEvent: () => {}, onError });
    const source = FakeEventSource.instances[0];
    source?.onerror?.();

    expect(onError).toHaveBeenCalledWith('SSE connection error');
  });

  it('no construye un EventSource cuando VITE_API_URL no está configurada', () => {
    vi.stubEnv('VITE_API_URL', undefined);
    const onError = vi.fn();

    const subscription = openRunEventStream('8f2c1a9b', { onEvent: () => {}, onError });

    expect(FakeEventSource.instances).toHaveLength(0);
    expect(onError).toHaveBeenCalledTimes(1);
    expect(() => subscription.close()).not.toThrow();
  });
});
