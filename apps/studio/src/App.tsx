import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from '@tanstack/react-router';
import React from 'react';

import { ThemeProvider } from '@/lib/theme';

import { router } from './router';

/**
 * Chimera Studio — la RAÍZ, y nada más: tema, cliente de queries y router.
 *
 * Las pantallas viven en `screens.tsx` (ver el porqué allá): antes estaban
 * acá mismo y el router las importaba, así que la raíz y el router se
 * importaban mutuamente — un ciclo que `depcruise` marcaba en rojo.
 */

const queryClient = new QueryClient();

export default function App(): React.ReactElement {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </ThemeProvider>
  );
}
