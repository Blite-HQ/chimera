/**
 * P7/M17 — el árbol de rutas anidable de la letra #78, desde el día 1.
 *
 * Lo que estos tests fijan no es «que el router ande»: es que la jerarquía de
 * contención (Workspace → Project → Run → vista) viva en la URL. Una URL que
 * no se puede copiar y pegar para volver al mismo sitio es estado escondido,
 * y el Studio es una herramienta de escrutinio: si un revisor no puede
 * enlazar la pestaña «Verificación» de un run, la revisión no se comparte.
 */

import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryHistory, createRouter, RouterProvider } from '@tanstack/react-router';
import { describe, expect, it, vi } from 'vitest';

import { ThemeProvider } from '@/lib/theme';

import {
  breadcrumbDePath,
  DEFAULT_PROJECT,
  DEFAULT_WORKSPACE,
  routeTree,
  seccionDePath
} from './router';

vi.mock('./spike/GridSpike', () => ({ default: () => <div data-testid="cy-container" /> }));
vi.mock('./views/GridMap', () => ({ default: () => <div data-testid="grid-map-stub" /> }));

function renderEn(ruta: string) {
  const router = createRouter({
    routeTree,
    history: createMemoryHistory({ initialEntries: [ruta] })
  });
  render(
    <ThemeProvider>
      <QueryClientProvider client={new QueryClient()}>
        {/* El router de test es otro que el del módulo — createRouter por
            render evita que dos tests compartan historial. */}
        <RouterProvider router={router as never} />
      </QueryClientProvider>
    </ThemeProvider>
  );
  return router;
}

describe('derivación de la URL (la URL es la fuente de verdad, no un useState paralelo)', () => {
  it('saca la sección del path del proyecto', () => {
    expect(seccionDePath('/w/local/p/islanding-ieee14/artifacts')).toBe('artifacts');
    expect(seccionDePath('/w/local/p/islanding-ieee14/runs/run-1/timeline')).toBe('runs');
  });

  it('cae a runs cuando el path no dice nada (entrada, redirect en vuelo)', () => {
    expect(seccionDePath('/')).toBe('runs');
  });

  it('el breadcrumb incluye el run cuando hay uno abierto', () => {
    expect(breadcrumbDePath('/w/local/p/proj-1/runs/run-1/verificacion')).toEqual([
      'runs',
      'run-1'
    ]);
    expect(breadcrumbDePath('/w/local/p/proj-1/papers')).toEqual(['papers']);
  });
});

describe('árbol de rutas', () => {
  it('la raíz redirige al árbol canónico — no existe una URL fuera de la jerarquía', async () => {
    const router = renderEn('/');

    await screen.findByRole('navigation', { name: /secciones del proyecto/i });
    expect(router.state.location.pathname).toBe(
      `/w/${DEFAULT_WORKSPACE}/p/${DEFAULT_PROJECT}/runs`
    );
  });

  it('un run sin tab no es 404: redirige a la tab por defecto (hilo)', async () => {
    const router = renderEn('/w/local/p/proj-1/runs/run-1');

    await screen.findByRole('navigation', { name: /secciones del proyecto/i });
    expect(router.state.location.pathname).toBe('/w/local/p/proj-1/runs/run-1/hilo');
  });

  it('el nombre del proyecto sale del path — el shell deja de tener uno hardcodeado', async () => {
    renderEn('/w/local/p/mi-investigacion/runs');

    // Aparece dos veces por diseño: la pill del sidebar y el breadcrumb.
    expect(await screen.findAllByText('mi-investigacion')).toHaveLength(2);
  });

  it('navegar a una sección cambia la URL y marca la nav', async () => {
    const router = renderEn('/w/local/p/proj-1/papers');

    await screen.findByRole('navigation', { name: /secciones del proyecto/i });
    expect(router.state.location.pathname).toBe('/w/local/p/proj-1/papers');
    expect(screen.getByRole('button', { name: 'Papers' })).toHaveAttribute('aria-current', 'page');
  });

  it('el ?thread= de la URL abre el form continuando ese hilo (§Contrato-4)', async () => {
    renderEn('/w/local/p/proj-1/runs?thread=run-raiz');

    expect(await screen.findByText(/continúa el hilo/i)).toBeInTheDocument();
  });

  it('ninguna ruta de la app cuelga de /runs — nginx proxea ese prefijo al API', () => {
    const paths = routeTree
      .addChildren([])
      .children?.flatMap((child: { fullPath?: string; children?: { fullPath?: string }[] }) => [
        child.fullPath,
        ...(child.children ?? []).map(nieto => nieto.fullPath)
      ]);

    const colisionan = (paths ?? []).filter(
      (path): path is string => typeof path === 'string' && /^\/runs(\/|$)/.test(path)
    );
    expect(colisionan).toEqual([]);
  });
});
