import { afterEach, describe, expect, it, vi } from 'vitest';

import MISSION_CONTRACT_FIXTURE from '../fixtures/contract/endpoints/post-runs-mission.json';
import * as gatewayClient from '../gatewayClient';
import { createRun, toCreateRunBody } from './mutations';
import { DEMO_RUN_ID } from './queries';

import type { NewRunInput } from '../views/types';

vi.mock('../gatewayClient', () => ({
  postRun: vi.fn()
}));

describe('toCreateRunBody (checkpoint 5 — modo misión, endpoints-studio.md)', () => {
  it('mapea instancia + proposer al body misión-first de POST /runs', () => {
    // Arrange
    const input: NewRunInput = { instance: 'ieee14', proposer: 'qaoa' };

    // Act
    const body = toCreateRunBody(input);

    // Assert
    expect(body).toEqual({
      mission:
        'Particionar la red ieee14 en islas controladas y certificar la optimalidad del corte',
      instance_id: 'ieee14',
      capability_id: 'blite.quantum.qaoa'
    });
  });

  it('produce EXACTAMENTE el body del fixture de costura (contrato E↔D, un solo origen)', () => {
    // Arrange — el fixture lo genera scripts/gen-contract-fixtures-endpoints.py
    // desde MissionRequest (Pydantic); el API prueba que ese body responde 202.
    const input: NewRunInput = { instance: 'ieee14', proposer: 'qaoa' };

    // Act & Assert — el 422 vivo del checkpoint 2 muere por contrato
    expect(toCreateRunBody(input)).toEqual(MISSION_CONTRACT_FIXTURE);
  });

  it('resuelve gw y greedy contra blite.graphs.maxcut (mismo manifest, method distingue)', () => {
    // `blite.graphs.maxcut` (capabilities/graphs/src/blite_cap_graphs/tool.py)
    // es la ÚNICA capability real de max-cut clásico instalada — cubre
    // ambos métodos (`method: "gw" | "greedy"`, default "greedy") bajo un
    // solo capability_id; no existen `blite.solvers.goemans_williamson` ni
    // `blite.solvers.greedy` en el registry (decisiones #95-#98).
    expect(toCreateRunBody({ instance: 'ieee9', proposer: 'gw' }).capability_id).toBe(
      'blite.graphs.maxcut'
    );
    expect(toCreateRunBody({ instance: 'ieee30', proposer: 'greedy' }).capability_id).toBe(
      'blite.graphs.maxcut'
    );
  });
});

describe('createRun (MVP task 2)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.mocked(gatewayClient.postRun).mockReset();
  });

  it('modo demo (sin VITE_API_URL): devuelve DEMO_RUN_ID sin llamar a postRun', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', undefined);

    // Act
    const result = await createRun({ instance: 'ieee14', proposer: 'qaoa' });

    // Assert
    expect(result).toEqual({ runId: DEMO_RUN_ID });
    expect(gatewayClient.postRun).not.toHaveBeenCalled();
  });

  it('modo live: llama a postRun con el body mapeado y devuelve el run_id de la respuesta', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.mocked(gatewayClient.postRun).mockResolvedValueOnce({
      success: true,
      data: { run_id: 'run-999' },
      error: null
    });
    const input: NewRunInput = { instance: 'ieee30', proposer: 'greedy' };

    // Act
    const result = await createRun(input);

    // Assert
    expect(gatewayClient.postRun).toHaveBeenCalledWith(toCreateRunBody(input));
    expect(result).toEqual({ runId: 'run-999' });
  });

  it('modo live: rechaza cuando postRun devuelve success:false', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.mocked(gatewayClient.postRun).mockResolvedValueOnce({
      success: false,
      data: null,
      error: 'Gateway error: 500 Internal Server Error'
    });

    // Act & Assert
    await expect(createRun({ instance: 'ieee14', proposer: 'qaoa' })).rejects.toThrow(
      'Gateway error: 500 Internal Server Error'
    );
  });

  it('modo live: rechaza con mensaje por defecto cuando la respuesta no trae error', async () => {
    // Arrange
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.mocked(gatewayClient.postRun).mockResolvedValueOnce({
      success: false,
      data: null,
      error: null
    });

    // Act & Assert
    await expect(createRun({ instance: 'ieee14', proposer: 'qaoa' })).rejects.toThrow(
      'No se pudo crear el run'
    );
  });
});
