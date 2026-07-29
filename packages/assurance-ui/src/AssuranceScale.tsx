import React from 'react';

import { cn } from './cn';

import { ASSURANCE_LEVELS, LEVEL_ORDER, type AssuranceLevel } from './assurance';

/**
 * El glifo de la escala de aseguramiento, simplificado (directriz Dylan
 * 2026-07-29, supersede la variante de 5 barras de DESIGN.md §4): TRES
 * barras alineadas por la base, altura ascendente, y CUATRO estados de
 * confianza — nula (AL0: ninguna barra coloreada), poca (AL1: la baja),
 * media (AL2: la intermedia), alta (AL3/AL4: la más alta). La barra
 * alcanzada se pinta con el color del veredicto; las demás quedan en tinta
 * al 25%. El AL exacto NO se pierde: viaja en la etiqueta accesible y en el
 * texto mono del badge — el glifo simplifica, el dato no.
 */

export type VerdictTone = 'pass' | 'fail' | 'inconclusive' | 'neutral';

const VERDICT_TOKENS: Readonly<Record<VerdictTone, string>> = {
  pass: 'var(--color-verdict-pass)',
  fail: 'var(--color-verdict-fail)',
  inconclusive: 'var(--color-verdict-inconclusive)',
  neutral: 'var(--color-verdict-neutral)'
};

const SIZES = {
  sm: { barWidth: 2, gap: 2, maxHeight: 10, minHeight: 4 },
  md: { barWidth: 4, gap: 2, maxHeight: 14, minHeight: 4 }
} as const;

const BAR_COUNT = 3;

/**
 * Bucket de confianza del glifo: índice de la barra coloreada (-1 = ninguna)
 * + etiqueta humana. AL3 y AL4 comparten "alta" — la distinción exacta vive
 * en el texto AL{n} del badge.
 */
const CONFIDENCE_BUCKETS = [
  { label: 'nula', bar: -1 },
  { label: 'poca', bar: 0 },
  { label: 'media', bar: 1 },
  { label: 'alta', bar: 2 },
  { label: 'alta', bar: 2 }
] as const;

export interface AssuranceScaleProps {
  readonly level: AssuranceLevel;
  /** Colorea la barra alcanzada; sin veredicto usa currentColor (hereda del contexto). */
  readonly verdict?: VerdictTone;
  readonly size?: keyof typeof SIZES;
  readonly className?: string;
}

export function AssuranceScale({
  level,
  verdict,
  size = 'sm',
  className
}: AssuranceScaleProps): React.ReactElement {
  const { barWidth, gap, maxHeight, minHeight } = SIZES[size];
  const width = BAR_COUNT * barWidth + (BAR_COUNT - 1) * gap;
  const heightStep = (maxHeight - minHeight) / (BAR_COUNT - 1);
  const maxLevel = ASSURANCE_LEVELS[ASSURANCE_LEVELS.length - 1];
  const bucket = CONFIDENCE_BUCKETS[LEVEL_ORDER[level]];

  return (
    <svg
      role="img"
      aria-label={`confianza ${bucket.label} (${level} de ${maxLevel})`}
      width={width}
      height={maxHeight}
      viewBox={`0 0 ${width} ${maxHeight}`}
      className={cn('shrink-0', className)}
    >
      {Array.from({ length: BAR_COUNT }, (_, index) => {
        const barHeight = minHeight + heightStep * index;
        const isReached = index === bucket.bar;
        return (
          <rect
            key={index}
            x={index * (barWidth + gap)}
            y={maxHeight - barHeight}
            width={barWidth}
            height={barHeight}
            rx={barWidth / 3}
            fill={isReached && verdict ? VERDICT_TOKENS[verdict] : 'currentColor'}
            opacity={isReached ? 1 : 0.25}
          />
        );
      })}
    </svg>
  );
}
