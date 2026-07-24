/**
 * queries.test.ts (task 3) — cubre la selección de rama demo/live de
 * `certificateQueryOptions` (S10: la fuente cambia, el shape que
 * consumen las vistas no). Mismo patrón que mutations.test.ts: se mockea
 * `../gatewayClient` completo y se stubea VITE_API_URL.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { z } from 'zod';

import * as gatewayClient from '../gatewayClient';
import { ABLATION_METRICS } from '../fixtures/ablationMetrics';
import { EXAMPLE_CERTIFICATE, EXAMPLE_CERTIFICATE_WIRE } from '../fixtures/certificate';
import { RUN_EVENTS } from '../fixtures/runEvents';
import { RVSP_EXPERIMENT } from '../fixtures/rvsp';
import { STEP_EVIDENCE } from '../fixtures/stepEvidence';
import { deriveArtifacts, deriveKnowledge, deriveRunSummary } from './projections';
import { projectedEventSchema } from './schemas';
import {
  ablationQueryOptions,
  certificateQueryOptions,
  DEMO_RUN_ID,
  loadAblation,
  loadArtifacts,
  loadCertificate,
  loadKnowledge,
  loadRunEvents,
  loadRunSummaries,
  loadRvsP,
  loadStepEvidence,
  runEventsQueryOptions,
  rvspQueryOptions
} from './queries';

vi.mock('../gatewayClient', () => ({
  getCertificate: vi.fn()
}));

describe('certificateQueryOptions', () => {
  it('arma la queryKey por runId', () => {
    const options = certificateQueryOptions('run-42');
    expect(options.queryKey).toEqual(['runs', 'run-42', 'certificate']);
  });
});

describe('loadCertificate (rama demo/live)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.mocked(gatewayClient.getCertificate).mockReset();
  });

  it('modo demo (sin VITE_API_URL): devuelve el fixture sin llamar a getCertificate', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', undefined);

    // Act
    const resource = await loadCertificate(DEMO_RUN_ID);

    // Assert
    expect(gatewayClient.getCertificate).not.toHaveBeenCalled();
    expect(resource.wire).toEqual(EXAMPLE_CERTIFICATE_WIRE);
    expect(resource.envelope.payload.predicate.runId).toBe('8f2c1a9b');
  });

  it('modo live: llama a getCertificate y decodifica el wire devuelto', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.mocked(gatewayClient.getCertificate).mockResolvedValueOnce({
      success: true,
      data: EXAMPLE_CERTIFICATE_WIRE,
      error: null
    });

    // Act
    const resource = await loadCertificate('run-live-1');

    // Assert
    expect(gatewayClient.getCertificate).toHaveBeenCalledWith('run-live-1');
    expect(resource.wire).toEqual(EXAMPLE_CERTIFICATE_WIRE);
    expect(resource.envelope.payload.predicate.runId).toBe('8f2c1a9b');
  });

  it('modo live: rechaza cuando getCertificate devuelve success:false', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.mocked(gatewayClient.getCertificate).mockResolvedValueOnce({
      success: false,
      data: null,
      error: 'Gateway error: 404 Not Found'
    });

    // Act & Assert
    await expect(loadCertificate('run-live-1')).rejects.toThrow('Gateway error: 404 Not Found');
  });

  it('modo live: rechaza con mensaje por defecto cuando la respuesta no trae error', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.mocked(gatewayClient.getCertificate).mockResolvedValueOnce({
      success: false,
      data: null,
      error: null
    });

    // Act & Assert
    await expect(loadCertificate('run-live-1')).rejects.toThrow(
      'No se pudo obtener el certificado'
    );
  });

  it('modo live: rechaza (Zod) cuando el wire devuelto llega mal formado', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.mocked(gatewayClient.getCertificate).mockResolvedValueOnce({
      success: true,
      data: { payloadType: 'x' }, // sin payload ni signatures
      error: null
    });

    // Act & Assert
    await expect(loadCertificate('run-live-1')).rejects.toThrow();
  });
});

/**
 * D1 (honestidad de modo) — los 5 recursos de proyecto/run que hoy NO
 * tienen endpoint real en chimera_api (solo existen POST /runs,
 * /certificate y /events): en vivo deben devolver vacío, jamás el
 * fixture. Mismo patrón AAA que loadCertificate arriba.
 */
describe('loadRunSummaries (rama demo/live)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('modo demo: proyecta el run del certificado real', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', undefined);

    // Act
    const summaries = await loadRunSummaries();

    // Assert
    const events = z.array(projectedEventSchema).parse(RUN_EVENTS);
    expect(summaries).toEqual([deriveRunSummary(EXAMPLE_CERTIFICATE, events)]);
  });

  it('modo live: sin GET /runs todavía — devuelve vacío, nunca el fixture', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');

    // Act
    const summaries = await loadRunSummaries();

    // Assert
    expect(summaries).toEqual([]);
  });
});

describe('loadArtifacts (rama demo/live)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('modo demo: proyecta los deliverables del certificado', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', undefined);

    // Act
    const artifacts = await loadArtifacts();

    // Assert
    expect(artifacts).toEqual(deriveArtifacts(EXAMPLE_CERTIFICATE));
  });

  it('modo live: sin GET /artifacts todavía — devuelve vacío, nunca el fixture', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');

    // Act
    const artifacts = await loadArtifacts();

    // Assert
    expect(artifacts).toEqual([]);
  });
});

describe('loadKnowledge (rama demo/live)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('modo demo: proyecta las conclusiones verificadas del certificado', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', undefined);

    // Act
    const claims = await loadKnowledge();

    // Assert
    expect(claims).toEqual(deriveKnowledge(EXAMPLE_CERTIFICATE));
  });

  it('modo live: sin GET /knowledge todavía — devuelve vacío, nunca el fixture', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');

    // Act
    const claims = await loadKnowledge();

    // Assert
    expect(claims).toEqual([]);
  });
});

describe('loadStepEvidence (rama demo/live)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('modo demo: devuelve el fixture de evidencia por paso', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', undefined);

    // Act
    const evidence = await loadStepEvidence();

    // Assert
    expect(evidence).toEqual(z.record(z.string(), z.unknown()).parse(STEP_EVIDENCE));
    expect(Object.keys(evidence)).toEqual(Object.keys(STEP_EVIDENCE));
  });

  it('modo live: sin GET /step-evidence todavía — devuelve un record vacío, nunca el fixture', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');

    // Act
    const evidence = await loadStepEvidence();

    // Assert
    expect(evidence).toEqual({});
  });
});

describe('loadAblation (rama demo/live)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('modo demo: devuelve las métricas de ablación del fixture', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', undefined);

    // Act
    const metrics = await loadAblation();

    // Assert
    expect(metrics).toEqual(ABLATION_METRICS);
  });

  it('modo live: sin GET /ablation todavía — devuelve vacío, nunca el fixture', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');

    // Act
    const metrics = await loadAblation();

    // Assert
    expect(metrics).toEqual([]);
  });
});

/**
 * D1 task 3 — la carrera SSE/fixture muerta: runEventsQueryOptions ya no
 * parsea el fixture incondicionalmente (useRunEventStream escribe al MISMO
 * query key en vivo). El staleTime/refetchOnWindowFocus/refetchOnReconnect
 * evita que un refetch automático (foco de ventana, reconexión) borre lo
 * que el SSE ya acumuló — en vivo, el SSE es el ÚNICO escritor.
 */
describe('loadRunEvents (rama demo/live)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('modo demo: devuelve el fixture de eventos del run', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', undefined);

    // Act
    const events = await loadRunEvents();

    // Assert
    expect(events).toEqual(z.array(projectedEventSchema).parse(RUN_EVENTS));
  });

  it('modo live: devuelve vacío — no fuga ningún evento del fixture', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');

    // Act
    const events = await loadRunEvents();

    // Assert
    expect(events).toEqual([]);
  });
});

describe('runEventsQueryOptions', () => {
  it('arma la queryKey por runId', () => {
    const options = runEventsQueryOptions('run-42');
    expect(options.queryKey).toEqual(['runs', 'run-42', 'events']);
  });

  it('desactiva el refetch automático — en vivo el SSE es el único escritor', () => {
    const options = runEventsQueryOptions('run-42');
    expect(options.staleTime).toBe(Infinity);
    expect(options.refetchOnWindowFocus).toBe(false);
    expect(options.refetchOnReconnect).toBe(false);
  });
});

describe('ablationQueryOptions', () => {
  it('arma la queryKey por runId', () => {
    const options = ablationQueryOptions('run-42');
    expect(options.queryKey).toEqual(['runs', 'run-42', 'ablation']);
  });
});

/**
 * D5 (dataviz "r vs p") — mismo patrón AAA que loadAblation: demo sirve el
 * experimento real copiado a fixture; en vivo, sin `GET /rvsp` todavía,
 * "nada" es `null` (no `[]` — este recurso es un objeto único, no lista).
 */
describe('loadRvsP (rama demo/live)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('modo demo: devuelve el experimento r-vs-p del fixture', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', undefined);

    // Act
    const experiment = await loadRvsP();

    // Assert
    expect(experiment).toEqual(RVSP_EXPERIMENT);
  });

  it('modo live: sin GET /rvsp todavía — devuelve null, nunca el fixture', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');

    // Act
    const experiment = await loadRvsP();

    // Assert
    expect(experiment).toBeNull();
  });
});

describe('rvspQueryOptions', () => {
  it('arma la queryKey por runId', () => {
    const options = rvspQueryOptions('run-42');
    expect(options.queryKey).toEqual(['runs', 'run-42', 'rvsp']);
  });
});
