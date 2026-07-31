import { ArrowLeft, Download } from 'lucide-react';
import React from 'react';

import {
  RUN_STATUS_LABELS,
  RUN_STATUS_TEXT_CLASS,
  RunStatusDot
} from '@/components/runs/RunStatusDot';
import { AssuranceBadge, conclusionTone } from '@chimera/assurance-ui';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';

import { shortDate } from './format';

import type { RunSummary } from './types';

/**
 * Página de un run (dominio Studio F2, mockup S2): header persistente — id +
 * estado + AL titular + acciones, siempre visibles (nota 07 §1.3) — y las
 * vistas del run como sub-tabs. Las vistas llegan como slots ya cableados
 * (App conserva queries y estado, este componente es layout).
 *
 * D6 (decisión #93, directriz #69/product-model.md): la entrada
 * conversacional es la presentación por defecto — la tab "Hilo" abre
 * primero (misión → plan → veredicto como turnos); el resto de vistas
 * quedan intactas como sub-tabs.
 */

export interface RunDetailProps {
  readonly summary: RunSummary;
  readonly onDownloadBundle: () => void;
  /** Vuelve a la lista de runs (directriz Dylan 2026-07-29: navegabilidad). */
  readonly onBack?: () => void;
  readonly hilo: React.ReactNode;
  readonly timeline: React.ReactNode;
  readonly verificacion: React.ReactNode;
  readonly red: React.ReactNode;
  readonly ablacion: React.ReactNode;
  readonly procedencia: React.ReactNode;
}

const SUB_TABS = [
  { id: 'hilo', label: 'Hilo' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'verificacion', label: 'Verificación' },
  { id: 'red', label: 'Red' },
  { id: 'ablacion', label: 'Ablación' },
  { id: 'procedencia', label: 'Procedencia' }
] as const;

export default function RunDetail({
  summary,
  onDownloadBundle,
  onBack,
  hilo,
  timeline,
  verificacion,
  red,
  ablacion,
  procedencia
}: RunDetailProps): React.ReactElement {
  const slots = { hilo, timeline, verificacion, red, ablacion, procedencia } as const;

  return (
    // Aire (directriz Dylan 2026-07-29): header+meta agrupados con gap-2 (8),
    // y gap-8 (32) hacia las tabs — potencias de 2.
    <section className="flex flex-col gap-8">
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-4">
          {onBack !== undefined && (
            <Button variant="ghost" size="icon" aria-label="Volver a runs" onClick={onBack}>
              <ArrowLeft />
            </Button>
          )}
          <RunStatusDot status={summary.status} />
          <h1 className="font-mono text-2xl font-medium tracking-tight">{summary.runId}</h1>
          <span
            className={cn(
              'inline-flex items-center rounded-4xl border px-2 py-0.5 text-xs',
              RUN_STATUS_TEXT_CLASS[summary.status]
            )}
          >
            {RUN_STATUS_LABELS[summary.status]}
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
      </div>

      <Tabs defaultValue="hilo">
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
