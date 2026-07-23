import { Download } from 'lucide-react';
import React from 'react';

import { AssuranceBadge } from '@/components/verification/AssuranceBadge';
import { conclusionTone } from '@/components/verification/assurance';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';

import { shortDate } from './format';

import type { RunSummary } from './types';

/**
 * Página de un run (carril 2 F2, mockup S2): header persistente — id +
 * estado + AL titular + acciones, siempre visibles (nota 07 §1.3) — y las
 * vistas del run como sub-tabs. Las vistas llegan como slots ya cableados
 * (App conserva queries y estado, este componente es layout).
 */

export interface RunDetailProps {
  readonly summary: RunSummary;
  readonly onDownloadBundle: () => void;
  readonly timeline: React.ReactNode;
  readonly verificacion: React.ReactNode;
  readonly red: React.ReactNode;
  readonly ablacion: React.ReactNode;
  readonly procedencia: React.ReactNode;
}

const SUB_TABS = [
  { id: 'timeline', label: 'Timeline' },
  { id: 'verificacion', label: 'Verificación' },
  { id: 'red', label: 'Red' },
  { id: 'ablacion', label: 'Ablación' },
  { id: 'procedencia', label: 'Procedencia' }
] as const;

export default function RunDetail({
  summary,
  onDownloadBundle,
  timeline,
  verificacion,
  red,
  ablacion,
  procedencia
}: RunDetailProps): React.ReactElement {
  const slots = { timeline, verificacion, red, ablacion, procedencia } as const;

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-4">
        <span
          aria-hidden
          className={cn(
            'size-2 rounded-full',
            summary.status === 'completado' ? 'bg-verdict-pass' : 'bg-status-warning'
          )}
        />
        <h1 className="font-mono text-2xl font-medium tracking-tight">{summary.runId}</h1>
        <span className="inline-flex items-center rounded-4xl border px-2 py-0.5 text-xs text-muted-foreground">
          {summary.status === 'completado' ? 'completado' : 'en curso'}
        </span>
        <AssuranceBadge
          level={summary.titularLevel}
          verdict={conclusionTone(summary.verdict)}
          verifierClass={summary.titularClass}
        />
        <div className="ml-auto">
          <Button variant="outline" size="sm" onClick={onDownloadBundle}>
            <Download data-icon="inline-start" />
            Descargar bundle
          </Button>
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        <span className="font-mono">{summary.actor}</span> · {shortDate(summary.completedAt)} ·{' '}
        {summary.eventsCount} eventos
      </p>

      <Tabs defaultValue="timeline">
        <TabsList variant="line">
          {SUB_TABS.map(tab => (
            <TabsTrigger key={tab.id} value={tab.id} className="px-2">
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>
        {SUB_TABS.map(tab => (
          <TabsContent key={tab.id} value={tab.id} className="pt-4">
            {slots[tab.id]}
          </TabsContent>
        ))}
      </Tabs>
    </section>
  );
}
