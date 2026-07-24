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

export function deriveRunSummary(
  envelope: DsseEnvelope,
  events: readonly ProjectedEvent[]
): RunSummary {
  const { predicate } = envelope.payload;
  const conclusion = predicate.conclusions[0];
  const lastEvent = events[events.length - 1];
  const isCompleted = events.some(event => event.type === 'run.completed');

  return {
    runId: predicate.runId,
    status: isCompleted ? 'completado' : 'en_curso',
    conclusion: conclusion?.canonicalStatement ?? 'Sin conclusión registrada',
    verdict: conclusion?.verdict ?? 'inconclusive',
    titularLevel: predicate.titularLevel,
    titularClass: conclusion ? titularClassFor(predicate, conclusion.claimDigest) : 'formal_exact',
    eventsCount: events.length,
    actor: predicate.actor,
    completedAt: isCompleted ? lastEvent?.occurredAt : undefined
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
