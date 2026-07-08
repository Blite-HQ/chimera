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
 * Palette: reuses this app's existing island colors (sky-500/purple-500,
 * spike/ieee14.ts ISLAND_COLORS) rather than an unrelated categorical
 * palette, so the Ablación tab reads as the same system as the rest of
 * the Studio. Validated with the dataviz skill's palette validator
 * (CVD ΔE 20.5, PASS; sky-500 vs white surface is 2.77:1 — below 3:1, so
 * every bar also carries a direct value label, not color alone).
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

import type { AblationMetric } from './types';

export interface AblationPanelProps {
  readonly metrics: readonly AblationMetric[];
}

const VARIANT_COLORS: Readonly<Record<AblationMetric['variant'], string>> = {
  quantum: '#0ea5e9', // sky-500 — same hue as Isla A in the network view
  classical: '#a855f7' // purple-500 — same hue as Isla B in the network view
};

const VARIANT_LABELS: Readonly<Record<AblationMetric['variant'], string>> = {
  quantum: 'Cuántico',
  classical: 'Clásico'
};

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

function Legend(): React.ReactElement {
  return (
    <div className="flex items-center gap-4 text-xs text-zinc-600">
      {(['quantum', 'classical'] as const).map(variant => (
        <span key={variant} className="flex items-center gap-1.5">
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
    <div className="rounded-lg border border-zinc-200 bg-white p-3">
      <p className="mb-2 text-sm font-semibold text-zinc-700">
        {config.title}
        {config.unit && <span className="text-zinc-400"> ({config.unit})</span>}
      </p>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={[...data]} margin={{ top: 16, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e1e0d9" vertical={false} />
          <XAxis
            dataKey="variant"
            tick={{ fontSize: 12, fill: '#898781' }}
            axisLine={{ stroke: '#c3c2b7' }}
          />
          <YAxis
            tick={{ fontSize: 12, fill: '#898781' }}
            axisLine={{ stroke: '#c3c2b7' }}
            width={40}
          />
          <Tooltip />
          {/* default tooltip is already clear (variant + value); a custom formatter isn't worth fighting recharts' generic ValueType for */}
          <Bar dataKey="value" radius={[4, 4, 0, 0]} isAnimationActive={false}>
            {data.map(row => (
              <Cell key={row.variant} fill={row.fill} />
            ))}
            <LabelList dataKey="value" position="top" style={{ fill: '#0b0b0b', fontSize: 12 }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function AblationPanel({ metrics }: AblationPanelProps): React.ReactElement {
  return (
    <div className="flex flex-col gap-3">
      <Legend />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {METRIC_CONFIGS.map(config => (
          <MetricChart key={config.key} config={config} metrics={metrics} />
        ))}
      </div>
    </div>
  );
}
