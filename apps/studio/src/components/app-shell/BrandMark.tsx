import React from 'react';

import { cn } from '@/lib/utils';

/**
 * Logomark (DESIGN.md §7): la escalera de verificación reducida a tres
 * barras descendentes en Ámbar de sodio (token --color-brand, así se
 * adapta al tema). El favicon usa el mismo dibujo sobre tile fijo.
 */
export function BrandMark({ className }: { readonly className?: string }): React.ReactElement {
  return (
    <svg viewBox="0 0 26 22" aria-hidden="true" className={cn('h-5 w-auto', className)}>
      <rect x="0" y="0" width="6" height="22" rx="1.5" fill="var(--color-brand)" />
      <rect x="10" y="7" width="6" height="15" rx="1.5" fill="var(--color-brand)" />
      <rect x="20" y="14" width="6" height="8" rx="1.5" fill="var(--color-brand)" />
    </svg>
  );
}
