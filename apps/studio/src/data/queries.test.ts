/**
 * queries.test.ts (task 3) — cubre la selección de rama demo/live de
 * `certificateQueryOptions` (S10: la fuente cambia, el shape que
 * consumen las vistas no). Mismo patrón que mutations.test.ts: se mockea
 * `../gatewayClient` completo y se stubea VITE_API_URL.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';

import * as gatewayClient from '../gatewayClient';
import { EXAMPLE_CERTIFICATE_WIRE } from '../fixtures/certificate';
import { certificateQueryOptions, DEMO_RUN_ID, loadCertificate } from './queries';

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
