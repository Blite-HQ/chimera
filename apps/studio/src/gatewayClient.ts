/**
 * Gateway client — the ONLY egress point for the Chimera Studio.
 *
 * All external HTTP calls from the Studio must flow through this module.
 * This enforces Invariant 1 (gateway chokepoint) and Invariant 6 (egress
 * only by authorization) at the Studio boundary.
 *
 * <!-- enforced: apps/studio/src/gatewayClient.ts::GatewayResponse -->
 */

import { apiBaseUrl } from './data/env';
import { sseProjectedEventSchema, toProjectedEvent } from './data/schemas';

import type { ProjectedEvent } from './views/types';

/**
 * La forma que devuelve TODA función de egress de este módulo — el ancla del
 * Invariante 1 del lado Studio (`docs/invariants.md`): si una respuesta del
 * exterior no pasó por acá, no tiene esta forma.
 */
export interface GatewayResponse<T = unknown> {
  readonly success: boolean;
  readonly data: T | null;
  readonly error: string | null;
}

/**
 * Nota de la ruta `/invoke` (hallazgo 7 · decidido en P-rt, 2026-08-02).
 *
 * Este módulo exportaba `invokeCapability()`, que posteaba a `POST /invoke`.
 * Esa ruta **nunca existió en el servidor**: el Studio la llamaba (solo desde
 * su propio test — ningún componente la usaba), nginx la proxeaba, y nadie la
 * servía. Se MATÓ en vez de implementarla, con causa:
 *
 * implementarla habría creado una SEGUNDA vía de invocar una capability que
 * evade run, claim y verificación — un resultado sin evidencia ni certificado,
 * exactamente lo que la doctrina fail-closed prohíbe («jamás un run sin
 * verificación», decisión #7). El camino real y único es `POST /runs`.
 *
 * El Invariante 1 (gateway como chokepoint) sigue intacto: lo garantiza que
 * TODO egress del Studio pase por ESTE módulo, no una función en particular.
 *
 * **En cascada:** `VITE_GATEWAY_URL` (y su constante `GATEWAY_BASE_URL`) existían
 * ÚNICAMENTE para armar esa URL. Todas las funciones vivas usan `apiBaseUrl`
 * (`./data/env`, gobernada por `VITE_API_URL`), así que la variable quedó sin
 * lector y se retira también — de compose.yaml, studio.Dockerfile y
 * .env.example. Una env var documentada que nadie lee es documentación de una
 * mentira.
 */

/**
 * Contrato claim-first de `POST /runs` (plan-01, decisión #6) — INTACTO:
 * exige el claim completo (instance+assignment) en el request. El Studio ya
 * no lo emite desde el form (ver CreateRunMissionBody), pero el tipo se
 * conserva porque el endpoint sigue aceptándolo (compat Nivel-1 total).
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
 * Decisión #91 — body misión-first de `POST /runs` (endpoints-studio.md
 * §"POST /runs — modo misión"): alternativa discriminada por presencia de
 * campo (`mission` vs `claim`). Sin instance/assignment — los claims los
 * emiten los sub-runs/steps del harness. Espejo del Pydantic
 * `MissionRequest` (chimera_api.runs); el fixture de costura vive en
 * src/fixtures/contract/endpoints/post-runs-mission.json.
 */
export interface CreateRunMissionBody {
  readonly mission: string;
  readonly instance_id?: string;
  readonly capability_id?: string;
  readonly max_turns?: number;
  readonly budget?: {
    readonly tokens?: number;
    readonly cost_usd?: number;
  };
}

/**
 * Crea un run vía `POST {VITE_API_URL}/runs` — acepta cualquiera de los dos
 * bodies del contrato (claim-first o misión-first). Mismo envelope de error
 * que invokeCapability (network error / non-OK / ok) — único lugar del
 * Studio que hace este POST (INV-1).
 */
export async function postRun(
  body: CreateRunBody | CreateRunMissionBody
): Promise<GatewayResponse<{ run_id: string }>> {
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
 * D3 — GET compartido para las rutas de lectura de `chimera_api`
 * (`docs/specs/endpoints-studio.md`): el body de la respuesta ES el wire
 * crudo (lista u objeto snake_case), no un GatewayResponse ya envuelto —
 * el envelope de éxito/error lo arma ESTE cliente, no el server (mismo
 * contrato que getCertificate). Único helper interno que arma el
 * fetch/try-catch/ok-check compartido por getCertificate/getRuns/
 * getArtifacts/getKnowledge/getStepEvidence/getAblation (DRY — repetir
 * este boilerplate 6 veces sería el mismo bug arreglado 6 veces distintas).
 */
async function fetchWireGet<T>(url: string): Promise<GatewayResponse<T>> {
  let response: Response;

  try {
    response = await fetch(url);
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

  const data = (await response.json()) as T;
  return { success: true, data, error: null };
}

/**
 * Task 3 (S10) — `GET {VITE_API_URL}/runs/{id}/certificate` (freeze §7): el
 * cuerpo de la respuesta ES el wire DSSE crudo (`{payloadType, payload,
 * signatures}`). Único lugar del Studio que hace este GET (INV-1); el
 * mapeo del wire vive en data/certificateCodec.ts, no acá.
 */
export async function getCertificate(runId: string): Promise<GatewayResponse<unknown>> {
  return fetchWireGet(`${apiBaseUrl()}/runs/${encodeURIComponent(runId)}/certificate`);
}

/**
 * D3 — `GET {VITE_API_URL}/runs` (endpoints-studio.md tabla, fila 1):
 * `RunSummary[]` wire snake_case. Único lugar del Studio que hace este GET
 * (INV-1); la validación Zod + el mapeo a `RunSummary` viven en
 * data/schemas.ts + data/queries.ts, no acá.
 */
export async function getRuns(): Promise<GatewayResponse<unknown>> {
  return fetchWireGet(`${apiBaseUrl()}/runs`);
}

/**
 * D3 — `GET {VITE_API_URL}/runs/{id}/artifacts` (tabla, fila 2):
 * `ProjectArtifact[]` wire snake_case.
 */
export async function getArtifacts(runId: string): Promise<GatewayResponse<unknown>> {
  return fetchWireGet(`${apiBaseUrl()}/runs/${encodeURIComponent(runId)}/artifacts`);
}

/**
 * D3 — `GET {VITE_API_URL}/runs/{id}/knowledge` (tabla, fila 3):
 * `KnowledgeClaim[]` wire snake_case.
 */
export async function getKnowledge(runId: string): Promise<GatewayResponse<unknown>> {
  return fetchWireGet(`${apiBaseUrl()}/runs/${encodeURIComponent(runId)}/knowledge`);
}

/**
 * D3 — `GET {VITE_API_URL}/runs/{id}/steps/{stepId}/evidence` (tabla, fila
 * 4): `StepDetail` wire snake_case, con `capability_id`/`input_digest`/
 * `output_digest` posiblemente `null` y `attestations` posiblemente `[]`
 * en runs reales (E1 aún no atribuye step_id) — honesto, no fabricado.
 */
export async function getStepEvidence(
  runId: string,
  stepId: string
): Promise<GatewayResponse<unknown>> {
  return fetchWireGet(
    `${apiBaseUrl()}/runs/${encodeURIComponent(runId)}/steps/${encodeURIComponent(stepId)}/evidence`
  );
}

/**
 * D3 — `GET {VITE_API_URL}/runs/{id}/ablation` (tabla, fila 5):
 * `AblationMetric[]` wire snake_case.
 */
export async function getAblation(runId: string): Promise<GatewayResponse<unknown>> {
  return fetchWireGet(`${apiBaseUrl()}/runs/${encodeURIComponent(runId)}/ablation`);
}

/**
 * Nivel-1 task 1 (S10) — el conjunto de tipos de evento que emite chimera_api
 * en `GET /runs/{id}/events` (freeze §9 · `chimera_api.projection`). El
 * wire nombra el evento SSE (`event: {type}`), no el genérico `message`,
 * así que no hay `onmessage` que capture todo: se registra un listener por
 * tipo conocido y todos apuntan al mismo parser.
 *
 * D3 (`docs/specs/endpoints-studio.md` §"Discrepancia de vocabulario") —
 * pin freeze §3/§14: el evento de provenance:pre es `capability.job.submitted`
 * (NUNCA `.invoked`, que era el nombre desalineado que este Studio escuchaba
 * antes). Mientras el listener registrado no coincida con el nombre real que
 * emite el SSE, ese frame puntual se pierde en silencio — el resto del
 * stream sigue funcionando.
 */
export const KNOWN_RUN_EVENT_TYPES = [
  // Auditoría Fase 2 (2026-07-29): el vocabulario COMPLETO que execute_run
  // emite — run.created, run.step.* y capability.job.failed faltaban y el
  // timeline en vivo perdía esos frames en silencio (mostraba 2 de 5
  // eventos de un run fallido). replay.divergence (A5) entra por lo mismo.
  'run.created',
  'run.started',
  'run.step.started',
  'run.step.completed',
  'run.step.failed',
  'capability.job.submitted',
  'capability.job.completed',
  'capability.job.failed',
  'verification.completed',
  'claim.emitted',
  'replay.divergence',
  // D6 (decisión #93) — el plan como artefacto del stream (harness-agentico.md
  // §Contrato-2): sin estos listeners el SSE real nunca entrega el checklist
  // del hilo conversacional (mismo fallo silencioso que el pin de .submitted).
  'plan.created',
  'plan.item_updated',
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
