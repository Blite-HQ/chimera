/**
 * certificateCodec.test.ts (task 3) — decodeEnvelope es el ÚNICO decoder
 * wire→DsseEnvelope, compartido por el fixture (demo) y el live path
 * (GET /runs/{id}/certificate). Este test cubre el caso feliz contra el
 * mismo wire de ejemplo que consume el fixture (prueba que DRY-ear el
 * mapping no cambió el resultado) y el caso de frontera (wire externo mal
 * formado en modo live → Zod explota acá, no en un render).
 */

import { describe, expect, it } from 'vitest';

import { EXAMPLE_CERTIFICATE_WIRE } from '../fixtures/certificate';
import { decodeEnvelope } from './certificateCodec';

describe('decodeEnvelope', () => {
  it('decodifica el wire de ejemplo en un DsseEnvelope con el predicate mapeado a camelCase', () => {
    const envelope = decodeEnvelope(EXAMPLE_CERTIFICATE_WIRE);

    expect(envelope.payloadType).toBe(EXAMPLE_CERTIFICATE_WIRE.payloadType);
    expect(envelope.signatures).toEqual(EXAMPLE_CERTIFICATE_WIRE.signatures);
    expect(envelope.payload.predicate.runId).toBe('8f2c1a9b');
    expect(envelope.payload.predicate.titularLevel).toBe('AL3');
    expect(envelope.payload.predicate.conclusions).toHaveLength(1);
    expect(envelope.payload.predicate.conclusions[0]).toMatchObject({
      verdict: 'verified',
      level: 'AL3'
    });
    expect(envelope.payload.predicate.attestations).toHaveLength(2);
    expect(envelope.payload.predicate.attestations[0]).toMatchObject({
      verifierId: 'ortools-cpsat',
      verifierClass: 'formal_exact',
      level: 'AL3',
      verdict: 'pass'
    });
  });

  it('conserva el rawPayload decodificado tal cual (nivel 3 crudo)', () => {
    const envelope = decodeEnvelope(EXAMPLE_CERTIFICATE_WIRE);

    expect(envelope.rawPayload).toMatchObject({
      predicate: { run_id: '8f2c1a9b', titular_level: 'AL3' }
    });
  });

  it('lanza (Zod) cuando el wire llega sin firmas — externo/untrusted en modo live', () => {
    const malformed = {
      payloadType: 'application/vnd.blite.trust-certificate+json',
      payload: 'e30='
      // sin `signatures` — wireEnvelopeSchema exige mínimo una
    };

    expect(() => decodeEnvelope(malformed)).toThrow();
  });

  it('lanza cuando el wire no es ni siquiera un objeto', () => {
    expect(() => decodeEnvelope(null)).toThrow();
    expect(() => decodeEnvelope('not-a-wire')).toThrow();
  });
});
