import React from 'react';

import { cn } from './cn';

import type { VerdictTone } from './AssuranceScale';

/**
 * Pill de veredicto (DESIGN.md §2 nivel 2 / §5): tinte al 10–15% + texto al
 * 100% del token; `inconclusive` SIEMPRE border-dashed (sin señal, no
 * peligro). Primitivo interno de la librería — mismas clases que las
 * variantes verdict del Badge del Studio; los tokens `--color-verdict-*`
 * son el contrato entre ambos.
 */

const PILL_TONES: Readonly<Record<VerdictTone, string>> = {
  pass: 'border-verdict-pass/40 bg-verdict-pass/12 text-verdict-pass',
  fail: 'border-verdict-fail/40 bg-verdict-fail/12 text-verdict-fail',
  inconclusive:
    'border-dashed border-verdict-inconclusive/50 bg-verdict-inconclusive/10 text-verdict-inconclusive',
  neutral: 'border-verdict-neutral/40 bg-verdict-neutral/10 text-verdict-neutral'
};

export interface VerdictPillProps {
  readonly tone: VerdictTone;
  readonly className?: string;
  readonly children: React.ReactNode;
}

export function VerdictPill({ tone, className, children }: VerdictPillProps): React.ReactElement {
  return (
    <span
      className={cn(
        'inline-flex h-5 w-fit shrink-0 items-center justify-center gap-1 rounded-4xl border border-transparent px-2 py-0.5 text-xs font-medium whitespace-nowrap',
        PILL_TONES[tone],
        className
      )}
    >
      {children}
    </span>
  );
}
