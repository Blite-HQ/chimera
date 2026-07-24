/**
 * MVP task 2 (S10, plan §03-frontend-studio) — puente de datos para
 * "Nuevo run": la vista (NewRunView) solo llama a `useCreateRun`/`createRun`,
 * jamás a `postRun`/`gatewayClient` directo (F3). El `POST /runs` real
 * todavía no existe en chimera_api (es dominio runtime-api) — modo demo
 * corta a `DEMO_RUN_ID` sin red; modo live arma el body del contrato
 * plan-01 y lo manda por `postRun` (INV-1: el fetch vive solo ahí).
 *
 * `capability_id`/`claim` son PROVISIONALES — el shape exacto se ratifica
 * cuando aterriza runtime-api (decisiones.md). El flip fixtures→live es
 * este archivo + gatewayClient.postRun, ya escritos y testeados.
 */

import { useMutation } from '@tanstack/react-query';

import { postRun } from '../gatewayClient';
import { isLiveMode } from './env';
import { DEMO_RUN_ID } from './queries';

import type { CreateRunBody } from '../gatewayClient';
import type { NewRunInput } from '../views/types';
import type { UseMutationResult } from '@tanstack/react-query';

export type { NewRunInput };

/** Proposer del form → capability_id del contrato plan-01 (provisional). */
const PROPOSER_CAPABILITY: Readonly<Record<string, string>> = {
  qaoa: 'blite.solvers.qaoa',
  gw: 'blite.solvers.goemans_williamson',
  greedy: 'blite.solvers.greedy'
};

export interface CreateRunResult {
  readonly runId: string;
}

/** Mapper puro: NewRunInput (form) → CreateRunBody (contrato plan-01). */
export function toCreateRunBody(input: NewRunInput): CreateRunBody {
  return {
    capability_id: PROPOSER_CAPABILITY[input.proposer] ?? input.proposer,
    inputs: { instance: input.instance },
    claim: {
      canonical_statement: `Partición controlada óptima de ${input.instance}`,
      scope: { instance: input.instance },
      claim_type: 'optimality'
    }
  };
}

export async function createRun(input: NewRunInput): Promise<CreateRunResult> {
  if (!isLiveMode()) {
    return { runId: DEMO_RUN_ID };
  }

  const res = await postRun(toCreateRunBody(input));
  if (!res.success || !res.data) {
    throw new Error(res.error ?? 'No se pudo crear el run');
  }
  return { runId: res.data.run_id };
}

export function useCreateRun(): UseMutationResult<CreateRunResult, Error, NewRunInput> {
  return useMutation({ mutationFn: createRun });
}
