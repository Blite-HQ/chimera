import React from 'react';

import { cn } from '@/lib/utils';

import type { RunStatus } from '../../views/types';

/**
 * Punto de estado de un run (extraído F3 — repetido en la lista de runs y
 * el header del run): verde = completado, ámbar = en curso. El estado va
 * nombrado para lectores de pantalla; el color solo lo refuerza.
 */

const STATUS_LABELS: Readonly<Record<RunStatus, string>> = {
  completado: 'completado',
  en_curso: 'en curso'
};

export interface RunStatusDotProps {
  readonly status: RunStatus;
  readonly className?: string;
}

export function RunStatusDot({ status, className }: RunStatusDotProps): React.ReactElement {
  return (
    <span
      role="img"
      aria-label={STATUS_LABELS[status]}
      className={cn(
        'size-2 rounded-full',
        status === 'completado' ? 'bg-verdict-pass' : 'bg-status-warning',
        className
      )}
    />
  );
}
