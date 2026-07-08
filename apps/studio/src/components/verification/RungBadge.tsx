import React from 'react';

import { Badge } from '@/components/ui/badge';

import { RungLadder, type RungVerdict } from './RungLadder';
import { rungLabel } from './rungs';

/**
 * Composición canónica glifo + texto (DESIGN.md §4): la única forma de
 * decir "escalón N" en toda la plataforma. El número va en mono (dato
 * verificable); `detail` reemplaza la etiqueta por defecto cuando el
 * contexto ya la aporta (p. ej. el verifierId en el certificado).
 */

export interface RungBadgeProps {
  readonly rung: number;
  readonly verdict: RungVerdict;
  readonly detail?: string;
  readonly className?: string;
}

export function RungBadge({
  rung,
  verdict,
  detail,
  className
}: RungBadgeProps): React.ReactElement {
  return (
    <Badge variant={verdict} className={className}>
      {/* span intermedio: el Badge fuerza size-3 en <svg> hijos directos */}
      <span className="flex items-center">
        <RungLadder rung={rung} />
      </span>
      <span>
        escalón <span className="font-mono font-medium">{rung}</span> · {detail ?? rungLabel(rung)}
      </span>
    </Badge>
  );
}
