# Plan maestro — cierre total (MVP → Planeado → Mejorado)

> **Estado: MVP Nivel-1 CERRADO (2026-07-24)** — los 5 dominios mergeados a `mvp/base` @310af53; cierre y condiciones en `auditoria-mvp.md` §Cierre de hallazgos. La sección «Estado real» de abajo es un snapshot pre-cierre (histórico); el roadmap Planeado/Mejorado sigue vigente.

**Fecha:** 2026-07-23 · **Autoridad:** Dylan (mandato de cierre no-bloqueante) · **Planner:** Fable
**Rama base:** `mvp/base` (consolidación de TODAS las ramas de trabajo, 2026-07-23) (@ `e0515a8`, 345 passed, 4 gates verdes)

## Los tres niveles

| Nivel            | Definición de done                                                                                                                                                                                                                                               | Prueba                                                    |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| **1 · MVP/Demo** | Chimera resuelve el reto 1 de punta a punta EN VIVO: grafo (corpus o ICE chico) → proposers (QAOA + baselines GW/greedy) → verificación 2 patas (CP-SAT + pandapower) → certificado 7/7 → Studio muestra el run por SSE → `verify-bundle` en la máquina del juez | Corrida en vivo de la escala "provincia" (6–8 nodos)      |
| **2 · Planeado** | Todo lo del freeze §15.4 que quedó diferido: cruce del gateway por step (+flip AX1), ModelServer replay, Z3 RuleVerifier, campos §1 del manifest, ICE 3 escalas, informe 8 páginas, H2 pre-corridas con digests                                                  | 3 escalas (provincia/región/país) con parámetros variados |
| **3 · Mejorado** | Ventajas mapeadas: retos 2/3 con Chimera, extensiones del reto (ZNE, warm-start QAOA), attestation por isla + badges, análisis de escalado completo                                                                                                              | Retos 2/3 + rúbrica completa en "Excelente"               |

La **sanitización** (limpieza/estandarización del repo) cierra SIEMPRE, aun si 2 y 3 no se alcanzan.

## Modelo operativo (no-bloqueante, redundante)

- **Fable** (sesión de Dylan): genera los planes (este set) y al final del MVP audita/testea E2E.
- **Cada sesión de dominio**: se abre con el prompt generador de abajo, **modelo principal Opus**
  (valida contra el plan, revisa resultados, decide), que **delega la implementación a
  subagentes Sonnet**. TDD siempre; los 4 gates (`pytest`/`lint-imports`/`ruff`/`pyright`)
  verdes antes de cada commit.
- **Nadie espera una opinión.** Toda decisión se toma EN el momento según feature, contexto,
  diseño y arquitectura, y se registra en `docs/mvp/decisiones.md` con nivel y dominio — el
  dueño la ratifica o edita DESPUÉS, nunca antes. Solo se espera a FEATURES (si el dominio A
  necesita algo de B que no existe, avanza en otra tarea del plan o lo stubea contra el
  contrato).
- **Redundancia:** estos planes viven en el repo. Si una sesión muere (tokens/contexto),
  la siguiente arranca con `git pull` + el plan del dominio + `decisiones.md`. Cada sesión
  DEBE commitear en verde al cerrar cada tarea (jamás trabajo suelto >1 tarea sin commit).
- **Ramas:** una por dominio (`mvp/<dominio>`), worktree propio si corre en paralelo.
  Merges hacia `integracion/runtime-confianza`. Áreas disjuntas por diseño (tabla de
  dueños en `docs/specs/README.md`).

## El reto 1 como contrato del MVP (doc oficial leído 2026-07-23)

- Grafo ponderado 6–12 nodos, ideal con datos reales (ICE: `datos-ice-se.opendata.arcgis.com` — premia ODS).
- QUBO documentado + verificado en instancia chica; QAOA con r = E_QAOA/E_óptimo por p
  (media+std de ≥5 corridas), gráfico r vs p; **suficiente: r ≥ 0.6 con p=1 en 6 nodos**.
- Baselines OBLIGATORIOS: Goemans-Williamson (CVXPY, ≥0.878) + greedy (~0.5) (+ SA/bruta).
- Emulador H2 (Quantinuum) hasta 26 qubits — escala "país" va clásica + extrapolación honesta.
- Entrega: repo público + requirements + **UN entry point que reproduce cada figura/cifra** +
  README + informe PDF ≤8 pág (limitaciones honestas OBLIGATORIAS) + slides 5 min + statement
  SDK ≤200 palabras. Reproducibilidad incumplida = deducción en TODA la rúbrica.
- Rúbrica general: implementación cuántica 30%, comparación/escalado 20%, explicación 20%,
  baseline 15%, reproducibilidad 10%, ODS 5%. Red flags: cherry-picking, sin limitaciones,
  "ventaja cuántica" sin escalado.
- **Ventaja Chimera:** cada figura/cifra del entregable respaldada por un certificado
  verificable offline — el plano de confianza automatiza lo que la rúbrica premia.

## Estado real (2026-07-23, post-cierre carril 1)

**HECHO:** engine golden path completo (ExactSolverVerifier CP-SAT, ExecutionVerifier
pandapower genérico, costura loop↔confianza, assemble_bundle event-sourced, bundle_check
7/7, certificado de refutación); capabilities sim/solvers/quantum REALES (falla sembrada
verde); API SSE + Postgres store; Studio UI (sobre fixtures); corpus ieee9/14/30; suite
345 passed / 4 gates verdes; decisiones delegadas en `docs/decisiones-delegadas-2026-07-23.md`.

**FALTANTE PARA MVP (por dominio — ver plan de cada uno):**

1. Endpoint de arranque de runs + cableado gateway→loop→SSE (`01-runtime-api.md`)
2. Baselines GW/greedy + experimento r vs p + datos ICE/eléctricos (`02-ciencia-reto.md`)
3. Studio en vivo: disparar run + timeline SSE + certificado real (`03-frontend-studio.md`)
4. Compose walking skeleton (`04-infra.md`)
5. Entregable del reto: entry point reproducible + informe + slides (`05-entregable.md`)

## Prompts generadores (uno por sesión de dominio)

Cada prompt se pega en una sesión nueva. TODOS empiezan igual:

> Corre esta sesión con **Opus como validador** y delega la implementación a subagentes
> **Sonnet**. Lee `docs/mvp/00-plan-maestro.md` y tu plan de dominio; trabaja en la rama
> `mvp/<dominio>` (worktree propio) desde `mvp/base`. TDD; 4 gates
> verdes antes de cada commit; commit por tarea terminada. Toda decisión que normalmente
> esperaría a otra persona: tómala YA según el plan/arquitectura y regístrala en
> `docs/mvp/decisiones.md` (nivel, dominio, decisión, racional, cómo revertirla). Si un
> hook GateGuard bloquea tu primer edit a un archivo, declara lo que pide y reintenta
> idéntico. Nada de push — los merges los coordina Dylan.

- **Runtime/API:** `…prefijo…` + "Ejecuta `docs/mvp/01-runtime-api.md`."
- **Ciencia/Reto:** `…prefijo…` + "Ejecuta `docs/mvp/02-ciencia-reto.md`."
- **Frontend:** `…prefijo…` + "Ejecuta `docs/mvp/03-frontend-studio.md`."
- **Infra:** `…prefijo…` + "Ejecuta `docs/mvp/04-infra.md`."
- **Entregable:** `…prefijo…` + "Ejecuta `docs/mvp/05-entregable.md`." (arranca cuando 1–3 tengan sus tareas MVP verdes)

**Auditoría final (Fable, etapa 3):** con los dominios MVP en verde, sesión Fable corre el
E2E completo (las 3 corridas de prueba), caza bugs, y emite el veredicto de paso a Planeado.
