import React from 'react';

import { cn } from '@/lib/utils';

import { RUNG_MAX, RUNG_MIN, rungLabel } from './rungs';

/**
 * El glifo de la escalera de verificación (DESIGN.md §4): siete barras
 * alineadas por la base, de altura descendente izquierda→derecha (rung 1,
 * la más alta, es el ancla más fuerte). La barra del escalón alcanzado se
 * pinta con el color del veredicto; las demás quedan en tinta al 25%.
 */

export type RungVerdict = 'pass' | 'fail' | 'inconclusive' | 'neutral';

const VERDICT_TOKENS: Readonly<Record<RungVerdict, string>> = {
  pass: 'var(--color-verdict-pass)',
  fail: 'var(--color-verdict-fail)',
  inconclusive: 'var(--color-verdict-inconclusive)',
  neutral: 'var(--color-verdict-neutral)'
};

const SIZES = {
  sm: { barWidth: 2, gap: 1.5, maxHeight: 10, minHeight: 2 },
  md: { barWidth: 3, gap: 2, maxHeight: 14, minHeight: 2 }
} as const;

export interface RungLadderProps {
  readonly rung: number;
  /** Colorea la barra alcanzada; sin veredicto usa currentColor (hereda del contexto). */
  readonly verdict?: RungVerdict;
  readonly size?: keyof typeof SIZES;
  readonly className?: string;
}

export function RungLadder({
  rung,
  verdict,
  size = 'sm',
  className
}: RungLadderProps): React.ReactElement {
  const { barWidth, gap, maxHeight, minHeight } = SIZES[size];
  const rungCount = RUNG_MAX - RUNG_MIN + 1;
  const width = rungCount * barWidth + (rungCount - 1) * gap;
  const heightStep = (maxHeight - minHeight) / (rungCount - 1);

  return (
    <svg
      role="img"
      aria-label={`escalón ${rung} de ${RUNG_MAX} — ${rungLabel(rung)}`}
      width={width}
      height={maxHeight}
      viewBox={`0 0 ${width} ${maxHeight}`}
      className={cn('shrink-0', className)}
    >
      {Array.from({ length: rungCount }, (_, index) => {
        const barRung = RUNG_MIN + index;
        const barHeight = maxHeight - heightStep * index;
        const isReached = barRung === rung;
        return (
          <rect
            key={barRung}
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
