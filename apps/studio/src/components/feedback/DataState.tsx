/**
 * Estados de datos diseñados (F3, ficha punto 2): carga con skeleton, vacío
 * con acción, error con recuperación. Copy en ustedeo (DESIGN.md §8): los
 * errores dicen qué pasó y cómo seguir; los estados vacíos invitan a actuar.
 */

import { RotateCw } from 'lucide-react';
import React from 'react';

import { Button } from '@/components/ui/button';

export function LoadingState({ label }: { readonly label: string }): React.ReactElement {
  return (
    <div
      role="status"
      aria-label={label}
      className="flex flex-col gap-3 rounded-lg border bg-card p-4"
    >
      <span className="sr-only">{label}</span>
      <div className="h-4 w-2/3 animate-pulse rounded bg-muted" />
      <div className="h-4 w-1/2 animate-pulse rounded bg-muted" />
      <div className="h-4 w-3/5 animate-pulse rounded bg-muted" />
    </div>
  );
}

export function EmptyState({
  title,
  hint
}: {
  readonly title: string;
  readonly hint?: string;
}): React.ReactElement {
  return (
    <div className="rounded-lg border border-dashed px-4 py-8 text-center">
      <p className="text-sm text-foreground">{title}</p>
      {hint && <p className="mt-1 text-sm text-muted-foreground">{hint}</p>}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry
}: {
  readonly message: string;
  readonly onRetry: () => void;
}): React.ReactElement {
  return (
    <div role="alert" className="rounded-lg border bg-card p-4">
      <p className="text-sm text-foreground">No se pudieron cargar los datos.</p>
      <p className="mt-1 text-sm text-muted-foreground">{message}</p>
      <Button variant="outline" size="sm" className="mt-3" onClick={onRetry}>
        <RotateCw data-icon="inline-start" />
        Reintentar
      </Button>
    </div>
  );
}
