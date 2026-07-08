import React, { useState } from 'react';

import { AppShell } from '@/components/app-shell/AppShell';
import { TabsContent } from '@/components/ui/tabs';
import { ThemeProvider } from '@/lib/theme';

import { ABLATION_METRICS } from './fixtures/ablationMetrics';
import { EXAMPLE_CERTIFICATE } from './fixtures/certificate';
import { RUN_EVENTS } from './fixtures/runEvents';
import { STEP_EVIDENCE } from './fixtures/stepEvidence';
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
 * All outbound calls go through gatewayClient.ts (Invariant 1 — gateway
 * chokepoint). This component never calls fetch/axios directly — every
 * view here renders static fixtures (src/fixtures/), no backend.
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

function ToggleButton({
  label,
  isActive,
  onClick
}: {
  readonly label: string;
  readonly isActive: boolean;
  readonly onClick: () => void;
}): React.ReactElement {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={isActive}
      className={`rounded-md border px-2 py-1 text-xs font-medium transition-colors ${
        isActive
          ? 'border-primary bg-primary text-primary-foreground'
          : 'border-border bg-card text-muted-foreground hover:bg-muted hover:text-foreground'
      }`}
    >
      {label}
    </button>
  );
}

export default function App(): React.ReactElement {
  const [activeTab, setActiveTab] = useState<TabId>('red');

  const { revealedEvents, playback } = usePlaybackReveal(RUN_EVENTS);
  const [selectedGlobalSeq, setSelectedGlobalSeq] = useState<number | undefined>(undefined);
  const [timelineViewMode, setTimelineViewMode] = useState<'tree' | 'timeline'>('tree');

  const [provenanceFilters, setProvenanceFilters] = useState<ProvenanceFilters>({});
  const [provenanceViewMode, setProvenanceViewMode] = useState<'compact' | 'raw'>('compact');
  const [provenanceCursor, setProvenanceCursor] = useState(0);

  const selectedEvent = revealedEvents.find(event => event.globalSeq === selectedGlobalSeq) ?? null;
  const selectedStep = selectedEvent?.stepId ? (STEP_EVIDENCE[selectedEvent.stepId] ?? null) : null;

  return (
    <ThemeProvider>
      <AppShell
        tabs={TABS}
        activeTab={activeTab}
        onTabChange={value => setActiveTab(value as TabId)}
      >
        <TabsContent value="red">
          <GridSpike />
        </TabsContent>

        <TabsContent value="timeline">
          <div className="mx-auto flex max-w-6xl gap-4 p-6">
            <div className="flex-1">
              <div className="mb-2 flex justify-end gap-1">
                <ToggleButton
                  label="árbol"
                  isActive={timelineViewMode === 'tree'}
                  onClick={() => setTimelineViewMode('tree')}
                />
                <ToggleButton
                  label="timeline"
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
            <aside className="w-[380px] shrink-0">
              <StepInspector step={selectedStep} />
            </aside>
          </div>
        </TabsContent>

        <TabsContent value="certificado">
          <div className="mx-auto max-w-3xl p-6">
            <CertificateView
              envelope={EXAMPLE_CERTIFICATE}
              onDownload={() => downloadJson('trust-certificate.example.json', EXAMPLE_CERTIFICATE)}
            />
          </div>
        </TabsContent>

        <TabsContent value="ablacion">
          <div className="mx-auto max-w-5xl p-6">
            <AblationPanel metrics={ABLATION_METRICS} />
          </div>
        </TabsContent>

        <TabsContent value="procedencia">
          <div className="mx-auto max-w-5xl p-6">
            <div className="mb-2 flex justify-end gap-1">
              <ToggleButton
                label="compacto"
                isActive={provenanceViewMode === 'compact'}
                onClick={() => setProvenanceViewMode('compact')}
              />
              <ToggleButton
                label="crudo"
                isActive={provenanceViewMode === 'raw'}
                onClick={() => setProvenanceViewMode('raw')}
              />
            </div>
            <ProvenanceExplorer
              events={RUN_EVENTS}
              filters={provenanceFilters}
              onFilterChange={setProvenanceFilters}
              viewMode={provenanceViewMode}
              page={{ cursor: provenanceCursor, pageSize: RUN_EVENTS.length, hasMore: false }}
              onPageChange={setProvenanceCursor}
            />
          </div>
        </TabsContent>
      </AppShell>
    </ThemeProvider>
  );
}
