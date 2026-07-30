import React from 'react';

import { cn } from '@/lib/utils';

import type { RunStatus } from '../../views/types';

/**
 * Punto de estado de un run (extraído F3 — repetido en la lista de runs y
 * el header del run): verde = completado, ámbar = en curso, rojo = fallido,
 * gris = cancelado (extensión aditiva, `docs/mvp/decisiones.md` §"Análisis
 * para discusión" punto 3 — antes fallido/cancelado colapsaban a "en curso"
 * para siempre). El estado va nombrado para lectores de pantalla; el color
 * solo lo refuerza.
 */

export const RUN_STATUS_LABELS: Readonly<Record<RunStatus, string>> = {
  completado: 'completado',
  en_curso: 'en curso',
  fallido: 'fallido',
  cancelado: 'cancelado'
};

/**
 * Exportado (no privado del componente) porque `RunDetail` reusa el MISMO
 * mapeo estado→tono para colorear el texto de su pill de estado — DRY, un
 * solo lugar decide "fallido = fail, cancelado = neutral".
 */
export const RUN_STATUS_TEXT_CLASS: Readonly<Record<RunStatus, string>> = {
  completado: 'text-verdict-pass',
  en_curso: 'text-status-warning',
  fallido: 'text-verdict-fail',
  cancelado: 'text-verdict-neutral'
};

const RUN_STATUS_DOT_CLASS: Readonly<Record<RunStatus, string>> = {
  completado: 'bg-verdict-pass',
  en_curso: 'bg-status-warning',
  fallido: 'bg-verdict-fail',
  cancelado: 'bg-verdict-neutral'
};

export interface RunStatusDotProps {
  readonly status: RunStatus;
  readonly className?: string;
}

export function RunStatusDot({ status, className }: RunStatusDotProps): React.ReactElement {
  return (
    <span
      role="img"
      aria-label={RUN_STATUS_LABELS[status]}
      className={cn('size-2 rounded-full', RUN_STATUS_DOT_CLASS[status], className)}
    />
  );
}
