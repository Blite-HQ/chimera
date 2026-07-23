import React from 'react';

import { cn } from '@/lib/utils';

import { conclusionTone, verdictLabel } from './assurance';

import type { ConclusionVerdict } from './assurance';

/**
 * Chip de veredicto de conclusión (DESIGN.md §2 nivel 2): tinte al 10% +
 * texto al 100% del token; `inconclusive` SIEMPRE border-dashed (sin señal,
 * no peligro). Compartido por Runs / Artifacts / Knowledge.
 */

const TONE_CLASSES = {
  pass: 'border-verdict-pass/40 bg-verdict-pass/10 text-verdict-pass',
  fail: 'border-verdict-fail/40 bg-verdict-fail/10 text-verdict-fail',
  inconclusive: 'border-dashed text-muted-foreground',
  neutral: 'text-muted-foreground'
} as const;

export interface VerdictChipProps {
  readonly verdict: ConclusionVerdict;
  readonly className?: string;
}

export function VerdictChip({ verdict, className }: VerdictChipProps): React.ReactElement {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-4xl border px-2 py-0.5 text-xs whitespace-nowrap',
        TONE_CLASSES[conclusionTone(verdict)],
        className
      )}
    >
      {verdictLabel(verdict)}
    </span>
  );
}
