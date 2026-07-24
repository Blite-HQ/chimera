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
import { STEP_EVIDENCE } from '../fixtures/stepEvidence';
import { decodeEnvelope } from './certificateCodec';
import { isLiveMode } from './env';
import { deriveArtifacts, deriveKnowledge, deriveRunSummary } from './projections';
import {
  ablationMetricSchema,
  projectedEventSchema,
  stepDetailSchema,
  wireEnvelopeSchema
} from './schemas';

import type { DsseEnvelope } from '../views/types';

/** El run del caso demo (mismo id del bundle de ejemplo, freeze §7). */
export const DEMO_RUN_ID = '8f2c1a9b';

/** Runs del proyecto (carril 2 F2) — hoy proyecta el run del bundle real. */
export function runSummariesQueryOptions() {
  return queryOptions({
    queryKey: ['runs'] as const,
    queryFn: async () => {
      const events = z.array(projectedEventSchema).parse(RUN_EVENTS);
      return [deriveRunSummary(EXAMPLE_CERTIFICATE, events)];
    }
  });
}

/** Artifacts del proyecto — deliverables del certificado, con procedencia. */
export function artifactsQueryOptions() {
  return queryOptions({
    queryKey: ['artifacts'] as const,
    queryFn: async () => deriveArtifacts(EXAMPLE_CERTIFICATE)
  });
}

/** Knowledge del proyecto — conclusiones verificadas acumuladas. */
export function knowledgeQueryOptions() {
  return queryOptions({
    queryKey: ['knowledge'] as const,
    queryFn: async () => deriveKnowledge(EXAMPLE_CERTIFICATE)
  });
}

export function runEventsQueryOptions(runId: string) {
  return queryOptions({
    queryKey: ['runs', runId, 'events'] as const,
    queryFn: async () => z.array(projectedEventSchema).parse(RUN_EVENTS)
  });
}

export function stepEvidenceQueryOptions(runId: string) {
  return queryOptions({
    queryKey: ['runs', runId, 'step-evidence'] as const,
    queryFn: async () => z.record(z.string(), stepDetailSchema).parse(STEP_EVIDENCE)
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

export function ablationQueryOptions(runId: string) {
  return queryOptions({
    queryKey: ['runs', runId, 'ablation'] as const,
    queryFn: async () => z.array(ablationMetricSchema).parse(ABLATION_METRICS)
  });
}
