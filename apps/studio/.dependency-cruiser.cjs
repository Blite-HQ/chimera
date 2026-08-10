/**
 * Dependency Cruiser configuration for apps/studio.
 *
 * Enforces INV-1 (gateway chokepoint) at the module graph level:
 * all outbound calls from Studio must go through gatewayClient.ts.
 *
 * Co-located here (rather than at the repo root) because its scope is only
 * this app; dependency-cruiser auto-discovers this file from the cwd.
 *
 * Run: pnpm -C apps/studio exec depcruise src
 */

/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: 'INV-1: no-direct-cross-feature-external-calls',
      severity: 'error',
      comment:
        'Feature modules must not make direct fetch/http calls; route all egress via gatewayClient (INV-1).',
      from: {
        path: '^src/(?!gatewayClient)'
      },
      to: {
        path: '^(\\.\\./\\.\\./)?node_modules/(axios|node-fetch|got|superagent|ky)/'
      }
    },
    {
      name: 'F3: views-consume-only-the-data-layer',
      severity: 'error',
      comment:
        'Las vistas/componentes consumen datos SOLO vía src/data/** (queryOptions + Zod en la frontera) — jamás fixtures ni gatewayClient directo (F3; S10 cambia la fuente sin tocar vistas).',
      from: {
        // `screens.tsx` entra acá el mismo día que existe: separar la raíz
        // de las pantallas rompió el ciclo App↔router, y si el gate no las
        // siguiera, la separación habría comprado el ciclo a cambio de
        // perder F3 sobre el archivo más grande del Studio.
        path: '^src/(views|components|spike|screens\\.tsx|App\\.tsx)',
        pathNot: '\\.test\\.(ts|tsx)$'
      },
      to: {
        path: '^src/(fixtures|gatewayClient)'
      }
    },
    {
      name: 'no-circular',
      severity: 'error',
      comment: 'Circular dependencies are forbidden.',
      from: {},
      to: {
        circular: true
      }
    }
  ],
  options: {
    doNotFollow: {
      path: 'node_modules'
    },
    tsPreCompilationDeps: true,
    tsConfig: {
      fileName: 'tsconfig.json'
    },
    enhancedResolveOptions: {
      exportsFields: ['exports'],
      conditionNames: ['import', 'require', 'node', 'default']
    },
    reporterOptions: {
      dot: {
        collapsePattern: 'node_modules/[^/]+'
      }
    }
  }
};
