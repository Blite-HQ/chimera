# Projects y workspaces — qué existe hoy (F1.1)

> **Estado: VIGENTE (2026-08-11).** Materializa parte de `docs/studio/product-model.md`
> (la doctrina Workspace → Project → Run, decidida en F2a): ESTE doc es el estado
> REAL de implementación, no la visión — dice honestamente qué es una fila de base
> de datos hoy y qué sigue siendo, únicamente, un segmento de URL.

## Por qué este doc

`product-model.md` fija la jerarquía de contención (decidida, aspiracional). Lo que
faltaba — y lo que F1.1 cierra (`docs/mejorado/09-cierre.md` §2·F1, ítem 1) — es un
lugar que diga, sin ambigüedad, cuál de las dos capas de esa jerarquía ya es dato
persistido y cuál sigue siendo un placeholder de ruta.

## `project` — fila relacional persistida

Existe de verdad: tabla `projects` (`docs/esquema-datos-v2.md` §2, ceremonia #176),
`domain_id` con FK a `domains`, servida por `blite.organization.ProjectRepository`
(puerto + adapters in-memory/Postgres, espejo de `blite.events`) y expuesta por
`GET/POST /projects` (`docs/specs/endpoints-studio.md`).

- `POST /runs` (modo misión) referencia un `project_id` OPACO: el evento
  `run.created` lo lleva sin validar (append-only, el log no conoce tablas
  relacionales), pero el API SÍ valida la FK antes de agendar el run
  (`_validate_project_reference`, F1.1 ítem 4) — `project_id` desconocido responde
  `422`, jamás un run fantasma sobre un proyecto que no existe.
- Todo despliegue arranca con el dominio `domain-default` y un proyecto neutro
  `id="default"` (`name="Proyecto por defecto"`) ya sembrados
  (`chimera_api.projects.ensure_default_project`, bootstrap idempotente del
  wiring). La semilla es deliberadamente NEUTRA — decisión #173.1: el caso
  ICE/islanding/IEEE es dato de prueba, jamás un activo del producto, así que el
  proyecto por defecto no lo nombra.

## `workspace` — hoy NO es una entidad persistida

No hay tabla `workspaces`. No hay repositorio, ni ruta `/workspaces`, ni fila en
ninguna base. Lo único que existe es un **segmento de la URL** del Studio:
`/w/:ws/p/:proj/...` (`apps/studio/src/router.tsx`), con
`DEFAULT_WORKSPACE = 'local'` fijo en el código — la forma de la ruta ya es la
definitiva (decidida en F2a para no reescribir rutas después), pero `:ws` hoy es
una constante, no un dato que salga de ningún lado.

`DEFAULT_PROJECT` ya está conciliado: vale `'default'`, el mismo `id` que el
backend siembra en cada arranque. Antes era el literal `'islanding-ieee14'` —
un default de FRONTEND que nombraba un caso de uso concreto en el código y que
además no existía en la base. Se cerró junto con el selector por la decisión
del ledger #173.1 (los datos de un caso de uso son material de prueba, jamás un
activo del producto) y porque un default que apunta a una fila inexistente rompe
el arranque limpio.

Frontera que SÍ queda abierta: el Studio todavía no manda `project_id` al crear
un run (`apps/studio/src/data/mutations.ts`), aunque el API ya valida esa FK y
responde 422 si no la reconoce. El selector cambia de proyecto en la URL, pero
los runs que se creen desde ahí no quedan atribuidos al proyecto.

## Qué implicaría persistir `workspace`

Para que `workspace` deje de ser un placeholder de ruta:

1. **Esquema**: una tabla `workspaces` (`id`, `name`, `created_at`, y algún dato de
   membresía/identidad — `product-model.md` la describe como "el espacio del
   equipo/organización: identidad, permisos, policies") entraría por la MISMA
   ceremonia que abrió `projects` (`docs/esquema-datos-v2.md`, contract-freeze.md).
2. **`projects.workspace_id`**: la FK que hoy no existe — `projects` pasaría a
   colgar de un workspace, no solo de un `domain_id`. Decisión abierta: si
   `workspace` reemplaza a `domain_id` como frontera de partición (AX1b) o
   convive con él como una capa organizacional aparte.
3. **Puerto + adapters**: mismo patrón que `blite.organization.ProjectRepository`
   — un `WorkspaceRepository` en `blite.organization` (o un paquete hermano),
   nunca acceso relacional directo desde `chimera_api`.
4. **Rutas**: `GET/POST /workspaces`, mismo contrato que este doc describe para
   `/projects` — slug validado, `409` en duplicado, dominio/identidad resolviendo
   quién puede ver qué.
5. **Studio**: `DEFAULT_WORKSPACE`/`DEFAULT_PROJECT` dejan de ser constantes;
   `AppShell` los recibe de un query real (mismo cableado que ya existe para
   `me`), y el selector de la sidebar (mencionado en
   `docs/mejorado/09-cierre.md` §2·F1 ítem 1 como pendiente) pasa a listar datos
   reales en vez de nada.

Ninguno de estos cinco puntos está implementado — es la lista de trabajo, no un
estado. Este documento se actualiza el día que el primero de ellos deje de serlo.

## Ver también

- `docs/studio/product-model.md` — la doctrina (Workspace → Project → Run), el
  "por qué" de la jerarquía.
- `docs/esquema-datos-v2.md` §2 — el esquema SQL de `domains`/`projects`.
- `docs/specs/endpoints-studio.md` — el contrato HTTP de `/projects`.
