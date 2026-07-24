import { History } from 'lucide-react';
import React from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

/**
 * Banner de honestidad (D1): Replay es un modo legítimo — repite una sesión
 * grabada real — pero jamás debe leerse como datos en vivo. Franja
 * prominente al tope de la columna de contenido (AppShell la recibe como
 * slot puro, sin decidir por su cuenta si se muestra — esa decisión vive en
 * App.tsx vía isLiveMode()).
 */
export function ReplayBanner(): React.ReactElement {
  return (
    <Alert variant="info" className="rounded-none border-x-0 border-t-0 px-4 md:px-8">
      <History />
      <AlertTitle>Modo Replay</AlertTitle>
      <AlertDescription>Está viendo una sesión grabada, no datos en vivo.</AlertDescription>
    </Alert>
  );
}
