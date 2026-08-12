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
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider, queryOptions } from '@tanstack/react-query';
import { createMemoryHistory, createRouter, RouterProvider } from '@tanstack/react-router';
import { describe, expect, it, vi } from 'vitest';

import { ThemeProvider } from '@/lib/theme';

import { projectsQueryOptions } from './data/queries';
import {
  breadcrumbDePath,
  DEFAULT_PROJECT,
  DEFAULT_WORKSPACE,
  routeTree,
  seccionDePath
} from './router';

import type { Project } from './views/types';

vi.mock('./spike/GridSpike', () => ({ default: () => <div data-testid="cy-container" /> }));
vi.mock('./views/GridMap', () => ({ default: () => <div data-testid="grid-map-stub" /> }));

/**
 * F1.1 (ceremonia #176) — solo se mockea `projectsQueryOptions` (mismo
 * criterio de mínimo mock que `screens.test.tsx`): el resto de
 * `./data/queries` queda REAL, así que `meQueryOptions` sigue resolviendo
 * `null` sin red (réplica, sin `VITE_API_URL`).
 */
vi.mock('./data/queries', async importOriginal => {
  const actual = await importOriginal<typeof import('./data/queries')>();
  return { ...actual, projectsQueryOptions: vi.fn(actual.projectsQueryOptions) };
});

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

/**
 * F1.1 (ítem 1, `docs/mejorado/09-cierre.md` §2·F1) — el selector del
 * sidebar consumiendo `GET /projects` real (antes: `AppShell` recibía
 * `projects`/`onProjectChange` ausentes, así que la pill era el único
 * estado posible). `AppShell.ProjectPicker` ya decide no dibujar un
 * selector con menos de dos proyectos (`AppShell.tsx:108-114`) — estos
 * tests fijan que el router LE ENTREGA esa decisión con datos reales, no
 * que la regla exista (eso ya lo cubre `AppShell.test.tsx`).
 *
 * Declarado ANTES de "árbol de rutas" a propósito: ese describe incluye un
 * test ("ninguna ruta de la app cuelga de /runs") que llama
 * `routeTree.addChildren([])` — `addChildren` de TanStack Router MUTA el
 * route object en el lugar (`this.children = children; return this;`), así
 * que después de ese test el `routeTree` compartido del módulo queda con
 * `children: []` para el resto del archivo. Declarar este describe después
 * dejaría CUALQUIER render posterior devolviendo "Not Found" — verificado
 * al bisectar la falla. No es un bug de este cambio: es una fuga de estado
 * preexistente en ese test que no se toca acá (fuera del alcance de F1.1).
 */
describe('selector de proyecto (F1.1 — GET /projects real)', () => {
  const PROJECTS: readonly Project[] = [
    {
      id: 'default',
      domainId: 'domain-default',
      name: 'Proyecto por defecto',
      createdAt: '2026-08-11T00:00:00.000000Z'
    },
    {
      id: 'mi-investigacion',
      domainId: 'domain-default',
      name: 'Mi investigación',
      createdAt: '2026-08-11T00:05:00.000000Z'
    }
  ];

  function mockProjects(projects: readonly Project[]): void {
    vi.mocked(projectsQueryOptions).mockReturnValue(
      queryOptions({ queryKey: ['projects'] as const, queryFn: async () => projects })
    );
  }

  it('con menos de dos proyectos ([] honesto, réplica sin servidor) no dibuja el selector', async () => {
    mockProjects([]);

    renderEn(`/w/${DEFAULT_WORKSPACE}/p/${DEFAULT_PROJECT}/runs`);

    await screen.findByRole('navigation', { name: /secciones del proyecto/i });
    expect(screen.queryByRole('combobox', { name: /proyecto/i })).not.toBeInTheDocument();
  });

  it('con dos o más proyectos reales el selector aparece', async () => {
    mockProjects(PROJECTS);

    renderEn(`/w/${DEFAULT_WORKSPACE}/p/${DEFAULT_PROJECT}/runs`);

    expect(await screen.findByRole('combobox', { name: /proyecto/i })).toBeInTheDocument();
  });

  it('elegir un proyecto navega a su ruta, conservando la sección actual', async () => {
    mockProjects(PROJECTS);
    const user = userEvent.setup();

    const router = renderEn(`/w/${DEFAULT_WORKSPACE}/p/${DEFAULT_PROJECT}/papers`);

    const trigger = await screen.findByRole('combobox', { name: /proyecto/i });
    await user.click(trigger);
    await user.click(await screen.findByRole('option', { name: 'Mi investigación' }));

    expect(router.state.location.pathname).toBe(
      `/w/${DEFAULT_WORKSPACE}/p/mi-investigacion/papers`
    );
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
