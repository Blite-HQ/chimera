import { afterEach, describe, expect, it, vi } from 'vitest';

import MISSION_CONTRACT_FIXTURE from '../fixtures/contract/endpoints/post-runs-mission.json';
import * as gatewayClient from '../gatewayClient';
import { createRun, toCreateRunBody } from './mutations';
import { DEMO_RUN_ID } from './queries';

import type { NewRunInput } from '../views/types';

vi.mock('../gatewayClient', () => ({
  postRun: vi.fn()
}));

const MISION =
  'Particionar la red ieee14 en islas controladas y certificar la optimalidad del corte';

describe('toCreateRunBody (modo misión — endpoints-studio.md)', () => {
  it('manda la misión del usuario TAL CUAL — no hay plantilla que la reescriba', () => {
    // Arrange — P3-D: el encargo lo redacta quien lo pide. La plantilla vieja
    // ("Particionar la red ${instance}…") fabricaba una misión que el usuario
    // nunca escribió y que quedaba journalizada dentro del provenance_hash.
    const input: NewRunInput = {
      mission: 'Compará QAOA contra greedy en ieee9 y decime cuál gana'
    };

    // Act
    const body = toCreateRunBody(input);

    // Assert
    expect(body).toEqual({ mission: 'Compará QAOA contra greedy en ieee9 y decime cuál gana' });
  });

  it('omite las pistas opcionales cuando no se dieron (el harness resuelve)', () => {
    const body = toCreateRunBody({ mission: MISION });

    expect(body).not.toHaveProperty('instance_id');
    expect(body).not.toHaveProperty('capability_id');
  });

  it('produce EXACTAMENTE el body del fixture de costura cuando se dan las pistas', () => {
    // El fixture lo genera scripts/gen-contract-fixtures-endpoints.py desde
    // MissionRequest (Pydantic); el API prueba que ese body responde 202.
    const input: NewRunInput = { mission: MISION, instance: 'ieee14', proposer: 'qaoa' };

    expect(toCreateRunBody(input)).toEqual(MISSION_CONTRACT_FIXTURE);
  });

  it('resuelve gw y greedy contra blite.graphs.maxcut (mismo manifest, method distingue)', () => {
    // `blite.graphs.maxcut` (capabilities/graphs/src/blite_cap_graphs/tool.py)
    // es la ÚNICA capability real de max-cut clásico instalada — cubre ambos
    // métodos bajo un solo capability_id (decisiones #95-#98).
    expect(toCreateRunBody({ mission: MISION, proposer: 'gw' }).capability_id).toBe(
      'blite.graphs.maxcut'
    );
    expect(toCreateRunBody({ mission: MISION, proposer: 'greedy' }).capability_id).toBe(
      'blite.graphs.maxcut'
    );
  });

  it('enhebra el hilo cuando viene threadId (§Contrato-4: el 409 se continúa con un run nuevo)', () => {
    const body = toCreateRunBody({ mission: 'seguimos', threadId: 'run-raiz' });

    expect(body.thread_id).toBe('run-raiz');
  });
});

describe('createRun', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.mocked(gatewayClient.postRun).mockReset();
  });

  it('en modo demo corta a DEMO_RUN_ID sin tocar la red', async () => {
    // Arrange
    vi.stubEnv('VITE_DATA_MODE', 'fixtures');

    // Act
    const result = await createRun({ mission: MISION });

    // Assert
    expect(result).toEqual({ runId: DEMO_RUN_ID });
    expect(gatewayClient.postRun).not.toHaveBeenCalled();
  });

  it('en modo live postea el body de misión y devuelve el run_id del server', async () => {
    // Arrange
    vi.stubEnv('VITE_DATA_MODE', 'live');
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.mocked(gatewayClient.postRun).mockResolvedValueOnce({
      success: true,
      data: { run_id: 'run-vivo' },
      error: null
    });

    // Act
    const result = await createRun({ mission: MISION });

    // Assert
    expect(gatewayClient.postRun).toHaveBeenCalledWith({ mission: MISION });
    expect(result).toEqual({ runId: 'run-vivo' });
  });

  it('propaga el error del gateway en vez de fabricar un run que no existe', async () => {
    // Arrange
    vi.stubEnv('VITE_DATA_MODE', 'live');
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    vi.mocked(gatewayClient.postRun).mockResolvedValueOnce({
      success: false,
      data: null,
      error: 'Gateway error: 422 Unprocessable Entity'
    });

    // Act & Assert
    await expect(createRun({ mission: MISION })).rejects.toThrow('422');
  });
});
