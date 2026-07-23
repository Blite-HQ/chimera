import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { Braces, LayoutList, List, ListTree } from 'lucide-react';
import React, { useState } from 'react';

import { AppShell } from '@/components/app-shell/AppShell';
import { EmptyState, ErrorState, LoadingState } from '@/components/feedback/DataState';
import { Button } from '@/components/ui/button';
import { TabsContent } from '@/components/ui/tabs';
import { ThemeProvider } from '@/lib/theme';

import {
  DEMO_RUN_ID,
  ablationQueryOptions,
  certificateQueryOptions,
  runEventsQueryOptions,
  stepEvidenceQueryOptions
} from './data/queries';
import GridSpike from './spike/GridSpike';
import AblationPanel from './views/AblationPanel';
import CertificateView from './views/CertificateView';
import { downloadJson } from './views/downloadJson';
import ProvenanceExplorer from './views/ProvenanceExplorer';
import RunTimeline from './views/RunTimeline';
import StepInspector from './views/StepInspector';
import type { ProvenanceFilters } from './views/types';
import { usePlaybackReveal } from './views/usePlaybackReveal';

/**
 * Chimera Studio root application component.
 *
 * F3: TODO dato llega por src/data/** (queryOptions + Zod en la frontera —
 * regla depcruise: ni App ni las vistas importan fixtures/gatewayClient
 * directo). Hoy las queryFn sirven fixtures; S10 cambia la fuente sin tocar
 * este árbol. INV-1 intacto: cuando haya red, vive en gatewayClient.ts.
 *
 * Navigation is a plain useState segmented control presented by AppShell
 * (topbar real, F1) — still a demo shell; F2 lo migra a TanStack Router.
 */

type TabId = 'red' | 'timeline' | 'certificado' | 'ablacion' | 'procedencia';

const TABS: readonly { readonly id: TabId; readonly label: string }[] = [
  { id: 'red', label: 'Red' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'certificado', label: 'Certificado' },
  { id: 'ablacion', label: 'Ablación' },
  { id: 'procedencia', label: 'Procedencia' }
];

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

function StudioTabs(): React.ReactElement {
  const [activeTab, setActiveTab] = useState<TabId>('red');

  const eventsQuery = useQuery(runEventsQueryOptions(DEMO_RUN_ID));
  const stepsQuery = useQuery(stepEvidenceQueryOptions(DEMO_RUN_ID));
  const certificateQuery = useQuery(certificateQueryOptions(DEMO_RUN_ID));
  const ablationQuery = useQuery(ablationQueryOptions(DEMO_RUN_ID));

  const runEvents = eventsQuery.data ?? [];
  const { revealedEvents, playback } = usePlaybackReveal(runEvents);
  const [selectedGlobalSeq, setSelectedGlobalSeq] = useState<number | undefined>(undefined);
  const [timelineViewMode, setTimelineViewMode] = useState<'tree' | 'timeline'>('tree');

  const [provenanceFilters, setProvenanceFilters] = useState<ProvenanceFilters>({});
  const [provenanceViewMode, setProvenanceViewMode] = useState<'compact' | 'raw'>('compact');
  const [provenanceCursor, setProvenanceCursor] = useState(0);

  const selectedEvent = revealedEvents.find(event => event.globalSeq === selectedGlobalSeq) ?? null;
  const selectedStep = selectedEvent?.stepId
    ? (stepsQuery.data?.[selectedEvent.stepId] ?? null)
    : null;

  return (
    <AppShell tabs={TABS} activeTab={activeTab} onTabChange={value => setActiveTab(value as TabId)}>
      <TabsContent value="red">
        <GridSpike />
      </TabsContent>

      <TabsContent value="timeline">
        <div className="mx-auto flex max-w-7xl gap-4 px-4 py-8 md:gap-8 md:px-8">
          {eventsQuery.isPending ? (
            <div className="flex-1">
              <LoadingState label="Cargando los eventos del run" />
            </div>
          ) : eventsQuery.isError ? (
            <div className="flex-1">
              <ErrorState
                message={eventsQuery.error.message}
                onRetry={() => void eventsQuery.refetch()}
              />
            </div>
          ) : (
            <>
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
                  events={revealedEvents}
                  selectedGlobalSeq={selectedGlobalSeq}
                  onSelectEvent={setSelectedGlobalSeq}
                  viewMode={timelineViewMode}
                  playback={playback}
                />
              </div>
              <aside className="w-96 shrink-0">
                <StepInspector step={selectedStep} />
              </aside>
            </>
          )}
        </div>
      </TabsContent>

      <TabsContent value="certificado">
        <div className="mx-auto max-w-3xl px-4 py-8 md:px-8">
          {certificateQuery.isPending ? (
            <LoadingState label="Cargando el certificado del run" />
          ) : certificateQuery.isError ? (
            <ErrorState
              message={certificateQuery.error.message}
              onRetry={() => void certificateQuery.refetch()}
            />
          ) : (
            <CertificateView
              envelope={certificateQuery.data.envelope}
              onDownload={() =>
                downloadJson('trust-certificate.example.json', certificateQuery.data.wire)
              }
            />
          )}
        </div>
      </TabsContent>

      <TabsContent value="ablacion">
        <div className="mx-auto max-w-5xl px-4 py-8 md:px-8">
          {ablationQuery.isPending ? (
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
          )}
        </div>
      </TabsContent>

      <TabsContent value="procedencia">
        <div className="mx-auto max-w-5xl px-4 py-8 md:px-8">
          {eventsQuery.isPending ? (
            <LoadingState label="Cargando la procedencia del run" />
          ) : eventsQuery.isError ? (
            <ErrorState
              message={eventsQuery.error.message}
              onRetry={() => void eventsQuery.refetch()}
            />
          ) : runEvents.length === 0 ? (
            <EmptyState
              title="Sin eventos registrados para este run."
              hint="La procedencia aparece en cuanto el run emite su primer evento."
            />
          ) : (
            <>
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
            </>
          )}
        </div>
      </TabsContent>
    </AppShell>
  );
}

export default function App(): React.ReactElement {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <StudioTabs />
      </QueryClientProvider>
    </ThemeProvider>
  );
}
