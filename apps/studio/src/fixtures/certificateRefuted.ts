/**
 * fixtures/certificateRefuted.ts (task 3) — un certificado REFUTADO
 * (freeze §7): la conclusión no fue verificada, fue contradicha por un
 * verificador formal exacto (CP-SAT). Esto es el CLIMAX de la demo — la
 * refutación tiene que leerse con la MISMA dignidad que un pass: mismo
 * layout de CertificateView (nivel 1 abre con el alcance, mismo
 * AssuranceBadge, mismo nivel titular expuesto), nada oculto ni
 * disculpado.
 *
 * `titularLevel: 'AL0'` (freeze §4 — el mínimo del camino crítico cuando
 * la única conclusión del run fue refutada: sin fuerza que reclamar).
 * `conclusions[0].verdict: 'refuted'` es el ConclusionVerdict de
 * `@chimera/assurance-ui` (packages/assurance-ui/src/assurance.ts) —
 * `conclusionTone('refuted') === 'fail'`. El attestation ligado usa el
 * `Verdict` equivalente ('fail', no 'refuted' — son vocabularios
 * distintos: Verdict es pass/fail/inconclusive a nivel attestation,
 * ConclusionVerdict es verified/refuted/inconclusive/not_required_declared
 * a nivel conclusión — el fixture real (certificate.example.json) sigue
 * el mismo patrón: attestation pass ↔ conclusion verified).
 *
 * Envelope decodificado literal (no wire+decodeEnvelope): el propósito es
 * probar el RENDER de CertificateView con una refutación, no volver a
 * ejercer el codec — eso ya lo cubre certificateCodec.test.ts contra
 * EXAMPLE_CERTIFICATE_WIRE.
 */

import type { DsseEnvelope } from '../views/types';

const RUN_ID = '9a1c3f0d';
const CLAIM_DIGEST = 'c3a9f1e0b6d4a27185f0e9d6c4b3a2918f7e6d5c4b3a2918f7e6d5c4b3a2918f';
const POLICY_DIGEST = 'f8a8fb05b36918cd4ca7d71eea90097aa2fc10188b30c34a69f51ef4533f804';
const PROVENANCE_HASH = '3dff6ad4c529b9005d7e5ebea260ff643bae06ca31ea66bebd382939c6d1670';

export const REFUTED_CERTIFICATE: DsseEnvelope = {
  payloadType: 'application/vnd.blite.trust-certificate+json',
  payload: {
    _type: 'https://blite.dev/Statement/v1',
    subject: [{ name: `run:${RUN_ID}`, digest: { sha256: PROVENANCE_HASH } }],
    predicateType: 'https://blite.dev/TrustCertificate/v1',
    predicate: {
      runId: RUN_ID,
      actor: 'user:dylan',
      provenanceHash: PROVENANCE_HASH,
      conclusions: [
        {
          claimDigest: CLAIM_DIGEST,
          canonicalStatement: 'La partición propuesta de ieee14 NO es óptima — refutada por CP-SAT',
          scope: { instance: 'ieee14', problem: 'islanding-partition', constraints: 'declared-v1' },
          verdict: 'refuted',
          level: 'AL0',
          claimType: 'solution'
        }
      ],
      titularLevel: 'AL0',
      assumptions: [
        {
          statement: 'Se verifica contra anclas declaradas, no contra la realidad última (SC3)',
          ref: { name: 'verification-default.yaml', digest: POLICY_DIGEST }
        }
      ],
      deliverables: [{ artifactRef: 'partition.json', digest: PROVENANCE_HASH }],
      unanchoredSteps: 0,
      policyDigest: POLICY_DIGEST,
      calculusVersion: 'cal-2.4',
      validAsOf: '2026-07-23T09:00:00.000000Z',
      revocation: 'none',
      attestations: [
        {
          verifierId: 'ortools-cpsat',
          verifierClass: 'formal_exact',
          anchorKind: 'solver',
          level: 'AL0',
          verdict: 'fail',
          independenceGroup: 'leg-formal',
          claimDigest: CLAIM_DIGEST,
          issuedAt: '2026-07-23T09:00:00.000000Z'
        }
      ]
    }
  },
  rawPayload: {
    _type: 'https://blite.dev/Statement/v1',
    predicate: {
      run_id: RUN_ID,
      titular_level: 'AL0',
      conclusions: [{ claim_digest: CLAIM_DIGEST, verdict: 'refuted' }]
    }
  },
  signatures: [{ keyid: 'certificate:v1-example', sig: 'refutation-fixture-signature==' }]
};
