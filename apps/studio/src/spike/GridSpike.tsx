/**
 * Studio spike — IEEE-14 grid visualizer with verification overlay.
 *
 * Validates the preselected stack (Cytoscape.js + Tailwind + shadcn
 * conventions) for the "Visualizador de la red" view: colored partition,
 * highlighted cut edges, and per-island verification badges.
 *
 * No network access: data is static spike data (ieee14.ts). All future
 * real data flows through gatewayClient (INV-1). Colors come from the
 * design tokens (readToken — canvas can't read CSS vars) and the whole
 * instance re-initializes on theme change so the canvas re-themes too.
 */

import cytoscape from 'cytoscape';
import { CircleAlert, CircleCheck, Crosshair, Info, TriangleAlert } from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { RungBadge } from '@/components/verification/RungBadge';
import { RungLadder } from '@/components/verification/RungLadder';
import { rungLabel } from '@/components/verification/rungs';
import { useTheme } from '@/lib/theme';
import { readToken } from '@/lib/tokens';

import {
  BRANCHES,
  BUSES,
  ISLAND_COLOR_TOKENS,
  PARTITION,
  RUN_VERIFICATION,
  type Island
} from './ieee14';

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

function islandToken(islandId: string): string {
  return ISLAND_COLOR_TOKENS[islandId] ?? '--color-verdict-neutral';
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

/**
 * Lee los tokens en el momento de construir el estilo: cytoscape pinta
 * canvas y no sigue var(--color-*) — el efecto principal se re-ejecuta al
 * cambiar el tema para re-aplicar estos valores (DESIGN.md §5).
 */
function buildCyStyle(): cytoscape.StylesheetJson {
  const nodeLabelColor = readToken('--color-background');
  const generatorBorderColor = readToken('--color-foreground');
  const edgeColor = readToken('--color-muted-foreground');
  const cutEdgeColor = readToken('--color-verdict-fail');
  // Colores por isla resueltos EAGER, todos en este mismo instante:
  // cytoscape evalúa las funciones de estilo en su propio frame de render,
  // que puede caer a caballo del flip de data-theme — leerlos lazy pintaba
  // nodos con temas mezclados (hallazgo de la verificación MCP).
  const fallbackFill = readToken('--color-verdict-neutral');
  const islandFill = new Map(
    PARTITION.islands.map(island => [island.id, readToken(islandToken(island.id))])
  );

  return [
    {
      selector: 'node',
      style: {
        width: 34,
        height: 34,
        label: 'data(id)',
        'text-valign': 'center',
        'text-halign': 'center',
        color: nodeLabelColor,
        'font-size': 13,
        'font-weight': 'bold',
        'background-color': (ele: cytoscape.NodeSingular): string =>
          islandFill.get(ele.data('islandId') as string) ?? fallbackFill
      }
    },
    {
      selector: 'node[?isGenerator]',
      style: {
        shape: 'round-rectangle',
        'border-width': 3,
        'border-color': generatorBorderColor
      }
    },
    {
      selector: 'edge',
      style: {
        width: 2,
        'line-color': edgeColor,
        'curve-style': 'bezier'
      }
    },
    {
      selector: 'edge[?isCut]',
      style: {
        width: 3.5,
        'line-color': cutEdgeColor,
        'line-style': 'dashed'
      }
    }
  ];
}

export default function GridSpike(): React.ReactElement {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [overlays, setOverlays] = useState<readonly IslandOverlay[]>([]);
  const { theme } = useTheme();

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const cy = cytoscape({
      container,
      elements: buildElements(),
      style: buildCyStyle(),
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
    // `theme` como dependencia: el canvas no sigue los tokens CSS, así que
    // el toggle re-crea la instancia con los valores del tema nuevo (el
    // re-fit resultante es aceptable en el spike; F4 lo refina).
  }, [theme]);

  const handleCenter = (): void => {
    const cy = cyRef.current;
    if (!cy) {
      return;
    }
    cy.animate({ fit: { eles: cy.elements(), padding: 48 } }, { duration: 200 });
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 md:px-8">
      <header className="mb-8">
        <h1 className="font-display text-2xl leading-tight font-medium tracking-tight text-foreground md:text-3xl">
          Red IEEE-14 · partición verificada
        </h1>
        <p className="mt-4 max-w-3xl text-base leading-relaxed text-muted-foreground">
          Lo cuántico propone la partición; las anclas no-modelo la verifican. Cada isla lleva su
          badge; el nivel agregado es el escalón más débil del camino crítico.
        </p>
      </header>

      <div className="flex gap-4 md:gap-8">
        <div className="relative flex-1 overflow-hidden rounded-xl border bg-card">
          {/* Cytoscape fuerza position:relative inline en su contenedor — necesita altura explícita, no absolute/inset (hallazgo del spike). */}
          <div ref={containerRef} className="h-128 w-full" data-testid="cy-container" />
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
                    style={{ backgroundColor: `var(${islandToken(island.id)})` }}
                  />
                  {island.name}:{' '}
                  {island.verification.verdict === 'pass'
                    ? 'factible'
                    : island.verification.verdict}
                  <span className="flex items-center">
                    <RungLadder rung={island.verification.rung} />
                  </span>
                  <span className="font-mono font-medium">{island.verification.rung}</span>
                </Badge>
              </div>
            ))}
          <Button
            variant="outline"
            size="icon-sm"
            onClick={handleCenter}
            aria-label="Centrar el diagrama"
            title="Centrar el diagrama"
            className="absolute top-2 right-2 z-10 bg-background/90 backdrop-blur"
          >
            <Crosshair />
          </Button>
          <div className="absolute bottom-2 left-2 z-10 rounded-md bg-background/80 px-2 py-1 text-xs text-muted-foreground backdrop-blur">
            ▢ generador · ─ ─ arista cortada
          </div>
        </div>

        <aside className="flex w-80 flex-col gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Partición propuesta</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="flex flex-col gap-2 text-sm">
                {PARTITION.islands.map(island => (
                  <li key={island.id} className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-2">
                      <span
                        className="inline-block h-3 w-3 rounded-full"
                        style={{ backgroundColor: `var(${islandToken(island.id)})` }}
                      />
                      {island.name} · {island.busIds.length} buses
                    </span>
                    <RungBadge
                      rung={island.verification.rung}
                      verdict={island.verification.verdict}
                    />
                  </li>
                ))}
              </ul>
              <p className="mt-4 border-t pt-4 text-sm text-muted-foreground">
                Corte: {PARTITION.cutBranchIds.join(', ')} · costo {PARTITION.cutCost}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Verificación del run</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="flex flex-col gap-4">
                {RUN_VERIFICATION.attestations.map(att => (
                  <li key={att.verifierId} className="text-sm">
                    <div className="mb-1 flex items-center gap-2">
                      <RungBadge
                        rung={att.rung}
                        verdict={att.verdict}
                        detail={rungLabel(att.rung, att.anchorKind)}
                      />
                      <span className="font-mono text-xs text-muted-foreground">
                        {att.verifierId}
                      </span>
                    </div>
                    <p className="text-muted-foreground">{att.summary}</p>
                  </li>
                ))}
              </ul>
              <div className="mt-4 flex items-center gap-2 border-t pt-4">
                <RungLadder
                  rung={RUN_VERIFICATION.aggregateRung}
                  size="md"
                  className="text-foreground"
                />
                <p className="text-sm font-medium text-foreground">
                  Nivel agregado: escalón{' '}
                  <span className="font-mono">{RUN_VERIFICATION.aggregateRung}</span> (
                  {rungLabel(RUN_VERIFICATION.aggregateRung)}) — el más débil del camino crítico ·{' '}
                  {RUN_VERIFICATION.unanchoredSteps} pasos sin anclar
                </p>
              </div>
            </CardContent>
          </Card>
        </aside>
      </div>

      {/* Muestrario de estados (nivel 2 de la paleta, DESIGN.md §2) —
          pedido por Dylan para calibrar los colores de status en ambos
          temas; retirar cuando el sistema quede validado. */}
      <section aria-label="Muestrario de estados" className="mt-8 flex flex-col gap-2">
        <p className="text-xs tracking-wider text-muted-foreground uppercase">
          Estados del sistema · muestrario
        </p>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Alert>
            <Info />
            <AlertTitle>Modo demostración</AlertTitle>
            <AlertDescription>
              Este run corre sobre fixtures locales; no hay egress fuera del gateway.
            </AlertDescription>
          </Alert>
          <Alert variant="info">
            <Info />
            <AlertTitle>Nuevo evento en el stream</AlertTitle>
            <AlertDescription>
              El run recibió el evento 14 · verification.completed.
            </AlertDescription>
          </Alert>
          <Alert variant="success">
            <CircleCheck />
            <AlertTitle>Verificación completada</AlertTitle>
            <AlertDescription>
              Las 3 anclas confirmaron la partición; escalón agregado 3.
            </AlertDescription>
          </Alert>
          <Alert variant="warning">
            <TriangleAlert />
            <AlertTitle>Verificación degradada</AlertTitle>
            <AlertDescription>
              Un ancla no respondió a tiempo; el escalón agregado puede bajar.
            </AlertDescription>
          </Alert>
          <Alert variant="destructive">
            <CircleAlert />
            <AlertTitle>Ancla en fallo</AlertTitle>
            <AlertDescription>
              pandapower-powerflow reportó divergencia del flujo en la Isla B.
            </AlertDescription>
          </Alert>
        </div>
      </section>
    </div>
  );
}
