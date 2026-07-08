/**
 * Studio spike — IEEE-14 grid visualizer with verification overlay.
 *
 * Validates the preselected stack (Cytoscape.js + Tailwind + shadcn
 * conventions) for the "Visualizador de la red" view: colored partition,
 * highlighted cut edges, and per-island verification badges.
 *
 * No network access: data is static spike data (ieee14.ts). All future
 * real data flows through gatewayClient (INV-1).
 */

import cytoscape from 'cytoscape';
import React, { useEffect, useRef, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader } from '@/components/ui/card';

import { BRANCHES, BUSES, ISLAND_COLORS, PARTITION, RUN_VERIFICATION, type Island } from './ieee14';

const RUNG_LABELS: Readonly<Record<number, string>> = {
  1: 'óptimo exacto',
  2: 'ejecución',
  3: 'verdad conocida',
  4: 'propiedad',
  5: 'consenso',
  6: 'detección',
  7: 'humano'
};

const BADGE_MARGIN_PX = 8;
const BADGE_MAX_WIDTH_PX = 200;
const BADGE_HEIGHT_PX = 28;
const PAN_MARGIN_PX = 80;
const MIN_ZOOM = 0.3;
const MAX_ZOOM = 3;

function clamp(value: number, min: number, max: number): number {
  return min > max ? (min + max) / 2 : Math.min(max, Math.max(min, value));
}

interface IslandOverlay {
  readonly island: Island;
  readonly left: number;
  readonly top: number;
  readonly isVisible: boolean;
}

function islandOfBus(busId: string): string {
  const island = PARTITION.islands.find(i => i.busIds.includes(busId));
  return island ? island.id : 'unassigned';
}

function buildElements(): cytoscape.ElementDefinition[] {
  const nodes: cytoscape.ElementDefinition[] = BUSES.map(bus => ({
    data: { id: bus.id, islandId: islandOfBus(bus.id), isGenerator: bus.isGenerator },
    position: { x: bus.x, y: bus.y }
  }));
  const edges: cytoscape.ElementDefinition[] = BRANCHES.map(branch => ({
    data: {
      id: branch.id,
      source: branch.from,
      target: branch.to,
      isCut: PARTITION.cutBranchIds.includes(branch.id)
    }
  }));
  return [...nodes, ...edges];
}

const CY_STYLE: cytoscape.StylesheetJson = [
  {
    selector: 'node',
    style: {
      width: 34,
      height: 34,
      label: 'data(id)',
      'text-valign': 'center',
      'text-halign': 'center',
      color: '#ffffff',
      'font-size': 13,
      'font-weight': 'bold',
      'background-color': (ele: cytoscape.NodeSingular): string =>
        ISLAND_COLORS[ele.data('islandId') as string] ?? '#71717a'
    }
  },
  {
    selector: 'node[?isGenerator]',
    style: {
      shape: 'round-rectangle',
      'border-width': 3,
      'border-color': '#18181b'
    }
  },
  {
    selector: 'edge',
    style: {
      width: 2,
      'line-color': '#a1a1aa',
      'curve-style': 'bezier'
    }
  },
  {
    selector: 'edge[?isCut]',
    style: {
      width: 3.5,
      'line-color': '#e11d48',
      'line-style': 'dashed'
    }
  }
];

export default function GridSpike(): React.ReactElement {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [overlays, setOverlays] = useState<readonly IslandOverlay[]>([]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const cy = cytoscape({
      container,
      elements: buildElements(),
      style: CY_STYLE,
      layout: { name: 'preset' },
      autoungrabify: true,
      minZoom: MIN_ZOOM,
      maxZoom: MAX_ZOOM
    });
    cyRef.current = cy;

    const updateOverlays = (): void => {
      const { width, height } = container.getBoundingClientRect();
      const next = PARTITION.islands.map((island): IslandOverlay => {
        const members = cy.nodes().filter(node => island.busIds.includes(node.id()));
        const box = members.renderedBoundingBox();
        return {
          island,
          left: clamp(box.x1, BADGE_MARGIN_PX, width - BADGE_MAX_WIDTH_PX - BADGE_MARGIN_PX),
          top: clamp(box.y1 - 34, BADGE_MARGIN_PX, height - BADGE_HEIGHT_PX - BADGE_MARGIN_PX),
          // Hide instead of clamp when the island itself has panned fully
          // out of view — clamping would otherwise pin the badge to the
          // container edge over empty canvas, floating with nothing to
          // anchor to (ficha B4).
          isVisible: box.x2 > 0 && box.x1 < width && box.y2 > 0 && box.y1 < height
        };
      });
      setOverlays(next);
    };

    // cytoscape's minZoom/maxZoom (above) bound zoom but not pan (B3): an
    // unbounded pan lets the whole graph drift out of the container with
    // no way back short of a reload. Clamp on every 'pan' event so the
    // bounding box always keeps a margin inside the viewport; a clamped
    // cy.pan() re-fires 'pan' but converges immediately since the second
    // pass computes a no-op delta.
    const clampPan = (): void => {
      const bb = cy.elements().boundingBox();
      const zoom = cy.zoom();
      const pan = cy.pan();
      const { width, height } = container.getBoundingClientRect();

      const nextX = clamp(
        pan.x,
        PAN_MARGIN_PX - bb.x2 * zoom,
        width - PAN_MARGIN_PX - bb.x1 * zoom
      );
      const nextY = clamp(
        pan.y,
        PAN_MARGIN_PX - bb.y2 * zoom,
        height - PAN_MARGIN_PX - bb.y1 * zoom
      );

      if (Math.abs(nextX - pan.x) > 0.5 || Math.abs(nextY - pan.y) > 0.5) {
        cy.pan({ x: nextX, y: nextY });
      }
    };

    // The old rAF-deferred fit (session 6) still raced the Tabs layout
    // pass and could measure a stale zero-size rect (B2). A ResizeObserver
    // reacts to every real size change so cytoscape's cached container
    // dimensions never go stale (cy.resize() must run every time, or a
    // later resize renders against the old, wrong size) — but cy.fit()
    // itself only runs once, the first time the container reports a real
    // size, so it doesn't keep yanking the view out from under a user who
    // has since panned or zoomed.
    let hasFitted = false;
    const handleContainerResize = (): void => {
      const { width, height } = container.getBoundingClientRect();
      if (width === 0 || height === 0) {
        return;
      }
      cy.resize();
      if (!hasFitted) {
        hasFitted = true;
        cy.fit(undefined, 48);
      }
      updateOverlays();
    };

    const resizeObserver = new ResizeObserver(handleContainerResize);
    resizeObserver.observe(container);
    handleContainerResize();

    cy.on('pan', clampPan);
    cy.on('pan zoom resize', updateOverlays);

    return () => {
      resizeObserver.disconnect();
      cyRef.current = null;
      cy.destroy();
    };
  }, []);

  const handleCenter = (): void => {
    const cy = cyRef.current;
    if (!cy) {
      return;
    }
    cy.animate({ fit: { eles: cy.elements(), padding: 48 } }, { duration: 200 });
  };

  return (
    <div className="mx-auto max-w-6xl p-6">
      <header className="mb-4">
        <h1 className="text-xl font-bold text-zinc-900">
          Chimera Studio · spike — red IEEE-14, partición verificada
        </h1>
        <p className="text-sm text-zinc-500">
          Lo cuántico propone la partición; las anclas no-modelo la verifican. Cada isla lleva su
          badge; el nivel agregado es el escalón más débil del camino crítico.
        </p>
      </header>

      <div className="flex gap-4">
        <div className="relative flex-1 overflow-hidden rounded-xl border border-zinc-200 bg-zinc-50">
          {/* Cytoscape fuerza position:relative inline en su contenedor — necesita altura explícita, no absolute/inset (hallazgo del spike). */}
          <div ref={containerRef} className="h-[560px] w-full" data-testid="cy-container" />
          {overlays
            .filter(overlay => overlay.isVisible)
            .map(({ island, left, top }) => (
              <div
                key={island.id}
                className="pointer-events-none absolute z-10"
                style={{ left, top }}
              >
                <Badge
                  variant={island.verification.verdict}
                  title={island.verification.summary}
                  className="max-w-[200px]"
                >
                  <span
                    className="inline-block h-2 w-2 shrink-0 rounded-full"
                    style={{ backgroundColor: ISLAND_COLORS[island.id] }}
                  />
                  {island.name}:{' '}
                  {island.verification.verdict === 'pass'
                    ? 'factible'
                    : island.verification.verdict}
                  {' · '}escalón {island.verification.rung}
                </Badge>
              </div>
            ))}
          <button
            type="button"
            onClick={handleCenter}
            className="absolute top-2 right-2 z-10 rounded-md border border-zinc-300 bg-white/90 px-2 py-1 text-xs font-medium text-zinc-700 hover:bg-white"
          >
            Centrar
          </button>
          <div className="absolute bottom-2 left-2 z-10 rounded-md bg-white/90 px-2 py-1 text-xs text-zinc-600">
            ▢ generador · ─ ─ arista cortada
          </div>
        </div>

        <aside className="flex w-[340px] flex-col gap-4">
          <Card>
            <CardHeader>Partición propuesta</CardHeader>
            <CardContent>
              <ul className="flex flex-col gap-2 text-sm">
                {PARTITION.islands.map(island => (
                  <li key={island.id} className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-2">
                      <span
                        className="inline-block h-3 w-3 rounded-full"
                        style={{ backgroundColor: ISLAND_COLORS[island.id] }}
                      />
                      {island.name} · {island.busIds.length} buses
                    </span>
                    <Badge variant={island.verification.verdict}>
                      escalón {island.verification.rung}
                    </Badge>
                  </li>
                ))}
              </ul>
              <p className="mt-3 border-t border-zinc-100 pt-2 text-sm text-zinc-600">
                Corte: {PARTITION.cutBranchIds.join(', ')} · costo {PARTITION.cutCost}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>Verificación del run</CardHeader>
            <CardContent>
              <ul className="flex flex-col gap-3">
                {RUN_VERIFICATION.attestations.map(att => (
                  <li key={att.verifierId} className="text-sm">
                    <div className="mb-1 flex items-center gap-2">
                      <Badge variant={att.verdict}>
                        escalón {att.rung} · {RUNG_LABELS[att.rung] ?? att.anchorKind}
                      </Badge>
                      <span className="text-xs text-zinc-400">{att.verifierId}</span>
                    </div>
                    <p className="text-zinc-600">{att.summary}</p>
                  </li>
                ))}
              </ul>
              <p className="mt-3 border-t border-zinc-100 pt-2 text-sm font-semibold text-zinc-800">
                Nivel agregado: escalón {RUN_VERIFICATION.aggregateRung} (
                {RUNG_LABELS[RUN_VERIFICATION.aggregateRung]}) — el más débil del camino crítico ·{' '}
                {RUN_VERIFICATION.unanchoredSteps} pasos sin anclar
              </p>
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  );
}
