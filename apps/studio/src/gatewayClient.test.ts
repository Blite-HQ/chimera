import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  getAblation,
  getArtifacts,
  getCertificate,
  getKnowledge,
  getRuns,
  getStepEvidence,
  openRunEventStream,
  postApprovalResponse,
  postRun,
  postRunCancel,
  postRunMessage
} from './gatewayClient';

import type { CreateRunBody } from './gatewayClient';
import type { ProjectedEvent } from './views/types';

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
    // El server responde el wire CRUDO `{run_id}` (CreateRunResponse, sin
    // envelope) — verificado en vivo contra compose el 2026-08-04.
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 202,
      json: async () => ({ run_id: 'run-123' })
    } as Response);

    // Act
    const result = await postRun(BODY);

    // Assert
    expect(mockFetch).toHaveBeenCalledWith('http://api.test/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(BODY),
      credentials: 'include'
    });
    expect(result.success).toBe(true);
    expect(result.data).toEqual({ run_id: 'run-123' });
  });

  /**
   * Defecto cazado EN VIVO contra compose (2026-08-04): `POST /runs` responde
   * el wire CRUDO `{run_id}` — nunca un envelope. Este cliente lo casteaba a
   * `GatewayResponse`, así que `success` salía `undefined` y `createRun`
   * lanzaba «No se pudo crear el run» AUNQUE el run se hubiera creado bien.
   * Los tests no lo veían porque el mock devolvía un envelope: el doble
   * codificaba un contrato que el servidor no cumple. El envelope lo arma
   * ESTE cliente, igual que en todos los GET.
   */
  it('arma el envelope desde el wire crudo del server (que responde {run_id} pelado)', async () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 202,
      json: async () => ({ run_id: 'run-vivo' })
    } as Response);

    const result = await postRun({ mission: 'particione ieee14' });

    expect(result.success).toBe(true);
    expect(result.data).toEqual({ run_id: 'run-vivo' });
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
    expect(mockFetch).toHaveBeenCalledWith('http://api.test/runs/8f2c1a9b/certificate', {
      credentials: 'include'
    });
    expect(result).toEqual({ success: true, data: wire, error: null });
  });

  it('encodea el runId en la url', async () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({})
    } as Response);

    await getCertificate('run/with slash');

    expect(mockFetch).toHaveBeenCalledWith('http://api.test/runs/run%2Fwith%20slash/certificate', {
      credentials: 'include'
    });
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

/**
 * D3 — las 5 rutas de lectura de E1 (`docs/specs/endpoints-studio.md`),
 * mismo patrón AAA y mismo envelope que getCertificate arriba (el body de
 * la respuesta ES el wire crudo, el envelope de éxito/error lo arma este
 * cliente — no el server).
 */
describe('getRuns', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('envía GET a {VITE_API_URL}/runs y devuelve el wire crudo como data', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const wire = [{ run_id: '8f2c1a9b', status: 'completado' }];
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => wire
    } as Response);

    // Act
    const result = await getRuns();

    // Assert
    expect(mockFetch).toHaveBeenCalledWith('http://api.test/runs', { credentials: 'include' });
    expect(result).toEqual({ success: true, data: wire, error: null });
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
    const result = await getRuns();

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
    const result = await getRuns();

    // Assert
    expect(result.success).toBe(false);
    expect(result.error).toContain('ERR_NETWORK');
    expect(result.data).toBeNull();
  });
});

/**
 * F1.2 (flip a 401-obligatorio) — el Studio nunca llamaba `POST
 * /auth/session` porque el fallback del servidor lo cubría; ver
 * `api/src/chimera_api/auth.py`. Ahora que el servidor exige cookie
 * SIEMPRE, cada función de egress pide sesión una vez si el primer intento
 * da 401, reintenta EXACTAMENTE una vez, y si el reintento también da 401
 * falla honesto — jamás un bucle. `getRuns` alcanza para probar el
 * mecanismo compartido (`fetchWithSession`): las demás funciones de egress
 * lo reusan, no lo reimplementan (DRY) — repetirlo por función sería el
 * mismo bug de sincronización arreglado N veces distintas.
 */
describe('sesión — reintento tras 401 (F1.2)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('un 401 dispara POST /auth/session y reintenta la request original UNA vez', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const wire = [{ run_id: '8f2c1a9b', status: 'completado' }];
    const mockFetch = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce({ ok: false, status: 401, statusText: 'Unauthorized' } as Response)
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) } as Response)
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => wire } as Response);
    // `fetch` es un spy COMPARTIDO por todo el archivo (nunca restaurado
    // entre tests): `mockClear()` zanja la cuenta de llamadas previas sin
    // tocar la cola de `mockResolvedValueOnce` recién armada.
    mockFetch.mockClear();

    // Act
    const result = await getRuns();

    // Assert — 3 llamadas: el 401 original, el bootstrap de sesión, el reintento.
    expect(mockFetch).toHaveBeenCalledTimes(3);
    expect(mockFetch).toHaveBeenNthCalledWith(1, 'http://api.test/runs', {
      credentials: 'include'
    });
    expect(mockFetch).toHaveBeenNthCalledWith(2, 'http://api.test/auth/session', {
      method: 'POST',
      credentials: 'include'
    });
    expect(mockFetch).toHaveBeenNthCalledWith(3, 'http://api.test/runs', {
      credentials: 'include'
    });
    expect(result).toEqual({ success: true, data: wire, error: null, status: 200 });
  });

  it('un segundo 401 (tras el reintento) falla honesto — jamás un bucle', async () => {
    // Arrange — el bootstrap de sesión "funciona" (200) pero el reintento
    // vuelve a dar 401 igual (p.ej. sesión rechazada por el server).
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const mockFetch = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce({ ok: false, status: 401, statusText: 'Unauthorized' } as Response)
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) } as Response)
      .mockResolvedValueOnce({ ok: false, status: 401, statusText: 'Unauthorized' } as Response);
    mockFetch.mockClear();

    // Act
    const result = await getRuns();

    // Assert — exactamente 3 llamadas: ni una cuarta (sería el bucle prohibido).
    expect(mockFetch).toHaveBeenCalledTimes(3);
    expect(result.success).toBe(false);
    expect(result.status).toBe(401);
  });
});

describe('getArtifacts', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('envía GET a {VITE_API_URL}/runs/{id}/artifacts y devuelve el wire crudo como data', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const wire = [{ artifact_ref: 'partition.json' }];
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => wire
    } as Response);

    // Act
    const result = await getArtifacts('8f2c1a9b');

    // Assert
    expect(mockFetch).toHaveBeenCalledWith('http://api.test/runs/8f2c1a9b/artifacts', {
      credentials: 'include'
    });
    expect(result).toEqual({ success: true, data: wire, error: null });
  });

  it('encodea el runId en la url', async () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const mockFetch = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce({ ok: true, json: async () => [] } as Response);

    await getArtifacts('run/with slash');

    expect(mockFetch).toHaveBeenCalledWith('http://api.test/runs/run%2Fwith%20slash/artifacts', {
      credentials: 'include'
    });
  });

  it('devuelve error cuando la respuesta no es OK (404 — run desconocido)', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found'
    } as Response);

    // Act
    const result = await getArtifacts('run-desconocido');

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
    const result = await getArtifacts('8f2c1a9b');

    // Assert
    expect(result.success).toBe(false);
    expect(result.error).toContain('ERR_NETWORK');
    expect(result.data).toBeNull();
  });
});

describe('getKnowledge', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('envía GET a {VITE_API_URL}/runs/{id}/knowledge y devuelve el wire crudo como data', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const wire = [{ statement: 'La partición es óptima' }];
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => wire
    } as Response);

    // Act
    const result = await getKnowledge('8f2c1a9b');

    // Assert
    expect(mockFetch).toHaveBeenCalledWith('http://api.test/runs/8f2c1a9b/knowledge', {
      credentials: 'include'
    });
    expect(result).toEqual({ success: true, data: wire, error: null });
  });

  it('devuelve error cuando la respuesta no es OK', async () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found'
    } as Response);

    const result = await getKnowledge('run-desconocido');

    expect(result.success).toBe(false);
    expect(result.error).toContain('404');
    expect(result.data).toBeNull();
  });

  it('devuelve error cuando la petición de red falla', async () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('ERR_NETWORK'));

    const result = await getKnowledge('8f2c1a9b');

    expect(result.success).toBe(false);
    expect(result.error).toContain('ERR_NETWORK');
    expect(result.data).toBeNull();
  });
});

describe('getStepEvidence', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('envía GET a {VITE_API_URL}/runs/{id}/steps/{stepId}/evidence y devuelve el wire crudo', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const wire = { step_id: 'step-solver', capability_id: null, attestations: [] };
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => wire
    } as Response);

    // Act
    const result = await getStepEvidence('8f2c1a9b', 'step-solver');

    // Assert
    expect(mockFetch).toHaveBeenCalledWith(
      'http://api.test/runs/8f2c1a9b/steps/step-solver/evidence',
      { credentials: 'include' }
    );
    expect(result).toEqual({ success: true, data: wire, error: null });
  });

  it('encodea runId y stepId en la url', async () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const mockFetch = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce({ ok: true, json: async () => ({}) } as Response);

    await getStepEvidence('run/with slash', 'step/with slash');

    expect(mockFetch).toHaveBeenCalledWith(
      'http://api.test/runs/run%2Fwith%20slash/steps/step%2Fwith%20slash/evidence',
      { credentials: 'include' }
    );
  });

  it('devuelve error cuando la respuesta no es OK (404 — step desconocido)', async () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found'
    } as Response);

    const result = await getStepEvidence('8f2c1a9b', 'step-desconocido');

    expect(result.success).toBe(false);
    expect(result.error).toContain('404');
    expect(result.data).toBeNull();
  });

  it('devuelve error cuando la petición de red falla', async () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('ERR_NETWORK'));

    const result = await getStepEvidence('8f2c1a9b', 'step-solver');

    expect(result.success).toBe(false);
    expect(result.error).toContain('ERR_NETWORK');
    expect(result.data).toBeNull();
  });
});

describe('getAblation', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('envía GET a {VITE_API_URL}/runs/{id}/ablation y devuelve el wire crudo como data', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const wire = [{ variant: 'quantum', cut_cost: 3, wall_ms: 820, verification_latency_ms: 410 }];
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => wire
    } as Response);

    // Act
    const result = await getAblation('8f2c1a9b');

    // Assert
    expect(mockFetch).toHaveBeenCalledWith('http://api.test/runs/8f2c1a9b/ablation', {
      credentials: 'include'
    });
    expect(result).toEqual({ success: true, data: wire, error: null });
  });

  it('devuelve error cuando la respuesta no es OK', async () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 503,
      statusText: 'Service Unavailable'
    } as Response);

    const result = await getAblation('8f2c1a9b');

    expect(result.success).toBe(false);
    expect(result.error).toContain('503');
    expect(result.data).toBeNull();
  });

  it('devuelve error cuando la petición de red falla', async () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('ERR_NETWORK'));

    const result = await getAblation('8f2c1a9b');

    expect(result.success).toBe(false);
    expect(result.error).toContain('ERR_NETWORK');
    expect(result.data).toBeNull();
  });
});

/**
 * Fake EventSource — captura los listeners registrados por tipo + close().
 * También captura `eventSourceInitDict` (F1.2): el SSE nativo no manda
 * headers, pero SÍ manda cookies same-origin; `withCredentials: true` es lo
 * que las manda también cross-origin.
 */
class FakeEventSource {
  static instances: FakeEventSource[] = [];
  readonly url: string;
  readonly withCredentials: boolean;
  readonly listenersByType = new Map<string, ((event: MessageEvent<string>) => void)[]>();
  onerror: (() => void) | null = null;
  closed = false;

  constructor(url: string, eventSourceInitDict?: EventSourceInit) {
    this.url = url;
    this.withCredentials = eventSourceInitDict?.withCredentials ?? false;
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
    // F1.2 — cross-origin (VITE_API_URL apunta a otro origen que el Studio)
    // necesita withCredentials para que el navegador mande la cookie de
    // sesión; same-origin la manda igual, así que encenderlo siempre es
    // seguro y cubre los dos despliegues con un solo camino de código.
    expect(source?.withCredentials).toBe(true);

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
      verdict: 'pass',
      // D6 (decisión #93) — el payload viaja íntegro con el evento
      // proyectado (freeze §9): RunThread parsea plan.* desde acá.
      payload: { verdict: 'pass' }
    });

    subscription.close();
    expect(source?.closed).toBe(true);
  });

  /**
   * Discrepancia de vocabulario (`docs/specs/endpoints-studio.md` §"Discrepancia"):
   * el freeze (§3/§14) fija `capability.job.submitted` para provenance:pre —
   * el SSE real emite ESE nombre, nunca `.invoked`. Mientras
   * KNOWN_RUN_EVENT_TYPES escuche `.invoked`, este frame se pierde en
   * silencio (ningún listener registrado lo captura).
   */
  /**
   * P3-D (CP1) — sin estos listeners el hilo conversacional en VIVO nunca ve
   * los mensajes sucesivos ni las aprobaciones: el mismo fallo silencioso que
   * el pin de `.submitted`, con otro nombre. El stream los emite (P-rt los
   * apendea en `chimera_api.chat`); el cliente tenía que escucharlos.
   */
  it.each(['mission.message', 'approval.requested', 'approval.responded'])(
    'escucha %s — sin el listener el hilo en vivo los pierde en silencio',
    tipo => {
      vi.stubEnv('VITE_API_URL', 'http://api.test');
      const events: ProjectedEvent[] = [];

      openRunEventStream('8f2c1a9b', { onEvent: e => events.push(e) });
      const source = FakeEventSource.instances[0];
      source?.dispatch(
        tipo,
        JSON.stringify({
          global_seq: 7,
          type: tipo,
          actor_id: 'user:dylan',
          occurred_at: '2026-07-22T12:00:07.000000Z',
          resumen: tipo,
          payload: {}
        })
      );

      expect(events).toHaveLength(1);
      expect(events[0]?.type).toBe(tipo);
    }
  );

  it('escucha capability.job.submitted (pin freeze §3/§14 — NO capability.job.invoked)', () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const events: ProjectedEvent[] = [];

    // Act
    openRunEventStream('8f2c1a9b', { onEvent: e => events.push(e) });
    const source = FakeEventSource.instances[0];
    source?.dispatch(
      'capability.job.submitted',
      JSON.stringify({
        global_seq: 2,
        type: 'capability.job.submitted',
        actor_id: 'service:runtime',
        occurred_at: '2026-07-22T12:00:02.000000Z',
        resumen: 'Invocando ortools-cpsat para la partición óptima',
        payload: {}
      })
    );

    // Assert
    expect(events).toHaveLength(1);
    expect(events[0]?.type).toBe('capability.job.submitted');
  });

  /**
   * Auditoría Fase 2 (vivo, 2026-07-29): `execute_run` emite `run.created`,
   * `run.step.*` y `capability.job.failed` en el stream real — sin listener,
   * el timeline en vivo mostraba 2 de 5 eventos de un run fallido mientras
   * el header decía "5 eventos" (pérdida silenciosa; la demo narra "cero
   * eventos perdidos"). `replay.divergence` (A5) entra por el mismo motivo:
   * es parte del vocabulario emitido del loop.
   */
  it('escucha el vocabulario completo que execute_run emite (run.created, run.step.*, job.failed, replay.divergence)', () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const events: ProjectedEvent[] = [];
    const emitted = [
      'run.created',
      'run.step.started',
      'run.step.completed',
      'run.step.failed',
      'capability.job.failed',
      'replay.divergence'
    ];

    // Act
    openRunEventStream('8f2c1a9b', { onEvent: e => events.push(e) });
    const source = FakeEventSource.instances[0];
    emitted.forEach((type, i) => {
      source?.dispatch(
        type,
        JSON.stringify({
          global_seq: i + 1,
          type,
          actor_id: 'service:runtime',
          occurred_at: `2026-07-29T12:00:0${i}.000000Z`,
          resumen: type,
          payload: {}
        })
      );
    });

    // Assert — cada tipo emitido llega proyectado, ninguno se pierde.
    expect(events.map(e => e.type)).toEqual(emitted);
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

/**
 * P3-D (CP1) — las tres rutas de conversación que P-rt dejó vivas del lado E
 * (`api/src/chimera_api/chat.py`, spec chat-conversacion.md §Contrato-2/3/7).
 *
 * A diferencia de `postRun`, estas rutas devuelven el wire CRUDO (202 con
 * `{message_id}` o `{}`), así que el envelope lo arma este cliente. Y a
 * diferencia de los GET, el STATUS importa: 409 (stream terminal), 403 (sin
 * `override:apply:run`) y 422 (no valida contra el json_schema) son estados
 * que la UI tiene que distinguir para decir la verdad, no un error genérico.
 */
describe('postRunMessage / postRunCancel / postApprovalResponse (P3-D)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('postRunMessage postea el texto y devuelve el message_id', async () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 202,
      json: async () => ({ message_id: 'msg-abc' })
    } as Response);

    const result = await postRunMessage('run-1', 'probá con 3 islas');

    expect(mockFetch).toHaveBeenCalledWith('http://api.test/runs/run-1/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: 'probá con 3 islas' }),
      credentials: 'include'
    });
    expect(result.success).toBe(true);
    expect(result.data).toEqual({ message_id: 'msg-abc' });
    expect(result.status).toBe(202);
  });

  it('propaga el 409 con el detail del server (stream terminal — freeze §2)', async () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 409,
      statusText: 'Conflict',
      json: async () => ({ detail: 'el run ya es terminal — continuá con un run nuevo' })
    } as Response);

    const result = await postRunMessage('run-1', 'tarde');

    expect(result.success).toBe(false);
    expect(result.status).toBe(409);
    expect(result.error).toContain('terminal');
  });

  it('no explota si el cuerpo de error no es JSON (degrada al status)', async () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 502,
      statusText: 'Bad Gateway',
      json: async () => {
        throw new Error('no es json');
      }
    } as unknown as Response);

    const result = await postRunMessage('run-1', 'x');

    expect(result.success).toBe(false);
    expect(result.status).toBe(502);
    expect(result.error).toContain('502');
  });

  it('postRunCancel manda el reason cuando se le da', async () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 202,
      json: async () => ({})
    } as Response);

    const result = await postRunCancel('run-1', 'ya no lo necesito');

    expect(mockFetch).toHaveBeenCalledWith('http://api.test/runs/run-1/cancel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: 'ya no lo necesito' }),
      credentials: 'include'
    });
    expect(result.success).toBe(true);
  });

  it('postRunCancel sin reason deja que el server ponga su default (user_requested)', async () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 202,
      json: async () => ({})
    } as Response);

    await postRunCancel('run-1');

    expect(mockFetch).toHaveBeenCalledWith(
      'http://api.test/runs/run-1/cancel',
      expect.objectContaining({ body: JSON.stringify({}) })
    );
  });

  it('postApprovalResponse postea la respuesta al par del approval', async () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 202,
      json: async () => ({})
    } as Response);

    const result = await postApprovalResponse('run-1', 'approval-1', { aprobado: true });

    expect(mockFetch).toHaveBeenCalledWith('http://api.test/runs/run-1/approvals/approval-1', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ response: { aprobado: true } }),
      credentials: 'include'
    });
    expect(result.success).toBe(true);
  });

  it('propaga el 403 de override:apply:run (fail-closed a propósito, no es bug)', async () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 403,
      statusText: 'Forbidden',
      json: async () => ({ detail: 'la identidad no porta override:apply:run' })
    } as Response);

    const result = await postApprovalResponse('run-1', 'approval-1', { aprobado: true });

    expect(result.status).toBe(403);
    expect(result.error).toContain('override:apply:run');
  });

  it('escapa los ids en la ruta (un run_id con / no se sale del path)', async () => {
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 202,
      json: async () => ({ message_id: 'm' })
    } as Response);

    await postRunMessage('run/1', 'x');

    expect(mockFetch).toHaveBeenCalledWith(
      'http://api.test/runs/run%2F1/messages',
      expect.anything()
    );
  });
});
