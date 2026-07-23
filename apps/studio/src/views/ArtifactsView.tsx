import React from 'react';

import { EmptyState } from '@/components/feedback/DataState';
import { AssuranceBadge } from '@/components/verification/AssuranceBadge';
import { conclusionTone } from '@/components/verification/assurance';

import { shortDate, shortDigest } from './format';

import type { ProjectArtifact } from './types';

/**
 * Artifacts del proyecto (carril 2 F2, mockup S4): todos los entregables de
 * todos los runs, cada uno con su procedencia — un artifact jamás se
 * muestra suelto (digest + run origen + confianza del run que lo emitió).
 */

export interface ArtifactsViewProps {
  readonly artifacts: readonly ProjectArtifact[];
  readonly onOpenRun: (runId: string) => void;
}

const HEADERS = ['Artifact', 'Digest', 'Run', 'Confianza', 'Emitido'];

export default function ArtifactsView({
  artifacts,
  onOpenRun
}: ArtifactsViewProps): React.ReactElement {
  return (
    <section className="flex flex-col gap-4">
      <div>
        <h1 className="font-display text-2xl font-medium tracking-tight md:text-3xl">Artifacts</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
          Entregables verificados de los runs del proyecto.
        </p>
      </div>

      {artifacts.length === 0 ? (
        <EmptyState
          title="Sin artifacts todavía."
          hint="Los entregables aparecen cuando un run verificado los emite."
        />
      ) : (
        <div className="overflow-x-auto rounded-xl ring-1 ring-foreground/10">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                {HEADERS.map(header => (
                  <th
                    key={header}
                    scope="col"
                    className="px-4 py-2 text-left text-xs font-medium tracking-wider text-muted-foreground uppercase"
                  >
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {artifacts.map(artifact => (
                <tr key={artifact.digest} className="border-b border-border last:border-b-0">
                  <td className="px-4 py-2 font-mono">{artifact.artifactRef}</td>
                  <td className="px-4 py-2">
                    <code
                      className="font-mono text-xs text-muted-foreground"
                      title={artifact.digest}
                    >
                      {shortDigest(artifact.digest)}
                    </code>
                  </td>
                  <td className="px-4 py-2">
                    <button
                      type="button"
                      onClick={() => onOpenRun(artifact.runId)}
                      className="focus-ring rounded-lg font-mono text-xs text-foreground underline-offset-4 hover:underline"
                    >
                      {artifact.runId}
                    </button>
                  </td>
                  <td className="px-4 py-2">
                    <AssuranceBadge
                      level={artifact.titularLevel}
                      verdict={conclusionTone(artifact.verdict)}
                      verifierClass={artifact.titularClass}
                    />
                  </td>
                  <td className="px-4 py-2 font-mono text-xs text-muted-foreground">
                    {shortDate(artifact.issuedAt)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
