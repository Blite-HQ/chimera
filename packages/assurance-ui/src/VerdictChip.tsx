import React from 'react';

import { conclusionTone, verdictLabel } from './assurance';
import { VerdictPill } from './VerdictPill';

import type { ConclusionVerdict } from './assurance';

/**
 * Chip de veredicto de conclusión (DESIGN.md §2 nivel 2): tinte al 10% +
 * texto al 100% del token; `inconclusive` SIEMPRE border-dashed (sin señal,
 * no peligro). Compartido por Runs / Artifacts / Knowledge.
 */

export interface VerdictChipProps {
  readonly verdict: ConclusionVerdict;
  readonly className?: string;
}

export function VerdictChip({ verdict, className }: VerdictChipProps): React.ReactElement {
  return (
    <VerdictPill tone={conclusionTone(verdict)} className={className}>
      {verdictLabel(verdict)}
    </VerdictPill>
  );
}
