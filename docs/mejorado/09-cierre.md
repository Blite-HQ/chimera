# Cierre de Mejorado — de «terminado» a «completado»

> Sesión de control, 2026-08-10 (decisiones #170–#174). Todas las sesiones del
> plan corrieron y mergearon (salvo C-2, en verificación), pero dejaron
> bloqueos, ceremonias y reencuadres. Este doc es el inventario completo y el
> plan para cerrarlos. Los reencuadres de Dylan están en #173.

## 1 · Inventario terminado → completado

### A. Estado incierto

| ítem                            | estado                                                                    | siguiente paso |
| ------------------------------- | ------------------------------------------------------------------------- | -------------- |
| **C-2** (C3→C11 + C12–C15, CP7) | **VALIDADA Y CONVALIDADA (#175)** — mergeada @52c90fa, gates vivos verdes | — cerrado      |

### B. Bloqueados-por-Dylan (insumos humanos)

- **P8 branding** — **DESBLOQUEADO (#175)**: las 21 referencias están en
  `~/projects/blite/hackathons/2026/Quantathon/branding-refs/`; entra a F1.
- **Grabar la sesión agéntica real** — API key de Anthropic de Dylan (la
  grabación paga llamadas reales del proposer); runbook en #145.
- **Sesión estratégica** (valor/público/Marco) — ordena el backlog de VISIÓN.

### C. Acciones y ceremonias de CONTROL

| acción                                                                       | estado                                                  |
| ---------------------------------------------------------------------------- | ------------------------------------------------------- |
| Colisión de numeración del ledger                                            | RESUELTA (#170, sufijos -V/-O)                          |
| `main` pública sincronizada                                                  | HECHA (#172)                                            |
| `CLAUDE.md` (contexto fresco para agentes)                                   | HECHO (#174)                                            |
| Ceremonia tabla `projects` (`docs/esquema-datos-v2.md`, DDL en handoff P-ui) | **HECHA (#176)** — F1 llena datos y valida FK en el API |
| Ceremonia 3.ª forma de body `POST /runs` (ablación; spec endpoints-studio)   | **HECHA (#177)** — F2 implementa el wire                |
| Ceremonia fusión `ExternalImportStatement` + `McpToolImport` (C-12)          | pendiente — puede esperar a C-2                         |
| Podar `ejercicio/sf-ratificacion-simulada` y ramas viejas remotas            | pendiente (handoff O §3.2)                              |
| Historia del repo (pasada integral)                                          | POST-Mejorado por decisión previa                       |

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

## 5 · Estado post-merge (#178, 2026-08-11)

F1 y F2 VALIDADOS Y MERGEADOS en `mejorado/base` (checkpoint #178; fricción de
integración 401↔ablación arreglada por control). Decisiones de Dylan: **P11
entra al cierre** (addendum de F1: app procrastinate + worker en compose →
approval humano VIVO) y **P12 queda en tramo 1**. Orden restante:

1. **Addendum P11** (sesión corta, rango #190–#199 del bloque F1).
2. **Grabación de la sesión real** (Dylan, runbook #145) — contra este árbol.
3. **F3 saneamiento-final** (prompt §6) — suma los ítems heredados de #178.
4. Auditoría de fase (tres llaves de #101) → cierre de Mejorado.

## 6 · Prompts de lanzamiento

### Addendum P11 (post-#178, decisión de Dylan)

> Eres la sesión ADDENDUM-P11 del cierre de Mejorado. Creá el worktree
> `mejorado/addendum-p11` desde `mejorado/base`. Lee PRIMERO: `CLAUDE.md` ·
> `docs/mvp/decisiones.md` #148 (el puerto JobQueue), #183/#184 (el gate de
> aprobación y la card) y #178 (este encargo) · el bloque REGLAS de
> `docs/mejorado/05-plan-paralelo.md` §4. Tu rango de ledger: **#190–#199**.
>
> Alcance ÚNICO: registrar la app procrastinate del worker y prenderla en
> compose (hoy el perfil `queue` existe pero el worker crashea sin app
> registrada, #146-nota) para que una capability `interaction: job` se ejecute
> de verdad y un `approval.requested` REAL llegue a la card del Studio. DoD:
> compose up con worker vivo + un run que pide aprobación, se aprueba desde el
> Studio y termina — VIVO, no fixtures. Nada fuera de ese alcance; cierra en tu
> rama sin mergear, registro + handoff a control.

Los tres se pegan tal cual en una sesión nueva del repo principal. CLAUDE.md ya
carga el contexto base; el bloque REGLAS de `05-plan-paralelo.md` §4 sigue
vigente y se pega también.

### F1 · CIERRE-PRODUCTO

> Eres la sesión CIERRE-PRODUCTO del cierre de Mejorado. Creá el worktree
> `mejorado/cierre-producto` desde `mejorado/base`. Lee PRIMERO: `CLAUDE.md` ·
> `docs/mejorado/09-cierre.md` (tu alcance es §2·F1 completo) · el bloque
> REGLAS de `docs/mejorado/05-plan-paralelo.md` §4 · el handoff P-ui (bloque
> «Sesión PRODUCTO-STUDIO» del ledger) · decisiones #170–#177. Tu rango de
> ledger: **#180–#199**. Modo #121: Opus orquesta → Sonnet implementa → Opus
> valida.
>
> Notas de alcance: la tabla `projects` YA existe (ceremonia #176) — te toca
> datos, validación de FK en el API al crear el run, y el doc corto de
> projects/workspaces. P8 branding está DESBLOQUEADO: las 21 referencias están
> en `~/projects/blite/hackathons/2026/Quantathon/branding-refs/`; la decisión
> red-de-nodos vs 3-barras y el sistema 16px se toman CON Dylan
> (AskUserQuestion) antes de implementar. DoD: gates completos verdes +
> verificación VIVA contra compose de cada ítem (401, chat con
> `approval.requested` real, P10, files). Cierre: registro en ledger + tabla de
> interacciones + handoff a control. Nada de push sin coordinación.

### F2 · CIERRE-PLATAFORMA/CIENCIA

> Eres la sesión CIERRE-PLATAFORMA/CIENCIA del cierre de Mejorado. Creá el
> worktree `mejorado/cierre-plataforma` desde `mejorado/base`. Lee PRIMERO:
> `CLAUDE.md` · `docs/mejorado/09-cierre.md` (tu alcance es §2·F2 completo) ·
> el bloque REGLAS de `docs/mejorado/05-plan-paralelo.md` §4 · el handoff de
> plataforma (`docs/mejorado/08-handoff-plataforma.md`) y el handoff V (bloque
> «sesión VISUAL/CIENCIA» del ledger) · decisiones #170–#177. Tu rango de
> ledger: **#200–#219**. Modo #121: Opus orquesta → Sonnet implementa → Opus
> valida.
>
> Notas de alcance: la 3.ª forma de body de `POST /runs` YA está registrada
> (ceremonia #177) — implementá el wire exactamente como la spec lo declara.
> Para ICE opción (b): las dos comprobaciones del handoff §1.1 son OBLIGATORIAS
> antes de sacar el geojson crudo. DoD: gates completos verdes + CP6 VIVO
> contra compose (ablación E2E: mapa + panel + curva en el Studio). Cierre:
> registro en ledger + tabla de interacciones + handoff a control. Nada de push
> sin coordinación. F1 corre en paralelo en otro worktree: el venv es
> compartido — cualquier cambio de dependencias se coordina con control ANTES
> de aplicarlo.

### F3 · SANEAMIENTO-FINAL (lanzar SOLO tras el merge de F1+F2)

> Eres la sesión SANEAMIENTO-FINAL del cierre de Mejorado. Creá el worktree
> `mejorado/saneamiento-final` desde `mejorado/base` (ya con F1+F2 mergeados).
> Lee PRIMERO: `CLAUDE.md` · `docs/mejorado/09-cierre.md` §2·F3 ·
> `docs/mejorado/06-saneamiento.md` y `07-censo-documental.md` (tu antecesor y
> su censo) · decisiones #170–#177 y los handoffs de F1/F2. Tu rango de ledger:
> **#220–#239**. Modo #121.
>
> Alcance: el refactoring documental final diferido en #108–#118 — reestructurar
> docs, actualizarlos a TODO lo que cambió en la fase, purgar lo obsoleto,
> decidir el destino del ledger (partirlo/moverlo) CON control, y las
> anotaciones sueltas heredadas (incluido el rename del remoto
> `Chimera`→`chimera` sin propagar, #175). La migración a inglés se pregunta a
> Dylan al arrancar (AskUserQuestion). LÍNEA ROJA: los artefactos con digest
> embebido y los docs congelados NO se tocan sin ceremonia. DoD: gates de docs
> verdes + `docs/README.md` como índice fiel. Cierre: registro + handoff a
> control para la auditoría de fase (tres llaves de #101).
