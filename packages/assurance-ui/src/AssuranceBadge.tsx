import React from 'react';

import { AssuranceScale, type VerdictTone } from './AssuranceScale';
import { classLabel, type AssuranceLevel } from './assurance';
import { VerdictPill } from './VerdictPill';

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
    <VerdictPill tone={verdict} className={className}>
      <AssuranceScale level={level} />
      <span>
        {label ? <>{label} · </> : null}
        <span className="font-mono font-medium">{level}</span>
      </span>
    </VerdictPill>
  );
}
