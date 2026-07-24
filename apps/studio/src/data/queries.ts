/**
 * queryOptions por recurso (F3) — la ÚNICA vía de datos hacia las vistas.
 *
 * Hoy cada queryFn valida y sirve fixtures (Zod en la frontera — un fixture
 * corrupto explota acá, no en un render); S10 cambia la FUENTE (gatewayClient
 * → api real) sin tocar ni las claves ni los tipos que las vistas consumen.
 * INV-1 intacto: cuando haya red, el fetch vive en gatewayClient.ts.
 */

import { queryOptions } from '@tanstack/react-query';
import { z } from 'zod';

import {
  getAblation,
  getArtifacts,
  getCertificate,
  getKnowledge,
  getRuns,
  getStepEvidence
} from '../gatewayClient';
import { ABLATION_METRICS } from '../fixtures/ablationMetrics';
import { EXAMPLE_CERTIFICATE, EXAMPLE_CERTIFICATE_WIRE } from '../fixtures/certificate';
import { RUN_EVENTS } from '../fixtures/runEvents';
import { RVSP_EXPERIMENT } from '../fixtures/rvsp';
import { STEP_EVIDENCE } from '../fixtures/stepEvidence';
import { decodeEnvelope } from './certificateCodec';
import { isLiveMode } from './env';
import { deriveArtifacts, deriveKnowledge, deriveRunSummary } from './projections';
import {
  ablationMetricSchema,
  ablationWireSchema,
  knowledgeClaimWireSchema,
  projectArtifactWireSchema,
  projectedEventSchema,
  runSummaryWireSchema,
  rvspSchema,
  stepDetailSchema,
  stepDetailWireSchema,
  toAblationMetric,
  toKnowledgeClaim,
  toProjectArtifact,
  toRunSummary,
  toStepDetail,
  wireEnvelopeSchema
} from './schemas';

import type {
  AblationMetric,
  DsseEnvelope,
  KnowledgeClaim,
  ProjectArtifact,
  ProjectedEvent,
  RunSummary,
  RvsPExperiment,
  StepDetail
} from '../views/types';

/** El run del caso demo (mismo id del bundle de ejemplo, freeze §7). */
export const DEMO_RUN_ID = '8f2c1a9b';

/**
 * Rama demo/live (D3 — E1 ya expone `GET /runs`): en vivo llama a
 * `gatewayClient.getRuns`, valida el wire (`runSummaryWireSchema`) y lo
 * mapea a `RunSummary[]` con `toRunSummary`. Cualquier `!success` (red,
 * gateway error) rechaza — surge como ErrorState, jamás un 200 fabricado;
 * `[]` es EmptyState honesto (proyecto sin runs todavía). Exportada por
 * separado, mismo patrón que loadCertificate, para poder testear la
 * selección de rama sin fabricar un QueryFunctionContext.
 */
export async function loadRunSummaries(): Promise<readonly RunSummary[]> {
  if (isLiveMode()) {
    const res = await getRuns();
    if (!res.success || res.data === null) {
      throw new Error(res.error ?? 'No se pudieron obtener los runs');
    }
    return z.array(runSummaryWireSchema).parse(res.data).map(toRunSummary);
  }
  const events = z.array(projectedEventSchema).parse(RUN_EVENTS);
  return [deriveRunSummary(EXAMPLE_CERTIFICATE, events)];
}

/** Runs del proyecto (carril 2 F2) — hoy proyecta el run del bundle real. */
export function runSummariesQueryOptions() {
  return queryOptions({
    queryKey: ['runs'] as const,
    queryFn: loadRunSummaries
  });
}

/**
 * Rama demo/live (D3 — E1 ya expone `GET /runs/{id}/artifacts`, pero la
 * ruta EXIGE un `run_id` en el path): `runId` es OPCIONAL porque hoy
 * `ArtifactsScreen` (App.tsx) es un screen de PROYECTO sin contexto de
 * run — RunDetail todavía no tiene un tab "Artifacts" que provea uno. Sin
 * `runId` en vivo: honest-empty (nunca el fixture, no hay ruta de
 * proyecto agregada). Con `runId`: llama al egress real.
 */
export async function loadArtifacts(runId?: string): Promise<readonly ProjectArtifact[]> {
  if (isLiveMode()) {
    if (runId === undefined) {
      return [];
    }
    const res = await getArtifacts(runId);
    if (!res.success || res.data === null) {
      throw new Error(res.error ?? 'No se pudieron obtener los artifacts');
    }
    return z.array(projectArtifactWireSchema).parse(res.data).map(toProjectArtifact);
  }
  return deriveArtifacts(EXAMPLE_CERTIFICATE);
}

/** Artifacts del proyecto — deliverables del certificado, con procedencia. */
export function artifactsQueryOptions(runId?: string) {
  return queryOptions({
    queryKey: ['artifacts', runId] as const,
    queryFn: () => loadArtifacts(runId)
  });
}

/** Rama demo/live (D3) — mismo patrón que loadArtifacts (runId opcional). */
export async function loadKnowledge(runId?: string): Promise<readonly KnowledgeClaim[]> {
  if (isLiveMode()) {
    if (runId === undefined) {
      return [];
    }
    const res = await getKnowledge(runId);
    if (!res.success || res.data === null) {
      throw new Error(res.error ?? 'No se pudo obtener el knowledge');
    }
    return z.array(knowledgeClaimWireSchema).parse(res.data).map(toKnowledgeClaim);
  }
  return deriveKnowledge(EXAMPLE_CERTIFICATE);
}

/** Knowledge del proyecto — conclusiones verificadas acumuladas. */
export function knowledgeQueryOptions(runId?: string) {
  return queryOptions({
    queryKey: ['knowledge', runId] as const,
    queryFn: () => loadKnowledge(runId)
  });
}

/**
 * Rama demo/live (D1 task 3) — la carrera SSE/fixture: antes este queryFn
 * parseaba el fixture SIEMPRE, mientras que en vivo `useRunEventStream`
 * escribe al MISMO query key vía setQueryData — se pisaban entre sí. En
 * vivo el SSE es el ÚNICO escritor: acá solo se siembra `[]` inicial.
 */
export async function loadRunEvents(): Promise<readonly ProjectedEvent[]> {
  if (isLiveMode()) {
    return [];
  }
  return z.array(projectedEventSchema).parse(RUN_EVENTS);
}

export function runEventsQueryOptions(runId: string) {
  return queryOptions({
    queryKey: ['runs', runId, 'events'] as const,
    queryFn: loadRunEvents,
    // Un refetch automático (foco de ventana, reconexión) NO debe borrar lo
    // que el SSE ya acumuló en el cache — el SSE es el único escritor en
    // vivo (D1 task 3).
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false
  });
}

/**
 * Rama demo/live (D3 — E1 expone `GET /runs/{id}/steps/{step_id}/evidence`,
 * POR PASO, no por run entero). Reconciliación con el consumidor
 * (`App.tsx` RunDetailScreen, `stepsQuery.data?.[stepId]` espera el mapa
 * completo): en vivo se arma el mapa pidiendo evidencia para los
 * `stepIds` YA presentes en los eventos del run (nunca se inventa un
 * stepId) — N fetches acotados al tamaño del run, correcto y simple dado
 * que E1 hoy devuelve evidencia mayormente vacía (sin over-engineering de
 * un fetch lazy por selección). Cualquier `!success` (404 de un step
 * desconocido, red) rechaza en vez de fabricar evidencia.
 */
export async function loadStepEvidence(
  runId: string,
  stepIds: readonly string[] = []
): Promise<Record<string, StepDetail>> {
  if (!isLiveMode()) {
    return z.record(z.string(), stepDetailSchema).parse(STEP_EVIDENCE);
  }
  const entries = await Promise.all(
    stepIds.map(async (stepId): Promise<readonly [string, StepDetail]> => {
      const res = await getStepEvidence(runId, stepId);
      if (!res.success || res.data === null) {
        throw new Error(res.error ?? `No se pudo obtener la evidencia del paso ${stepId}`);
      }
      return [stepId, toStepDetail(stepDetailWireSchema.parse(res.data))];
    })
  );
  return Object.fromEntries(entries);
}

export function stepEvidenceQueryOptions(runId: string, stepIds: readonly string[] = []) {
  return queryOptions({
    queryKey: ['runs', runId, 'step-evidence', stepIds] as const,
    queryFn: () => loadStepEvidence(runId, stepIds)
  });
}

export interface CertificateResource {
  /** Decodificado y mapeado para la UI (nota 18 §2.3). */
  readonly envelope: DsseEnvelope;
  /** El wire tal cual (base64+firma) — lo único descargable/verificable offline. */
  readonly wire: z.infer<typeof wireEnvelopeSchema>;
}

/**
 * Rama demo/live (task 3, S10): demo sirve el fixture (sin red); live pide
 * `GET /runs/{id}/certificate` vía gatewayClient.getCertificate — el wire
 * de la respuesta es EXTERNO/untrusted, así que se valida con
 * `wireEnvelopeSchema` antes de decodificarlo (decodeEnvelope ya lo hace,
 * pero se valida acá también para levantar el error de "no se pudo
 * obtener" antes de intentar decodificar un `data` inesperado).
 * Exportada (no inlined en el queryFn) para poder testear la selección de
 * rama mockeando `../gatewayClient` sin tener que fabricar un
 * QueryFunctionContext.
 */
export async function loadCertificate(runId: string): Promise<CertificateResource> {
  if (!isLiveMode()) {
    return {
      envelope: EXAMPLE_CERTIFICATE,
      wire: wireEnvelopeSchema.parse(EXAMPLE_CERTIFICATE_WIRE)
    };
  }

  const res = await getCertificate(runId);
  if (!res.success || res.data === null) {
    throw new Error(res.error ?? 'No se pudo obtener el certificado');
  }
  const wire = wireEnvelopeSchema.parse(res.data);
  return { envelope: decodeEnvelope(wire), wire };
}

export function certificateQueryOptions(runId: string) {
  return queryOptions({
    queryKey: ['runs', runId, 'certificate'] as const,
    queryFn: () => loadCertificate(runId)
  });
}

/**
 * Rama demo/live (D3 — E1 ya expone `GET /runs/{id}/ablation`): en vivo
 * llama al egress real, valida el wire snake_case (`ablationWireSchema`) y
 * lo mapea a `AblationMetric[]` con `toAblationMetric`.
 */
export async function loadAblation(runId: string): Promise<readonly AblationMetric[]> {
  if (isLiveMode()) {
    const res = await getAblation(runId);
    if (!res.success || res.data === null) {
      throw new Error(res.error ?? 'No se pudieron obtener las métricas de ablación');
    }
    return z.array(ablationWireSchema).parse(res.data).map(toAblationMetric);
  }
  return z.array(ablationMetricSchema).parse(ABLATION_METRICS);
}

export function ablationQueryOptions(runId: string) {
  return queryOptions({
    queryKey: ['runs', runId, 'ablation'] as const,
    queryFn: () => loadAblation(runId)
  });
}

/**
 * D5 (dataviz "r vs p") — rama demo/live: sin `GET /rvsp` todavía (ver
 * loadRunSummaries). A diferencia de los recursos en lista (`[]` vacío),
 * este es un experimento único por instancia, así que "nada todavía" en
 * vivo es `null`, no un array — el consumidor (App.tsx) lo trata igual que
 * las demás ramas vacías: EmptyState, jamás el fixture inventado.
 */
export async function loadRvsP(): Promise<RvsPExperiment | null> {
  if (isLiveMode()) {
    return null;
  }
  return rvspSchema.parse(RVSP_EXPERIMENT);
}

export function rvspQueryOptions(runId: string) {
  return queryOptions({
    queryKey: ['runs', runId, 'rvsp'] as const,
    queryFn: loadRvsP
  });
}
