import {
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  redirect,
  useNavigate,
  useParams,
  useRouterState
} from '@tanstack/react-router';
import React from 'react';
import { z } from 'zod';

import { useQuery } from '@tanstack/react-query';

import { AppShell } from '@/components/app-shell/AppShell';
import { ReplayBanner } from '@/components/app-shell/ReplayBanner';

import { ArtifactsScreen, KnowledgeScreen, RunDetailScreen, RunsScreen, SECTIONS } from './App';
import { isLiveMode } from './data/env';
import { meQueryOptions } from './data/queries';
import PapersView from './views/PapersView';

/**
 * Router del Studio (P7/M17) — **TanStack Router**, decidido con Dylan
 * (2026-08-03) tras comparar contra React Router v7 y wouter: mismo
 * ecosistema que `@tanstack/react-query` (ya instalado) y params tipados de
 * verdad, que es lo que un árbol anidado de cuatro niveles necesita.
 *
 * **El árbol es el de la letra #78 desde el día 1**
 * (`docs/studio/product-model.md`): `/w/:ws/p/:proj/runs/:id/:tab`. La
 * jerarquía de contención (Workspace → Project → Run) deja de vivir en
 * `useState` y pasa a la URL, que es donde el usuario puede copiarla,
 * compartirla y volver con el botón atrás del navegador. Hasta P6/M15 el
 * workspace y el project son los valores por defecto de abajo — la FORMA de
 * la ruta ya es la definitiva, así que P6 llena datos, no reescribe rutas.
 *
 * **Colisión con nginx, verificada:** `docker/studio-nginx.conf` proxea
 * `location ~ ^/(runs|health)` al API. Por eso el árbol NO expone ninguna
 * ruta de primer nivel `/runs/...`: quedaría capturada por el proxy y el
 * navegador recibiría JSON en vez de la SPA. Todas las rutas de la app
 * cuelgan de `/w/…`, que el bloque `try_files … /index.html` sí sirve.
 */

/** Defaults hasta que P6/M15 traiga workspaces y projects reales. */
export const DEFAULT_WORKSPACE = 'local';
export const DEFAULT_PROJECT = 'islanding-ieee14';

/** Tab por defecto de un run: la conversación (D6, decisión #93). */
const DEFAULT_TAB = 'hilo';

const rootRoute = createRootRoute({ component: () => <Outlet /> });

/**
 * `/` no es una pantalla: es la entrada. Redirige al árbol canónico para que
 * jamás exista una URL "de la app" fuera de la jerarquía de contención.
 */
const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  beforeLoad: () => {
    throw redirect({
      to: '/w/$ws/p/$proj/runs',
      params: { ws: DEFAULT_WORKSPACE, proj: DEFAULT_PROJECT }
    });
  }
});

/** Layout del proyecto: shell + navegación. Todo lo demás cuelga de acá. */
function ProjectLayout(): React.ReactElement {
  const { ws, proj } = useParams({ from: projectRoute.id });
  const navigate = useNavigate();
  const pathname = usePathname();
  const section = seccionDePath(pathname);
  // P6 — quién opera sale del API, no de una constante: el bloque de usuario
  // muestra la MISMA identidad que quedará en `actor_id` de los eventos.
  const me = useQuery(meQueryOptions()).data;

  return (
    <AppShell
      projectName={proj}
      {...(me !== null &&
        me !== undefined && { user: { id: me.id, label: me.id.split(':')[1] ?? me.id } })}
      sections={SECTIONS}
      activeSection={section}
      onSectionChange={sectionId =>
        void navigate({ to: `/w/$ws/p/$proj/${sectionId}`, params: { ws, proj } })
      }
      breadcrumb={breadcrumbDePath(pathname)}
      onBreadcrumbNavigate={index => {
        // Tramo 0 = la raíz de la sección actual: navegar ahí cierra el detalle.
        if (index === 0) {
          void navigate({ to: `/w/$ws/p/$proj/${section}`, params: { ws, proj } });
        }
      }}
      banner={isLiveMode() ? undefined : <ReplayBanner />}
    >
      <div className="mx-auto max-w-7xl px-4 py-8 md:px-8">
        <Outlet />
      </div>
    </AppShell>
  );
}

const projectRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/w/$ws/p/$proj',
  component: ProjectLayout
});

/** Pantalla de runs; `?thread=` la abre continuando un hilo (§Contrato-4). */
const runsRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: 'runs',
  validateSearch: z.object({ thread: z.string().min(1).optional() }),
  component: RunsRouteScreen
});

function RunsRouteScreen(): React.ReactElement {
  const { ws, proj } = useParams({ from: projectRoute.id });
  const { thread } = runsRoute.useSearch();
  const navigate = useNavigate();

  return (
    <RunsScreen
      onSelectRun={runId =>
        void navigate({
          to: '/w/$ws/p/$proj/runs/$runId/$tab',
          params: { ws, proj, runId, tab: DEFAULT_TAB }
        })
      }
      {...(thread !== undefined && { threadId: thread })}
      onThreadConsumed={() =>
        void navigate({ to: '/w/$ws/p/$proj/runs', params: { ws, proj }, search: {} })
      }
    />
  );
}

/**
 * Un run sin tab no es un error del usuario: es la forma corta de la URL.
 * Se redirige a la tab por defecto en vez de mostrar un 404.
 */
const runRedirectRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: 'runs/$runId',
  beforeLoad: ({ params }) => {
    throw redirect({
      to: '/w/$ws/p/$proj/runs/$runId/$tab',
      params: { ...params, tab: DEFAULT_TAB }
    });
  }
});

const runDetailRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: 'runs/$runId/$tab',
  component: RunDetailRouteScreen
});

function RunDetailRouteScreen(): React.ReactElement {
  const { ws, proj, runId, tab } = useParams({ from: runDetailRoute.id });
  const navigate = useNavigate();

  return (
    <RunDetailScreen
      runId={runId}
      tab={tab}
      onTabChange={siguiente =>
        void navigate({
          to: '/w/$ws/p/$proj/runs/$runId/$tab',
          params: { ws, proj, runId, tab: siguiente }
        })
      }
      onBack={() => void navigate({ to: '/w/$ws/p/$proj/runs', params: { ws, proj }, search: {} })}
      onContinueThread={raiz =>
        void navigate({
          to: '/w/$ws/p/$proj/runs',
          params: { ws, proj },
          search: { thread: raiz }
        })
      }
    />
  );
}

/**
 * Artifacts / Papers / Knowledge: secciones de PROYECTO. Reciben `onBack`
 * porque desde ellas se abre un run, y volver tiene que llevar a la sección
 * de la que se salió, no al inicio (go-back de P7).
 */
function seccionDeProyecto(
  path: 'artifacts' | 'papers' | 'knowledge',
  render: (abrirRun: (runId: string) => void) => React.ReactElement
) {
  return createRoute({
    getParentRoute: () => projectRoute,
    path,
    component: function SeccionScreen(): React.ReactElement {
      const { ws, proj } = useParams({ from: projectRoute.id });
      const navigate = useNavigate();
      return render(
        runId =>
          void navigate({
            to: '/w/$ws/p/$proj/runs/$runId/$tab',
            params: { ws, proj, runId, tab: DEFAULT_TAB }
          })
      );
    }
  });
}

const artifactsRoute = seccionDeProyecto('artifacts', abrirRun => (
  <ArtifactsScreen onOpenRun={abrirRun} />
));
const papersRoute = seccionDeProyecto('papers', () => <PapersView />);
const knowledgeRoute = seccionDeProyecto('knowledge', abrirRun => (
  <KnowledgeScreen onOpenRun={abrirRun} />
));

/**
 * Sección y breadcrumb se DERIVAN de la URL, no de estado paralelo: si el
 * usuario pega una URL o usa el botón atrás, el shell tiene que reflejarlo.
 * Mantener un `useState` en paralelo sería tener dos fuentes de verdad para
 * lo mismo — el bug clásico de las migraciones a router a medias.
 */
function usePathname(): string {
  return useRouterState({ select: state => state.location.pathname });
}

export function seccionDePath(pathname: string): string {
  return /\/w\/[^/]+\/p\/[^/]+\/([^/?]+)/.exec(pathname)?.[1] ?? 'runs';
}

export function breadcrumbDePath(pathname: string): readonly string[] {
  const run = /\/w\/[^/]+\/p\/[^/]+\/runs\/([^/?]+)/.exec(pathname);
  return run ? ['runs', run[1] as string] : [seccionDePath(pathname)];
}

export const routeTree = rootRoute.addChildren([
  indexRoute,
  projectRoute.addChildren([
    runsRoute,
    runRedirectRoute,
    runDetailRoute,
    artifactsRoute,
    papersRoute,
    knowledgeRoute
  ])
]);

export const router = createRouter({ routeTree });

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}
