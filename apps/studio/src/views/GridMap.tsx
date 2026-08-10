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
 * **[V1/M18] El seam de partición dejó de ser un seam.** Antes este archivo
 * declaraba `partition` y NO lo renderizaba, con causa: no existía mapeo
 * determinista bus↔subestación. Ese mapeo SÍ existe — la instancia derivada
 * estampó su `nodos` (`data/iceInstance.ts`) — y ahora existe además el
 * productor de particiones verificadas por isla. Lo que se pinta sale del
 * run; lo que no casa se DECLARA (ver `PartitionLegend`), nunca se rellena.
 */

import { geoMercator, geoPath } from 'd3-geo';
import React, { useMemo } from 'react';

import { AssuranceBadge } from '@chimera/assurance-ui';

import { normalizeProvincia } from '../data/iceGridSchemas';

import type { AssuranceLevel } from '@chimera/assurance-ui';
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
const ISLAND_SUBSTATION_RADIUS_PX = 5.5;

/**
 * Color por isla: los tokens `--chart-*` del design system, en el mismo orden
 * que el resto del Studio (DESIGN.md §5). Se reparten cíclicamente por índice
 * de isla — el color identifica la ENTIDAD (la isla), nunca su veredicto: eso
 * lo dice el badge, que además no depende del color para leerse.
 */
const ISLAND_COLORS = [
  'var(--color-chart-2)',
  'var(--color-chart-3)',
  'var(--color-chart-1)',
  'var(--color-chart-4)',
  'var(--color-chart-5)'
] as const;

/** Subestación que la partición no cubre — neutra y declarada, no oculta. */
const UNASSIGNED_COLOR = 'var(--color-muted-foreground)';

export interface IslandVerificationView {
  readonly verdict: 'pass' | 'fail' | 'inconclusive';
  readonly level: AssuranceLevel;
  readonly verifierClass: string;
  readonly method: string;
  readonly summary: string;
}

/**
 * Una isla lista para pintarse: qué subestaciones la componen (por nombre YA
 * reconciliado) y con qué constancia — freeze §9: `verification` POR isla,
 * sin excepción.
 */
export interface GridIslandOverlay {
  readonly id: string;
  readonly label: string;
  readonly substationNames: readonly string[];
  readonly verification: IslandVerificationView;
}

export interface GridPartitionOverlay {
  readonly islands: readonly GridIslandOverlay[];
  /** Subestaciones del mapa que la partición cubre. */
  readonly matchedSubstations: number;
  /** Digest de la instancia derivada que se reconcilió (procedencia). */
  readonly instanceDigest: string;
}

export interface GridMapProps {
  readonly dataset: GeoJsonGridDataset;
  readonly partition?: GridPartitionOverlay;
}

function lineWidthPx(feature: TransmissionLineFeature): number {
  return LINE_WIDTH_PX_BY_KV[feature.properties.Voltaje] ?? DEFAULT_LINE_WIDTH_PX;
}

function lineTitle(feature: TransmissionLineFeature): string {
  const circuito = feature.properties.Circuito ?? 'línea';
  return `${circuito} · ${feature.properties.Voltaje} kV`;
}

/** nombre normalizado de subestación → { islandIndex, island }. */
type IslandBySubstation = ReadonlyMap<string, { index: number; island: GridIslandOverlay }>;

function buildIslandIndex(partition: GridPartitionOverlay | undefined): IslandBySubstation {
  const index = new Map<string, { index: number; island: GridIslandOverlay }>();
  partition?.islands.forEach((island, islandIndex) => {
    for (const name of island.substationNames) {
      index.set(name, { index: islandIndex, island });
    }
  });
  return index;
}

function islandColor(index: number): string {
  return ISLAND_COLORS[index % ISLAND_COLORS.length] ?? UNASSIGNED_COLOR;
}

function PartitionLegend({
  partition,
  totalSubstations
}: {
  readonly partition: GridPartitionOverlay;
  readonly totalSubstations: number;
}): React.ReactElement {
  const sinAsignar = totalSubstations - partition.matchedSubstations;
  return (
    <div className="flex flex-col gap-2 rounded-lg border bg-card p-3">
      <div className="flex flex-wrap items-center gap-3">
        {partition.islands.map((island, index) => (
          <span key={island.id} className="flex items-center gap-2 text-xs">
            <span
              aria-hidden
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: islandColor(index) }}
            />
            <span className="text-foreground">{island.label}</span>
            <AssuranceBadge
              level={island.verification.level}
              verdict={island.verification.verdict}
              verifierClass={island.verification.verifierClass}
              detail={island.verification.method}
            />
          </span>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">
        {partition.matchedSubstations} de {totalSubstations} subestaciones reconciliadas con la
        instancia <code className="font-mono">{partition.instanceDigest.slice(0, 12)}</code>
        {sinAsignar > 0 && (
          <>
            {' '}
            · {sinAsignar} sin isla: ningún circuito del snapshot resuelve hacia ellas, así que la
            instancia derivada nunca las incluyó. Se dibujan en gris.
          </>
        )}
      </p>
    </div>
  );
}

export default function GridMap({ dataset, partition }: GridMapProps): React.ReactElement {
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
  const islandBySubstation = useMemo(() => buildIslandIndex(partition), [partition]);

  const totalSubstations = dataset.substations.features.length;

  return (
    <div className="flex flex-col gap-2">
      <header>
        <h2 className="font-display text-xl leading-tight font-medium tracking-tight text-foreground">
          Red nacional del ICE — mapa geográfico
        </h2>
        <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
          {totalSubstations} subestaciones · {dataset.lines.features.length} líneas de transmisión
          (230/138 kV).{' '}
          {partition === undefined
            ? 'Esta es la red real del país; este run no produjo una partición verificada por isla, así que no se colorea nada.'
            : 'Coloreada por la partición que este run verificó — cada isla con su propia constancia.'}
        </p>
      </header>

      {partition !== undefined && (
        <PartitionLegend partition={partition} totalSubstations={totalSubstations} />
      )}

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
            const asignada = islandBySubstation.get(feature.properties.Subestacio);
            const fill = asignada === undefined ? UNASSIGNED_COLOR : islandColor(asignada.index);
            const sufijo =
              asignada === undefined
                ? partition === undefined
                  ? ''
                  : ' — sin isla'
                : ` — ${asignada.island.label} (${asignada.island.verification.level})`;
            return (
              <circle
                key={`sub-${index}`}
                cx={cx}
                cy={cy}
                r={asignada === undefined ? SUBSTATION_RADIUS_PX : ISLAND_SUBSTATION_RADIUS_PX}
                fill={fill}
                stroke="var(--color-background)"
                strokeWidth={1}
              >
                <title>{`${feature.properties.Subestacio} — ${provincia}, ${feature.properties.Canton}${sufijo}`}</title>
              </circle>
            );
          })}
        </g>
      </svg>

      <footer className="text-xs text-muted-foreground">{dataset.attribution}</footer>
    </div>
  );
}
