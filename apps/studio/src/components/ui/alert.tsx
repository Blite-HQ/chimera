import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';

import { cn } from '@/lib/utils';

/**
 * Alert — vendoreado de la landing de Blite y extendido con las variantes
 * del nivel de status (DESIGN.md §2 nivel 2): mismo patrón flat de la
 * landing (bg-card + texto/ícono en el color del status), sin tintes de
 * fondo ni sombras. La landing solo trae default/destructive; info/
 * success/warning consumen los tokens status-*.
 */
const alertVariants = cva(
  "group/alert relative grid w-full gap-1 rounded-lg border px-2 py-2 text-left text-sm has-data-[slot=alert-action]:relative has-data-[slot=alert-action]:pr-16 has-[>svg]:grid-cols-[auto_1fr] has-[>svg]:gap-x-2 *:[svg]:row-span-2 *:[svg]:translate-y-0.5 *:[svg]:text-current *:[svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: 'bg-card text-card-foreground',
        info: 'bg-card text-status-info *:data-[slot=alert-description]:text-status-info/90 *:[svg]:text-current',
        success:
          'bg-card text-status-success *:data-[slot=alert-description]:text-status-success/90 *:[svg]:text-current',
        warning:
          'bg-card text-status-warning *:data-[slot=alert-description]:text-status-warning/90 *:[svg]:text-current',
        destructive:
          'bg-card text-destructive *:data-[slot=alert-description]:text-destructive/90 *:[svg]:text-current'
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
