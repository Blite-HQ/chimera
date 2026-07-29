/**
 * RunThread — D6 (product-model.md, decisión F2a): el run presentado como
 * HILO CONVERSACIONAL, un LAYOUT sobre los eventos existentes del stream —
 * cero feature nueva, cero persistencia de chat (eso es M1).
 *
 * - La misión (journalizada como `description` del ítem fundacional del
 *   plan — contrato endpoints-studio.md §"POST /runs — modo misión") se
 *   renderiza como mensaje del usuario.
 * - `plan.created` es el checklist del agente; `plan.item_updated` pliega
 *   transiciones sobre él (reducer puro append-only, INV-5 — el cliente
 *   nunca reconstruye el plan entero por update, superficie-visual.md §2).
 * - El terminal (`run.completed`/`run.failed`/`run.cancelled`) es el
 *   mensaje de cierre: conclusión + AL titular si hay veredicto; el
 *   error_kind sin fingir veredicto si no lo hay.
 * - Un run claim-first (sin `plan.*`) muestra el estado honesto — jamás un
 *   hilo fabricado.
 */

import { LoaderCircle } from 'lucide-react';
import React from 'react';

import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/feedback/DataState';
import { AssuranceBadge, conclusionTone } from '@chimera/assurance-ui';

import { planCreatedSchema, planItemUpdatedSchema } from '../data/schemas';

import type { PlanItemStatus } from '../data/schemas';
import type { ProjectedEvent, RunSummary } from './types';

const TERMINAL_EVENT_TYPES: ReadonlySet<string> = new Set([
  'run.completed',
  'run.failed',
  'run.cancelled'
]);

export interface ThreadPlanItem {
  readonly id: string;
  readonly description: string;
  readonly verification: string;
  readonly status: PlanItemStatus;
  readonly cause?: string;
}

export interface RunThreadModel {
  readonly mission?: string;
  readonly checklist: readonly ThreadPlanItem[];
  readonly terminal?: ProjectedEvent;
}

/**
 * Reducer puro del hilo: `plan.created` funda el checklist, cada
 * `plan.item_updated` produce una COPIA con el ítem transicionado (jamás
 * mutación). Payloads se validan con el Zod espejo — un payload fuera de
 * contrato se ignora (graceful), nunca explota la vista.
 */
export function deriveRunThread(events: readonly ProjectedEvent[]): RunThreadModel {
  const planEvent = events.find(e => e.type === 'plan.created');
  const plan = planEvent ? planCreatedSchema.safeParse(planEvent.payload) : undefined;
  const baseItems: readonly ThreadPlanItem[] = plan?.success ? plan.data.items : [];

  const checklist = events
    .filter(e => e.type === 'plan.item_updated')
    .reduce((items: readonly ThreadPlanItem[], updateEvent) => {
      const update = planItemUpdatedSchema.safeParse(updateEvent.payload);
      if (!update.success) {
        return items;
      }
      return items.map(item =>
        item.id === update.data.item_id
          ? {
              ...item,
              status: update.data.status,
              ...(update.data.cause !== undefined && { cause: update.data.cause })
            }
          : item
      );
    }, baseItems);

  const terminal = events.find(e => TERMINAL_EVENT_TYPES.has(e.type));

  return {
    // Contrato del modo misión: la misión ES la description del ítem
    // fundacional del plan (endpoints-studio.md) — sin plan no hay misión.
    mission: plan?.success ? plan.data.items[0]?.description : undefined,
    checklist,
    ...(terminal && { terminal })
  };
}

const STATUS_BADGE_VARIANT: Readonly<Record<PlanItemStatus, 'outline' | 'pass' | 'fail'>> = {
  pending: 'outline',
  running: 'outline',
  ok: 'pass',
  failed: 'fail'
};

function PlanStatusBadge({ status }: { readonly status: PlanItemStatus }): React.ReactElement {
  return (
    <Badge variant={STATUS_BADGE_VARIANT[status]}>
      {status === 'running' && <LoaderCircle className="animate-spin" data-icon="inline-start" />}
      {status}
    </Badge>
  );
}

function UserBubble({
  actor,
  mission
}: {
  readonly actor: string;
  readonly mission: string;
}): React.ReactElement {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-primary/10 px-4 py-3">
        <p className="mb-1 text-xs font-medium text-muted-foreground">
          Misión · <span className="font-mono">{actor}</span>
        </p>
        <p className="text-sm">{mission}</p>
      </div>
    </div>
  );
}

function AgentBubble({
  label,
  children
}: {
  readonly label: string;
  readonly children: React.ReactNode;
}): React.ReactElement {
  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] rounded-2xl rounded-bl-sm border bg-card px-4 py-3">
        <p className="mb-2 text-xs font-medium text-muted-foreground">{label}</p>
        {children}
      </div>
    </div>
  );
}

function ClosingBubble({
  summary,
  terminal
}: {
  readonly summary: RunSummary;
  readonly terminal?: ProjectedEvent;
}): React.ReactElement {
  if (!terminal) {
    return (
      <AgentBubble label="Agente">
        <p className="text-sm text-muted-foreground">
          El agente sigue trabajando — el hilo se actualiza con el stream en vivo.
        </p>
      </AgentBubble>
    );
  }

  if (terminal.type === 'run.completed') {
    return (
      <AgentBubble label="Veredicto">
        <p className="text-sm">{summary.conclusion}</p>
        <div className="mt-2">
          <AssuranceBadge
            level={summary.titularLevel}
            verdict={conclusionTone(summary.verdict)}
            verifierClass={summary.titularClass}
          />
        </div>
      </AgentBubble>
    );
  }

  const errorKind = terminal.payload?.['error_kind'];
  return (
    <AgentBubble label="Cierre">
      <p className="text-sm">
        El run terminó con <span className="font-mono">{terminal.type}</span>
        {typeof errorKind === 'string' && (
          <>
            {' '}
            (<span className="font-mono">{errorKind}</span>)
          </>
        )}{' '}
        — sin veredicto verificado no hay conclusión que afirmar.
      </p>
    </AgentBubble>
  );
}

export interface RunThreadProps {
  readonly summary: RunSummary;
  readonly events: readonly ProjectedEvent[];
}

export default function RunThread({ summary, events }: RunThreadProps): React.ReactElement {
  const thread = deriveRunThread(events);

  if (thread.mission === undefined) {
    return (
      <EmptyState
        title="Este run no arrancó de una misión conversacional."
        hint="El hilo aparece cuando el stream trae plan.created (modo misión) — un run claim-first no tiene turnos que mostrar."
      />
    );
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <UserBubble actor={summary.actor} mission={thread.mission} />

      <AgentBubble label="Plan del agente">
        <ul className="flex flex-col gap-2">
          {thread.checklist.map(item => (
            <li key={item.id} className="flex items-center justify-between gap-3 text-sm">
              <span>
                {item.description}
                {item.cause !== undefined && (
                  <span className="ml-1 text-xs text-muted-foreground">
                    (<span className="font-mono">{item.cause}</span>)
                  </span>
                )}
              </span>
              <PlanStatusBadge status={item.status} />
            </li>
          ))}
        </ul>
      </AgentBubble>

      <ClosingBubble summary={summary} terminal={thread.terminal} />
    </div>
  );
}
