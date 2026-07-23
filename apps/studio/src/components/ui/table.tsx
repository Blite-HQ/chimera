import React from 'react';

import { cn } from '@/lib/utils';

/**
 * Table (shadcn, vendoreado y ajustado al chasis Blite — extraído F3 por
 * repetición real entre RunsView y ArtifactsView): contenedor con scroll
 * horizontal propio, ring flat (§3b), th eyebrow y celdas densas.
 */

export function Table({ className, ...props }: React.ComponentProps<'table'>): React.ReactElement {
  return (
    <div className="overflow-x-auto rounded-xl ring-1 ring-foreground/10">
      <table className={cn('w-full text-sm', className)} {...props} />
    </div>
  );
}

export function TableHeader(props: React.ComponentProps<'thead'>): React.ReactElement {
  return <thead {...props} />;
}

export function TableBody(props: React.ComponentProps<'tbody'>): React.ReactElement {
  return <tbody {...props} />;
}

export function TableRow({ className, ...props }: React.ComponentProps<'tr'>): React.ReactElement {
  return (
    <tr
      className={cn('border-b border-border transition-colors last:border-b-0', className)}
      {...props}
    />
  );
}

export function TableHead({ className, ...props }: React.ComponentProps<'th'>): React.ReactElement {
  return (
    <th
      scope="col"
      className={cn(
        'px-4 py-2 text-left text-xs font-medium tracking-wider text-muted-foreground uppercase',
        className
      )}
      {...props}
    />
  );
}

export function TableCell({ className, ...props }: React.ComponentProps<'td'>): React.ReactElement {
  return <td className={cn('px-4 py-2', className)} {...props} />;
}
