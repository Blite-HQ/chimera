/**
 * Gateway client — the ONLY egress point for the Chimera Studio.
 *
 * All external HTTP calls from the Studio must flow through this module.
 * This enforces Invariant 1 (gateway chokepoint) and Invariant 6 (egress
 * only by authorization) at the Studio boundary.
 *
 * <!-- enforced: apps/studio/src/gatewayClient.ts::invokeCapability -->
 */

import { apiBaseUrl } from './data/env';
import { sseProjectedEventSchema, toProjectedEvent } from './data/schemas';

import type { ProjectedEvent } from './views/types';

const GATEWAY_BASE_URL: string =
  (import.meta.env as Record<string, string>)['VITE_GATEWAY_URL'] ?? 'http://localhost:8000';

export interface GatewayRequest {
  readonly capability: string;
  readonly inputs: Readonly<Record<string, unknown>>;
}

export interface GatewayResponse<T = unknown> {
  readonly success: boolean;
  readonly data: T | null;
  readonly error: string | null;
}

/**
 * Invoke a capability through the engine gateway.
 *
 * This is the single egress function for the Studio — all capability
 * calls, regardless of feature, must go through invokeCapability().
 */
export async function invokeCapability<T = unknown>(
  request: GatewayRequest
): Promise<GatewayResponse<T>> {
  let response: Response;

  try {
    response = await fetch(`${GATEWAY_BASE_URL}/invoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });
  } catch (networkErr) {
    return {
      success: false,
      data: null,
      error: `Network error: ${networkErr instanceof Error ? networkErr.message : String(networkErr)}`
    };
  }

  if (!response.ok) {
    return {
      success: false,
      data: null,
      error: `Gateway error: ${response.status} ${response.statusText}`
    };
  }

  const body = (await response.json()) as GatewayResponse<T>;
  return body;
}

/**
 * MVP task 2 (S10) — contrato provisional de `POST /runs` (plan-01,
 * decisión pendiente de ratificar cuando aterrice runtime-api). El shape
 * exacto de `claim`/`inputs` puede cambiar; el chokepoint (INV-1) y el
 * envelope de error no.
 */
export interface CreateRunBody {
  readonly capability_id: string;
  readonly inputs: Readonly<Record<string, unknown>>;
  readonly claim: {
    readonly canonical_statement: string;
    readonly scope: Readonly<Record<string, unknown>>;
    readonly claim_type: string;
  };
  readonly max_steps?: number;
}

/**
 * Crea un run vía `POST {VITE_API_URL}/runs` (plan-01). Mismo envelope de
 * error que invokeCapability (network error / non-OK / ok) — único lugar
 * del Studio que hace este POST (INV-1).
 */
export async function postRun(body: CreateRunBody): Promise<GatewayResponse<{ run_id: string }>> {
  let response: Response;

  try {
    response = await fetch(`${apiBaseUrl()}/runs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
  } catch (networkErr) {
    return {
      success: false,
      data: null,
      error: `Network error: ${networkErr instanceof Error ? networkErr.message : String(networkErr)}`
    };
  }

  if (!response.ok) {
    return {
      success: false,
      data: null,
      error: `Gateway error: ${response.status} ${response.statusText}`
    };
  }

  const parsed = (await response.json()) as GatewayResponse<{ run_id: string }>;
  return parsed;
}

/**
 * MVP task 1 (S10) — el conjunto de tipos de evento que emite chimera_api
 * en `GET /runs/{id}/events` (freeze §9 · `chimera_api.projection`). El
 * wire nombra el evento SSE (`event: {type}`), no el genérico `message`,
 * así que no hay `onmessage` que capture todo: se registra un listener por
 * tipo conocido y todos apuntan al mismo parser.
 */
const KNOWN_RUN_EVENT_TYPES = [
  'run.started',
  'capability.job.invoked',
  'capability.job.completed',
  'verification.completed',
  'claim.emitted',
  'run.completed',
  'run.failed',
  'run.cancelled'
] as const;

export interface RunEventStreamHandlers {
  readonly onEvent: (event: ProjectedEvent) => void;
  readonly onError?: (message: string) => void;
}

export interface RunEventStreamSubscription {
  readonly close: () => void;
}

function toErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/**
 * Abre el SSE real de un run (`GET {VITE_API_URL}/runs/{id}/events`,
 * freeze §9) y transmite cada frame ya parseado (sseProjectedEventSchema) y
 * mapeado (toProjectedEvent) a quien escuche. Único lugar del Studio que
 * construye un EventSource (INV-1). Reanudación: el EventSource nativo
 * reenvía `Last-Event-ID` con el último `id:` visto — no hay catch-up que
 * reimplementar acá.
 */
export function openRunEventStream(
  runId: string,
  handlers: RunEventStreamHandlers
): RunEventStreamSubscription {
  const base = apiBaseUrl();
  if (base === undefined) {
    handlers.onError?.('VITE_API_URL no está configurada — no se puede abrir el stream en vivo');
    return { close: () => {} };
  }

  const source = new EventSource(`${base}/runs/${encodeURIComponent(runId)}/events`);

  const handleFrame = (event: MessageEvent<string>): void => {
    try {
      const wire = sseProjectedEventSchema.parse(JSON.parse(event.data));
      handlers.onEvent(toProjectedEvent(wire));
    } catch (error) {
      handlers.onError?.(toErrorMessage(error));
    }
  };

  for (const type of KNOWN_RUN_EVENT_TYPES) {
    source.addEventListener(type, handleFrame);
  }
  source.onerror = () => {
    handlers.onError?.('SSE connection error');
  };

  return {
    close: () => {
      source.close();
    }
  };
}
