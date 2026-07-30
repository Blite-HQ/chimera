/**
 * Proyecciones de PROYECTO (carril 2 F2): funciones puras que derivan las
 * filas de Runs / Artifacts / Knowledge desde el certificado (bundle real)
 * y los eventos del run. Viven en data/ porque son forma-de-datos, no
 * presentación; las vistas las reciben ya proyectadas vía queryOptions.
 */

import { LEVEL_ORDER } from '@chimera/assurance-ui';

import type {
  DsseEnvelope,
  KnowledgeClaim,
  ProjectArtifact,
  ProjectedEvent,
  RunStatus,
  RunSummary,
  TrustCertificateStatement
} from '../views/types';

type Predicate = TrustCertificateStatement['predicate'];

/**
 * Clase del attestation más fuerte amarrado al claim — es la clase que
 * acompaña al AL titular en los badges de proyecto.
 */
function titularClassFor(predicate: Predicate, claimDigest: string): string {
  const bound = predicate.attestations.filter(
    attestation => attestation.claimDigest === claimDigest
  );
  const strongest = [...bound].sort((a, b) => LEVEL_ORDER[b.level] - LEVEL_ORDER[a.level])[0];
  return strongest?.verifierClass ?? 'formal_exact';
}

/**
 * Auditoría Fase 2 (`docs/mvp/decisiones.md` §"Análisis para discusión"
 * punto 3, extensión aditiva) — mirror EXACTO de
 * `api/src/chimera_api/reads.py::_run_status`: el PRIMER evento terminal
 * (`run.completed`/`run.failed`/`run.cancelled`, freeze §2
 * `TERMINAL_RUN_EVENTS`) que aparece en el stream decide el status; sin
 * ninguno todavía, `en_curso`. `run.completed` conserva su cómputo previo
 * (sin cambio de comportamiento para el camino ya congelado).
 */
const STATUS_BY_TERMINAL_EVENT_TYPE: Readonly<Record<string, RunStatus>> = {
  'run.completed': 'completado',
  'run.failed': 'fallido',
  'run.cancelled': 'cancelado'
};

function deriveStatus(events: readonly ProjectedEvent[]): RunStatus {
  for (const event of events) {
    const status = STATUS_BY_TERMINAL_EVENT_TYPE[event.type];
    if (status !== undefined) {
      return status;
    }
  }
  return 'en_curso';
}

export function deriveRunSummary(
  envelope: DsseEnvelope,
  events: readonly ProjectedEvent[]
): RunSummary {
  const { predicate } = envelope.payload;
  const conclusion = predicate.conclusions[0];
  const lastEvent = events[events.length - 1];
  const status = deriveStatus(events);
  const isTerminal = status !== 'en_curso';

  return {
    runId: predicate.runId,
    status,
    conclusion: conclusion?.canonicalStatement ?? 'Sin conclusión registrada',
    verdict: conclusion?.verdict ?? 'inconclusive',
    titularLevel: predicate.titularLevel,
    titularClass: conclusion ? titularClassFor(predicate, conclusion.claimDigest) : 'formal_exact',
    eventsCount: events.length,
    actor: predicate.actor,
    completedAt: isTerminal ? lastEvent?.occurredAt : undefined
  };
}

export function deriveArtifacts(envelope: DsseEnvelope): readonly ProjectArtifact[] {
  const { predicate } = envelope.payload;
  const conclusion = predicate.conclusions[0];

  return predicate.deliverables.map(deliverable => ({
    artifactRef: deliverable.artifactRef,
    digest: deliverable.digest,
    runId: predicate.runId,
    titularLevel: predicate.titularLevel,
    titularClass: conclusion ? titularClassFor(predicate, conclusion.claimDigest) : 'formal_exact',
    verdict: conclusion?.verdict ?? 'inconclusive',
    issuedAt: predicate.validAsOf
  }));
}

export function deriveKnowledge(envelope: DsseEnvelope): readonly KnowledgeClaim[] {
  const { predicate } = envelope.payload;

  return predicate.conclusions.map(conclusion => ({
    statement: conclusion.canonicalStatement,
    scope: conclusion.scope,
    verdict: conclusion.verdict,
    level: conclusion.level,
    titularClass: titularClassFor(predicate, conclusion.claimDigest),
    runId: predicate.runId,
    validAsOf: predicate.validAsOf
  }));
}
