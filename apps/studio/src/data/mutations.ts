/**
 * Puente de datos para "Nuevo run": la vista (NewRunView) solo llama a
 * `useCreateRun`/`createRun`, jamás a `postRun`/`gatewayClient` directo
 * (F3). Modo demo corta a `DEMO_RUN_ID` sin red; modo live arma el body
 * MISIÓN-FIRST del contrato (decisión #91, endpoints-studio.md §"POST /runs
 * — modo misión") y lo manda por `postRun` (INV-1: el fetch vive solo ahí).
 *
 * El body claim-first del Nivel-1 (instance+assignment) exigía un claim que
 * el form no puede armar — era el 422 reproducido en vivo contra el gateway
 * (previo a la decisión #91). El contrato de
 * misión lo cierra: el fixture de costura single-origin
 * (`src/fixtures/contract/endpoints/post-runs-mission.json`, generado desde
 * el Pydantic `MissionRequest`) fija este body en ambos lados.
 */

import { useMutation } from '@tanstack/react-query';

import { postRun } from '../gatewayClient';
import { isLiveMode } from './env';
import { DEMO_RUN_ID } from './queries';

import type { CreateRunMissionBody } from '../gatewayClient';
import type { NewRunInput } from '../views/types';
import type { UseMutationResult } from '@tanstack/react-query';

export type { NewRunInput };

/**
 * Proposer del form → capability meta REAL del arranque de misión
 * (decisiones #95-#98, `docs/mvp/decisiones.md` §"Análisis para discusión"
 * punto 1) — IDs verificados contra los manifests instalados
 * (`capabilities/*\/src/*\/tool.py`), nunca inventados:
 *  - `qaoa` → `blite.quantum.qaoa` (capabilities/quantum).
 *  - `gw`/`greedy` → `blite.graphs.maxcut` (capabilities/graphs): la ÚNICA
 *    capability real de max-cut clásico instalada, cubre ambos métodos vía
 *    `inputs.method` ("gw" | "greedy", default "greedy") — no existen
 *    `blite.solvers.goemans_williamson` ni `blite.solvers.greedy`.
 */
const PROPOSER_CAPABILITY: Readonly<Record<string, string>> = {
  qaoa: 'blite.quantum.qaoa',
  gw: 'blite.graphs.maxcut',
  greedy: 'blite.graphs.maxcut'
};

export interface CreateRunResult {
  readonly runId: string;
}

/**
 * Mapper puro: NewRunInput (form) → CreateRunMissionBody (modo misión).
 * La misión es el encargo conversacional (product-model.md, D6) — el server
 * la journaliza como description del ítem fundacional del plan.
 */
export function toCreateRunBody(input: NewRunInput): CreateRunMissionBody {
  return {
    mission: `Particionar la red ${input.instance} en islas controladas y certificar la optimalidad del corte`,
    instance_id: input.instance,
    capability_id: PROPOSER_CAPABILITY[input.proposer] ?? input.proposer
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
