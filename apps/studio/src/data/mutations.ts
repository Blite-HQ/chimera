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

import { useMutation, useQueryClient } from '@tanstack/react-query';

import {
  postApprovalResponse,
  postFile,
  postRun,
  postRunCancel,
  postRunMessage
} from '../gatewayClient';
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
 *
 * **P3-D — la plantilla murió.** Este mapper interpolaba una misión fija
 * («Particionar la red ${instance} en islas controladas…») a partir de dos
 * selects. Eso no era un default: era el Studio poniéndole palabras al
 * usuario. Y como el modo misión journaliza la misión como `description` del
 * ítem fundacional del plan —dentro del `provenance_hash`— el certificado
 * terminaba amparando un encargo que nadie escribió. Además cableaba la
 * plataforma a UN problema (partición de redes), justo lo que la generalidad
 * de esta fase existe para romper.
 *
 * Hoy la misión viaja tal cual. Las pistas se OMITEN cuando no vienen —
 * `extra="forbid"` del Pydantic acepta ausencia, no `undefined` explícito.
 */
export function toCreateRunBody(input: NewRunInput): CreateRunMissionBody {
  const capabilityId =
    input.proposer === undefined
      ? undefined
      : (PROPOSER_CAPABILITY[input.proposer] ?? input.proposer);

  return {
    mission: input.mission,
    ...(input.instance !== undefined && { instance_id: input.instance }),
    ...(capabilityId !== undefined && { capability_id: capabilityId }),
    ...(input.threadId !== undefined && { thread_id: input.threadId })
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

/**
 * P3-D — las tres acciones de conversación del run. Todas comparten la misma
 * forma: postean por `gatewayClient` (INV-1), traducen un `!success` a
 * `Error` con el TEXTO DEL SERVER (nunca uno genérico — el 409 y el 403
 * dicen cosas distintas y accionables) e invalidan lo que quedó viejo.
 *
 * En vivo el SSE es el escritor del stream, así que los eventos nuevos
 * llegan solos; la invalidación cubre el resto (`GET /runs`, cuyo `status`
 * cambia al cancelar) y el caso de un SSE caído.
 */

/** Error tipado por status, para que la UI pueda reaccionar al 409 sin parsear texto. */
export class GatewayCallError extends Error {
  readonly status: number | undefined;

  constructor(message: string, status: number | undefined) {
    super(message);
    this.name = 'GatewayCallError';
    this.status = status;
  }
}

function throwOnFailure(res: { success: boolean; error: string | null; status?: number }): void {
  if (!res.success) {
    throw new GatewayCallError(res.error ?? 'La operación no se pudo completar', res.status);
  }
}

export function useSendMessage(runId: string): UseMutationResult<void, Error, string> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (text: string) => {
      throwOnFailure(await postRunMessage(runId, text));
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['runs', runId, 'events'] });
    }
  });
}

export function useCancelRun(runId: string): UseMutationResult<void, Error, string | undefined> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (reason?: string) => {
      throwOnFailure(await postRunCancel(runId, reason));
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['runs', runId, 'events'] });
      void queryClient.invalidateQueries({ queryKey: ['runs'] });
    }
  });
}

export interface ApprovalDecision {
  readonly approvalId: string;
  readonly response: unknown;
}

export function useRespondApproval(
  runId: string
): UseMutationResult<void, Error, ApprovalDecision> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ approvalId, response }: ApprovalDecision) => {
      throwOnFailure(await postApprovalResponse(runId, approvalId, response));
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['runs', runId, 'events'] });
    }
  });
}

/**
 * P10/M24 — subir un archivo del proyecto. Invalida el listado en vez de
 * insertarlo a mano: el server decide el digest (y si el contenido ya
 * existía, no crea nada), así que la única verdad es la que él devuelve.
 */
export function useUploadFile(): UseMutationResult<void, Error, File> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      throwOnFailure(await postFile(file));
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['files'] });
    }
  });
}
