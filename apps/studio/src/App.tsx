import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import {
  BookOpen,
  Braces,
  FileText,
  LayoutList,
  List,
  ListTree,
  Package,
  Play,
  Plus
} from 'lucide-react';
import React, { useState } from 'react';

import { AppShell } from '@/components/app-shell/AppShell';
import { ReplayBanner } from '@/components/app-shell/ReplayBanner';
import { EmptyState, ErrorState, LoadingState } from '@/components/feedback/DataState';
import { ToggleButton } from '@/components/layout/ToggleButton';
import { Button } from '@/components/ui/button';
import { ThemeProvider } from '@/lib/theme';

import { isLiveMode } from './data/env';
import { useCancelRun, useCreateRun, useRespondApproval, useSendMessage } from './data/mutations';
import {
  artifactsQueryOptions,
  certificateQueryOptions,
  knowledgeQueryOptions,
  runEventsQueryOptions,
  runSummariesQueryOptions,
  stepEvidenceQueryOptions
} from './data/queries';
import { DOMAIN_LENSES, deriveLensContext, resolveLenses } from './lenses';
import { useRunEventStream } from './data/useRunEventStream';
import ArtifactsView from './views/ArtifactsView';
import CertificateView from './views/CertificateView';
import { downloadJson } from './views/downloadJson';
import KnowledgeView from './views/KnowledgeView';
import NewRunView from './views/NewRunView';
import PapersView from './views/PapersView';
import ProvenanceExplorer from './views/ProvenanceExplorer';
import RunDetail from './views/RunDetail';
import RunsView from './views/RunsView';
import RunThread from './views/RunThread';
import RunTimeline from './views/RunTimeline';
import StepInspector from './views/StepInspector';
import { usePlaybackReveal } from './views/usePlaybackReveal';

import type { ProvenanceFilters } from './views/types';

/**
 * Chimera Studio — raíz (dominio Studio F2, shell B).
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

/** Vistas del run montadas como slots de RunDetail (queries + estado acá). */
function RunDetailScreen({
  runId,
  onBack,
  onContinueThread
}: {
  readonly runId: string;
  readonly onBack?: () => void;
  /**
   * P3-D §Contrato-4 — el stream terminal no acepta appends (409), así que
   * continuar la conversación es abrir un run NUEVO que cite a este como
   * hilo. Sin esta salida, el 409 sería un callejón sin salida.
   */
  readonly onContinueThread?: (threadId: string) => void;
}): React.ReactElement {
  // No-op en modo fixtures/demo; en modo live alimenta el cache con el SSE
  // real (Nivel-1 task 1) — llamada incondicional, el hook decide adentro.
  useRunEventStream(runId);
  const summariesQuery = useQuery(runSummariesQueryOptions());
  // P3-D — las tres acciones de conversación del run. Solo se CONECTAN en
  // modo live: en réplica no hay servidor que reciba el POST, y un botón que
  // no puede cumplir lo que promete es peor que su ausencia (regla 1 del plan
  // paralelo: cero mocks silenciosos).
  const sendMessage = useSendMessage(runId);
  const cancelRun = useCancelRun(runId);
  const respondApproval = useRespondApproval(runId);
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

  // D6 (decisión #93) — el hilo conversacional es un layout sobre los MISMOS
  // eventos del run (misión → plan checklist → cierre); mismos estados de
  // carga/error que el timeline, misma fuente (`runEvents`), cero query nueva.
  const hilo = eventsQuery.isPending ? (
    <LoadingState label="Cargando el hilo del run" />
  ) : eventsQuery.isError ? (
    <ErrorState message={eventsQuery.error.message} onRetry={() => void eventsQuery.refetch()} />
  ) : (
    <RunThread
      summary={summary}
      events={runEvents}
      {...(isLiveMode() && {
        onSendMessage: (text: string) => sendMessage.mutate(text),
        isSendingMessage: sendMessage.isPending,
        sendError: sendMessage.error?.message ?? null,
        onRespondApproval: (approvalId: string, response: unknown) =>
          respondApproval.mutate({ approvalId, response }),
        approvalError: respondApproval.error?.message ?? null
      })}
      {...(onContinueThread !== undefined && {
        onContinueThread: () => onContinueThread(runId)
      })}
    />
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

  // P13 — las lentes de dominio se RESUELVEN contra lo que el run declara
  // (claim types + capability ids del stream y del certificado). El shell no
  // sabe qué lentes existen: agregar un dominio es registrar una lente en
  // src/lenses/index.ts, no editar esta función.
  const lensContext = deriveLensContext(
    runId,
    runEvents,
    certificateQuery.data?.envelope.payload.predicate.conclusions ?? []
  );
  const lenses = resolveLenses(DOMAIN_LENSES, lensContext).map(lens => ({
    id: lens.id,
    label: lens.label,
    content: lens.render(lensContext)
  }));

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
      {...(isLiveMode() && {
        onCancelRun: () => cancelRun.mutate(undefined),
        isCancelling: cancelRun.isPending,
        cancelError: cancelRun.error?.message ?? null
      })}
      onDownloadBundle={() => {
        if (certificateQuery.data) {
          downloadJson('bundle.json', certificateQuery.data.wire);
        }
      }}
      hilo={hilo}
      timeline={timeline}
      verificacion={verificacion}
      lenses={lenses}
      procedencia={procedencia}
    />
  );
}

function RunsScreen({
  onSelectRun,
  threadId,
  onThreadConsumed
}: {
  readonly onSelectRun: (runId: string) => void;
  /** Presente ⇒ el form abre continuando ese hilo (§Contrato-4). */
  readonly threadId?: string;
  readonly onThreadConsumed?: () => void;
}): React.ReactElement {
  const summariesQuery = useQuery(runSummariesQueryOptions());
  const [showNewRun, setShowNewRun] = useState(false);
  const createRunMutation = useCreateRun();
  const formAbierto = showNewRun || threadId !== undefined;

  const cerrarForm = (): void => {
    setShowNewRun(false);
    onThreadConsumed?.();
  };

  // Nivel-1 task 2 — "Nuevo run" reemplaza la lista mientras está abierto; el
  // POST /runs real no existe todavía (createRun corta a DEMO_RUN_ID en
  // modo fixtures/demo — el flip a live ya está escrito en data/mutations).
  if (formAbierto) {
    return (
      <NewRunView
        onSubmit={input =>
          createRunMutation.mutate(input, {
            onSuccess: ({ runId }) => {
              cerrarForm();
              onSelectRun(runId);
            }
          })
        }
        isPending={createRunMutation.isPending}
        error={createRunMutation.error?.message ?? null}
        onCancel={cerrarForm}
        {...(threadId !== undefined && { threadId })}
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
  const [threadId, setThreadId] = useState<string | undefined>(undefined);

  const openRun = (id: string): void => {
    setSection('runs');
    setRunId(id);
    setThreadId(undefined);
  };

  // §Contrato-4 — continuar un hilo cerrado: se deja el detalle y se abre el
  // form citando al run raíz. El hilo es correlación de LECTURA entre
  // corridas; cada run conserva su propio stream y su propio certificado.
  const continueThread = (raiz: string): void => {
    setRunId(undefined);
    setThreadId(raiz);
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
            <RunDetailScreen
              runId={runId}
              onBack={() => setRunId(undefined)}
              onContinueThread={continueThread}
            />
          ) : (
            <RunsScreen
              onSelectRun={openRun}
              {...(threadId !== undefined && { threadId })}
              onThreadConsumed={() => setThreadId(undefined)}
            />
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
