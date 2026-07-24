# Auditoría E2E del MVP — etapa 3 (Fable) · 2026-07-23/24

**Veredicto: MVP APROBADO CON CONDICIONES** — el flujo completo funciona integrado y el
reto está resuelto en el nivel "provincia" con el criterio oficial cumplido. Dos
condiciones antes del día D (F1, F4) y el pulido de demo pasa a Planeado por decisión
de Dylan (mantener el MVP como base estable de iteración).

> **Actualización 2026-07-24 — condiciones CERRADAS.** F1–F4 resueltos y verificados en
> la rama `mvp/fix-auditoria` (Opus valida / Sonnet implementa). Las dos condiciones de
> cierre (F1 gate Studio, F4 compose vivo) quedan cumplidas; el MVP puede congelarse como
> base y arrancar Planeado. Evidencia por hallazgo en la sección **«Cierre de hallazgos»**
> al final de este documento; decisiones #52–#55 en `docs/mvp/decisiones.md`.

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

- **F1 · ALTA — gate de tests del Studio roto.** ✅ **CERRADO (2026-07-24).** `pnpm -C apps/studio run test:run` reporta
  "no tests" y exit 1; la corrida directa (`pnpm exec vitest run`) sí encuentra y pasa
  7 archivos/23 tests pero con **11 errores colgantes** y 255 s de duración (timers/handles
  sin drenar — sospecha: mocks de SSE/EventSource sin cerrar). El CI del frontend está
  ciego hasta arreglarlo. _Condición para cerrar el MVP._
- **F2 · MEDIA — `matplotlib` ausente**: ✅ **CERRADO (2026-07-24).** el experimento omite la figura r vs p (el JSON sí
  sale). El entregable la exige. Agregar dep al grupo del entregable/experimento.
- **F3 · BAJA — `highspy` roto** (símbolo faltante): ✅ **CERRADO (2026-07-24).** cvxpy cae a otro solver y GW funciona;
  limpiar la dep o pinnear para quitar el ruido del log.
- **F4 · MANUAL PENDIENTE — compose vivo sin bootear en esta auditoría** ✅ **CERRADO (2026-07-24).** (config validada
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

## Cierre de hallazgos (2026-07-24 · rama `mvp/fix-auditoria`)

Modelo operativo: **Opus valida / Sonnet implementa**. TDD/diagnóstico sistemático donde
aplicó; commit por hallazgo; los 4 gates Python + los gates JS verdes sobre el árbol final.

**Batería final (árbol completo):** `pytest` 436 passed · 9 skipped · 2 xpassed · cobertura
91.26% · `lint-imports` 12/12 · `ruff check`/`format` limpios · `pyright` 0 · Studio
`test:run` 18 archivos/89 tests (4.2 s) · `assurance-ui` `test:run` 2/12 · `eslint` 0
warnings · `depcruise` 0 violaciones (96 módulos).

- **F1 · CERRADO** (commit `2d6af8e`). Causa raíz: el pool `forks` (default de vitest)
  cuelga al spawnear workers bajo presión en el sandbox WSL2 («Timeout waiting for worker»,
  nota #47) — el auditor corrió la config `forks` commiteada y obtuvo el cuelgue 255 s /
  «no tests» / errores colgantes. Fix: `pool: 'threads'` en `apps/studio/vite.config.ts`
  (liviano, CI-safe para tests jsdom puros). Evidencia: `pnpm -C apps/studio run test:run`
  → 18 archivos/89 tests verdes en ~4 s, exit 0; verificado 2× con threads + 9 corridas de
  control con forks (todas verdes); ningún test borrado ni debilitado; `assurance-ui` 12/12.
  Los teardowns de SSE/EventSource ya estaban higiénicos (FakeEventSource.close(),
  `vi.unstubAllGlobals()`, `useRealTimers`), así que la fragilidad era del pool, no del test.
- **F2 · CERRADO** (commit `c861411`). Fix: grupo `[dependency-groups] experiment =
["matplotlib>=3.9"]` + `[tool.uv] default-groups = ["dev","experiment"]` (para que
  `uv run` sin flags lo instale). Evidencia: `uv run python scripts/exp_r_vs_p.py
--instance ieee6-flujo` genera `results/exp_r_vs_p/ieee6-flujo_r_vs_p.png` (640×480, con
  barras de error de `r_muestral` ±std: p1=0.0051, p2/p3=0.0041) además del JSON; matplotlib
  3.11.1. PNG commiteado como artefacto del entregable.
- **F3 · CERRADO** (commit `f1ccf4b`). Causa raíz: el wheel de highspy 1.15.0/1.15.1
  (linux cp312) no exporta `_ZN5Highs13releaseMemoryEv`; cvxpy lo importa al enumerar
  solvers durante `Problem.solve()` → ImportError → caída a otro solver SDP con warning
  ruidoso. Fix: `[tool.uv] override-dependencies = ["highspy==1.14.0"]` (la versión más
  alta que importa limpio; HiGHS es LP/MIP y no participa en la relajación SDP de GW → el
  pin es cosmético para el resultado). Evidencia: el log del experimento ya no imprime la
  ImportError/undefined-symbol; `HIGHS` vuelve a `installed_solvers()`; la fila baseline
  `gw` sigue presente.
- **F4 · CERRADO** (verificación viva; sin cambios de código, doc en este commit).
  `bash scripts/smoke_infra.sh` → **SMOKE: PASS**: postgres healthy + api `/health ==
{"status":"ok"}` + un evento real `run.created` escrito por `create_event_store()` →
  postgres(compose) → leído por el api como frame SSE. `tests/integration` contra el
  Postgres vivo (`CHIMERA_TEST_DATABASE_URL`): **25 passed / 0 skipped** (los 8 tests de
  Postgres antes saltados, ahora verdes; verificado además de forma independiente por el
  validador reusando la imagen construida). Stack bajado (`docker compose down`, sin `-v`).
  El compose booteó tal cual: la imagen `api` NO incluye matplotlib (`--package chimera-api`
  deja fuera el grupo `experiment`) y respeta el override de highspy.

F5 (instancia ICE diferida) y F6 (p=3 < p=2, mínimo local) siguen siendo NOTAS informativas
de Planeado — no eran acciones de cierre y quedan tal cual.

### Adenda — Dominio 05 (Entregable) cerrado en re-auditoría de completitud

La auditoría Fable original (F1–F6) **no evaluó el Dominio 05**. Una re-auditoría de
completitud del scope MVP (2026-07-24, pedida antes del freeze) lo detectó como gap real
Nivel-1 y lo cerró: `05-entregable.md` §"Nivel MVP" define tres ítems (entry point único,
README del reto, esqueleto de informe) — los tres implementados en `challenges/reto1/`:

- `challenges/reto1/run_all.py` (decisión #56) — entry point único reproducible: reproduce
  figuras/cifras del reto en `ieee6-flujo` (reusa `scripts/exp_r_vs_p.py`) Y dispara una
  corrida Chimera REAL in-process que emite un certificado 7/7 (AL3, dos patas) sobre
  `sintetica-4bus`. Salida en `results/reto1/`. `verify-bundle.py` → 7/7.
- `challenges/reto1/README.md` — reproducción en un comando + verificación offline del
  certificado (CLI del juez) + mapa del código.
- `challenges/reto1/informe.md` — esqueleto del informe de 8 páginas con cifras reales
  pre-llenadas y §Limitaciones honestas ya completa (6 limitaciones reales citadas). La
  prosa completa / PDF / slides siguen siendo Planeado.

Con esto el **MVP Nivel-1 queda completo en scope** (dominios 01–05); los diferidos (ICE
real, informe completo, ModelServer replay, 3 escalas, superficie agéntica) están en
Planeado con decisión registrada. Ver decisión #57.
