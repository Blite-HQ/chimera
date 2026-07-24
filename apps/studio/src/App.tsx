import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { Braces, LayoutList, List, ListTree, Plus } from 'lucide-react';
import React, { useState } from 'react';

import { AppShell } from '@/components/app-shell/AppShell';
import { EmptyState, ErrorState, LoadingState } from '@/components/feedback/DataState';
import { Button } from '@/components/ui/button';
import { ThemeProvider } from '@/lib/theme';

import { isLiveMode } from './data/env';
import { useCreateRun } from './data/mutations';
import {
  ablationQueryOptions,
  artifactsQueryOptions,
  certificateQueryOptions,
  knowledgeQueryOptions,
  runEventsQueryOptions,
  runSummariesQueryOptions,
  stepEvidenceQueryOptions
} from './data/queries';
import { useRunEventStream } from './data/useRunEventStream';
import GridSpike from './spike/GridSpike';
import AblationPanel from './views/AblationPanel';
import ArtifactsView from './views/ArtifactsView';
import CertificateView from './views/CertificateView';
import { downloadJson } from './views/downloadJson';
import KnowledgeView from './views/KnowledgeView';
import NewRunView from './views/NewRunView';
import PapersView from './views/PapersView';
import ProvenanceExplorer from './views/ProvenanceExplorer';
import RunDetail from './views/RunDetail';
import RunsView from './views/RunsView';
import RunTimeline from './views/RunTimeline';
import StepInspector from './views/StepInspector';
import { usePlaybackReveal } from './views/usePlaybackReveal';

import type { ProvenanceFilters } from './views/types';

/**
 * Chimera Studio — raíz (carril 2 F2, shell B).
 *
 * IA de PROYECTO (mockups F1 validados): secciones Runs / Artifacts /
 * Papers / Knowledge en el sidebar; un run abre como página con header
 * persistente + sub-tabs (RunDetail). F3 intacto: TODO dato llega por
 * src/data/** (queryOptions + Zod en la frontera); INV-1 intacto (red solo
 * en gatewayClient cuando exista). Navegación por estado local — la
 * migración a router es aditiva y no cambia esta IA.
 */

type SectionId = 'runs' | 'artifacts' | 'papers' | 'knowledge';

const SECTIONS: readonly { readonly id: SectionId; readonly label: string }[] = [
  { id: 'runs', label: 'Runs' },
  { id: 'artifacts', label: 'Artifacts' },
  { id: 'papers', label: 'Papers' },
  { id: 'knowledge', label: 'Knowledge' }
];

const PROJECT_NAME = 'islanding-ieee14';

const queryClient = new QueryClient();

function ToggleButton({
  label,
  icon,
  isActive,
  onClick
}: {
  readonly label: string;
  readonly icon: React.ReactNode;
  readonly isActive: boolean;
  readonly onClick: () => void;
}): React.ReactElement {
  return (
    <Button
      variant={isActive ? 'default' : 'outline'}
      size="sm"
      onClick={onClick}
      aria-pressed={isActive}
    >
      {icon}
      {label}
    </Button>
  );
}

/** Vistas del run montadas como slots de RunDetail (queries + estado acá). */
function RunDetailScreen({ runId }: { readonly runId: string }): React.ReactElement {
  // No-op en modo fixtures/demo; en modo live alimenta el cache con el SSE
  // real (MVP task 1) — llamada incondicional, el hook decide adentro.
  useRunEventStream(runId);
  const summariesQuery = useQuery(runSummariesQueryOptions());
  const eventsQuery = useQuery(runEventsQueryOptions(runId));
  const stepsQuery = useQuery(stepEvidenceQueryOptions(runId));
  const certificateQuery = useQuery(certificateQueryOptions(runId));
  const ablationQuery = useQuery(ablationQueryOptions(runId));

  const runEvents = eventsQuery.data ?? [];
  const { revealedEvents, playback } = usePlaybackReveal(runEvents);
  const [selectedGlobalSeq, setSelectedGlobalSeq] = useState<number | undefined>(undefined);
  const [timelineViewMode, setTimelineViewMode] = useState<'tree' | 'timeline'>('tree');
  const [provenanceFilters, setProvenanceFilters] = useState<ProvenanceFilters>({});
  const [provenanceViewMode, setProvenanceViewMode] = useState<'compact' | 'raw'>('compact');
  const [provenanceCursor, setProvenanceCursor] = useState(0);

  const summary = summariesQuery.data?.find(run => run.runId === runId);
  if (summariesQuery.isPending || !summary) {
    return <LoadingState label="Cargando el run" />;
  }

  const selectedEvent = revealedEvents.find(event => event.globalSeq === selectedGlobalSeq) ?? null;
  const selectedStep = selectedEvent?.stepId
    ? (stepsQuery.data?.[selectedEvent.stepId] ?? null)
    : null;

  const timeline = eventsQuery.isPending ? (
    <LoadingState label="Cargando los eventos del run" />
  ) : eventsQuery.isError ? (
    <ErrorState message={eventsQuery.error.message} onRetry={() => void eventsQuery.refetch()} />
  ) : (
    <div className="flex gap-4 md:gap-8">
      <div className="flex-1">
        <div className="mb-2 flex justify-end gap-1">
          <ToggleButton
            label="árbol"
            icon={<ListTree data-icon="inline-start" />}
            isActive={timelineViewMode === 'tree'}
            onClick={() => setTimelineViewMode('tree')}
          />
          <ToggleButton
            label="timeline"
            icon={<List data-icon="inline-start" />}
            isActive={timelineViewMode === 'timeline'}
            onClick={() => setTimelineViewMode('timeline')}
          />
        </div>
        <RunTimeline
          events={isLiveMode() ? runEvents : revealedEvents}
          selectedGlobalSeq={selectedGlobalSeq}
          onSelectEvent={setSelectedGlobalSeq}
          viewMode={timelineViewMode}
          playback={isLiveMode() ? undefined : playback}
        />
      </div>
      <aside className="w-96 shrink-0">
        <StepInspector step={selectedStep} />
      </aside>
    </div>
  );

  const verificacion = certificateQuery.isPending ? (
    <LoadingState label="Cargando el certificado del run" />
  ) : certificateQuery.isError ? (
    <ErrorState
      message={certificateQuery.error.message}
      onRetry={() => void certificateQuery.refetch()}
    />
  ) : (
    <div className="mx-auto max-w-3xl">
      <CertificateView
        envelope={certificateQuery.data.envelope}
        onDownload={() =>
          downloadJson('trust-certificate.example.json', certificateQuery.data.wire)
        }
      />
    </div>
  );

  const ablacion = ablationQuery.isPending ? (
    <LoadingState label="Cargando las métricas de ablación" />
  ) : ablationQuery.isError ? (
    <ErrorState
      message={ablationQuery.error.message}
      onRetry={() => void ablationQuery.refetch()}
    />
  ) : ablationQuery.data.length === 0 ? (
    <EmptyState
      title="Sin métricas de ablación todavía."
      hint="Ejecute un run comparativo (cuántico vs. clásico) para poblar esta vista."
    />
  ) : (
    <div className="mx-auto max-w-5xl">
      <AblationPanel metrics={ablationQuery.data} />
    </div>
  );

  const procedencia =
    runEvents.length === 0 ? (
      <EmptyState
        title="Sin eventos registrados para este run."
        hint="La procedencia aparece en cuanto el run emite su primer evento."
      />
    ) : (
      <div className="mx-auto max-w-5xl">
        <div className="mb-2 flex justify-end gap-1">
          <ToggleButton
            label="compacto"
            icon={<LayoutList data-icon="inline-start" />}
            isActive={provenanceViewMode === 'compact'}
            onClick={() => setProvenanceViewMode('compact')}
          />
          <ToggleButton
            label="crudo"
            icon={<Braces data-icon="inline-start" />}
            isActive={provenanceViewMode === 'raw'}
            onClick={() => setProvenanceViewMode('raw')}
          />
        </div>
        <ProvenanceExplorer
          events={runEvents}
          filters={provenanceFilters}
          onFilterChange={setProvenanceFilters}
          viewMode={provenanceViewMode}
          page={{ cursor: provenanceCursor, pageSize: runEvents.length, hasMore: false }}
          onPageChange={setProvenanceCursor}
        />
      </div>
    );

  return (
    <RunDetail
      summary={summary}
      onDownloadBundle={() => {
        if (certificateQuery.data) {
          downloadJson('trust-certificate.example.json', certificateQuery.data.wire);
        }
      }}
      timeline={timeline}
      verificacion={verificacion}
      red={<GridSpike />}
      ablacion={ablacion}
      procedencia={procedencia}
    />
  );
}

function RunsScreen({
  onSelectRun
}: {
  readonly onSelectRun: (runId: string) => void;
}): React.ReactElement {
  const summariesQuery = useQuery(runSummariesQueryOptions());
  const [showNewRun, setShowNewRun] = useState(false);
  const createRunMutation = useCreateRun();

  // MVP task 2 — "Nuevo run" reemplaza la lista mientras está abierto; el
  // POST /runs real no existe todavía (createRun corta a DEMO_RUN_ID en
  // modo fixtures/demo — el flip a live ya está escrito en data/mutations).
  if (showNewRun) {
    return (
      <NewRunView
        onSubmit={input =>
          createRunMutation.mutate(input, {
            onSuccess: ({ runId }) => {
              setShowNewRun(false);
              onSelectRun(runId);
            }
          })
        }
        isPending={createRunMutation.isPending}
        error={createRunMutation.error?.message ?? null}
        onCancel={() => setShowNewRun(false)}
      />
    );
  }

  if (summariesQuery.isPending) return <LoadingState label="Cargando los runs del proyecto" />;
  if (summariesQuery.isError) {
    return (
      <ErrorState
        message={summariesQuery.error.message}
        onRetry={() => void summariesQuery.refetch()}
      />
    );
  }
  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setShowNewRun(true)}>
          <Plus data-icon="inline-start" />
          Nuevo run
        </Button>
      </div>
      <RunsView runs={summariesQuery.data} onSelectRun={onSelectRun} />
    </div>
  );
}

function ArtifactsScreen({
  onOpenRun
}: {
  readonly onOpenRun: (runId: string) => void;
}): React.ReactElement {
  const artifactsQuery = useQuery(artifactsQueryOptions());

  if (artifactsQuery.isPending) return <LoadingState label="Cargando los artifacts" />;
  if (artifactsQuery.isError) {
    return (
      <ErrorState
        message={artifactsQuery.error.message}
        onRetry={() => void artifactsQuery.refetch()}
      />
    );
  }
  return <ArtifactsView artifacts={artifactsQuery.data} onOpenRun={onOpenRun} />;
}

function KnowledgeScreen({
  onOpenRun
}: {
  readonly onOpenRun: (runId: string) => void;
}): React.ReactElement {
  const knowledgeQuery = useQuery(knowledgeQueryOptions());

  if (knowledgeQuery.isPending) return <LoadingState label="Cargando el knowledge" />;
  if (knowledgeQuery.isError) {
    return (
      <ErrorState
        message={knowledgeQuery.error.message}
        onRetry={() => void knowledgeQuery.refetch()}
      />
    );
  }
  return <KnowledgeView claims={knowledgeQuery.data} onOpenRun={onOpenRun} />;
}

function Studio(): React.ReactElement {
  const [section, setSection] = useState<SectionId>('runs');
  const [runId, setRunId] = useState<string | undefined>(undefined);

  const openRun = (id: string): void => {
    setSection('runs');
    setRunId(id);
  };
  const goToSection = (id: string): void => {
    setSection(id as SectionId);
    setRunId(undefined);
  };

  const breadcrumb = section === 'runs' && runId ? ['runs', runId] : [section];

  return (
    <AppShell
      projectName={PROJECT_NAME}
      sections={SECTIONS}
      activeSection={section}
      onSectionChange={goToSection}
      breadcrumb={breadcrumb}
    >
      <div className="mx-auto max-w-7xl px-4 py-8 md:px-8">
        {section === 'runs' &&
          (runId ? <RunDetailScreen runId={runId} /> : <RunsScreen onSelectRun={openRun} />)}
        {section === 'artifacts' && <ArtifactsScreen onOpenRun={openRun} />}
        {section === 'papers' && <PapersView />}
        {section === 'knowledge' && <KnowledgeScreen onOpenRun={openRun} />}
      </div>
    </AppShell>
  );
}

export default function App(): React.ReactElement {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <Studio />
      </QueryClientProvider>
    </ThemeProvider>
  );
}
