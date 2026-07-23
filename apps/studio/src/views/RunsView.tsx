import React from 'react';

import { EmptyState } from '@/components/feedback/DataState';
import { AssuranceBadge } from '@/components/verification/AssuranceBadge';
import { conclusionTone } from '@/components/verification/assurance';
import { VerdictChip } from '@/components/verification/VerdictChip';
import { cn } from '@/lib/utils';

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
      <div>
        <h1 className="font-display text-2xl font-medium tracking-tight md:text-3xl">Runs</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
          Lo cuántico propone, las anclas verifican — cada run llega con su nivel de confianza.
        </p>
      </div>

      {runs.length === 0 ? (
        <EmptyState
          title="Sin runs en este proyecto todavía."
          hint="Ejecute un run desde el SDK para verlo aparecer acá."
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
              {runs.map(run => (
                <tr
                  key={run.runId}
                  className="border-b border-border transition-colors last:border-b-0 hover:bg-foreground/5"
                >
                  <td className="px-4 py-2">
                    <button
                      type="button"
                      onClick={() => onSelectRun(run.runId)}
                      className="focus-ring flex items-center gap-2 rounded-lg font-mono text-foreground"
                    >
                      <span
                        aria-hidden
                        className={cn(
                          'size-2 rounded-full',
                          run.status === 'completado' ? 'bg-verdict-pass' : 'bg-status-warning'
                        )}
                      />
                      {run.runId}
                    </button>
                  </td>
                  <td className="max-w-md px-4 py-2">{run.conclusion}</td>
                  <td className="px-4 py-2">
                    <VerdictChip verdict={run.verdict} />
                  </td>
                  <td className="px-4 py-2">
                    <AssuranceBadge
                      level={run.titularLevel}
                      verdict={conclusionTone(run.verdict)}
                      verifierClass={run.titularClass}
                    />
                  </td>
                  <td className="px-4 py-2 font-mono text-xs">{run.eventsCount}</td>
                  <td className="px-4 py-2 font-mono text-xs">{run.actor}</td>
                  <td className="px-4 py-2 font-mono text-xs text-muted-foreground">
                    {shortDate(run.completedAt)}
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
