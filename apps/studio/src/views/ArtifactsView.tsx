import React from 'react';

import { EmptyState } from '@/components/feedback/DataState';
import { SectionHeader } from '@/components/layout/SectionHeader';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table';
import { AssuranceBadge, conclusionTone } from '@chimera/assurance-ui';

import { shortDate, shortDigest } from './format';

import type { ProjectArtifact } from './types';

/**
 * Artifacts del proyecto (dominio Studio F2, mockup S4): todos los entregables de
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
      <SectionHeader
        title="Artifacts"
        description="Entregables verificados de los runs del proyecto."
      />

      {artifacts.length === 0 ? (
        <EmptyState
          title="Sin artifacts todavía."
          hint="Los entregables aparecen cuando un run verificado los emite."
        />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              {HEADERS.map(header => (
                <TableHead key={header}>{header}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {artifacts.map(artifact => (
              <TableRow key={artifact.digest}>
                <TableCell className="font-mono">{artifact.artifactRef}</TableCell>
                <TableCell>
                  <code className="font-mono text-xs text-muted-foreground" title={artifact.digest}>
                    {shortDigest(artifact.digest)}
                  </code>
                </TableCell>
                <TableCell>
                  <button
                    type="button"
                    onClick={() => onOpenRun(artifact.runId)}
                    className="focus-ring rounded-lg font-mono text-xs text-foreground underline-offset-4 hover:underline"
                  >
                    {artifact.runId}
                  </button>
                </TableCell>
                <TableCell>
                  <AssuranceBadge
                    level={artifact.titularLevel}
                    verdict={conclusionTone(artifact.verdict)}
                    verifierClass={artifact.titularClass}
                  />
                </TableCell>
                <TableCell className="font-mono text-xs text-muted-foreground">
                  {shortDate(artifact.issuedAt)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </section>
  );
}
