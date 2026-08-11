/**
 * GeoMap — artifact de render geoespacial GENÉRICO (O7/#173.2, directiva de
 * Dylan 2026-08-11): un `FeatureCollection` con geometrías Point/LineString/
 * MultiLineString y propiedades ARBITRARIAS, proyectado a SVG con d3-geo.
 * Cero conocimiento del dataset concreto que lo alimenta — este componente
 * no sabe qué es una "subestación" ni una "provincia": qué propiedad usar
 * como etiqueta y cuál como peso de línea son CONFIGURACIÓN del caller
 * (`GeoRenderConfig`), nunca nombres de campo clavados acá. Mismo patrón que
 * `blite.ingesta.geojson.to_graph` (`node_match_property`/`endpoint_property`/
 * `weight_property` viajan como PARAMS de invocación — ver
 * `capabilities/ingesta/tests/test_geojson_to_graph.py`
 * ::TestEndpointNameMatchStrategyGenericBehaviour, la convención que este
 * componente replica del lado del Studio).
 *
 * Honestidad de propiedad ausente: si `config.labelProperty` no resuelve en
 * un feature dado, se muestra el índice del feature — nunca una etiqueta
 * inventada (regla dura: cero mocks silenciosos).
 *
 * SVG en vez de canvas: d3 pinta elementos DOM reales que SÍ siguen
 * `var(--color-*)` — el tema cambia solo, sin reinicializar nada. Proyección
 * sobre un lienzo lógico fijo (viewBox), no el tamaño medido del contenedor:
 * evita depender de ResizeObserver/getBoundingClientRect, que jsdom no
 * implementa realmente.
 *
 * El overlay de grupo verificado (`GeoOverlay`) es la contraparte genérica
 * de lo que antes era "partición por isla": un grupo de features que
 * comparten una constancia (`verdict`/`level`/`verifierClass`), unidos por
 * el valor de `config.labelProperty` de cada feature (`matchKeys`). Sin
 * config, o sin overlay, no se colorea ni se agrupa nada — jamás se inventa
 * una agrupación.
 */

import { geoMercator, geoPath } from 'd3-geo';
import React, { useMemo } from 'react';

import { AssuranceBadge } from '@chimera/assurance-ui';

import type { AssuranceLevel } from '@chimera/assurance-ui';
import type { GeoFeature, GenericGeoDataset } from '../data/geoJsonSchemas';

const VIEWBOX_WIDTH = 800;
const VIEWBOX_HEIGHT = 520;
const PROJECTION_PADDING_PX = 24;

const DEFAULT_LINE_WIDTH_PX = 1.5;
const MIN_LINE_WIDTH_PX = 1;
const MAX_LINE_WIDTH_PX = 4;
const POINT_RADIUS_PX = 4;
const MATCHED_POINT_RADIUS_PX = 5.5;

/** Color por grupo: los tokens `--chart-*` del design system, cíclicos por
 * índice de grupo — el color identifica la ENTIDAD (el grupo), nunca su
 * veredicto: eso lo dice el badge, que no depende del color para leerse. */
const GROUP_COLORS = [
  'var(--color-chart-2)',
  'var(--color-chart-3)',
  'var(--color-chart-1)',
  'var(--color-chart-4)',
  'var(--color-chart-5)'
] as const;

/** Feature que el overlay no cubre — neutro y declarado, no oculto. */
const UNASSIGNED_COLOR = 'var(--color-muted-foreground)';

export interface GeoRenderConfig {
  /** Propiedad a mostrar como etiqueta de cada feature (y como clave de
   * emparejamiento con `GeoOverlay.groups[].matchKeys`). */
  readonly labelProperty?: string;
  /** Propiedad numérica que escala el ancho de trazo de las líneas. */
  readonly weightProperty?: string;
}

export interface GeoGroupVerification {
  readonly verdict: 'pass' | 'fail' | 'inconclusive';
  readonly level: AssuranceLevel;
  readonly verifierClass: string;
  readonly method: string;
  readonly summary: string;
}

/** Un grupo de features listo para pintarse, con su propia constancia
 * (regla §9 del freeze: verification POR sub-entidad, nunca global-only). */
export interface GeoFeatureGroup {
  readonly id: string;
  readonly label: string;
  /** Valores de `config.labelProperty` que pertenecen a este grupo. */
  readonly matchKeys: readonly string[];
  readonly verification: GeoGroupVerification;
}

export interface GeoOverlay {
  readonly groups: readonly GeoFeatureGroup[];
  /** Features del dataset que el overlay cubre. */
  readonly matchedFeatures: number;
  /** Procedencia del overlay (digest de lo que lo generó), si aplica. */
  readonly sourceDigest?: string;
}

export interface GeoMapProps {
  readonly dataset: GenericGeoDataset;
  readonly config?: GeoRenderConfig;
  readonly overlay?: GeoOverlay;
}

interface IndexedFeature {
  readonly feature: GeoFeature;
  readonly index: number;
}

function resolveLabel(feature: GeoFeature, index: number, labelProperty?: string): string {
  if (labelProperty !== undefined) {
    const raw = feature.properties[labelProperty];
    if (typeof raw === 'string' && raw.length > 0) {
      return raw;
    }
  }
  return `Feature ${index}`;
}

function resolveWeight(feature: GeoFeature, weightProperty?: string): number | undefined {
  if (weightProperty === undefined) return undefined;
  const raw = feature.properties[weightProperty];
  return typeof raw === 'number' && Number.isFinite(raw) ? raw : undefined;
}

function isLineGeometry(feature: GeoFeature): boolean {
  return feature.geometry.type === 'LineString' || feature.geometry.type === 'MultiLineString';
}

function lineWidthPx(weight: number | undefined, maxWeight: number): number {
  if (weight === undefined || maxWeight <= 0) return DEFAULT_LINE_WIDTH_PX;
  const ratio = weight / maxWeight;
  return MIN_LINE_WIDTH_PX + ratio * (MAX_LINE_WIDTH_PX - MIN_LINE_WIDTH_PX);
}

/** etiqueta (resuelta vía `labelProperty`) → { índice de grupo, grupo }. */
type GroupByMatchKey = ReadonlyMap<string, { index: number; group: GeoFeatureGroup }>;

function buildGroupIndex(overlay: GeoOverlay | undefined): GroupByMatchKey {
  const index = new Map<string, { index: number; group: GeoFeatureGroup }>();
  overlay?.groups.forEach((group, groupIndex) => {
    for (const key of group.matchKeys) {
      index.set(key, { index: groupIndex, group });
    }
  });
  return index;
}

function groupColor(index: number): string {
  return GROUP_COLORS[index % GROUP_COLORS.length] ?? UNASSIGNED_COLOR;
}

function GeoOverlayLegend({
  overlay,
  totalFeatures
}: {
  readonly overlay: GeoOverlay;
  readonly totalFeatures: number;
}): React.ReactElement {
  const sinAsignar = totalFeatures - overlay.matchedFeatures;
  return (
    <div className="flex flex-col gap-2 rounded-lg border bg-card p-3">
      <div className="flex flex-wrap items-center gap-3">
        {overlay.groups.map((group, index) => (
          <span key={group.id} className="flex items-center gap-2 text-xs">
            <span
              aria-hidden
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: groupColor(index) }}
            />
            <span className="text-foreground">{group.label}</span>
            <AssuranceBadge
              level={group.verification.level}
              verdict={group.verification.verdict}
              verifierClass={group.verification.verifierClass}
              detail={group.verification.method}
            />
          </span>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">
        {overlay.matchedFeatures} de {totalFeatures} features reconciliados
        {overlay.sourceDigest !== undefined && (
          <>
            {' '}
            con <code className="font-mono">{overlay.sourceDigest.slice(0, 12)}</code>
          </>
        )}
        {sinAsignar > 0 && (
          <>
            {' '}
            · {sinAsignar} sin grupo: ninguna clave del overlay resuelve hacia ellos. Se dibujan en
            gris.
          </>
        )}
      </p>
    </div>
  );
}

export default function GeoMap({ dataset, config, overlay }: GeoMapProps): React.ReactElement {
  const indexed: readonly IndexedFeature[] = useMemo(
    () => dataset.collection.features.map((feature, index) => ({ feature, index })),
    [dataset]
  );
  const lineFeatures = useMemo(
    () => indexed.filter(item => isLineGeometry(item.feature)),
    [indexed]
  );
  const pointFeatures = useMemo(
    () => indexed.filter(item => item.feature.geometry.type === 'Point'),
    [indexed]
  );

  const projection = useMemo(
    () =>
      geoMercator().fitExtent(
        [
          [PROJECTION_PADDING_PX, PROJECTION_PADDING_PX],
          [VIEWBOX_WIDTH - PROJECTION_PADDING_PX, VIEWBOX_HEIGHT - PROJECTION_PADDING_PX]
        ],
        dataset.collection
      ),
    [dataset]
  );
  const path = useMemo(() => geoPath(projection), [projection]);

  const maxWeight = useMemo(
    () =>
      Math.max(0, ...indexed.map(item => resolveWeight(item.feature, config?.weightProperty) ?? 0)),
    [indexed, config?.weightProperty]
  );
  const groupIndex = useMemo(() => buildGroupIndex(overlay), [overlay]);

  const totalFeatures = dataset.collection.features.length;

  return (
    <div className="flex flex-col gap-2">
      <header>
        <h2 className="font-display text-xl leading-tight font-medium tracking-tight text-foreground">
          Datos geoespaciales
        </h2>
        <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
          {totalFeatures} features · {pointFeatures.length} puntos · {lineFeatures.length} líneas.{' '}
          {overlay === undefined
            ? 'Sin agrupación verificada asociada — se muestran sin colorear.'
            : 'Coloreado por el grupo que este run verificó — cada grupo con su propia constancia.'}
        </p>
      </header>

      {overlay !== undefined && (
        <GeoOverlayLegend overlay={overlay} totalFeatures={totalFeatures} />
      )}

      <svg
        viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`}
        role="img"
        aria-label="Mapa de datos geoespaciales"
        className="h-auto w-full rounded-xl border bg-card"
      >
        <g>
          {lineFeatures.map(({ feature, index }) => {
            const d = path(feature);
            if (d === null) return null;
            const weight = resolveWeight(feature, config?.weightProperty);
            const label = resolveLabel(feature, index, config?.labelProperty);
            const titulo = weight === undefined ? label : `${label} · ${weight}`;
            return (
              <path
                key={`line-${index}`}
                d={d}
                fill="none"
                stroke="var(--color-chart-3)"
                strokeWidth={lineWidthPx(weight, maxWeight)}
                strokeLinecap="round"
                opacity={0.85}
              >
                <title>{titulo}</title>
              </path>
            );
          })}
        </g>
        <g>
          {pointFeatures.map(({ feature, index }) => {
            const projected = projection(
              (feature.geometry as { coordinates: [number, number] }).coordinates
            );
            if (projected === null) return null;
            const [cx, cy] = projected;
            const label = resolveLabel(feature, index, config?.labelProperty);
            const matched = config?.labelProperty !== undefined ? groupIndex.get(label) : undefined;
            const fill = matched === undefined ? UNASSIGNED_COLOR : groupColor(matched.index);
            const sufijo =
              matched === undefined
                ? overlay === undefined
                  ? ''
                  : ' — sin grupo'
                : ` — ${matched.group.label} (${matched.group.verification.level})`;
            return (
              <circle
                key={`point-${index}`}
                cx={cx}
                cy={cy}
                r={matched === undefined ? POINT_RADIUS_PX : MATCHED_POINT_RADIUS_PX}
                fill={fill}
                stroke="var(--color-background)"
                strokeWidth={1}
              >
                <title>{`${label}${sufijo}`}</title>
              </circle>
            );
          })}
        </g>
      </svg>

      {dataset.attribution !== undefined && (
        <footer className="text-xs text-muted-foreground">{dataset.attribution}</footer>
      )}
    </div>
  );
}
