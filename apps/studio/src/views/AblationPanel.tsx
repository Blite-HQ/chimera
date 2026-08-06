/**
 * AblationPanel — nota 07 §1.3 "Ablación" row: quantum vs. classical
 * solver for the same problem, ×2 runs.
 *
 * cutCost/wallMs/verificationLatencyMs live on very different scales, so
 * this is three small-multiple bar charts (one metric each) rather than
 * one dual-axis chart (dual-axis is the #1 chart mistake — dataviz
 * skill). Color follows the entity (quantum/classical), never the
 * metric: the same two hues repeat across all three charts, with a
 * single shared legend above them instead of one repeated per chart.
 *
 * Palette: the same island hues as the network view, via the chart tokens
 * (--color-chart-2 = Isla A cian, --color-chart-3 = Isla B magenta,
 * DESIGN.md §5), so the Ablación tab reads as the same system as the rest
 * of the Studio and re-themes with data-theme (SVG fills accept var()).
 * Mid-tone fills can sit under 3:1 against the card surface, so every bar
 * also carries a direct value label, not color alone.
 */

import React from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';

import type { AblationMetric, AblationVariant } from './types';

export interface AblationPanelProps {
  readonly metrics: readonly AblationMetric[];
}

/**
 * [V2/M19 · C-4] Cuatro variantes, no dos: `mitigated`/`zne` son los brazos de
 * mitigación de M6. El color identifica la VARIANTE (la entidad comparada) y
 * se mantiene igual en los tres charts — un color por métrica haría creer que
 * los paneles comparan cosas distintas.
 */
const VARIANT_COLORS: Readonly<Record<AblationVariant, string>> = {
  quantum: 'var(--color-chart-2)', // misma familia que Isla A (cian de traza)
  classical: 'var(--color-chart-3)', // misma familia que Isla B (magenta)
  mitigated: 'var(--color-chart-1)',
  zne: 'var(--color-chart-4)'
};

const VARIANT_LABELS: Readonly<Record<AblationVariant, string>> = {
  quantum: 'Cuántico',
  classical: 'Clásico',
  mitigated: 'Mitigado',
  zne: 'ZNE'
};

/** Orden estable de presentación — dos renders del mismo run dan lo mismo. */
const VARIANT_ORDER: readonly AblationVariant[] = ['quantum', 'classical', 'mitigated', 'zne'];

interface MetricConfig {
  readonly key: keyof Pick<AblationMetric, 'cutCost' | 'wallMs' | 'verificationLatencyMs'>;
  readonly title: string;
  readonly unit: string;
}

const METRIC_CONFIGS: readonly MetricConfig[] = [
  { key: 'cutCost', title: 'Costo de corte', unit: '' },
  { key: 'wallMs', title: 'Tiempo total', unit: 'ms' },
  { key: 'verificationLatencyMs', title: 'Latencia de verificación', unit: 'ms' }
];

interface ChartRow {
  readonly variant: string;
  readonly value: number;
  readonly fill: string;
}

function buildChartData(
  metrics: readonly AblationMetric[],
  config: MetricConfig
): readonly ChartRow[] {
  return metrics.map(metric => ({
    variant: VARIANT_LABELS[metric.variant],
    value: metric[config.key],
    fill: VARIANT_COLORS[metric.variant]
  }));
}

/**
 * La leyenda nombra SOLO las variantes que este run produjo. Anunciar «ZNE»
 * cuando ningún brazo de mitigación corrió sugeriría una comparación que no
 * ocurrió — el panel dice lo que hay, no lo que el enum admite.
 */
function Legend({ variants }: { readonly variants: readonly AblationVariant[] }) {
  return (
    <div className="flex items-center gap-4 text-xs text-muted-foreground">
      {variants.map(variant => (
        <span key={variant} className="flex items-center gap-2">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: VARIANT_COLORS[variant] }}
          />
          {VARIANT_LABELS[variant]}
        </span>
      ))}
    </div>
  );
}

function MetricChart({
  config,
  metrics
}: {
  readonly config: MetricConfig;
  readonly metrics: readonly AblationMetric[];
}): React.ReactElement {
  const data = buildChartData(metrics, config);
  return (
    <div className="rounded-lg border bg-card p-4">
      <p className="mb-2 text-sm font-medium text-foreground">
        {config.title}
        {config.unit && <span className="text-muted-foreground"> ({config.unit})</span>}
      </p>
      <ResponsiveContainer width="100%" height={192}>
        <BarChart data={[...data]} margin={{ top: 16, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
          <XAxis
            dataKey="variant"
            tick={{ fontSize: 12, fill: 'var(--color-muted-foreground)' }}
            axisLine={{ stroke: 'var(--color-border)' }}
          />
          <YAxis
            tick={{ fontSize: 12, fill: 'var(--color-muted-foreground)' }}
            axisLine={{ stroke: 'var(--color-border)' }}
            width={40}
          />
          <Tooltip
            cursor={{ fill: 'var(--color-muted)' }}
            contentStyle={{
              backgroundColor: 'var(--color-popover)',
              borderColor: 'var(--color-border)',
              borderRadius: 8,
              color: 'var(--color-popover-foreground)'
            }}
            itemStyle={{ color: 'var(--color-popover-foreground)' }}
            labelStyle={{ color: 'var(--color-popover-foreground)' }}
          />
          {/* default tooltip content is already clear (variant + value); a custom formatter isn't worth fighting recharts' generic ValueType for */}
          <Bar dataKey="value" radius={[4, 4, 0, 0]} isAnimationActive={false}>
            {data.map(row => (
              <Cell key={row.variant} fill={row.fill} />
            ))}
            <LabelList
              dataKey="value"
              position="top"
              style={{ fill: 'var(--color-foreground)', fontSize: 12 }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function AblationPanel({ metrics }: AblationPanelProps): React.ReactElement {
  const presentes = VARIANT_ORDER.filter(variant =>
    metrics.some(metric => metric.variant === variant)
  );
  return (
    <div className="flex flex-col gap-4">
      <Legend variants={presentes} />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {METRIC_CONFIGS.map(config => (
          <MetricChart key={config.key} config={config} metrics={metrics} />
        ))}
      </div>
    </div>
  );
}
