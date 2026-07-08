/**
 * RunTimeline — nota 18 §2.1.
 *
 * Renders the projected event stream of a run as a vertical list, grouped
 * by stepId when `viewMode === 'tree'` (Langfuse-style Tree⇄Timeline
 * toggle, nota 18 §1.1) or flat/chronological when `viewMode ===
 * 'timeline'`. Clicking a row is the "jump-to-detail" affordance —
 * `onSelectEvent` is the only way this component talks to a sibling
 * StepInspector (no internal coupling between the two).
 *
 * `playback` is optional and fixture/demo-only (nota 18 §2.1 "Nota de
 * diseño"): this component never owns an interval itself, it only renders
 * the play/pause/scrub chrome and delegates to the callbacks it's given
 * (see usePlaybackReveal.ts for the actual simulation).
 */

import React from 'react';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

import type { PlaybackControls, ProjectedEvent } from './types';

export interface RunTimelineProps {
  readonly events: readonly ProjectedEvent[]; // orden global_seq ascendente
  readonly selectedGlobalSeq?: number;
  readonly onSelectEvent: (globalSeq: number) => void;
  readonly viewMode: 'tree' | 'timeline';
  readonly playback?: PlaybackControls;
}

// Exported for reuse by ProvenanceExplorer.tsx (Temporal §1.2 "Event
// Group" pattern applies to both the timeline's tree mode and the
// explorer's compact mode — one grouping function, two renderers).
export interface EventGroup {
  readonly key: string;
  readonly stepId?: string;
  readonly events: readonly ProjectedEvent[];
}

export function groupByStep(events: readonly ProjectedEvent[]): readonly EventGroup[] {
  const groups: EventGroup[] = [];
  const groupIndexByStepId = new Map<string, number>();

  for (const event of events) {
    if (!event.stepId) {
      groups.push({ key: `event-${event.globalSeq}`, events: [event] });
      continue;
    }
    const existingIndex = groupIndexByStepId.get(event.stepId);
    if (existingIndex === undefined) {
      groupIndexByStepId.set(event.stepId, groups.length);
      groups.push({ key: `step-${event.stepId}`, stepId: event.stepId, events: [event] });
      continue;
    }
    const existing = groups[existingIndex];
    groups[existingIndex] = { ...existing, events: [...existing.events, event] };
  }

  return groups;
}

function formatTime(occurredAt: string): string {
  const date = new Date(occurredAt);
  if (Number.isNaN(date.getTime())) {
    return occurredAt;
  }
  return date.toISOString().slice(11, 23);
}

interface EventRowProps {
  readonly event: ProjectedEvent;
  readonly isSelected: boolean;
  readonly onSelectEvent: (globalSeq: number) => void;
}

function EventRow({ event, isSelected, onSelectEvent }: EventRowProps): React.ReactElement {
  return (
    <li>
      <button
        type="button"
        onClick={() => onSelectEvent(event.globalSeq)}
        aria-pressed={isSelected}
        className={cn(
          'flex w-full flex-col gap-1 rounded-lg border px-3 py-2 text-left text-sm transition-colors',
          isSelected ? 'border-zinc-400 bg-zinc-100' : 'border-transparent hover:bg-zinc-50'
        )}
      >
        <div className="flex items-center justify-between gap-2">
          <span className="font-mono text-xs text-zinc-400">{formatTime(event.occurredAt)}</span>
          {event.verdict && <Badge variant={event.verdict}>{event.verdict}</Badge>}
        </div>
        <p className="text-zinc-700">{event.resumen}</p>
        <p className="text-xs text-zinc-400">
          {event.actorId} · {event.type}
        </p>
      </button>
    </li>
  );
}

const PLAYBACK_BUTTON_LABELS: Readonly<Record<PlaybackControls['state'], string>> = {
  idle: 'Reproducir',
  playing: 'Pausar',
  paused: 'Reanudar',
  finished: 'Repetir'
};

const PLAYBACK_STATUS_LABELS: Readonly<Record<PlaybackControls['state'], string>> = {
  idle: 'sin iniciar',
  playing: 'reproduciendo',
  paused: 'pausado',
  finished: 'completo'
};

function PlaybackBar({
  playback,
  revealedGlobalSeq
}: {
  readonly playback: PlaybackControls;
  readonly revealedGlobalSeq: number;
}): React.ReactElement {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2">
      <button
        type="button"
        onClick={playback.state === 'playing' ? playback.onPause : playback.onPlay}
        className="rounded-md border border-zinc-300 bg-white px-3 py-1 text-xs font-semibold text-zinc-700 hover:bg-zinc-100"
      >
        {PLAYBACK_BUTTON_LABELS[playback.state]}
      </button>
      <input
        type="range"
        min={0}
        max={playback.maxGlobalSeq}
        value={revealedGlobalSeq}
        aria-label="Saltar a un punto del stream"
        onChange={event => playback.onScrub(Number(event.target.value))}
        className="h-1.5 flex-1 accent-zinc-700"
      />
      <span className="text-xs text-zinc-400">{PLAYBACK_STATUS_LABELS[playback.state]}</span>
    </div>
  );
}

export default function RunTimeline({
  events,
  selectedGlobalSeq,
  onSelectEvent,
  viewMode,
  playback
}: RunTimelineProps): React.ReactElement {
  return (
    <div className="flex flex-col gap-3">
      {playback && (
        <PlaybackBar
          playback={playback}
          revealedGlobalSeq={events.length > 0 ? events[events.length - 1].globalSeq : 0}
        />
      )}

      {events.length === 0 ? (
        <p className="rounded-lg border border-dashed border-zinc-300 px-3 py-6 text-center text-sm text-zinc-400">
          Sin eventos todavía — presioná Reproducir para simular la llegada del stream.
        </p>
      ) : (
        <ol className="flex flex-col gap-2">
          {viewMode === 'tree'
            ? groupByStep(events).map(group => (
                <li key={group.key} className="flex flex-col gap-1">
                  {group.stepId && (
                    <p className="px-1 text-xs font-semibold tracking-wide text-zinc-400 uppercase">
                      {group.stepId}
                    </p>
                  )}
                  <ul className="flex flex-col gap-1">
                    {group.events.map(event => (
                      <EventRow
                        key={event.globalSeq}
                        event={event}
                        isSelected={event.globalSeq === selectedGlobalSeq}
                        onSelectEvent={onSelectEvent}
                      />
                    ))}
                  </ul>
                </li>
              ))
            : events.map(event => (
                <EventRow
                  key={event.globalSeq}
                  event={event}
                  isSelected={event.globalSeq === selectedGlobalSeq}
                  onSelectEvent={onSelectEvent}
                />
              ))}
        </ol>
      )}
    </div>
  );
}
