import React from 'react';
import {
  CartesianGrid,
  ComposedChart,
  ErrorBar,
  Line,
  ReferenceLine,
  Scatter,
  XAxis,
  YAxis
} from 'recharts';

import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig
} from '@/components/ui/chart';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table';

import type { RvsPExperiment } from './types';

/**
 * RvsPChart (D5 — dataviz "r vs p") — curva de razón de aproximación
 * `r = energía / óptimo` contra la profundidad `p` de QAOA, ComposedChart
 * vía el wrapper shadcn (regla de stack: TODO recharts pasa por acá).
 *
 * Fuente: la ciencia real (`results/exp_r_vs_p/<instancia>.json`, ver
 * `RvsPExperiment` en types.ts) — NO `AblationMetric[]` que
 * `docs/specs/superficie-visual.md` §5 pinnea; esa forma no tiene eje `p`
 * ni barras de error, no puede expresar esta curva (divergencia deliberada,
 * registrada en `docs/mvp/decisiones.md`).
 *
 * Dos curvas honestas conviven (decisión #21 — no trivializar con
 * best-of-shots):
 * - `rEsperadoMean` (⟨C⟩): la `<Line>` primaria, sin barras de error
 *   porque es determinista dado el circuito (independiente de semilla).
 * - `rMuestralMean`: el `<Scatter>` + `<ErrorBar>` — ESTA carga el error de
 *   muestreo real (std/min/max sobre 5 semillas). `<ErrorBar>` se mantiene
 *   en configuración estándar (hijo directo de `<Scatter>`, `direction="y"`,
 *   offsets relativos al valor — historial de bugs de Recharts en configs
 *   exóticas, nota R5).
 *
 * Adaptación recharts 3.8 (vs. el shadcn `chart` stock que apunta a v2): el
 * snag conocido es que `ResponsiveContainer` mide con `ResizeObserver`, que
 * jsdom no implementa — sin polyfill, un `ResponsiveContainer` v2 mediría
 * 0×0 y no renderizaría nada en tests. La plantilla `chart.tsx` que
 * `shadcn add chart` generó para esta versión de recharts ya trae
 * `initialDimension` (default 320×200) como estado inicial de
 * `ResponsiveContainer` — se usa tal cual llega mientras `ResizeObserver`
 * está indefinido (recharts lo detecta y se abstiene de observar), así que
 * el chart renderiza con esa dimensión inicial sin necesitar un polyfill.
 */

export interface RvsPChartProps {
  readonly experiment: RvsPExperiment;
}

const CHART_CONFIG = {
  rEsperadoMean: {
    label: 'r esperado ⟨C⟩ — valor honesto',
    color: 'var(--color-chart-1)'
  },
  rMuestralMean: {
    label: 'r muestral — media ± error de muestreo',
    color: 'var(--color-chart-2)'
  }
} satisfies ChartConfig;

type BaselineKey = keyof RvsPExperiment['baselines'];

const BASELINE_STYLE: Readonly<
  Record<BaselineKey, { readonly color: string; readonly dash: string; readonly label: string }>
> = {
  cpsat: { color: 'var(--color-chart-3)', dash: '4 4', label: 'CP-SAT (exacto)' },
  gw: { color: 'var(--color-chart-4)', dash: '2 6', label: 'Goemans-Williamson' },
  greedy: { color: 'var(--color-chart-5)', dash: '6 3', label: 'Greedy' }
};

const BASELINE_ORDER: readonly BaselineKey[] = ['cpsat', 'gw', 'greedy'];

interface ChartRow {
  readonly p: number;
  readonly rEsperadoMean: number;
  readonly rMuestralMean: number;
  readonly rMuestralErrorRange: readonly [number, number];
}

function buildChartRows(points: RvsPExperiment['points']): readonly ChartRow[] {
  return points.map(point => ({
    p: point.p,
    rEsperadoMean: point.rEsperadoMean,
    rMuestralMean: point.rMuestralMean,
    // ErrorBar espera offsets relativos al valor, NO el mín/máx absoluto
    // (ver recharts/types/cartesian/ErrorBar.d.ts) — [value - min, max - value].
    rMuestralErrorRange: [
      point.rMuestralMean - point.rMuestralMin,
      point.rMuestralMax - point.rMuestralMean
    ]
  }));
}

function formatRatio(value: number): string {
  return value.toFixed(3);
}

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function RvsPFigure({ experiment }: RvsPChartProps): React.ReactElement {
  const data = buildChartRows(experiment.points);
  const pValues = experiment.points.map(point => point.p);

  return (
    <ChartContainer config={CHART_CONFIG} className="aspect-auto h-72 w-full">
      <ComposedChart data={[...data]} margin={{ top: 16, right: 24, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
        <XAxis
          dataKey="p"
          type="number"
          domain={[Math.min(...pValues), Math.max(...pValues)]}
          ticks={pValues}
          tickFormatter={(value: number) => `p=${value}`}
          tick={{ fontSize: 12, fill: 'var(--color-muted-foreground)' }}
          axisLine={{ stroke: 'var(--color-border)' }}
        />
        <YAxis
          domain={[0, 1]}
          tickFormatter={(value: number) => value.toFixed(1)}
          tick={{ fontSize: 12, fill: 'var(--color-muted-foreground)' }}
          axisLine={{ stroke: 'var(--color-border)' }}
          width={40}
        />
        <ChartTooltip
          content={
            <ChartTooltipContent labelFormatter={(label: unknown) => `p = ${String(label)}`} />
          }
        />
        {BASELINE_ORDER.map(key => {
          const baseline = experiment.baselines[key];
          const style = BASELINE_STYLE[key];
          return (
            <ReferenceLine
              key={key}
              y={baseline.r}
              stroke={style.color}
              strokeDasharray={style.dash}
              ifOverflow="extendDomain"
              label={{
                value: `${style.label} (r=${formatRatio(baseline.r)})`,
                position: 'insideTopRight',
                fill: style.color,
                fontSize: 11
              }}
            />
          );
        })}
        <Line
          type="monotone"
          dataKey="rEsperadoMean"
          stroke="var(--color-rEsperadoMean)"
          strokeWidth={2}
          dot={{ r: 4 }}
          isAnimationActive={false}
          name="rEsperadoMean"
        />
        <Scatter
          dataKey="rMuestralMean"
          fill="var(--color-rMuestralMean)"
          isAnimationActive={false}
          name="rMuestralMean"
        >
          <ErrorBar
            dataKey="rMuestralErrorRange"
            direction="y"
            stroke="var(--color-rMuestralMean)"
            width={4}
          />
        </Scatter>
      </ComposedChart>
    </ChartContainer>
  );
}

function RvsPTable({ experiment }: RvsPChartProps): React.ReactElement {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Método</TableHead>
          <TableHead>r</TableHead>
          <TableHead>Detalle</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {experiment.points.map(point => (
          <TableRow key={point.p}>
            <TableCell>QAOA p={point.p}</TableCell>
            <TableCell className="font-mono">{formatRatio(point.rEsperadoMean)}</TableCell>
            <TableCell className="text-muted-foreground">
              r muestral {formatRatio(point.rMuestralMean)} ± {formatRatio(point.rMuestralStd)} (mín{' '}
              {formatRatio(point.rMuestralMin)}–máx {formatRatio(point.rMuestralMax)}) · éxito{' '}
              {formatPercent(point.successRate)} (best-of-shots, trivial en esta instancia)
            </TableCell>
          </TableRow>
        ))}
        {BASELINE_ORDER.map(key => {
          const baseline = experiment.baselines[key];
          return (
            <TableRow key={key}>
              <TableCell>{BASELINE_STYLE[key].label}</TableCell>
              <TableCell className="font-mono">{formatRatio(baseline.r)}</TableCell>
              <TableCell className="text-muted-foreground">
                energía {baseline.energy.toLocaleString('es-CR')}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

export default function RvsPChart({ experiment }: RvsPChartProps): React.ReactElement {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className="text-sm font-medium text-foreground">
          Razón de aproximación r vs. profundidad p — {experiment.instance}
        </p>
        <p className="text-xs text-muted-foreground">
          r esperado ⟨C⟩ es el valor esperado del circuito (independiente de la semilla, sin barras
          de error); r muestral incorpora el error de muestreo real sobre 5 semillas (barras =
          mín–máx). Las líneas punteadas son los baselines clásicos.
        </p>
      </div>
      <RvsPFigure experiment={experiment} />
      <RvsPTable experiment={experiment} />
    </div>
  );
}
