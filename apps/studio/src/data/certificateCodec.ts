/**
 * certificateCodec.ts (task 3, plan §03-frontend-studio) — el ÚNICO
 * decoder wire→DsseEnvelope, DRYed out of `fixtures/certificate.ts` para
 * que el fixture (demo) Y el live path (`GET /runs/{id}/certificate`, vía
 * gatewayClient.getCertificate) compartan un solo mapping (nota 18 §2.3 +
 * freeze §7 — reobra ET-9, vocabulario clase+AL).
 *
 * `wire` es `unknown` a propósito: en modo live es la respuesta HTTP
 * cruda (externa/untrusted — F3), en modo demo es el JSON del fixture. En
 * ambos casos se valida con `wireEnvelopeSchema` ANTES de decodificar —
 * un wire corrupto explota acá (Zod), no en un render de CertificateView.
 * El payload base64 se decodifica y se mapea explícitamente campo por
 * campo (run_id → runId, titular_level → titularLevel, etc.) en vez de un
 * deep-camelcase genérico: el contrato del predicate está congelado
 * (freeze §7), así que el mapping explícito es más auditable que una
 * transformación recursiva genérica.
 */

import { wireEnvelopeSchema } from './schemas';

import type {
  AssuranceLevel,
  CertificateAttestation,
  DsseEnvelope,
  TrustCertificateStatement,
  Verdict
} from '../views/types';

interface RawAttestation {
  readonly verifier_id: string;
  readonly verifier_class: string;
  readonly anchor_kind?: string;
  readonly level: string;
  readonly verdict: string;
  readonly independence_group: string;
  readonly claim_digest: string;
  readonly issued_at: string;
}

interface RawConclusion {
  readonly claim_digest: string;
  readonly canonical_statement: string;
  readonly scope: Readonly<Record<string, string>>;
  readonly verdict: string;
  readonly level: string;
  readonly claim_type?: string;
}

interface RawStatement {
  readonly _type: string;
  readonly subject: readonly {
    readonly name: string;
    readonly digest: { readonly sha256: string };
  }[];
  readonly predicateType: string;
  readonly predicate: {
    readonly run_id: string;
    readonly actor: string;
    readonly provenance_hash: string;
    readonly conclusions: readonly RawConclusion[];
    readonly titular_level: string;
    readonly assumptions: readonly {
      readonly statement: string;
      readonly ref?: { readonly name: string; readonly digest: string };
    }[];
    readonly deliverables: readonly {
      readonly artifact_ref: string;
      readonly digest: string;
    }[];
    readonly unanchored_steps: number;
    readonly policy_digest: string;
    readonly calculus_version: string;
    readonly valid_as_of: string;
    readonly revocation: string;
    readonly attestations: readonly RawAttestation[];
  };
}

function decodeBase64Utf8(base64: string): string {
  const binary = atob(base64);
  const bytes = Uint8Array.from(binary, char => char.charCodeAt(0));
  return new TextDecoder('utf-8').decode(bytes);
}

function mapAttestation(raw: RawAttestation): CertificateAttestation {
  return {
    verifierId: raw.verifier_id,
    verifierClass: raw.verifier_class,
    anchorKind: raw.anchor_kind,
    level: raw.level as AssuranceLevel,
    verdict: raw.verdict as Verdict,
    independenceGroup: raw.independence_group,
    claimDigest: raw.claim_digest,
    issuedAt: raw.issued_at
  };
}

function mapStatement(raw: RawStatement): TrustCertificateStatement {
  const { predicate } = raw;
  return {
    _type: raw._type,
    subject: raw.subject,
    predicateType: raw.predicateType,
    predicate: {
      runId: predicate.run_id,
      actor: predicate.actor,
      provenanceHash: predicate.provenance_hash,
      conclusions: predicate.conclusions.map(conclusion => ({
        claimDigest: conclusion.claim_digest,
        canonicalStatement: conclusion.canonical_statement,
        scope: conclusion.scope,
        verdict:
          conclusion.verdict as TrustCertificateStatement['predicate']['conclusions'][number]['verdict'],
        level: conclusion.level as AssuranceLevel,
        claimType: conclusion.claim_type
      })),
      titularLevel: predicate.titular_level as AssuranceLevel,
      assumptions: predicate.assumptions,
      deliverables: predicate.deliverables.map(deliverable => ({
        artifactRef: deliverable.artifact_ref,
        digest: deliverable.digest
      })),
      unanchoredSteps: predicate.unanchored_steps,
      policyDigest: predicate.policy_digest,
      calculusVersion: predicate.calculus_version,
      validAsOf: predicate.valid_as_of,
      revocation: predicate.revocation,
      attestations: predicate.attestations.map(mapAttestation)
    }
  };
}

/**
 * Decodifica un wire DSSE (`{payloadType, payload: base64, signatures}`)
 * en el `DsseEnvelope` camelCase que consumen las vistas. Único punto de
 * entrada del módulo — fixture y live path lo comparten (task 3).
 */
export function decodeEnvelope(wire: unknown): DsseEnvelope {
  const parsedWire = wireEnvelopeSchema.parse(wire);
  const decodedPayload = decodeBase64Utf8(parsedWire.payload);
  const statement = JSON.parse(decodedPayload) as RawStatement;
  return {
    payloadType: parsedWire.payloadType,
    payload: mapStatement(statement),
    rawPayload: JSON.parse(decodedPayload) as unknown,
    signatures: parsedWire.signatures
  };
}
