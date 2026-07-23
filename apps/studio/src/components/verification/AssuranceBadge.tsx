import React from 'react';

import { Badge } from '@/components/ui/badge';

import { AssuranceScale, type VerdictTone } from './AssuranceScale';
import { classLabel, type AssuranceLevel } from './assurance';

/**
 * Composición canónica glifo + texto (DESIGN.md §4): la única forma de
 * decir "{clase} · AL{n}" en toda la plataforma (trust/18 §2.3 — clase+AL
 * como badge, jamás como titular). El nivel va en mono (dato verificable);
 * `detail` reemplaza la etiqueta de clase cuando el contexto ya la aporta
 * (p. ej. el verifierId en el certificado).
 */

export interface AssuranceBadgeProps {
  readonly level: AssuranceLevel;
  readonly verdict: VerdictTone;
  /** Clase decisoria cruda (freeze §4); se etiqueta con classLabel(). */
  readonly verifierClass?: string;
  readonly detail?: string;
  readonly className?: string;
}

export function AssuranceBadge({
  level,
  verdict,
  verifierClass,
  detail,
  className
}: AssuranceBadgeProps): React.ReactElement {
  const label = detail ?? (verifierClass ? classLabel(verifierClass) : undefined);
  return (
    <Badge variant={verdict} className={className}>
      {/* span intermedio: el Badge fuerza size-3 en <svg> hijos directos */}
      <span className="flex items-center">
        <AssuranceScale level={level} />
      </span>
      <span>
        {label ? <>{label} · </> : null}
        <span className="font-mono font-medium">{level}</span>
      </span>
    </Badge>
  );
}
