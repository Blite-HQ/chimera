/**
 * ProvenanceExplorer — nota 18 §2.4.
 *
 * Treats `events` as the current page of the full archival stream
 * (Temporal UI §1.2: no live-state tab, no replay — everything here is a
 * client-side projection over data already received). `viewMode`:
 * 'compact' collapses each stepId's related events into one row (reuses
 * RunTimeline's groupByStep — same "Event Group" idea, Temporal §1.2);
 * 'raw' prints the full JSON of every event. type/actorId filters are
 * real client-side filters over the current page.
 *
 * Pagination is a no-op single page for this fixture (it's small enough
 * to hand over whole), but the cursor/hasMore contract is still wired
 * through for real — `onPageChange` gets called, it just has nothing
 * further to fetch (cursor = global_seq, notify-then-catchup, nota 01).
 */

import React from 'react';

import { Badge } from '@/components/ui/badge';

import { groupByStep } from './RunTimeline';
import type { ProjectedEvent, ProvenanceFilters } from './types';

export interface ProvenanceExplorerProps {
  readonly events: readonly ProjectedEvent[]; // página actual
  readonly filters: ProvenanceFilters;
  readonly onFilterChange: (filters: ProvenanceFilters) => void;
  readonly viewMode: 'compact' | 'raw';
  readonly page: { readonly cursor: number; readonly pageSize: number; readonly hasMore: boolean };
  readonly onPageChange: (cursor: number) => void;
}

function applyFilters(
  events: readonly ProjectedEvent[],
  filters: ProvenanceFilters
): readonly ProjectedEvent[] {
  return events.filter(event => {
    if (filters.type && event.type !== filters.type) {
      return false;
    }
    if (filters.actorId && event.actorId !== filters.actorId) {
      return false;
    }
    return true;
  });
}

function uniqueSorted(values: readonly string[]): readonly string[] {
  return Array.from(new Set(values)).sort();
}

function FilterBar({
  events,
  filters,
  onFilterChange
}: {
  readonly events: readonly ProjectedEvent[];
  readonly filters: ProvenanceFilters;
  readonly onFilterChange: (filters: ProvenanceFilters) => void;
}): React.ReactElement {
  const types = uniqueSorted(events.map(event => event.type));
  const actorIds = uniqueSorted(events.map(event => event.actorId));

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border bg-card px-3 py-2 text-xs">
      <label className="flex items-center gap-2 text-muted-foreground">
        type
        <select
          value={filters.type ?? ''}
          onChange={event => onFilterChange({ ...filters, type: event.target.value || undefined })}
          className="rounded-md border bg-background px-2 py-1 text-foreground"
        >
          <option value="">todos</option>
          {types.map(type => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </label>
      <label className="flex items-center gap-2 text-muted-foreground">
        actorId
        <select
          value={filters.actorId ?? ''}
          onChange={event =>
            onFilterChange({ ...filters, actorId: event.target.value || undefined })
          }
          className="rounded-md border bg-background px-2 py-1 text-foreground"
        >
          <option value="">todos</option>
          {actorIds.map(actorId => (
            <option key={actorId} value={actorId}>
              {actorId}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

function CompactRow({
  group
}: {
  readonly group: ReturnType<typeof groupByStep>[number];
}): React.ReactElement {
  const last = group.events[group.events.length - 1];
  return (
    <li className="flex items-center justify-between gap-3 rounded-lg border bg-card px-3 py-2 text-sm">
      <div className="flex flex-col">
        <span className="font-mono font-semibold text-foreground">{group.stepId ?? last.type}</span>
        <span className="text-xs text-muted-foreground">
          {group.events.length} evento{group.events.length > 1 ? 's' : ''} · {last.resumen}
        </span>
      </div>
      {last.verdict && <Badge variant={last.verdict}>{last.verdict}</Badge>}
    </li>
  );
}

function RawRow({ event }: { readonly event: ProjectedEvent }): React.ReactElement {
  return (
    <li className="rounded-lg border bg-card p-3">
      <pre className="overflow-x-auto text-xs text-foreground">
        {JSON.stringify(event, null, 2)}
      </pre>
    </li>
  );
}

export default function ProvenanceExplorer({
  events,
  filters,
  onFilterChange,
  viewMode,
  page,
  onPageChange
}: ProvenanceExplorerProps): React.ReactElement {
  const filtered = applyFilters(events, filters);

  return (
    <div className="flex flex-col gap-3">
      <FilterBar events={events} filters={filters} onFilterChange={onFilterChange} />

      <p className="font-mono text-xs text-muted-foreground">
        {filtered.length} / {events.length} eventos · cursor {page.cursor} ·{' '}
        {page.hasMore ? 'hay más páginas' : 'fin del stream'}
      </p>

      {filtered.length === 0 ? (
        <p className="rounded-lg border border-dashed px-3 py-6 text-center text-sm text-muted-foreground">
          Ningún evento coincide con los filtros.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {viewMode === 'compact'
            ? groupByStep(filtered).map(group => <CompactRow key={group.key} group={group} />)
            : filtered.map(event => <RawRow key={event.globalSeq} event={event} />)}
        </ul>
      )}

      <div className="flex justify-end">
        <button
          type="button"
          disabled={!page.hasMore}
          onClick={() => onPageChange(page.cursor + page.pageSize)}
          className="rounded-md border bg-card px-3 py-1 text-xs font-semibold text-foreground transition-colors hover:bg-muted disabled:opacity-40"
        >
          Página siguiente
        </button>
      </div>
    </div>
  );
}
