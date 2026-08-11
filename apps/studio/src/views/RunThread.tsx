/**
 * RunThread — D6 (product-model.md, decisión F2a) + P3-D (M1): el run como
 * HILO CONVERSACIONAL, un LAYOUT sobre los eventos del stream.
 *
 * La regla de #93 no cambia con M1: el chat sigue siendo PROYECCIÓN, jamás un
 * almacén paralelo de mensajes. Lo que cambia es que ahora hay más que
 * proyectar — el usuario puede escribir turnos sucesivos (`mission.message`)
 * y el agente puede pedir permiso (`approval.requested`). Ambos son eventos
 * del MISMO stream, así que quedan dentro del `provenance_hash`: el
 * certificado ampara también lo que se pidió y lo que se autorizó.
 *
 * - La misión (journalizada como `description` del ítem fundacional del plan)
 *   abre el hilo como mensaje del usuario.
 * - `plan.created` es el checklist; `plan.item_updated` pliega transiciones
 *   sobre él (reducer puro append-only, INV-5).
 * - Los `mission.message` se intercalan EN EL ORDEN DEL LOG, no agrupados al
 *   final: el hilo cuenta la conversación como ocurrió.
 * - Un `approval.requested` sin su `approval.responded` es lo único que
 *   BLOQUEA: el agente se detuvo esperando a un humano y la card lo dice.
 * - El terminal es el cierre; después de él el stream no acepta appends
 *   (freeze §2), así que el compositor desaparece y se explica por qué.
 */

import { LoaderCircle, ShieldQuestion } from 'lucide-react';
import React, { useState } from 'react';

import { EmptyState } from '@/components/feedback/DataState';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { AssuranceBadge, conclusionTone } from '@chimera/assurance-ui';

import {
  approvalRequestedSchema,
  approvalRespondedSchema,
  missionMessageSchema,
  planCreatedSchema,
  planItemUpdatedSchema
} from '../data/schemas';

import type { ApprovalRequested, ApprovalResponded, PlanItemStatus } from '../data/schemas';
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

export type ThreadEntry =
  | { readonly kind: 'plan'; readonly globalSeq: number; readonly items: readonly ThreadPlanItem[] }
  | {
      readonly kind: 'message';
      readonly globalSeq: number;
      readonly messageId: string;
      readonly author: string;
      readonly text: string;
    }
  | {
      readonly kind: 'approval';
      readonly globalSeq: number;
      readonly request: ApprovalRequested;
      readonly response?: ApprovalResponded;
    };

export interface RunThreadModel {
  readonly mission?: string;
  readonly entries: readonly ThreadEntry[];
  readonly terminal?: ProjectedEvent;
}

/** Pliega los `plan.item_updated` sobre el checklist fundacional (copias, jamás mutación). */
function foldChecklist(
  base: readonly ThreadPlanItem[],
  events: readonly ProjectedEvent[]
): readonly ThreadPlanItem[] {
  return events
    .filter(e => e.type === 'plan.item_updated')
    .reduce((items: readonly ThreadPlanItem[], updateEvent) => {
      const update = planItemUpdatedSchema.safeParse(updateEvent.payload);
      if (!update.success) return items;
      return items.map(item =>
        item.id === update.data.item_id
          ? {
              ...item,
              status: update.data.status,
              ...(update.data.cause !== undefined && { cause: update.data.cause })
            }
          : item
      );
    }, base);
}

/**
 * Reducer puro del hilo. Recorre el stream UNA vez en orden de log y emite las
 * entradas que el layout dibuja. Todo payload se valida con el Zod espejo: uno
 * fuera de contrato se ignora (graceful) en vez de tumbar la vista — un run
 * con un evento raro sigue siendo legible.
 */
export function deriveRunThread(events: readonly ProjectedEvent[]): RunThreadModel {
  const ordered = [...events].sort((a, b) => a.globalSeq - b.globalSeq);

  const planEvent = ordered.find(e => e.type === 'plan.created');
  const plan = planEvent ? planCreatedSchema.safeParse(planEvent.payload) : undefined;
  const baseItems: readonly ThreadPlanItem[] = plan?.success ? plan.data.items : [];

  // Las respuestas se indexan primero: la card de una solicitud necesita saber
  // si ya fue contestada, y la respuesta llega DESPUÉS en el log.
  const responses = new Map<string, ApprovalResponded>();
  for (const event of ordered) {
    if (event.type !== 'approval.responded') continue;
    const parsed = approvalRespondedSchema.safeParse(event.payload);
    if (parsed.success) responses.set(parsed.data.approval_id, parsed.data);
  }

  const entries: ThreadEntry[] = [];
  for (const event of ordered) {
    if (event.type === 'plan.created' && plan?.success) {
      entries.push({
        kind: 'plan',
        globalSeq: event.globalSeq,
        items: foldChecklist(baseItems, ordered)
      });
      continue;
    }
    if (event.type === 'mission.message') {
      const parsed = missionMessageSchema.safeParse(event.payload);
      if (!parsed.success) continue;
      entries.push({
        kind: 'message',
        globalSeq: event.globalSeq,
        messageId: parsed.data.message_id,
        author: parsed.data.author,
        text: parsed.data.text
      });
      continue;
    }
    if (event.type === 'approval.requested') {
      const parsed = approvalRequestedSchema.safeParse(event.payload);
      if (!parsed.success) continue;
      const response = responses.get(parsed.data.approval_id);
      entries.push({
        kind: 'approval',
        globalSeq: event.globalSeq,
        request: parsed.data,
        ...(response !== undefined && { response })
      });
    }
  }

  const terminal = ordered.find(e => TERMINAL_EVENT_TYPES.has(e.type));

  return {
    // Contrato del modo misión: la misión ES la description del ítem
    // fundacional del plan (endpoints-studio.md) — sin plan no hay misión.
    mission: plan?.success ? plan.data.items[0]?.description : undefined,
    entries,
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
  text,
  label
}: {
  readonly actor: string;
  readonly text: string;
  readonly label: string;
}): React.ReactElement {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-primary/10 px-4 py-3">
        <p className="mb-1 text-xs font-medium text-muted-foreground">
          {label} · <span className="font-mono">{actor}</span>
        </p>
        <p className="text-sm">{text}</p>
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

/**
 * El único campo booleano REQUERIDO del `json_schema`, si el schema tiene esa
 * forma. Es lo que permite ofrecer Aprobar/Rechazar sin inventarse el
 * vocabulario: el nombre del campo lo pone el schema que declaró el emisor,
 * no esta vista. Cualquier otra forma cae al editor JSON — decir «no sé
 * dibujar este formulario» es más honesto que adivinar la respuesta.
 */
function booleanDecisionField(jsonSchema: Readonly<Record<string, unknown>>): string | undefined {
  const properties = jsonSchema.properties;
  const required = jsonSchema.required;
  if (typeof properties !== 'object' || properties === null || !Array.isArray(required)) {
    return undefined;
  }
  if (required.length !== 1 || typeof required[0] !== 'string') return undefined;
  const campo = required[0];
  const definicion = (properties as Record<string, unknown>)[campo];
  if (typeof definicion !== 'object' || definicion === null) return undefined;
  return (definicion as { type?: unknown }).type === 'boolean' ? campo : undefined;
}

function ApprovalCard({
  entry,
  onRespond,
  error
}: {
  readonly entry: Extract<ThreadEntry, { kind: 'approval' }>;
  readonly onRespond?: (approvalId: string, response: unknown) => void;
  readonly error?: string | null;
}): React.ReactElement {
  const { request, response } = entry;
  const campo = booleanDecisionField(request.json_schema);
  const [borrador, setBorrador] = useState('{}');
  const [errorLocal, setErrorLocal] = useState<string | null>(null);

  const enviarJson = (): void => {
    try {
      onRespond?.(request.approval_id, JSON.parse(borrador));
      setErrorLocal(null);
    } catch {
      setErrorLocal('La respuesta no es JSON válido — corrija el texto antes de enviarla.');
    }
  };

  return (
    <section
      aria-label={`Aprobación ${request.approval_id}`}
      className="rounded-xl border border-status-warning/40 bg-status-warning/10 p-4"
    >
      <p className="mb-2 flex items-center gap-2 text-xs font-medium tracking-wider text-muted-foreground uppercase">
        <ShieldQuestion className="size-4" aria-hidden />
        {response === undefined ? 'Aprobación pendiente' : 'Aprobación resuelta'}
      </p>
      <p className="text-sm">{request.prompt}</p>
      {/* F1.3: el emisor real journaliza `step_id: null` (la aprobación
          corre ANTES de abrir el `RunStep` del turno) — `typeof === 'string'`
          descarta tanto `undefined` (fixtures/replays viejos) como `null`
          (el wire real) sin renderizar un badge vacío. */}
      {typeof request.step_id === 'string' && (
        <p className="mt-1 font-mono text-xs text-muted-foreground">{request.step_id}</p>
      )}

      {response !== undefined ? (
        <p className="mt-2 text-sm text-muted-foreground">
          Respondida por <span className="font-mono">{response.authorized_by}</span>:{' '}
          <span className="font-mono">{JSON.stringify(response.response)}</span>
        </p>
      ) : (
        <>
          <p className="mt-2 text-xs text-muted-foreground">
            El agente está detenido en este punto — no avanza hasta que un humano decida.
          </p>
          {error !== undefined && error !== null && error !== '' && (
            <Alert variant="destructive" className="mt-2">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {errorLocal !== null && (
            <Alert variant="destructive" className="mt-2">
              <AlertDescription>{errorLocal}</AlertDescription>
            </Alert>
          )}
          {onRespond !== undefined &&
            (campo !== undefined ? (
              <div className="mt-4 flex gap-2">
                <Button size="sm" onClick={() => onRespond(request.approval_id, { [campo]: true })}>
                  Aprobar
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onRespond(request.approval_id, { [campo]: false })}
                >
                  Rechazar
                </Button>
              </div>
            ) : (
              <div className="mt-4 flex flex-col gap-2">
                <label
                  htmlFor={`approval-${request.approval_id}`}
                  className="text-xs text-muted-foreground"
                >
                  Esta solicitud declara un esquema propio — escriba la respuesta como JSON.
                </label>
                <Textarea
                  id={`approval-${request.approval_id}`}
                  value={borrador}
                  onChange={event => setBorrador(event.target.value)}
                  rows={4}
                  className="font-mono"
                />
                <div>
                  <Button size="sm" onClick={enviarJson}>
                    Enviar respuesta
                  </Button>
                </div>
              </div>
            ))}
        </>
      )}
    </section>
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

/** Compositor de turnos nuevos — solo existe mientras el stream acepta appends. */
function MessageComposer({
  onSend,
  isPending,
  error
}: {
  readonly onSend: (text: string) => void;
  readonly isPending?: boolean;
  readonly error?: string | null;
}): React.ReactElement {
  const [texto, setTexto] = useState('');
  const recortado = texto.trim();

  const enviar = (): void => {
    if (recortado.length === 0) return;
    onSend(recortado);
    setTexto('');
  };

  return (
    <div className="flex flex-col gap-2 border-t border-border pt-4">
      {error !== undefined && error !== null && error !== '' && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <label htmlFor="run-thread-composer" className="text-xs text-muted-foreground">
        Mensaje al agente — entra al stream y se atiende en el turno siguiente.
      </label>
      <Textarea
        id="run-thread-composer"
        value={texto}
        onChange={event => setTexto(event.target.value)}
        rows={2}
        placeholder="Escriba una corrección o una pregunta…"
      />
      <div>
        <Button size="sm" onClick={enviar} disabled={isPending === true}>
          {isPending === true ? 'Enviando…' : 'Enviar'}
        </Button>
      </div>
    </div>
  );
}

export interface RunThreadProps {
  readonly summary: RunSummary;
  readonly events: readonly ProjectedEvent[];
  /** Ausente ⇒ el hilo es solo lectura (modo réplica o run terminal). */
  readonly onSendMessage?: (text: string) => void;
  readonly isSendingMessage?: boolean;
  readonly sendError?: string | null;
  readonly onRespondApproval?: (approvalId: string, response: unknown) => void;
  readonly approvalError?: string | null;
  /** Abre un run nuevo que cita a este como hilo (§Contrato-4). */
  readonly onContinueThread?: () => void;
}

export default function RunThread({
  summary,
  events,
  onSendMessage,
  isSendingMessage,
  sendError,
  onRespondApproval,
  approvalError,
  onContinueThread
}: RunThreadProps): React.ReactElement {
  const thread = deriveRunThread(events);

  if (thread.mission === undefined) {
    return (
      <EmptyState
        title="Este run no arrancó de una misión conversacional."
        hint="El hilo aparece cuando el stream trae plan.created (modo misión) — un run claim-first no tiene turnos que mostrar."
      />
    );
  }

  const esTerminal = thread.terminal !== undefined;

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <UserBubble actor={summary.actor} text={thread.mission} label="Misión" />

      {thread.entries.map(entry => {
        if (entry.kind === 'plan') {
          return (
            <AgentBubble key={`plan-${entry.globalSeq}`} label="Plan del agente">
              <ul className="flex flex-col gap-2">
                {entry.items.map(item => (
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
          );
        }
        if (entry.kind === 'message') {
          return (
            <UserBubble
              key={entry.messageId}
              actor={entry.author}
              text={entry.text}
              label="Mensaje"
            />
          );
        }
        return (
          <ApprovalCard
            key={entry.request.approval_id}
            entry={entry}
            {...(onRespondApproval !== undefined && { onRespond: onRespondApproval })}
            {...(approvalError !== undefined && { error: approvalError })}
          />
        );
      })}

      <ClosingBubble summary={summary} terminal={thread.terminal} />

      {esTerminal ? (
        <div className="flex flex-col items-start gap-2 border-t border-border pt-4">
          <p className="text-xs text-muted-foreground">
            Este stream ya cerró y no acepta más mensajes (freeze §2). Para seguir la conversación,
            abra un run nuevo que cite a este como hilo.
          </p>
          {onContinueThread !== undefined && (
            <Button size="sm" variant="outline" onClick={onContinueThread}>
              Continuar en un run nuevo
            </Button>
          )}
        </div>
      ) : (
        onSendMessage !== undefined && (
          <MessageComposer
            onSend={onSendMessage}
            {...(isSendingMessage !== undefined && { isPending: isSendingMessage })}
            {...(sendError !== undefined && { error: sendError })}
          />
        )
      )}
    </div>
  );
}
