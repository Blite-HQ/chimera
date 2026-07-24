/**
 * Fixture — the example DSSE-signed TrustCertificate, decoded via the
 * shared `decodeEnvelope` codec (task 3 — DRYed out of this file into
 * `data/certificateCodec.ts` so the live path, `GET /runs/{id}/certificate`,
 * decodes with the exact same mapping).
 *
 * certificate.example.json is emitted by scripts/gen-example-bundle.py in
 * real wire format (snake_case Statement fields, base64 payload, Ed25519
 * signature over the DSSE PAE) — the SAME auto-validated 7/7 bundle that
 * scripts/example-bundle.json carries, one single source.
 */

import rawEnvelopeJson from './certificate.example.json';
import { decodeEnvelope } from '../data/certificateCodec';

import type { wireEnvelopeSchema } from '../data/schemas';
import type { DsseEnvelope } from '../views/types';
import type { z } from 'zod';

export const EXAMPLE_CERTIFICATE: DsseEnvelope = decodeEnvelope(rawEnvelopeJson);

/**
 * El envelope wire tal cual (payload base64 + firma): lo que se descarga.
 * Un envelope mapeado a camelCase NO es verificable offline — los bytes del
 * payload son la fe del certificado (freeze §7).
 */
export const EXAMPLE_CERTIFICATE_WIRE: z.infer<typeof wireEnvelopeSchema> = rawEnvelopeJson;
