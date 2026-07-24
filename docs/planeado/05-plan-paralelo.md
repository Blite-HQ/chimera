# Plan de ejecución paralela — Planeado (metodología v2)

> **Estado: VIGENTE (2026-07-24).** La ejecución del backlog de `04-consolidacion.md`.
> Evolución de la metodología MVP (que funcionó: 5 dominios, gates verdes, decisiones al
> momento) endurecida con las lecciones aprendidas: los mocks silenciosos, el compose que
> nunca se booteó, y los contratos implícitos entre dominios.

## Rama base y flujo

- **`planeado/base`** se crea desde `mvp/base` (el MVP queda congelado como base estable).
- Una rama por dominio (`planeado/<dominio>`), worktree propio.
- Merges a `planeado/base` **por checkpoint de costura** (ver abajo), no big-bang al
  final. Nada de push — merges los coordina Dylan.

## Fase 0 — Contratos (UNA sesión, bloquea a las demás)

La lección del MVP: los dominios eran "disjuntos por diseño" y aun así el frontend
terminó con mocks divergentes del API real. Ahora las costuras se especifican ANTES:

1. **Ceremonia de supersede** (A1): "pipeline fijo Fase 1" → "loop agéntico Planeado",
   registrada en `decisiones.md` con el diseño del loop (5 componentes R1) — se marca
   PENDIENTE-Steven y NO bloquea el resto de la Fase 0.
2. **Specs de costura** en `docs/specs/` (formato de `confianza-api-sse.md`):
   - `harness-agentico.md` — loop, plan events, replay por digest, tripwires (A↔E↔D).
   - `capability-ingesta.md` — manifest + claim_type + receta (B↔A).
   - `evidencia-externa.md` — esquema normalizado + predicado de importación (B).
   - `informe-derivado.md` — capabilities plotting/report + binding (C↔B).
   - `superficie-visual.md` — payloads de mapa/plan/aprobación, extensión §9 (D↔E↔A).
   - `endpoints-studio.md` — rutas + formas (E↔D).
3. Cada spec declara: **interfaces con otros dominios** (tabla), **tests de contrato**
   (fixtures compartidos generados DE la spec — un solo origen para Pydantic y Zod), y
   los eventos nuevos que introduce.

## Fase 1 — Implementación paralela (5 sesiones de dominio)

| Dominio             | Alcance (IDs de `04`) | Arranca cuando                                                                                                 |
| ------------------- | --------------------- | -------------------------------------------------------------------------------------------------------------- |
| A · Harness         | A2–A6                 | Fase 0 lista (A3 espera ratificación Steven o la marca PENDIENTE y avanza sobre el diseño registrado)          |
| B · Datos/evidencia | B1–B4                 | Fase 0 lista (B2 puede stubear cr6/cr8 si Sebas no ratifica — patrón MVP)                                      |
| C · Informe         | C1–C3                 | Fase 0 lista; consume fixtures de B por contrato                                                               |
| D · Studio          | D1–D6                 | D1–D2 YA (no dependen de Fase 0); D3–D6 tras specs                                                             |
| E · API             | E1–E2                 | Fase 0 lista; entrega rutas antes de que D las consuma (o D programa contra el contrato con mocks ETIQUETADOS) |

### Reglas heredadas del MVP (funcionaron)

- Opus valida / Sonnet implementa; TDD; 4 gates Python + gates JS verdes antes de cada
  commit; commit por tarea; decisiones al momento en `docs/mvp/decisiones.md` (mismo
  registro, niveles Planeado); GateGuard: declarar y reintentar idéntico; nada de push.

### Reglas NUEVAS (las lecciones)

1. **Cero mocks silenciosos**: todo dato falso en la app corriendo lleva etiqueta visible
   de Replay. En tests, los fixtures de costura vienen del contrato (Fase 0), no se
   inventan por dominio. _(Lección: los 6 queries con fixtures del MVP.)_
2. **Definition of Done incluye integración VIVA**: una feature de costura no está done
   con unit tests — está done cuando corre contra el stack real (`docker compose up`) y
   el smoke lo demuestra. _(Lección: F4 — el compose jamás se booteó en el MVP.)_
3. **Tabla de interacciones por sesión**: cada sesión mantiene al cierre una tabla
   "interfaz tocada → dominio afectado → estado del contrato" en su entrada de
   `decisiones.md`. Cambiar una costura sin actualizar su spec = defecto.
4. **Checkpoints de costura**: cuando ambos lados de un contrato están verdes (ej. E1
   rutas + D3 egress), se mergea a `planeado/base` y se corre el smoke E2E — integración
   incremental, no acumulada. Orden esperado de checkpoints: (1) D1+D2 honestidad+compose,
   (2) E1+D3 rutas+egress, (3) B1+B2 corpus vivo, (4) A2+A5 ModelServer+replay,
   (5) A3+A4+D6 loop+timeline, (6) B3 evidencia, (7) C1–C3+D4–D5 informe+visual.
5. **Presupuesto de sesión**: si una sesión llega a ~70% de contexto sin cerrar su
   checkpoint, commitea en verde, actualiza su tabla de interacciones y entrega el
   handoff — la siguiente retoma con `git pull` + spec + decisiones. _(Regla de
   redundancia del MVP, ahora obligatoria.)_

## Fase 2 — Validación y cierre

1. **Auditoría E2E (Fable)**: los 7 checkpoints verdes → corrida completa del guion
   (`01-demo-dia-d.md`) contra el stack vivo, incluida la prueba anti-mock (Studio vacío
   sin API) y la prueba air-gap (red cortada: mapa, glyphs, replay).
2. **Ensayo del demo + grabación** (`compose.record.yml`) → video de respaldo.
3. **Ratificaciones pendientes** (Steven: supersede A1; Sebas: cr6/cr8; Dylan: decisiones
   #58+) — no bloquean el trabajo, bloquean el CIERRE.
4. Veredicto de paso a Mejorado (`04` §4), empezando por lo que el ensayo pida.

## Prompts generadores

**Prefijo común (todas las sesiones):**

> Corre esta sesión con Opus como validador y delega la implementación a subagentes
> Sonnet. Base: rama `planeado/base` (worktree propio en `planeado/<dominio>`). Lee
> `docs/planeado/04-consolidacion.md` (tu backlog), `docs/planeado/05-plan-paralelo.md`
> (las reglas — las NUEVAS son obligatorias), tu spec en `docs/specs/`, y las notas de
> `knowledge/` que tu spec cita. TDD; gates verdes antes de cada commit; decisiones al
> momento en `docs/mvp/decisiones.md` (nivel Planeado). DoD de costura = integración viva
> contra compose. Cero mocks sin etiqueta. Mantén tu tabla de interacciones. Si GateGuard
> bloquea tu primer edit, declara lo que pide y reintenta idéntico. Nada de push.

- **Fase 0 (contratos):** prefijo + "Ejecuta la Fase 0 de `05-plan-paralelo.md`: escribe
  las 6 specs de costura con sus tests de contrato y registra la ceremonia de supersede
  A1. No implementes features."
- **Dominio A:** prefijo + "Ejecuta A2–A6 de `04-consolidacion.md` §3."
- **Dominio B:** prefijo + "Ejecuta B1–B4." · **C:** "Ejecuta C1–C3." ·
  **D:** "Ejecuta D1–D6 (D1–D2 primero, son el checkpoint 1)." · **E:** "Ejecuta E1–E2."
- **Auditoría (Fable):** "Ejecuta la Fase 2 §1: los 7 checkpoints contra el stack vivo +
  guion completo + prueba air-gap. Veredicto con evidencia ejecutada, no leída."
