/**
 * GridMap (D4) — la red nacional REAL del ICE (70 subestaciones + 102
 * líneas de transmisión) proyectada a SVG con d3-geo. Fase 1: aire-gap, sin
 * tiles ni red — el GeoJSON llega bundleado vía `data/iceGrid.ts` (INV-1),
 * jamás un fetch a un servidor de mapas.
 *
 * SVG en vez de canvas (a diferencia de spike/GridSpike.tsx): d3 pinta
 * elementos DOM reales, que SÍ siguen `var(--color-*)` — el tema cambia
 * solo, sin reinicializar nada (ver `readToken`/`lib/tokens.ts`, que existe
 * justamente porque cytoscape/canvas NO tiene ese lujo).
 *
 * Proyección sobre un lienzo lógico fijo (viewBox), no el tamaño medido del
 * contenedor: `fitExtent` corre una sola vez con las dimensiones lógicas y
 * el SVG escala vía CSS (`w-full h-auto` + viewBox) — evita depender de
 * ResizeObserver/getBoundingClientRect, que jsdom no implementa realmente
 * (ver el workaround que sí necesita GridSpike con cytoscape).
 *
 * Honestidad de dato (B2/R5, mandato Dylan): el grid real del ICE es una
 * red DISTINTA a la instancia benchmark del run (ieee6/ieee14) — hoy no
 * existe un mapeo determinista bus↔subestación entre ambas. `partition` se
 * declara como seam para cuando ese mapeo exista, pero NO se renderiza: cero
 * islas/veredictos fabricados sobre datos reales. El grid se muestra
 * completo y sin partición.
 */

import { geoMercator, geoPath } from 'd3-geo';
import React, { useMemo } from 'react';

import { normalizeProvincia } from '../data/iceGridSchemas';

import type { GeoJsonGridDataset, TransmissionLineFeature } from '../data/iceGridSchemas';

const VIEWBOX_WIDTH = 800;
const VIEWBOX_HEIGHT = 520;
const PROJECTION_PADDING_PX = 24;

/** kV → grosor de trazo (230kV es la línea troncal, más gruesa que 138kV). */
const LINE_WIDTH_PX_BY_KV: Readonly<Record<number, number>> = {
  230: 3,
  138: 1.5
};
const DEFAULT_LINE_WIDTH_PX = 1;
const SUBSTATION_RADIUS_PX = 4;

/**
 * Seam para la superposición de partición/verificación (B2/R5) — futuro
 * trabajo, NO implementado acá. Cuando exista un mapeo bus↔subestación real
 * entre la instancia benchmark del run y el grid del ICE, este prop puede
 * colorear islas sobre el mapa real sin cambiar el resto de GridMap.
 */
export interface GridPartitionOverlay {
  readonly islands: readonly {
    readonly id: string;
    readonly label: string;
    readonly substationNames: readonly string[];
  }[];
}

export interface GridMapProps {
  readonly dataset: GeoJsonGridDataset;
  /** Reservado (B2/R5) — declarado pero deliberadamente sin renderizar. */
  readonly partition?: GridPartitionOverlay;
}

function lineWidthPx(feature: TransmissionLineFeature): number {
  return LINE_WIDTH_PX_BY_KV[feature.properties.Voltaje] ?? DEFAULT_LINE_WIDTH_PX;
}

function lineTitle(feature: TransmissionLineFeature): string {
  const circuito = feature.properties.Circuito ?? 'línea';
  return `${circuito} · ${feature.properties.Voltaje} kV`;
}

export default function GridMap({ dataset }: GridMapProps): React.ReactElement {
  const projection = useMemo(() => {
    const combined = {
      type: 'FeatureCollection' as const,
      features: [...dataset.substations.features, ...dataset.lines.features]
    };
    return geoMercator().fitExtent(
      [
        [PROJECTION_PADDING_PX, PROJECTION_PADDING_PX],
        [VIEWBOX_WIDTH - PROJECTION_PADDING_PX, VIEWBOX_HEIGHT - PROJECTION_PADDING_PX]
      ],
      combined
    );
  }, [dataset]);

  const path = useMemo(() => geoPath(projection), [projection]);

  return (
    <div className="flex flex-col gap-2">
      <header>
        <h2 className="font-display text-xl leading-tight font-medium tracking-tight text-foreground">
          Red nacional del ICE — mapa geográfico
        </h2>
        <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
          {dataset.substations.features.length} subestaciones · {dataset.lines.features.length}{' '}
          líneas de transmisión (230/138 kV). Esta es la red real del país — no la partición de este
          run (esa vive en la pestaña "Diagrama"); todavía no existe un mapeo determinista entre
          ambas redes.
        </p>
      </header>

      <svg
        viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`}
        role="img"
        aria-label="Mapa de la red de transmisión eléctrica de Costa Rica"
        className="h-auto w-full rounded-xl border bg-card"
      >
        <g>
          {dataset.lines.features.map((feature, index) => {
            const d = path(feature);
            if (d === null) {
              return null;
            }
            return (
              <path
                key={`line-${index}`}
                d={d}
                fill="none"
                stroke="var(--color-chart-3)"
                strokeWidth={lineWidthPx(feature)}
                strokeLinecap="round"
                opacity={0.85}
              >
                <title>{lineTitle(feature)}</title>
              </path>
            );
          })}
        </g>
        <g>
          {dataset.substations.features.map((feature, index) => {
            const projected = projection(feature.geometry.coordinates);
            if (projected === null) {
              return null;
            }
            const [cx, cy] = projected;
            const provincia = normalizeProvincia(feature.properties.Provincia);
            return (
              <circle
                key={`sub-${index}`}
                cx={cx}
                cy={cy}
                r={SUBSTATION_RADIUS_PX}
                fill="var(--color-foreground)"
                stroke="var(--color-background)"
                strokeWidth={1}
              >
                <title>{`${feature.properties.Subestacio} — ${provincia}, ${feature.properties.Canton}`}</title>
              </circle>
            );
          })}
        </g>
      </svg>

      <footer className="text-xs text-muted-foreground">{dataset.attribution}</footer>
    </div>
  );
}
