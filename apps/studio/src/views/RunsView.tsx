import React from 'react';

import { EmptyState } from '@/components/feedback/DataState';
import { SectionHeader } from '@/components/layout/SectionHeader';
import { RunStatusDot } from '@/components/runs/RunStatusDot';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table';
import { AssuranceBadge, VerdictChip, conclusionTone } from '@chimera/assurance-ui';

import { shortDate } from './format';

import type { RunSummary } from './types';

/**
 * Lista de runs del proyecto (carril 2 F2, mockup S1 — layout Vercel):
 * tabla densa, una fila = un run, la confianza clase·AL como columna de
 * primera clase. La fila navega al run.
 */

export interface RunsViewProps {
  readonly runs: readonly RunSummary[];
  readonly onSelectRun: (runId: string) => void;
}

const HEADERS = ['Run', 'Conclusión', 'Veredicto', 'Confianza', 'Eventos', 'Actor', 'Fecha'];

export default function RunsView({ runs, onSelectRun }: RunsViewProps): React.ReactElement {
  return (
    <section className="flex flex-col gap-4">
      <SectionHeader
        title="Runs"
        description="Lo cuántico propone, las anclas verifican — cada run llega con su nivel de confianza."
      />

      {runs.length === 0 ? (
        <EmptyState
          title="Sin runs en este proyecto todavía."
          hint="Ejecute un run desde el SDK para verlo aparecer acá."
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
            {runs.map(run => (
              <TableRow key={run.runId} className="hover:bg-foreground/5">
                <TableCell className="whitespace-nowrap">
                  <button
                    type="button"
                    onClick={() => onSelectRun(run.runId)}
                    // El prefijo `run-` SÍ es parte del ID real (runs.py:
                    // `run-{uuid4().hex}`) — acá se recorta SOLO en la celda
                    // (es uniforme en toda fila y no aporta); el ID canónico
                    // completo queda en `title` y en el heading del detalle.
                    title={run.runId}
                    className="focus-ring flex items-center gap-2 rounded-lg font-mono text-foreground"
                  >
                    <RunStatusDot status={run.status} />
                    {run.runId.replace(/^run-/, '')}
                  </button>
                </TableCell>
                <TableCell className="max-w-md">{run.conclusion}</TableCell>
                <TableCell>
                  <VerdictChip verdict={run.verdict} />
                </TableCell>
                <TableCell>
                  <AssuranceBadge
                    level={run.titularLevel}
                    verdict={conclusionTone(run.verdict)}
                    verifierClass={run.titularClass}
                  />
                </TableCell>
                <TableCell className="font-mono text-xs">{run.eventsCount}</TableCell>
                <TableCell className="font-mono text-xs whitespace-nowrap">{run.actor}</TableCell>
                <TableCell className="font-mono text-xs whitespace-nowrap text-muted-foreground">
                  {shortDate(run.completedAt)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </section>
  );
}
