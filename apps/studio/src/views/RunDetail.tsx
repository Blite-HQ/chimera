import { ArrowLeft, Ban, Download } from 'lucide-react';
import React, { useState } from 'react';

import {
  RUN_STATUS_LABELS,
  RUN_STATUS_TEXT_CLASS,
  RunStatusDot
} from '@/components/runs/RunStatusDot';
import { AssuranceBadge, conclusionTone } from '@chimera/assurance-ui';
import { Alert, AlertDescription } from '@/components/ui/alert';
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
  /**
   * P3-D (N1) — emisor de `run.cancelled`. Ausente ⇒ no hay quién atienda la
   * acción (modo réplica) y el botón NO se dibuja: un control que no hace nada
   * es peor que ninguno.
   */
  readonly onCancelRun?: () => void;
  readonly cancelError?: string | null;
  readonly isCancelling?: boolean;
  readonly hilo: React.ReactNode;
  readonly timeline: React.ReactNode;
  readonly verificacion: React.ReactNode;
  readonly procedencia: React.ReactNode;
  /**
   * P13 — las lentes de dominio YA RESUELTAS para este run
   * (`product-model.md` §"Superficies de plataforma vs dominio"). Este
   * componente no sabe qué lentes existen ni cuál aplica: las pinta como
   * sub-tabs después de las de plataforma, en el orden en que llegan.
   *
   * Antes acá había `red` y `ablacion` como props OBLIGATORIAS — el shell
   * nombraba el dominio del caso demo, y un run de otro dominio igual
   * mostraba esas tabs vacías.
   */
  readonly lenses?: readonly ResolvedLens[];
}

/** Una lente ya resuelta: id, etiqueta y su contenido listo para pintar. */
export interface ResolvedLens {
  readonly id: string;
  readonly label: string;
  readonly content: React.ReactNode;
}

/**
 * Las superficies de PLATAFORMA (genéricas, product-model.md): existen en
 * todo run, sea del dominio que sea. Las de dominio llegan por `lenses` y se
 * intercalan entre estas dos listas.
 */
const LEADING_TABS = [
  { id: 'hilo', label: 'Hilo' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'verificacion', label: 'Verificación' }
] as const;

/** Procedencia cierra siempre: es la superficie de auditoría del run. */
const TRAILING_TABS = [{ id: 'procedencia', label: 'Procedencia' }] as const;

export default function RunDetail({
  summary,
  onDownloadBundle,
  onBack,
  hilo,
  timeline,
  verificacion,
  procedencia,
  lenses = [],
  onCancelRun,
  cancelError,
  isCancelling
}: RunDetailProps): React.ReactElement {
  const platformSlots = { hilo, timeline, verificacion, procedencia } as const;
  const conContenido = (tab: {
    readonly id: keyof typeof platformSlots;
    readonly label: string;
  }) => ({
    ...tab,
    content: platformSlots[tab.id]
  });
  const tabs: readonly ResolvedLens[] = [
    ...LEADING_TABS.map(conContenido),
    ...lenses,
    ...TRAILING_TABS.map(conContenido)
  ];
  const [confirmandoCancel, setConfirmandoCancel] = useState(false);

  // Freeze §2: un stream terminal no acepta appends. Cancelar un run cerrado
  // no es una acción deshabilitada — es una acción que no existe.
  const puedeCancelar = onCancelRun !== undefined && summary.status === 'en_curso';

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
          <div className="ml-auto flex items-center gap-2">
            {puedeCancelar &&
              (confirmandoCancel ? (
                <>
                  <span className="text-xs text-muted-foreground">
                    Se detiene la corrida y el stream queda cerrado.
                  </span>
                  <Button
                    variant="destructive"
                    size="sm"
                    disabled={isCancelling === true}
                    onClick={() => {
                      setConfirmandoCancel(false);
                      onCancelRun?.();
                    }}
                  >
                    {isCancelling === true ? 'Cancelando…' : 'Confirmar'}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setConfirmandoCancel(false)}>
                    Volver
                  </Button>
                </>
              ) : (
                <Button variant="outline" size="sm" onClick={() => setConfirmandoCancel(true)}>
                  <Ban data-icon="inline-start" />
                  Cancelar run
                </Button>
              ))}
            <Button variant="outline" size="sm" onClick={onDownloadBundle}>
              <Download data-icon="inline-start" />
              Descargar bundle
            </Button>
          </div>
        </div>

        {cancelError !== undefined && cancelError !== null && cancelError !== '' && (
          <Alert variant="destructive">
            <AlertDescription>{cancelError}</AlertDescription>
          </Alert>
        )}

        <p className="text-xs text-muted-foreground">
          <span className="font-mono">{summary.actor}</span> · {shortDate(summary.completedAt)} ·{' '}
          {summary.eventsCount} eventos
        </p>
      </div>

      <Tabs defaultValue="hilo">
        <TabsList variant="line">
          {tabs.map(tab => (
            <TabsTrigger key={tab.id} value={tab.id} className="px-2">
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>
        {tabs.map(tab => (
          <TabsContent key={tab.id} value={tab.id} className="pt-4">
            {tab.content}
          </TabsContent>
        ))}
      </Tabs>
    </section>
  );
}
