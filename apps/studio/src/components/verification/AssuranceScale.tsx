import React from 'react';

import { cn } from '@/lib/utils';

import { ASSURANCE_LEVELS, LEVEL_ORDER, type AssuranceLevel } from './assurance';

/**
 * El glifo de la escala de aseguramiento (DESIGN.md §4): cinco barras
 * alineadas por la base, de altura ascendente izquierda→derecha (AL4, la
 * más alta, es la fuerza máxima — la dirección se invierte respecto de la
 * escalera supersedida). La barra del nivel alcanzado se pinta con el color
 * del veredicto; las demás quedan en tinta al 25%.
 */

export type VerdictTone = 'pass' | 'fail' | 'inconclusive' | 'neutral';

const VERDICT_TOKENS: Readonly<Record<VerdictTone, string>> = {
  pass: 'var(--color-verdict-pass)',
  fail: 'var(--color-verdict-fail)',
  inconclusive: 'var(--color-verdict-inconclusive)',
  neutral: 'var(--color-verdict-neutral)'
};

const SIZES = {
  sm: { barWidth: 2, gap: 1.5, maxHeight: 10, minHeight: 2 },
  md: { barWidth: 3, gap: 2, maxHeight: 14, minHeight: 2 }
} as const;

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
  const levelCount = ASSURANCE_LEVELS.length;
  const width = levelCount * barWidth + (levelCount - 1) * gap;
  const heightStep = (maxHeight - minHeight) / (levelCount - 1);
  const maxLevel = ASSURANCE_LEVELS[levelCount - 1];

  return (
    <svg
      role="img"
      aria-label={`nivel ${level} de ${maxLevel}`}
      width={width}
      height={maxHeight}
      viewBox={`0 0 ${width} ${maxHeight}`}
      className={cn('shrink-0', className)}
    >
      {ASSURANCE_LEVELS.map((barLevel, index) => {
        const barHeight = minHeight + heightStep * index;
        const isReached = LEVEL_ORDER[barLevel] === LEVEL_ORDER[level];
        return (
          <rect
            key={barLevel}
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
