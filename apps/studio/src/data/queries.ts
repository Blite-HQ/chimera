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

import { getCertificate } from '../gatewayClient';
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
  projectedEventSchema,
  rvspSchema,
  stepDetailSchema,
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
 * Rama demo/live (D1, honestidad de modo): hoy chimera_api solo expone
 * `POST /runs`, `GET /runs/{id}/certificate` y `GET /runs/{id}/events`
 * (SSE) — no hay `GET /runs` (lista), así que en vivo esto es "nada
 * todavía", nunca el fixture (D3/D4 lo cablean cuando el endpoint exista).
 * Exportada por separado, mismo patrón que loadCertificate, para poder
 * testear la selección de rama sin fabricar un QueryFunctionContext.
 */
export async function loadRunSummaries(): Promise<readonly RunSummary[]> {
  if (isLiveMode()) {
    return [];
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

/** Rama demo/live — sin `GET /artifacts` todavía (ver loadRunSummaries). */
export async function loadArtifacts(): Promise<readonly ProjectArtifact[]> {
  if (isLiveMode()) {
    return [];
  }
  return deriveArtifacts(EXAMPLE_CERTIFICATE);
}

/** Artifacts del proyecto — deliverables del certificado, con procedencia. */
export function artifactsQueryOptions() {
  return queryOptions({
    queryKey: ['artifacts'] as const,
    queryFn: loadArtifacts
  });
}

/** Rama demo/live — sin `GET /knowledge` todavía (ver loadRunSummaries). */
export async function loadKnowledge(): Promise<readonly KnowledgeClaim[]> {
  if (isLiveMode()) {
    return [];
  }
  return deriveKnowledge(EXAMPLE_CERTIFICATE);
}

/** Knowledge del proyecto — conclusiones verificadas acumuladas. */
export function knowledgeQueryOptions() {
  return queryOptions({
    queryKey: ['knowledge'] as const,
    queryFn: loadKnowledge
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

/** Rama demo/live — sin `GET /step-evidence` todavía (ver loadRunSummaries). */
export async function loadStepEvidence(): Promise<Record<string, StepDetail>> {
  if (isLiveMode()) {
    return {};
  }
  return z.record(z.string(), stepDetailSchema).parse(STEP_EVIDENCE);
}

export function stepEvidenceQueryOptions(runId: string) {
  return queryOptions({
    queryKey: ['runs', runId, 'step-evidence'] as const,
    queryFn: loadStepEvidence
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

/** Rama demo/live — sin `GET /ablation` todavía (ver loadRunSummaries). */
export async function loadAblation(): Promise<readonly AblationMetric[]> {
  if (isLiveMode()) {
    return [];
  }
  return z.array(ablationMetricSchema).parse(ABLATION_METRICS);
}

export function ablationQueryOptions(runId: string) {
  return queryOptions({
    queryKey: ['runs', runId, 'ablation'] as const,
    queryFn: loadAblation
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
