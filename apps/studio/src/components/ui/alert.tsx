import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';

import { cn } from '@/lib/utils';

/**
 * Alert — vendoreado de la landing de Blite y extendido con las variantes
 * del nivel de status (DESIGN.md §2 nivel 2). Decisión de Dylan
 * (2026-07-08): a diferencia del patrón bg-card de la landing, las
 * variantes de status llevan el tinte del propio status de fondo (10%) y
 * borde (40%) — el mismo lenguaje que los badges de veredicto.
 */
const alertVariants = cva(
  "group/alert relative grid w-full gap-1 rounded-lg border px-2 py-2 text-left text-sm has-data-[slot=alert-action]:relative has-data-[slot=alert-action]:pr-16 has-[>svg]:grid-cols-[auto_1fr] has-[>svg]:gap-x-2 *:[svg]:row-span-2 *:[svg]:translate-y-0.5 *:[svg]:text-current *:[svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: 'bg-muted/50 text-foreground',
        info: 'border-status-info/40 bg-status-info/10 text-status-info *:data-[slot=alert-description]:text-status-info/90 *:[svg]:text-current',
        success:
          'border-status-success/40 bg-status-success/10 text-status-success *:data-[slot=alert-description]:text-status-success/90 *:[svg]:text-current',
        warning:
          'border-status-warning/40 bg-status-warning/10 text-status-warning *:data-[slot=alert-description]:text-status-warning/90 *:[svg]:text-current',
        destructive:
          'border-destructive/40 bg-destructive/10 text-destructive *:data-[slot=alert-description]:text-destructive/90 *:[svg]:text-current'
      }
    },
    defaultVariants: {
      variant: 'default'
    }
  }
);

function Alert({
  className,
  variant,
  ...props
}: React.ComponentProps<'div'> & VariantProps<typeof alertVariants>) {
  return (
    <div
      data-slot="alert"
      role="alert"
      className={cn(alertVariants({ variant }), className)}
      {...props}
    />
  );
}

function AlertTitle({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="alert-title"
      className={cn(
        'font-medium group-has-[>svg]/alert:col-start-2 [&_a]:underline [&_a]:underline-offset-3 [&_a]:hover:text-foreground',
        className
      )}
      {...props}
    />
  );
}

function AlertDescription({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="alert-description"
      className={cn(
        'text-sm text-balance text-muted-foreground md:text-pretty [&_a]:underline [&_a]:underline-offset-3 [&_a]:hover:text-foreground [&_p:not(:last-child)]:mb-4',
        className
      )}
      {...props}
    />
  );
}

function AlertAction({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div data-slot="alert-action" className={cn('absolute top-2 right-2', className)} {...props} />
  );
}

export { Alert, AlertTitle, AlertDescription, AlertAction };
