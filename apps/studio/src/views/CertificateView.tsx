/**
 * CertificateView — nota 18 §2.3 + freeze §7 (reobra ET-9, clase+AL).
 *
 * Three-tier progressive disclosure, ported from `gh attestation verify`
 * (nota 18 §1.3): (1) verdict line que ABRE CON EL ALCANCE — la conclusión
 * canónica + su scope, con clase+AL como badge, jamás "escalón agregado"
 * como titular (P0-2: un nivel sin alcance es pasivo legal); (2) compact
 * table (política, assumptions, unanchored_steps, valid_as_of + revocación
 * honesta); (3) collapsed raw envelope behind a toggle + a client-side-only
 * download.
 *
 * Explicitly does NOT use transparency-log/OIDC language (no "logged at
 * index N", no "signed by workflow X via Sigstore") — this certificate is
 * verified offline against a local key, never a public log (nota 02 §1.2,
 * nota 18 §1.3 "no aplica"). The keyid is always named so the copy reads
 * as "verificado contra la llave local `{keyid}`", never implying a
 * public/third-party trust root.
 */

import { Download, Eye, EyeOff } from 'lucide-react';
import React, { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { AssuranceBadge, conclusionTone } from '@chimera/assurance-ui';

import { shortDigest } from './format';

import type { DsseEnvelope } from './types';

export interface CertificateViewProps {
  readonly envelope: DsseEnvelope;
  readonly onDownload: () => void; // ofrece el JSON crudo como archivo — sin egress nuevo (INV-1)
}

function IdentityRow({
  label,
  value,
  title
}: {
  readonly label: string;
  readonly value: string;
  readonly title?: string;
}): React.ReactElement {
  return (
    <div className="flex items-center justify-between gap-4 py-2 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono text-foreground" title={title}>
        {value}
      </span>
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
      {/* Nivel 1 — la conclusión ABRE con el alcance (trust/18 §2.3, P0-2) */}
      {predicate.conclusions.map(conclusion => {
        const bound = predicate.attestations.filter(
          attestation => attestation.claimDigest === conclusion.claimDigest
        );
        return (
          <div key={conclusion.claimDigest} className="rounded-lg border bg-card p-4">
            <p className="font-display text-base font-medium tracking-tight text-foreground">
              {conclusion.canonicalStatement}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              alcance:{' '}
              {Object.entries(conclusion.scope)
                .map(([key, value]) => `${key}: ${value}`)
                .join(' · ')}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {bound.length > 0 ? (
                bound.map(attestation => (
                  <AssuranceBadge
                    key={`${attestation.verifierId}-${attestation.independenceGroup}`}
                    level={attestation.level}
                    verdict={attestation.verdict}
                    verifierClass={attestation.verifierClass}
                  />
                ))
              ) : (
                <AssuranceBadge
                  level={conclusion.level}
                  verdict={conclusionTone(conclusion.verdict)}
                />
              )}
            </div>
          </div>
        );
      })}

      <div className="rounded-lg border bg-card p-4">
        <p className="text-sm text-foreground">
          Nivel titular <span className="font-mono font-medium">{predicate.titularLevel}</span> — el
          mínimo del camino crítico, jamás promedio · {predicate.unanchoredSteps} pasos sin anclar
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          Verificado contra la llave local <code className="font-mono">{keyid}</code> — sin log
          público ni OIDC: la verificación es offline (nota 02).
        </p>
      </div>

      {/* Nivel 2 — tabla compacta (§2.3) */}
      <div className="rounded-lg border bg-card p-4">
        <IdentityRow label="run_id" value={predicate.runId} />
        <Separator />
        <IdentityRow label="actor" value={predicate.actor} />
        <Separator />
        <IdentityRow
          label="política"
          value={shortDigest(predicate.policyDigest)}
          title={predicate.policyDigest}
        />
        <Separator />
        <div className="flex flex-col gap-1 py-2 text-sm">
          <span className="text-muted-foreground">assumptions</span>
          <ul className="flex flex-col gap-1">
            {predicate.assumptions.map(assumption => (
              <li key={assumption.statement} className="text-foreground">
                {assumption.statement}
                {assumption.ref && (
                  <span
                    className="ml-1 font-mono text-xs text-muted-foreground"
                    title={assumption.ref.digest}
                  >
                    ({assumption.ref.name} · {shortDigest(assumption.ref.digest)})
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
        <Separator />
        <IdentityRow label="unanchored_steps" value={String(predicate.unanchoredSteps)} />
        <Separator />
        <IdentityRow label="valid_as_of" value={predicate.validAsOf} />
        <Separator />
        <IdentityRow
          label="revocación"
          value={`${predicate.revocation} — sin mecanismo de revocación en Fase 1`}
        />
      </div>

      {/* Nivel 3 — envelope crudo colapsado + descarga */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setShowRaw(current => !current)}>
            {showRaw ? <EyeOff data-icon="inline-start" /> : <Eye data-icon="inline-start" />}
            {showRaw ? 'Ocultar envelope crudo' : 'Ver envelope crudo'}
          </Button>
          <Button variant="outline" size="sm" onClick={onDownload}>
            <Download data-icon="inline-start" />
            Descargar JSON
          </Button>
        </div>
        {showRaw && (
          <div className="flex flex-col gap-2">
            <div>
              <p className="mb-1 text-xs tracking-wider text-muted-foreground uppercase">
                Payload (Statement decodificado)
              </p>
              <pre className="overflow-x-auto rounded-md bg-muted p-4 text-xs text-foreground">
                {JSON.stringify(envelope.rawPayload, null, 2)}
              </pre>
            </div>
            <div>
              <p className="mb-1 text-xs tracking-wider text-muted-foreground uppercase">
                Firmas (DSSE)
              </p>
              <pre className="overflow-x-auto rounded-md bg-muted p-4 text-xs text-foreground">
                {JSON.stringify(envelope.signatures, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
