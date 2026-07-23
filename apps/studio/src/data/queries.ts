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

import { ABLATION_METRICS } from '../fixtures/ablationMetrics';
import { EXAMPLE_CERTIFICATE, EXAMPLE_CERTIFICATE_WIRE } from '../fixtures/certificate';
import { RUN_EVENTS } from '../fixtures/runEvents';
import { STEP_EVIDENCE } from '../fixtures/stepEvidence';
import {
  ablationMetricSchema,
  projectedEventSchema,
  stepDetailSchema,
  wireEnvelopeSchema
} from './schemas';

import type { DsseEnvelope } from '../views/types';

/** El run del caso demo (mismo id del bundle de ejemplo, freeze §7). */
export const DEMO_RUN_ID = '8f2c1a9b';

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

export function certificateQueryOptions(runId: string) {
  return queryOptions({
    queryKey: ['runs', runId, 'certificate'] as const,
    queryFn: async (): Promise<CertificateResource> => ({
      envelope: EXAMPLE_CERTIFICATE,
      wire: wireEnvelopeSchema.parse(EXAMPLE_CERTIFICATE_WIRE)
    })
  });
}

export function ablationQueryOptions(runId: string) {
  return queryOptions({
    queryKey: ['runs', runId, 'ablation'] as const,
    queryFn: async () => z.array(ablationMetricSchema).parse(ABLATION_METRICS)
  });
}
