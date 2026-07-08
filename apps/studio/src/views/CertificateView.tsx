/**
 * CertificateView — nota 18 §2.3.
 *
 * Three-tier progressive disclosure, ported from `gh attestation verify`
 * (nota 18 §1.3): (1) one-line verdict, (2) compact identity table, (3)
 * collapsed raw envelope behind a toggle + a client-side-only download.
 *
 * Explicitly does NOT use transparency-log/OIDC language (no "logged at
 * index N", no "signed by workflow X via Sigstore") — this certificate is
 * verified offline against a local key, never a public log (nota 02 §1.2,
 * nota 18 §1.3 "no aplica"). The keyid is always named so the copy reads
 * as "verificado contra la llave local `{keyid}`", never implying a
 * public/third-party trust root.
 */

import React, { useState } from 'react';

import { Separator } from '@/components/ui/separator';
import { RungBadge } from '@/components/verification/RungBadge';

import type { DsseEnvelope } from './types';

export interface CertificateViewProps {
  readonly envelope: DsseEnvelope;
  readonly onDownload: () => void; // ofrece el JSON crudo como archivo — sin egress nuevo (INV-1)
}

function IdentityRow({
  label,
  value
}: {
  readonly label: string;
  readonly value: string;
}): React.ReactElement {
  return (
    <div className="flex items-center justify-between gap-4 py-1.5 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono text-foreground">{value}</span>
    </div>
  );
}

export default function CertificateView({
  envelope,
  onDownload
}: CertificateViewProps): React.ReactElement {
  const [showRaw, setShowRaw] = useState(false);
  const { predicate } = envelope.payload;
  const keyid = envelope.signatures[0]?.keyid ?? 'desconocida';

  return (
    <div className="flex flex-col gap-4">
      {/* Nivel 1 — veredicto en una línea */}
      <div className="rounded-lg border bg-card p-4">
        <p className="font-display text-base font-medium tracking-tight text-foreground">
          Certificado · escalón agregado {predicate.aggregateRung} · política {predicate.policyId}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          Verificado contra la llave local <code className="font-mono">{keyid}</code> — sin log
          público ni OIDC: la verificación es offline (nota 02).
        </p>
      </div>

      {/* Nivel 2 — tabla compacta */}
      <div className="rounded-lg border bg-card p-4">
        <IdentityRow label="run_id" value={predicate.runId} />
        <Separator />
        <IdentityRow
          label="actor"
          value={`${predicate.actor.id} · ${predicate.actor.kind} · ${predicate.actor.domainId}`}
        />
        <Separator />
        <IdentityRow label="unanchored_steps" value={String(predicate.unanchoredSteps)} />
        <Separator />
        <IdentityRow label="issued_at" value={predicate.issuedAt} />
      </div>

      {/* Nivel 3 — envelope crudo colapsado + descarga */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowRaw(current => !current)}
            className="rounded-md border bg-card px-3 py-1 text-xs font-semibold text-foreground transition-colors hover:bg-muted"
          >
            {showRaw ? 'Ocultar envelope crudo' : 'Ver envelope crudo'}
          </button>
          <button
            type="button"
            onClick={onDownload}
            className="rounded-md border bg-card px-3 py-1 text-xs font-semibold text-foreground transition-colors hover:bg-muted"
          >
            Descargar JSON
          </button>
        </div>
        {showRaw && (
          <div className="flex flex-col gap-2">
            <div>
              <p className="mb-1 text-xs font-semibold text-muted-foreground uppercase">
                Payload (Statement decodificado)
              </p>
              <pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs text-foreground">
                {JSON.stringify(envelope.payload, null, 2)}
              </pre>
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold text-muted-foreground uppercase">
                Firmas (DSSE)
              </p>
              <pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs text-foreground">
                {JSON.stringify(envelope.signatures, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        {predicate.attestations.map((attestation, index) => (
          <RungBadge
            key={`${attestation.verifierId}-${index}`}
            rung={attestation.rung}
            verdict={attestation.verdict}
            detail={attestation.verifierId}
          />
        ))}
      </div>
    </div>
  );
}
