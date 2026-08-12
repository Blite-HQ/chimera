import React from 'react';

import { cn } from '@/lib/utils';

/**
 * Logomark (DESIGN.md §7): un racimo de tres escalas de círculo — un núcleo
 * grande en el token de marca (`--color-brand`) rodeado de un anillo de seis
 * medianos y seis pequeños en tinta (`currentColor`). Reobra P8 (docs #P8):
 * reemplaza la geometría F1 de tres barras, que reutilizaba sin querer el
 * dibujo del glifo de dato `AssuranceScale` — la marca ahora se lee aparte
 * del dato. El favicon (`public/favicon.svg`) usa la variante compacta
 * (núcleo + seis medianos, sin los pequeños que se pierden bajo 1px a 16px).
 */
export function BrandMark({ className }: { readonly className?: string }): React.ReactElement {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={cn('h-5 w-auto', className)}>
      {/* Pequeños (tinta) */}
      <circle cx="19.25" cy="17.66" r="1.1" fill="currentColor" />
      <circle cx="10.59" cy="20.89" r="1.3" fill="currentColor" />
      <circle cx="3.45" cy="15.11" r="1.0" fill="currentColor" />
      <circle cx="5.01" cy="6.33" r="1.2" fill="currentColor" />
      <circle cx="13.28" cy="2.89" r="0.9" fill="currentColor" />
      <circle cx="20.55" cy="8.89" r="1.2" fill="currentColor" />

      {/* Medianos (tinta) */}
      <circle cx="19.18" cy="13.01" r="2.7" fill="currentColor" />
      <circle cx="14.60" cy="18.44" r="2.4" fill="currentColor" />
      <circle cx="7.21" cy="17.71" r="2.9" fill="currentColor" />
      <circle cx="5.06" cy="10.78" r="2.5" fill="currentColor" />
      <circle cx="9.25" cy="5.18" r="2.8" fill="currentColor" />
      <circle cx="16.40" cy="6.75" r="2.3" fill="currentColor" />

      {/* Núcleo (único elemento con croma, token de marca) */}
      <circle cx="12" cy="12" r="4" fill="var(--color-brand)" />
    </svg>
  );
}
