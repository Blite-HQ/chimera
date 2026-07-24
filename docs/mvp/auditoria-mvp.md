# Auditoría E2E del MVP — etapa 3 (Fable) · 2026-07-23/24

**Veredicto: MVP APROBADO CON CONDICIONES** — el flujo completo funciona integrado y el
reto está resuelto en el nivel "provincia" con el criterio oficial cumplido. Dos
condiciones antes del día D (F1, F4) y el pulido de demo pasa a Planeado por decisión
de Dylan (mantener el MVP como base estable de iteración).

## Qué se verificó (evidencia ejecutada, no leída)

| Verificación                                | Resultado                                                                                                                                                                |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Integración de los 4 dominios en `mvp/base` | 4 merges (runtime-api FF, ciencia/infra/frontend con conflictos triviales por unión) — árbol limpio                                                                      |
| Gates Python                                | **436 passed · cobertura 91.26% · import-linter 12/12 · ruff limpio · pyright 0**                                                                                        |
| Seeds                                       | **5/5 en verde** (bundle, proyección, palanca, ciencia, infra)                                                                                                           |
| Tests API (runs+SSE+certificado)            | 48 passed (8 skipped = Postgres vivo, ver F4)                                                                                                                            |
| Tests Studio                                | 23 passed + 12 en `@chimera/assurance-ui` (= los 35 pre-merge, movidos con la extracción) — PERO ver F1                                                                  |
| Arquitectura JS                             | dependency-cruiser: 0 violaciones (96 módulos)                                                                                                                           |
| **El reto (nivel provincia, ieee6-flujo)**  | **QAOA p=1: r=0.608 ≥ 0.6 (criterio oficial CUMPLIDO)**; p=2: 0.756; p=3: 0.685; baselines CP-SAT r=1.0, GW r=1.0, greedy r=0.80; 5 seeds, std ≤0.005; JSON reproducible |
| CLI del juez                                | `verify-bundle` → **7/7**                                                                                                                                                |

## Hallazgos

- **F1 · ALTA — gate de tests del Studio roto.** `pnpm -C apps/studio run test:run` reporta
  "no tests" y exit 1; la corrida directa (`pnpm exec vitest run`) sí encuentra y pasa
  7 archivos/23 tests pero con **11 errores colgantes** y 255 s de duración (timers/handles
  sin drenar — sospecha: mocks de SSE/EventSource sin cerrar). El CI del frontend está
  ciego hasta arreglarlo. _Condición para cerrar el MVP._
- **F2 · MEDIA — `matplotlib` ausente**: el experimento omite la figura r vs p (el JSON sí
  sale). El entregable la exige. Agregar dep al grupo del entregable/experimento.
- **F3 · BAJA — `highspy` roto** (símbolo faltante): cvxpy cae a otro solver y GW funciona;
  limpiar la dep o pinnear para quitar el ruido del log.
- **F4 · MANUAL PENDIENTE — compose vivo sin bootear en esta auditoría** (config validada
  estáticamente: seed + test de integración verdes; docker 29.3.1 disponible). Correr una
  vez: `bash scripts/smoke_infra.sh` (y contra el stack, los 8 tests skipped de Postgres).
  _Condición para cerrar el MVP._
- **F5 · NOTA — instancia ICE diferida** (decisión ciencia D8: CSVs del ICE no disponibles
  en la sesión): "provincia" = ieee6 congelada. Válido para el MVP; la instancia ICE real
  sube puntaje ODS → primera tarea de Planeado (ciencia).
- **F6 · NOTA — p=3 < p=2** (0.685 vs 0.756): mínimo local del optimizador; reportarlo tal
  cual en la sección de limitaciones (la rúbrica premia esa honestidad, no penaliza el dip).

## Alcance movido a Planeado (decisión de Dylan, 2026-07-23)

El pulido de demo NO bloquea el MVP y abre la iteración Planeado:

1. **Superficie agéntica de presentación** (sin LLM, freeze-compatible): lanzar el run como
   "misión" en lenguaje natural mapeada a capability+claim; timeline narrado como agente.
2. **Reorganización narrativa del contenido del Studio**: Problema → Corrida → Veredicto →
   Resultados (mismo material, orden de la historia — no de la arquitectura).
3. **Guion escénico del demo** (mapa → misión → verificación en vivo → certificado pass →
   la trampa/refutación AL0 → verify-bundle + r vs p).
4. Chat/agente real = sobre ModelServer replay (ya en Planeado del plan maestro).

## Ruta de decisión acordada

Si F1+F4 cierran y el demo ensaya limpio → el MVP queda congelado como base y arranca
Planeado (pulido de demo + ICE + 3 escalas + diferidos del freeze). El intento de resolver
retos 2/3 queda para el final de Planeado / Mejorado, como propuso Dylan.
