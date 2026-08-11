# Cierre de Mejorado — de «terminado» a «completado»

> Sesión de control, 2026-08-10 (decisiones #170–#174). Todas las sesiones del
> plan corrieron y mergearon (salvo C-2, en verificación), pero dejaron
> bloqueos, ceremonias y reencuadres. Este doc es el inventario completo y el
> plan para cerrarlos. Los reencuadres de Dylan están en #173.

## 1 · Inventario terminado → completado

### A. Estado incierto

| ítem                            | estado                                                            | siguiente paso                                                                                           |
| ------------------------------- | ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| **C-2** (C3→C11 + C12–C15, CP7) | sin rastro en el repo; pudo correr en la laptop de Dylan sin push | Dylan verifica; si existe → push y control valida/mergea; si no → decisión junto a la sesión estratégica |

### B. Bloqueados-por-Dylan (insumos humanos)

- **P8 branding** — faltan las 21 referencias visuales.
- **Grabar la sesión agéntica real** — API key de Dylan; runbook en #145.
- **Sesión estratégica** (valor/público/Marco) — ordena el backlog de VISIÓN.

### C. Acciones y ceremonias de CONTROL

| acción                                                                       | estado                                                      |
| ---------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Colisión de numeración del ledger                                            | RESUELTA (#170, sufijos -V/-O)                              |
| `main` pública sincronizada                                                  | HECHA (#172)                                                |
| `CLAUDE.md` (contexto fresco para agentes)                                   | HECHO (#174)                                                |
| Ceremonia tabla `projects` (`docs/esquema-datos-v2.md`, DDL en handoff P-ui) | pendiente — control la registra, CIERRE-PRODUCTO implementa |
| Ceremonia 3.ª forma de body `POST /runs` (ablación; spec endpoints-studio)   | pendiente — ídem, para el wire de CP6                       |
| Ceremonia fusión `ExternalImportStatement` + `McpToolImport` (C-12)          | pendiente — puede esperar a C-2                             |
| Podar `ejercicio/sf-ratificacion-simulada` y ramas viejas remotas            | pendiente (handoff O §3.2)                                  |
| Historia del repo (pasada integral)                                          | POST-Mejorado por decisión previa                           |

### D. Implementación pendiente → tres frentes

## 2 · Frentes de implementación

Modo (#121 vigente): Opus orquesta → Sonnet implementa → Opus valida; control
valida/mergea cada frente con gates vivos. Cada prompt lleva el bloque REGLAS
de `05-plan-paralelo.md` §4 + este doc + `CLAUDE.md` ya en el árbol.
**Rangos de ledger asignados** (regla #170): PRODUCTO #180–#199 ·
PLATAFORMA/CIENCIA #200–#219 · SANEAMIENTO #220–#239.

### F1 · CIERRE-PRODUCTO (worktree `mejorado/cierre-producto`, rango #180+)

1. **Sistema organizacional completo (#173.4):** tabla `projects` (tras la
   ceremonia), doc corto formalizando projects/workspaces (hoy no existe),
   selector/sidebar consumiendo datos reales.
2. **Flip 401-obligatorio** (frontera declarada en `test_auth_session.py`).
3. **Chat completo:** approval card contra un `approval.requested` REAL (armar
   un run que pida aprobación), cert 409 silenciado salvo `completado`, pulido
   del hilo.
4. **P10 vivo** contra compose (receta exacta en handoff P-ui §3).
5. **P12** ingesta RAG/KB con procedencia DSSE (O ya corrió: desbloqueado).
6. **Content store durable por defecto** en compose (`blite.content_fs` ya
   existe; cambia el plano de confianza a mejor: la evidencia deja de
   evaporarse — decisión de control al validar el frente).
7. Flake `NewRunView.test.tsx` (delay por tecla de user-event).

### F2 · CIERRE-PLATAFORMA/CIENCIA (worktree `mejorado/cierre-plataforma`, rango #200+)

1. **ICE opción (b) (#173.1):** dos comprobaciones previas (índices nexus +
   fixture propio para `test_geojson_to_graph.py`) → sale el geojson crudo.
2. **G3 residual:** los corpus por ruta literal en el API pasan a resolverse
   por `datasets:` del `DistributionManifest` (#167-O).
3. **O7 reencuadrado (#173.2):** artifact geoespacial genérico en el registry
   de lentes, disparado por tipo de dato; medir FPS ahí.
4. **V9 AI-QEM** (no bloqueado; baseline y control negativo listos desde V4) +
   declarar el brazo `mitigated` en `scripts/run_ablation.py`.
5. **CP6 DoD vivo:** compose + `run_ablation.py` + mapa/panel/curva en Studio
   (tras la ceremonia de la 3.ª forma de body).
6. **G5/G6/G8** triage y cierre (o registro con causa definitiva).
7. **Escalación `side_effects` de §13** (sin motor de reintentos) + convención
   ADR-029 (`TestGenericitySelfCheck` como regla escrita).

### F3 · SANEAMIENTO-FINAL (worktree `mejorado/saneamiento-final`, rango #220+)

El «refactoring documental final» diferido en #108–#118, ahora mandatorio
(#173.3): reestructurar, actualizar docs a TODO lo que cambió en la fase,
mover/partir el ledger si procede, purgar lo obsoleto. Corre AL FINAL, sobre
árbol estable. Migración a inglés: decisión de Dylan al lanzarla.

## 3 · Orden

1. Control: ceremonias `projects` + 3.ª forma de body (desbloquean F1/F2).
2. F1 y F2 en paralelo (worktrees separados; venv compartido — coordinar deps).
3. C-2 según verificación de Dylan (en cualquier momento).
4. F3 al final, sobre el árbol ya mergeado.
5. Auditoría de fase (tres llaves de #101) → cierre de Mejorado.

## 4 · Qué NO entra (→ fase VISIÓN, la ordena la sesión estratégica)

Editor tipo Overleaf · sistema completo de artifacts de chat · suite de datos
(todas las etapas) · research/deep-search · pipeline de publicación de papers ·
benchmark vs co-scientist y afines · V7 QEC medido · destino del diferenciador
de confianza (análisis Marco).
