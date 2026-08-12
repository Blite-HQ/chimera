import * as React from 'react';

import { cn } from '@/lib/utils';

/**
 * Textarea — shadcn, alineado al mismo lenguaje de superficie que
 * `SelectTrigger` (DESIGN.md §3b): radio `lg`, borde de 1px sobre
 * `border-input`, foco por `ring-3 ring-ring/50` (el acento de marca), transición solo
 * de colores. No tiene altura del eje 32/40/48 porque no es un control de una
 * línea: la altura la fija el consumidor (`min-h-*` en potencias de 2).
 */
function Textarea({ className, ...props }: React.ComponentProps<'textarea'>) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        'flex w-full rounded-lg border border-input bg-transparent px-4 py-2 text-sm transition-colors outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 dark:bg-input/30 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40',
        className
      )}
      {...props}
    />
  );
}

export { Textarea };
