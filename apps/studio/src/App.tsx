import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import {
  BookOpen,
  Braces,
  FileText,
  LayoutList,
  List,
  ListTree,
  Map,
  Network,
  Package,
  Play,
  Plus
} from 'lucide-react';
import React, { useState } from 'react';

import { AppShell } from '@/components/app-shell/AppShell';
import { ReplayBanner } from '@/components/app-shell/ReplayBanner';
import { EmptyState, ErrorState, LoadingState } from '@/components/feedback/DataState';
import { Button } from '@/components/ui/button';
import { ThemeProvider } from '@/lib/theme';

import { isLiveMode } from './data/env';
import { ICE_GRID_DATASET } from './data/iceGrid';
import { useCreateRun } from './data/mutations';
import {
  ablationQueryOptions,
  artifactsQueryOptions,
  certificateQueryOptions,
  knowledgeQueryOptions,
  runEventsQueryOptions,
  runSummariesQueryOptions,
  rvspQueryOptions,
  stepEvidenceQueryOptions
} from './data/queries';
import { useRunEventStream } from './data/useRunEventStream';
import GridSpike from './spike/GridSpike';
import AblationPanel from './views/AblationPanel';
import ArtifactsView from './views/ArtifactsView';
import CertificateView from './views/CertificateView';
import DataFormatRouter from './views/DataFormatRouter';
import { downloadJson } from './views/downloadJson';
import KnowledgeView from './views/KnowledgeView';
import NewRunView from './views/NewRunView';
import PapersView from './views/PapersView';
import ProvenanceExplorer from './views/ProvenanceExplorer';
import RunDetail from './views/RunDetail';
import RunsView from './views/RunsView';
import RunThread from './views/RunThread';
import RunTimeline from './views/RunTimeline';
import RvsPChart from './views/RvsPChart';
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

const SECTION_ICON = 'size-4 shrink-0';

const SECTIONS: readonly {
  readonly id: SectionId;
  readonly label: string;
  readonly icon: React.ReactNode;
}[] = [
  { id: 'runs', label: 'Runs', icon: <Play className={SECTION_ICON} aria-hidden /> },
  { id: 'artifacts', label: 'Artifacts', icon: <Package className={SECTION_ICON} aria-hidden /> },
  { id: 'papers', label: 'Papers', icon: <FileText className={SECTION_ICON} aria-hidden /> },
  { id: 'knowledge', label: 'Knowledge', icon: <BookOpen className={SECTION_ICON} aria-hidden /> }
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

type RedViewMode = 'diagrama' | 'mapa';

/**
 * Slot "Red" de RunDetailScreen (D1 task 4 — honestidad de modo; D4 task 6
 * — spec superficie-visual.md §4.3 "dual diagrama + mapa, no reemplazo"):
 * en replay ofrece AMBAS vistas vía el mismo patrón ToggleButton que usan
 * timeline y procedencia — "Diagrama" (`GridSpike`, la partición benchmark
 * IEEE-14 del run, data ESTÁTICA fabricada) y "Mapa" (`DataFormatRouter` →
 * `GridMap`, la red nacional REAL del ICE, 70 subestaciones + 102 líneas).
 * Son DOS redes distintas — el mapa nunca sustituye al diagrama, lo
 * complementa (honestidad: no hay todavía un mapeo determinista entre la
 * instancia benchmark y el grid real, ver GridMap.tsx).
 *
 * En vivo no existe todavía un endpoint que devuelva la topología real del
 * run, así que anuncia "pendiente" en vez de mostrar cualquiera de las dos
 * vistas — el toggle tampoco aparece. Nombrada aparte (no inline en el
 * JSX) para poder testearla sin depender de `runSummariesQueryOptions` (que
 * en vivo devuelve `[]` hasta que exista `GET /runs` — D3/D4 — y
 * bloquearía la navegación a RunDetailScreen).
 */
export function RedSlot(): React.ReactElement {
  const [viewMode, setViewMode] = useState<RedViewMode>('diagrama');

  if (isLiveMode()) {
    return (
      <EmptyState
        title="Topología en vivo — pendiente"
        hint="La vista de red contra el payload real del run llega con D3/D4 (rutas + mapa)."
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end gap-1">
        <ToggleButton
          label="Diagrama"
          icon={<Network data-icon="inline-start" />}
          isActive={viewMode === 'diagrama'}
          onClick={() => setViewMode('diagrama')}
        />
        <ToggleButton
          label="Mapa"
          icon={<Map data-icon="inline-start" />}
          isActive={viewMode === 'mapa'}
          onClick={() => setViewMode('mapa')}
        />
      </div>
      {viewMode === 'diagrama' ? <GridSpike /> : <DataFormatRouter dataset={ICE_GRID_DATASET} />}
    </div>
  );
}

/** Vistas del run montadas como slots de RunDetail (queries + estado acá). */
function RunDetailScreen({
  runId,
  onBack
}: {
  readonly runId: string;
  readonly onBack?: () => void;
}): React.ReactElement {
  // No-op en modo fixtures/demo; en modo live alimenta el cache con el SSE
  // real (MVP task 1) — llamada incondicional, el hook decide adentro.
  useRunEventStream(runId);
  const summariesQuery = useQuery(runSummariesQueryOptions());
  const eventsQuery = useQuery(runEventsQueryOptions(runId));
  const runEvents = eventsQuery.data ?? [];
  // D3 — GET /runs/{id}/steps/{step_id}/evidence es POR PASO; se piden los
  // stepIds YA presentes en los eventos del run (nunca se inventa uno) y
  // se arma el mapa que el consumidor de abajo espera (Record<stepId, _>).
  const stepIds = Array.from(
    new Set(runEvents.map(event => event.stepId).filter((id): id is string => id !== undefined))
  );
  const stepsQuery = useQuery(stepEvidenceQueryOptions(runId, stepIds));
  const certificateQuery = useQuery(certificateQueryOptions(runId));
  const ablationQuery = useQuery(ablationQueryOptions(runId));
  const rvspQuery = useQuery(rvspQueryOptions(runId));
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

  // D6 (checkpoint 5) — el hilo conversacional es un layout sobre los MISMOS
  // eventos del run (misión → plan checklist → cierre); mismos estados de
  // carga/error que el timeline, misma fuente (`runEvents`), cero query nueva.
  const hilo = eventsQuery.isPending ? (
    <LoadingState label="Cargando el hilo del run" />
  ) : eventsQuery.isError ? (
    <ErrorState message={eventsQuery.error.message} onRetry={() => void eventsQuery.refetch()} />
  ) : (
    <RunThread summary={summary} events={runEvents} />
  );

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
        onDownload={() => downloadJson('bundle.json', certificateQuery.data.wire)}
      />
    </div>
  );

  // D5 (dataviz "r vs p") — contenido PRIMARIO de la sub-tab "Ablación": la
  // curva r-vs-p real de la ciencia (ver RvsPChart.tsx, divergencia
  // deliberada de spec superficie-visual.md §5). Sin endpoint en vivo
  // todavía (rvspQueryOptions), mismo patrón de EmptyState que el resto.
  const rvspSection = rvspQuery.isPending ? (
    <LoadingState label="Cargando la curva r vs p" />
  ) : rvspQuery.isError ? (
    <ErrorState message={rvspQuery.error.message} onRetry={() => void rvspQuery.refetch()} />
  ) : rvspQuery.data === null ? (
    <EmptyState
      title="Sin curva r vs p todavía."
      hint="Esta vista solo existe en modo réplica hoy — el endpoint en vivo llega con un run comparativo real."
    />
  ) : (
    <RvsPChart experiment={rvspQuery.data} />
  );

  // Contenido SECUNDARIO: la ablación cuántico vs. clásico ya existente
  // (nota 07 §1.3) — ambas son vistas honestas de ablación, conviven en la
  // misma sub-tab (D5 no reemplaza AblationPanel, lo complementa).
  const ablationSection = ablationQuery.isPending ? (
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
    <AblationPanel metrics={ablationQuery.data} />
  );

  const ablacion = (
    <div className="mx-auto flex max-w-5xl flex-col gap-8">
      {rvspSection}
      <div className="flex flex-col gap-4 border-t border-border pt-6">
        <h3 className="text-sm font-medium text-muted-foreground">
          Ablación — cuántico vs. clásico
        </h3>
        {ablationSection}
      </div>
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
      onBack={onBack}
      onDownloadBundle={() => {
        if (certificateQuery.data) {
          downloadJson('bundle.json', certificateQuery.data.wire);
        }
      }}
      hilo={hilo}
      timeline={timeline}
      verificacion={verificacion}
      red={<RedSlot />}
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
      onBreadcrumbNavigate={index => {
        // Tramo 0 = la raíz de la sección actual (p. ej. 'runs' desde un
        // run abierto) — navegar ahí es cerrar el detalle.
        if (index === 0) {
          goToSection(section);
        }
      }}
      banner={isLiveMode() ? undefined : <ReplayBanner />}
    >
      <div className="mx-auto max-w-7xl px-4 py-8 md:px-8">
        {section === 'runs' &&
          (runId ? (
            <RunDetailScreen runId={runId} onBack={() => setRunId(undefined)} />
          ) : (
            <RunsScreen onSelectRun={openRun} />
          ))}
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
