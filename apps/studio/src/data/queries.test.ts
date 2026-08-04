/**
 * queries.test.ts (task 3 + D3) — cubre la selección de rama demo/live de
 * las queryOptions de proyecto/run (S10/D3: la fuente cambia, el shape que
 * consumen las vistas no). Mismo patrón que mutations.test.ts: se mockea
 * `../gatewayClient` completo y se stubea VITE_API_URL.
 *
 * D3 (`docs/specs/endpoints-studio.md`) — 5 de las 6 rutas de lectura de
 * E1 ya tienen egress real (getRuns/getArtifacts/getKnowledge/
 * getStepEvidence/getAblation); la rama live de sus queryOptions pasa de
 * "sin endpoint todavía, honest-empty" a "llama al egress, valida el wire,
 * mapea a la UI". `artifactsQueryOptions`/`knowledgeQueryOptions` aceptan
 * un `runId` OPCIONAL: sin runId (los screens de proyecto, sin contexto de
 * run) siguen honest-empty en vivo — ver App.tsx, no hay todavía un tab
 * "Artifacts"/"Knowledge" dentro de RunDetail que provea un runId real.
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

import type { RunSummary } from '../views/types';
import {
  ablationQueryOptions,
  artifactsQueryOptions,
  certificateQueryOptions,
  DEMO_RUN_ID,
  knowledgeQueryOptions,
  loadAblation,
  loadArtifacts,
  loadCertificate,
  loadKnowledge,
  loadRunEvents,
  loadRunSummaries,
  loadRvsP,
  loadStepEvidence,
  runEventsQueryOptions,
  runSummariesQueryOptions,
  rvspQueryOptions,
  stepEvidenceQueryOptions
} from './queries';

vi.mock('../gatewayClient', () => ({
  getCertificate: vi.fn(),
  getRuns: vi.fn(),
  getArtifacts: vi.fn(),
  getKnowledge: vi.fn(),
  getStepEvidence: vi.fn(),
  getAblation: vi.fn()
}));

describe('certificateQueryOptions', () => {
  it('arma la queryKey por runId', () => {
    const options = certificateQueryOptions('run-42');
    expect(options.queryKey).toEqual(['runs', 'run-42', 'certificate']);
  });

  /**
   * Auditoría Fase 2 (2026-07-29, verificado vivo): antes de esto, un 409
   * ("claim aún no emitido", `chimera_api/certificate.py`) se reintentaba
   * 3 veces (default de TanStack Query) como si fuera transitorio — 3
   * fetches + consola roja para un estado que un retry inmediato no
   * cambia. Mismo criterio para 404 (run desconocido). Un error de red/5xx
   * SÍ sigue reintentando (hasta 3 veces, default previo).
   */
  it('no reintenta un 409 (claim aún no emitido) — el error se muestra una vez', () => {
    const options = certificateQueryOptions('run-42');
    const retry = options.retry as (failureCount: number, error: unknown) => boolean;
    expect(retry(0, new Error('Gateway error: 409 Conflict'))).toBe(false);
  });

  it('no reintenta un 404 (run desconocido)', () => {
    const options = certificateQueryOptions('run-42');
    const retry = options.retry as (failureCount: number, error: unknown) => boolean;
    expect(retry(0, new Error('Gateway error: 404 Not Found'))).toBe(false);
  });

  it('sí reintenta un error transitorio (red) hasta 3 veces', () => {
    const options = certificateQueryOptions('run-42');
    const retry = options.retry as (failureCount: number, error: unknown) => boolean;
    expect(retry(0, new Error('Network error: fetch failed'))).toBe(true);
    expect(retry(2, new Error('Network error: fetch failed'))).toBe(true);
    expect(retry(3, new Error('Network error: fetch failed'))).toBe(false);
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

  it('modo live: acepta el BUNDLE real del api ({envelope, stream, …}) y conserva el bundle íntegro como wire', async () => {
    // Arrange — auditoría Fase 2 (vivo, 2026-07-29): GET /certificate
    // devuelve el bundle COMPLETO (envelope + public_key + stream + …), no
    // el envelope pelado; parsearlo con wireEnvelopeSchema explotaba la
    // vista Verificación en vivo, y descargar solo el envelope rompería
    // `scripts/verify-bundle.py` (necesita el bundle entero).
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    const liveBundle = {
      envelope: EXAMPLE_CERTIFICATE_WIRE,
      public_key: 'a'.repeat(64),
      stream: [{ type: 'run.created' }],
      anchor_descriptors: [],
      verifier_descriptors: [],
      policy_yaml_b64: 'cG9saWN5',
      deliverable_contents: {}
    };
    vi.mocked(gatewayClient.getCertificate).mockResolvedValueOnce({
      success: true,
      data: liveBundle,
      error: null
    });

    // Act
    const resource = await loadCertificate('run-live-1');

    // Assert — wire = el bundle entero (descargable y verificable offline);
    // envelope = el DSSE decodificado para la vista.
    expect(gatewayClient.getCertificate).toHaveBeenCalledWith('run-live-1');
    expect(resource.wire).toEqual(liveBundle);
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
 * D3 — `GET /runs` ya existe (E1): la rama live llama a
 * `gatewayClient.getRuns`, valida el wire (`runSummaryWireSchema`) y
 * mapea con `toRunSummary`. Mismo patrón AAA que loadCertificate arriba.
 */
describe('loadRunSummaries (rama demo/live)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.mocked(gatewayClient.getRuns).mockReset();
  });

  it('modo demo: proyecta el run del certificado real', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', undefined);

    // Act
    const summaries = await loadRunSummaries();

    // Assert
    const events = z.array(projectedEventSchema).parse(RUN_EVENTS);
    expect(summaries).toEqual([deriveRunSummary(EXAMPLE_CERTIFICATE, events)]);
    expect(gatewayClient.getRuns).not.toHaveBeenCalled();
  });

  it('modo live: llama a getRuns, valida el wire y lo mapea a RunSummary[]', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.mocked(gatewayClient.getRuns).mockResolvedValueOnce({
      success: true,
      data: [
        {
          run_id: '8f2c1a9b',
          status: 'completado',
          conclusion: 'La partición propuesta de ieee14 es el óptimo exacto del corte',
          verdict: 'verified',
          titular_level: 'AL3',
          titular_class: 'formal_exact',
          events_count: 12,
          actor: 'user:dylan',
          completed_at: '2026-07-22T12:00:06.000000Z'
        }
      ],
      error: null
    });

    // Act
    const summaries = await loadRunSummaries();

    // Assert
    expect(summaries).toEqual([
      {
        runId: '8f2c1a9b',
        status: 'completado',
        conclusion: 'La partición propuesta de ieee14 es el óptimo exacto del corte',
        verdict: 'verified',
        titularLevel: 'AL3',
        titularClass: 'formal_exact',
        eventsCount: 12,
        actor: 'user:dylan',
        completedAt: '2026-07-22T12:00:06.000000Z'
      }
    ]);
  });

  it('modo live: lista vacía es EmptyState honesto, no un error', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.mocked(gatewayClient.getRuns).mockResolvedValueOnce({
      success: true,
      data: [],
      error: null
    });

    // Act
    const summaries = await loadRunSummaries();

    // Assert
    expect(summaries).toEqual([]);
  });

  it('modo live: rechaza cuando getRuns devuelve success:false (surge como ErrorState)', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.mocked(gatewayClient.getRuns).mockResolvedValueOnce({
      success: false,
      data: null,
      error: 'Gateway error: 503 Service Unavailable'
    });

    // Act & Assert
    await expect(loadRunSummaries()).rejects.toThrow('Gateway error: 503 Service Unavailable');
  });
});

describe('runSummariesQueryOptions', () => {
  it('arma la queryKey de proyecto', () => {
    const options = runSummariesQueryOptions();
    expect(options.queryKey).toEqual(['runs']);
  });
});

/**
 * D3 — `GET /runs/{id}/artifacts` ya existe (E1), pero la ruta EXIGE un
 * `run_id`: los screens de proyecto (`ArtifactsScreen`, sin runId — no hay
 * todavía un tab "Artifacts" dentro de RunDetail) siguen honest-empty en
 * vivo; el egress real solo se ejercita cuando SÍ se pasa un runId.
 */
describe('loadArtifacts (rama demo/live)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.mocked(gatewayClient.getArtifacts).mockReset();
  });

  it('modo demo: proyecta los deliverables del certificado (ignora runId)', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', undefined);

    // Act
    const artifacts = await loadArtifacts();

    // Assert
    expect(artifacts).toEqual(deriveArtifacts(EXAMPLE_CERTIFICATE));
    expect(gatewayClient.getArtifacts).not.toHaveBeenCalled();
  });

  it('modo live sin runId (screen de proyecto, sin contexto de run): honest-empty, nunca el fixture', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');

    // Act
    const artifacts = await loadArtifacts();

    // Assert
    expect(artifacts).toEqual([]);
    expect(gatewayClient.getArtifacts).not.toHaveBeenCalled();
  });

  it('modo live con runId: llama a getArtifacts, valida el wire y lo mapea', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.mocked(gatewayClient.getArtifacts).mockResolvedValueOnce({
      success: true,
      data: [
        {
          artifact_ref: 'partition.json',
          digest: 'a1b751764b2d516ab45b8ac077a0eff0ab49c3d4245e882f3c0bef59de498b93',
          run_id: '8f2c1a9b',
          titular_level: 'AL3',
          titular_class: 'formal_exact',
          verdict: 'verified',
          issued_at: '2026-07-22T12:00:06.000000Z'
        }
      ],
      error: null
    });

    // Act
    const artifacts = await loadArtifacts('8f2c1a9b');

    // Assert
    expect(gatewayClient.getArtifacts).toHaveBeenCalledWith('8f2c1a9b');
    expect(artifacts).toEqual([
      {
        artifactRef: 'partition.json',
        digest: 'a1b751764b2d516ab45b8ac077a0eff0ab49c3d4245e882f3c0bef59de498b93',
        runId: '8f2c1a9b',
        titularLevel: 'AL3',
        titularClass: 'formal_exact',
        verdict: 'verified',
        issuedAt: '2026-07-22T12:00:06.000000Z'
      }
    ]);
  });

  it('modo live con runId: sin certificado emitido aún — [] es EmptyState honesto', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.mocked(gatewayClient.getArtifacts).mockResolvedValueOnce({
      success: true,
      data: [],
      error: null
    });

    // Act
    const artifacts = await loadArtifacts('run-en-curso');

    // Assert
    expect(artifacts).toEqual([]);
  });

  it('modo live con runId: 404 (run desconocido) rechaza — surge como ErrorState', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.mocked(gatewayClient.getArtifacts).mockResolvedValueOnce({
      success: false,
      data: null,
      error: 'Gateway error: 404 Not Found'
    });

    // Act & Assert
    await expect(loadArtifacts('run-desconocido')).rejects.toThrow('Gateway error: 404 Not Found');
  });
});

describe('artifactsQueryOptions', () => {
  it('arma la queryKey por runId opcional', () => {
    expect(artifactsQueryOptions().queryKey).toEqual(['artifacts', undefined]);
    expect(artifactsQueryOptions('run-42').queryKey).toEqual(['artifacts', 'run-42']);
  });
});

/** D3 — mismo patrón que loadArtifacts (runId opcional, misma honestidad de screens de proyecto). */
describe('loadKnowledge (rama demo/live)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.mocked(gatewayClient.getKnowledge).mockReset();
  });

  it('modo demo: proyecta las conclusiones verificadas del certificado (ignora runId)', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', undefined);

    // Act
    const claims = await loadKnowledge();

    // Assert
    expect(claims).toEqual(deriveKnowledge(EXAMPLE_CERTIFICATE));
    expect(gatewayClient.getKnowledge).not.toHaveBeenCalled();
  });

  it('modo live sin runId (screen de proyecto): honest-empty, nunca el fixture', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');

    // Act
    const claims = await loadKnowledge();

    // Assert
    expect(claims).toEqual([]);
    expect(gatewayClient.getKnowledge).not.toHaveBeenCalled();
  });

  it('modo live con runId: llama a getKnowledge, valida el wire y lo mapea', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.mocked(gatewayClient.getKnowledge).mockResolvedValueOnce({
      success: true,
      data: [
        {
          statement: 'La partición propuesta de ieee14 es el óptimo exacto del corte',
          scope: { problem: 'islanding-partition', instance: 'ieee14' },
          verdict: 'verified',
          level: 'AL3',
          titular_class: 'formal_exact',
          run_id: '8f2c1a9b',
          valid_as_of: '2026-07-22T12:00:06.000000Z'
        }
      ],
      error: null
    });

    // Act
    const claims = await loadKnowledge('8f2c1a9b');

    // Assert
    expect(gatewayClient.getKnowledge).toHaveBeenCalledWith('8f2c1a9b');
    expect(claims).toEqual([
      {
        statement: 'La partición propuesta de ieee14 es el óptimo exacto del corte',
        scope: { problem: 'islanding-partition', instance: 'ieee14' },
        verdict: 'verified',
        level: 'AL3',
        titularClass: 'formal_exact',
        runId: '8f2c1a9b',
        validAsOf: '2026-07-22T12:00:06.000000Z'
      }
    ]);
  });

  it('modo live con runId: 404 (run desconocido) rechaza', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.mocked(gatewayClient.getKnowledge).mockResolvedValueOnce({
      success: false,
      data: null,
      error: 'Gateway error: 404 Not Found'
    });

    // Act & Assert
    await expect(loadKnowledge('run-desconocido')).rejects.toThrow('Gateway error: 404 Not Found');
  });
});

describe('knowledgeQueryOptions', () => {
  it('arma la queryKey por runId opcional', () => {
    expect(knowledgeQueryOptions().queryKey).toEqual(['knowledge', undefined]);
    expect(knowledgeQueryOptions('run-42').queryKey).toEqual(['knowledge', 'run-42']);
  });
});

/**
 * D3 — `GET /runs/{id}/steps/{step_id}/evidence` es POR PASO, pero el
 * consumidor (`App.tsx` RunDetailScreen, `stepsQuery.data?.[stepId]`)
 * espera el mapa completo `Record<stepId, StepDetail>`. Reconciliación
 * pragmática (elegida entre las 2 opciones del brief): en vivo se arma el
 * mapa pidiendo evidencia para los `stepId`s YA presentes en los eventos
 * del run (2do param `stepIds`) — nunca se inventa un stepId, y no hace
 * falta un fetch lazy por selección (E1 devuelve mayormente evidencia
 * vacía hoy, así que N fetches por los pocos steps del run es correcto y
 * simple, no over-engineering).
 */
describe('loadStepEvidence (rama demo/live)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.mocked(gatewayClient.getStepEvidence).mockReset();
  });

  it('modo demo: devuelve el fixture de evidencia por paso (ignora runId/stepIds)', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', undefined);

    // Act
    const evidence = await loadStepEvidence(DEMO_RUN_ID);

    // Assert
    expect(evidence).toEqual(z.record(z.string(), z.unknown()).parse(STEP_EVIDENCE));
    expect(Object.keys(evidence)).toEqual(Object.keys(STEP_EVIDENCE));
    expect(gatewayClient.getStepEvidence).not.toHaveBeenCalled();
  });

  it('modo live sin stepIds: devuelve un record vacío sin llamar a la red (nada que pedir todavía)', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');

    // Act
    const evidence = await loadStepEvidence('8f2c1a9b');

    // Assert
    expect(evidence).toEqual({});
    expect(gatewayClient.getStepEvidence).not.toHaveBeenCalled();
  });

  it('modo live con stepIds: pide evidencia por paso y arma el mapa camelCase', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.mocked(gatewayClient.getStepEvidence).mockImplementation(async (_runId, stepId) => ({
      success: true,
      data: {
        step_id: stepId,
        capability_id: null,
        input_digest: null,
        output_digest: null,
        attestations: []
      },
      error: null
    }));

    // Act
    const evidence = await loadStepEvidence('8f2c1a9b', ['step-solver', 'step-execution-a']);

    // Assert
    expect(gatewayClient.getStepEvidence).toHaveBeenCalledWith('8f2c1a9b', 'step-solver');
    expect(gatewayClient.getStepEvidence).toHaveBeenCalledWith('8f2c1a9b', 'step-execution-a');
    expect(evidence).toEqual({
      'step-solver': {
        stepId: 'step-solver',
        capabilityId: '',
        inputDigest: '',
        outputDigest: '',
        attestations: []
      },
      'step-execution-a': {
        stepId: 'step-execution-a',
        capabilityId: '',
        inputDigest: '',
        outputDigest: '',
        attestations: []
      }
    });
  });

  it('modo live: 404 (step desconocido) rechaza — surge como ErrorState, no se fabrica evidencia', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.mocked(gatewayClient.getStepEvidence).mockResolvedValueOnce({
      success: false,
      data: null,
      error: 'Gateway error: 404 Not Found'
    });

    // Act & Assert
    await expect(loadStepEvidence('8f2c1a9b', ['step-desconocido'])).rejects.toThrow(
      'Gateway error: 404 Not Found'
    );
  });
});

describe('stepEvidenceQueryOptions', () => {
  it('arma la queryKey por runId + stepIds', () => {
    const options = stepEvidenceQueryOptions('run-42', ['step-a']);
    expect(options.queryKey).toEqual(['runs', 'run-42', 'step-evidence', ['step-a']]);
  });
});

describe('loadAblation (rama demo/live)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.mocked(gatewayClient.getAblation).mockReset();
  });

  it('modo demo: devuelve las métricas de ablación del fixture (ignora runId)', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', undefined);

    // Act
    const metrics = await loadAblation('8f2c1a9b');

    // Assert
    expect(metrics).toEqual(ABLATION_METRICS);
    expect(gatewayClient.getAblation).not.toHaveBeenCalled();
  });

  it('modo live: llama a getAblation, valida el wire snake_case y lo mapea', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.mocked(gatewayClient.getAblation).mockResolvedValueOnce({
      success: true,
      data: [{ variant: 'quantum', cut_cost: 3, wall_ms: 820, verification_latency_ms: 410 }],
      error: null
    });

    // Act
    const metrics = await loadAblation('8f2c1a9b');

    // Assert
    expect(gatewayClient.getAblation).toHaveBeenCalledWith('8f2c1a9b');
    expect(metrics).toEqual([
      { variant: 'quantum', cutCost: 3, wallMs: 820, verificationLatencyMs: 410 }
    ]);
  });

  it('modo live: sin métricas todavía — [] es EmptyState honesto', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.mocked(gatewayClient.getAblation).mockResolvedValueOnce({
      success: true,
      data: [],
      error: null
    });

    // Act
    const metrics = await loadAblation('8f2c1a9b');

    // Assert
    expect(metrics).toEqual([]);
  });

  it('modo live: 404 (run desconocido) rechaza', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.mocked(gatewayClient.getAblation).mockResolvedValueOnce({
      success: false,
      data: null,
      error: 'Gateway error: 404 Not Found'
    });

    // Act & Assert
    await expect(loadAblation('run-desconocido')).rejects.toThrow('Gateway error: 404 Not Found');
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

/**
 * P3-D — la lista de runs se refresca sola MIENTRAS haya trabajo en curso.
 *
 * `GET /runs` es una lectura, no un stream: sin refetch, un run lanzado desde
 * el Studio se queda en «en_curso» en pantalla hasta que alguien recarga —
 * la plataforma parece colgada cuando en realidad terminó. Y al revés: dejar
 * un polling permanente castiga a un proyecto con 200 runs terminales para
 * no enterarse de nada. El intervalo se ATA al dato: hay `en_curso` ⇒ hay
 * motivo para volver a preguntar.
 */
describe('runSummariesQueryOptions — refetch atado al estado real', () => {
  const RUN = (status: RunSummary['status']): RunSummary => ({
    runId: 'r1',
    status,
    conclusion: 'c',
    verdict: 'inconclusive',
    titularLevel: 'AL0',
    titularClass: 'formal_exact',
    eventsCount: 1,
    actor: 'user:dylan'
  });

  it('sigue preguntando mientras al menos un run está en curso', () => {
    const { refetchInterval } = runSummariesQueryOptions();
    const intervalo = refetchInterval as (query: {
      state: { data?: readonly RunSummary[] };
    }) => number | false;

    expect(intervalo({ state: { data: [RUN('completado'), RUN('en_curso')] } })).toBeGreaterThan(0);
  });

  it('deja de preguntar cuando todos terminaron', () => {
    const { refetchInterval } = runSummariesQueryOptions();
    const intervalo = refetchInterval as (query: {
      state: { data?: readonly RunSummary[] };
    }) => number | false;

    expect(intervalo({ state: { data: [RUN('completado'), RUN('fallido')] } })).toBe(false);
    expect(intervalo({ state: { data: [RUN('cancelado')] } })).toBe(false);
  });

  it('no pregunta cuando todavía no hay datos (el primer fetch está en vuelo)', () => {
    const { refetchInterval } = runSummariesQueryOptions();
    const intervalo = refetchInterval as (query: {
      state: { data?: readonly RunSummary[] };
    }) => number | false;

    expect(intervalo({ state: {} })).toBe(false);
  });
});
