# Chimera — Arquitectura Reconciliada

## El documento autoritativo para construir (POC de Steven + adiciones)

> **Estado: PARCIALMENTE SUPERSEDIDO.** Vale: el modelo agente/runtime (§2), la pieza de formulación QUBO de _islanding_ (§4), el mapa de protocolos (§5), la ablación cuántico ON/OFF (§6), y la frontera Plan A/B/C con sus puntos de pivote (§7). No vale: core en TypeScript/NestJS (§1 fila 1, "Por qué TS core"), monorepo TS (§3), carriles en TS (§9) — la decisión vigente es core Python, ver [`arquitectura-python.md`](arquitectura-python.md). Ver [`README.md`](README.md) para el índice completo.
> **Corrección S-E (2026-07-18, contra el enunciado oficial):** §4 formula ahora el **Max-Cut oficial** (la penalización/factibilidad se re-scopea a limitaciones + extensión "constraint mixers"), y la columna Plan B de §7 es el **Challenge 3 oficial (TFIM/Trotter)**, no VQE/química; su regla de activación es "segundo reto condicional", no "pivote ante fallo".
>
> **Qué es esto.** El merge de las dos arquitecturas: la **POC de Steven** (la mejor base _para construir_ — concreta, con DDL, contratos TS, endpoints, monorepo) + las **4 piezas y 2 arreglos** del documento de arquitectura/estrategia, + el **modelo agente/runtime** que resuelve la discusión del equipo. Este es el documento contra el cual se construye.
>
> **La POC de Steven es la base. Este documento la confirma y le agrega lo que falta.** No reproduce su DDL, sus endpoints ni sus manifiestos completos (ya están bien en la POC) — los confirma y se concentra en lo net-new.
>
> **Notación:** ✓ = confirma la POC tal cual · ➕ = adición (no estaba) · ✏️ = corrección a la POC.

---

## 1 · Decisiones congeladas (resultado de la reconciliación)

| #   | Decisión                                                                                                       | Origen                                                       |
| --- | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| 1   | **Core en TypeScript (NestJS); ciencia en Python detrás de HTTP.**                                             | ✓ POC de Steven (yo reversé mi recomendación de Python core) |
| 2   | **Monolito modular** para el core; servicios Python separados.                                                 | ✓ POC                                                        |
| 3   | **El Engine llama a MODELOS, no a arneses.** Los agentes son manifiestos delgados sobre el runtime del Engine. | ➕ (resuelve las dos preguntas — §2)                         |
| 4   | **La compuerta de verificación + la procedencia + el control exigen que el Engine sea dueño del loop.**        | ➕ (§2)                                                      |
| 5   | **Profundidad sobre amplitud:** un Servicio QUBO verificado, no cinco herramientas superficiales.              | ✓ POC + estrategia                                           |
| 6   | **El motor no sabe qué es un QUBO/VQE/molécula.** La ciencia vive en herramientas, no en el kernel.            | ✓ POC                                                        |
| 7   | **Router de modelos desde el día 1**; modelo intercambiable.                                                   | ✓ ambos                                                      |
| 8   | **PostgreSQL + pgvector + Redis/BullMQ**, event sourcing en `run_events`.                                      | ✓ POC                                                        |

**Por qué TS core (cierre del tema, decisión histórica — ver el estado de supersesión arriba):** lo que el core hace de verdad (API, orquestación, eventos, streaming a la UI, llamadas HTTP) es el wheelhouse de Node/TS; los tipos compartidos end-to-end backend↔frontend son enormes cuando "la transparencia ES el demo"; y TS/NestJS es lo más cercano a C#/ASP.NET que existe, así que el equipo rinde de inmediato. La ciencia se queda en Python detrás de contratos HTTP — el borde correcto. (El cuello de botella, la formulación QUBO, es Python en cualquier caso; la elección de lenguaje del core no lo afecta.)

---

## 2 · El modelo agente / runtime (la resolución de las dos preguntas) ➕✏️

Esta sección formaliza la discusión del equipo ("un agente es solo una definición de pasos") y la regla de integración ("por qué no Claude Code adentro").

## 2.1 Qué es un agente (y qué no)

**Un agente = un loop de control delgado (que el Engine define) + delegación en runtime de la decisión "¿qué sigue?" a un modelo (que el Engine no define).**

- El loop es "una definición de pasos" — cierto, pero es el esqueleto (~10%).
- La inteligencia es el modelo decidiendo la acción en runtime, sobre un espacio no enumerable (~90%).
- **No es un pipeline:** en un pipeline el autor escribe las ramas (la inteligencia es el autor); en el agente el modelo elige en runtime (la inteligencia es el modelo). Test: _¿podés dibujar el diagrama de flujo de antemano?_ Si sí → pipeline; si no → agente.

```
Pipeline:  paso1(); paso2(); if cond: paso3() else: paso4()   // autor = inteligencia
Agente:    while not done: a = model.decide(ctx); ctx += exec(a)  // modelo = inteligencia
```

## 2.2 Cómo se relacionan los agentes externos con el Engine (tres formas)

**Aclaración de precisión:** el Engine NO es incompatible con otros agentes — integrarse con y alojar agentes externos **ES la visión**. La afirmación estrecha y verdadera es: _un arnés externo no puede ser el orquestador central de un run con verificación fina (paso por paso)_, porque ahí la compuerta y la procedencia necesitan que el Engine sea dueño del loop. Hay tres formas de relación, y el usuario elige según cuánta verificación quiere vs cuánto quiere reusar:

| Forma                                               | Dueño del loop                     | Qué gobierna el Engine                                                                                                                                         | Para qué                                                                     |
| --------------------------------------------------- | ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| **1. Agente nativo delgado**                        | El Engine                          | Todo (loop, herramientas, compuerta inline, procedencia, control)                                                                                              | Workloads de máxima confianza (CHIMERA cuántico)                             |
| **2. Agente externo alojado**                       | El arnés externo (su loop interno) | El **perímetro**: identidad + gateway de herramientas + verificación de salidas antes de comprometer + procedencia. Corre en sandbox con egress por el gateway | Traer un Claude Code / agente de LangGraph / automatización sin reescribirla |
| **3. Agente/automatización como herramienta o par** | El sistema externo                 | La salida (se verifica) + la llamada (se registra)                                                                                                             | n8n, Zapier, Make, un servicio existente (vía MCP/A2A/HTTP)                  |

**Taxonomía útil:** _arneses_ (Claude Code, Codex, OpenHands — traen su propio loop/herramientas/contexto/proceso) vs _modelos_ (Claude, GPT, Llama, Hermes — función pura texto→decisión). En la **Forma 1**, el cerebro del agente nativo es un **modelo** vía el router (no un arnés) — así se obtiene la inteligencia del mejor modelo sin un runtime competidor, y como el modelo puede ser Claude, no es "más débil por construcción": mismo cerebro que Claude Code, más el sustrato. Un **arnés** entra por la Forma 2 (alojado, gobernado en el perímetro) o la Forma 3 (como herramienta), nunca como el orquestador de la Forma 1.

**Por qué la Forma 1 exige que el Engine sea dueño del loop:** la compuerta de verificación inline y la procedencia paso-a-paso viven en el borde de cada tool-call del Engine. Si un arnés externo fuera el orquestador, sus tool-calls internos no pasarían por la compuerta (se pierde el diferenciador) y no emitiría los `run_events` (se pierde el demo). Por eso, para la verificación más profunda, el loop es del Engine.

**Para la hackathon:** solo se usa la **Forma 1** (los agentes cuánticos de CHIMERA, nativos sobre el runtime). Las Formas 2 y 3 (alojamiento/perímetro) son **roadmap (Zona C)** — pero el Tool Registry/gateway se diseña anticipándolas: _el mismo gateway que enruta herramientas hoy será el perímetro de los agentes alojados mañana._

## 2.3 ✏️ Corrección al flujo: es agéntico, no lineal

La POC dibuja el flujo lineal (planner → quantum → tool → verify → report). Eso es el _happy path_. El flujo real es un **loop con retroalimentación**: el verificador puede **devolver trabajo al formulador** cuando el resultado es infactible o el gap es alto.

```
Planner → Formulador → [QUBO tool + Baseline tool] → Verificador
                ↑                                          │
                └──────────── reformular ──────────────────┘   (si infactible / gap alto)
                                   ↓ (cuando pasa)
                                Reporter → resultado verificado
```

El Orchestration Service debe permitir este ciclo (con límite de iteraciones — una Ley). El número de ciclos y qué cambia en cada uno lo decide el verificador en runtime — eso es lo que lo hace agéntico y no un pipeline.

## 2.4 Cuántos agentes (cierre)

Default del demo: **un orquestador delgado + Formulador + Verificador** (3, como dice la POC), con resolución/verificación como **herramientas deterministas** (no agentes — no querés que el modelo _aproxime_ lo que Gurobi computa exacto). Multi-agente adicional **solo** si compra juicio paralelo real (N formulaciones exploradas a la vez → la feature de branching) o verificación adversarial. No por decorar.

---

## 3 · Confirmación de la base (POC de Steven) ✓

Se construye tal cual la POC. Resumen de lo que se confirma (ver la POC para DDL/endpoints/manifiestos completos):

- **Módulos del Engine:** Projects, Agents, Runtime, Orchestration, Tool Registry, Tool Execution, Verification, Event Log/Provenance, Context/RAG, Model Router, Sandbox (diseñado, no implementado en el demo).
- **Contratos:** `Project`, `AgentManifest`, `ToolManifest`, `Run`/`RunStatus`, `ToolCall`, `VerificationResult`, `RunEvent`, `Document`/`DocumentChunk`, `DistributionManifest`. ✓
- **DDL:** las 10 tablas (`projects`, `agents`, `tools`, `runs`, `run_events`, `tool_calls`, `verification_results`, `documents`, `document_chunks`, `model_providers`). ✓
- **API:** los endpoints de Projects/Agents/Tools/Runs/Verification/Documents/CHIMERA. ✓ con la regla de la POC: _los endpoints CHIMERA crean runs normales del Engine, no se saltan el runtime_. ✓ (crítico — es lo que mantiene la compuerta y los eventos en el camino).
- **Monorepo:** `apps/` (engine-api, studio-web) + `packages/` (core, runtime, tools, verification, context, observability, model-router) + `services/chimera-tools/` (Python) + `distributions/chimera/` + `infra/`. ✓
- **Stack:** NestJS, React+Vite, PostgreSQL+pgvector, Redis+BullMQ, OTEL básico + Run Events propios. ✓
- **Agentes mínimos:** planner / quantum / verification (3). ✓ (con el matiz de §2.3–2.4)
- **Herramientas imprescindibles:** `qubo_solver`, `classical_baseline_solver`, `constraint_checker`, `document_retriever`. ✓
- **Verificación foco:** `constraint_verification` + `baseline_comparison`. ✓ (con el reframe de §6)

**Único cambio a la base:** el Runtime/Orchestration implementa el loop con retroalimentación de §2.3, no el flujo lineal.

---

## 4 · Pieza 1 ➕ — La formulación QUBO de _islanding_ (el contenido del qubo-service)

**La POC tiene el _shell_ del qubo-service (request/response) pero no la receta.** Sin esto el servicio está vacío — y es el cuello de botella, lo más urgente (arranca semana 1, dueño Sebas). Fuente: REGRID-QAOA (arXiv 2606.15083) y González Calaza/Hartmann et al. (arXiv 2408.04097).

**Variables.** `x_i ∈ {0,1}` por bus/nodo (a qué isla pertenece).

**Términos del QUBO** (`Q = Σ λ_i Q_i`):

- **Corte (objetivo — corregido S-E 2026-07-18 al enunciado oficial):** el Challenge 1 formula OFICIALMENTE **Max-Cut**: `max Σ_(i,j)∈E w_ij·(x_i + x_j − 2·x_i·x_j)`, con `w_ij = |P_ij|` (peso de la línea; convenciones congeladas del corpus en `knowledge/islanding/01`). La formulación min-corte de REGRID (minimizar la potencia interrumpida sujeta a islas conexas) queda como **capa de realismo para la conversación ICE**, no como el core del reto.
- **Balance de tamaño:** `γ·(Σ_i x_i − |V|/2)²`. Iniciar `γ ≈ óptimo estimado`; `chain_strength = γ·len(nodes)`; `num_reads = 1000`.
- **Balance generación-carga por isla:** `(Σ_gen − Σ_carga)²` por isla.
- **Coherencia de generadores:** _must-link_/_cannot-link_ (generadores que oscilan juntos en la misma isla).
- **Conectividad:** NO cabe limpio en el QUBO → se verifica/repara clásicamente con DFS (componentes conexas).

> **Re-scope S-E (2026-07-18, Δ1 del stress test):** bajo el Max-Cut oficial (sin restricciones), los términos de penalización de arriba y los chequeos físicos (`island_connectivity`, `power_balance`) se re-scopean como **análisis de limitaciones + extensión oficial "constraint mixers"** — exactamente la sección de limitaciones obligatoria del enunciado ("el óptimo Max-Cut de ieee9 corta todas las líneas — físicamente degenerado; lo cuantificamos con pandapower y mostramos constraint mixers como ruta"). La reparación M.3 y el corredor de factibilidad viven en esa extensión, no en el camino core del claim de optimalidad.

**Trucos accionables (lo que separa del baseline ingenuo):**

- **Reducción por coherencia** antes de construir el QUBO (agrupar buses coherentes → baja qubits sin alterar el óptimo). Primer bloque del pipeline.
- **Truco de pesos:** para IEEE-30, fijar `λ_cut = 2` (con `λ_comp = λ_net = 1`) mejoró el time-to-solution **~110×** sin cambiar la partición óptima. Reescalar penalizaciones no cambia el óptimo pero transforma la dinámica del solver.
- **Warm-start** (Goemans-Williamson / clustering espectral) + **CVaR-QAOA** (`alpha` en `SamplingVQE`: α→0 enfatiza los mejores shots) + **XY-mixer** (preserva el subespacio factible para K>2 islas).
- **Post-procesamiento M.3 (el núcleo del diferenciador):** reparación en 2 etapas + filtro de descenso monótono + verificación DFS. Recupera el cut óptimo de Gurobi en los 6 benchmarks IEEE. **Demo en vivo: "QAOA vanilla ~0% factible → post-proceso 100% factible".**

**Benchmarks/herramientas:** IEEE 9 (smoke test, ~6–9 qubits tras reducción), IEEE 14 (caso estrella), IEEE 30 (escala + truco λ_cut) + modelo estilizado de la red CR (ICE). **pandapower** (topología + power flow → `w_ij`), **NetworkX** (grafo + DFS), **Gurobi/CP-SAT** (ground-truth).

> Esto encaja en el `QuboSolveRequest`/`QuboSolveResponse` de la POC: el `quboMatrix` lo produce el Formulador con esta receta; el `backend` enruta a clásico/QAOA/annealing; el post-proceso M.3 corre antes de devolver.
>
> **⚠️ A investigar (Sebas, camino crítico):** leer el PDF completo de REGRID-QAOA (ecuaciones de penalización exactas y tablas); bajar a código y validar en IEEE 9/14/30 con pandapower **esta semana**; confirmar SDK según el hardware del evento.

---

## 5 · Pieza 2 ➕ — El mapa de protocolos (sobre el stack de Steven)

La POC reconoce MCP como transporte de herramienta y "OTEL básico", pero no mapea el resto. **El Engine adopta estándares en sus bordes; no los inventa.** Mapeado al stack de la POC:

| Borde                          | Estándar                                       | Estado en el demo                                                                             |
| ------------------------------ | ---------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Agente → Herramienta           | **MCP**                                        | ✓ Ya en la POC (`ToolManifest.execution.type: "mcp"`); los servicios cuánticos se exponen así |
| Agente → Agente                | **A2A**                                        | ◑ Condicional: contrato definido; solo si hay multi-agente con coordinación real (§2.4)       |
| Agente → Usuario               | **AG-UI** (CopilotKit)                         | ✅/◑ El Studio Web ES este borde; AG-UI o un WS/SSE lite (la POC ya planea "run en vivo")     |
| Cada acción → Observabilidad   | **OpenTelemetry GenAI**                        | ✓ La POC ya usa Run Events + OTEL básico; adoptar las semantic conventions de naming          |
| Workload → Identidad           | **SPIFFE/SPIRE**                               | ◑ Lite: JWT; contrato objetivo SPIFFE (§8)                                                    |
| Usuario → Permiso (delegación) | **OAuth Token Exchange (RFC 8693)** + Keycloak | ◑ Lite: JWT; contrato objetivo RFC 8693 (§8)                                                  |
| Catálogo → Seguridad           | **SAFE-MCP**                                   | ○ Diferido (el demo usa herramientas propias/confiables)                                      |
| Seguridad (diseño)             | **OWASP Agentic Top 10 2026**                  | ✓ Diseñar contra la lista                                                                     |
| A vigilar                      | **AIMS, MCP-I, Provenance Protocol**           | ○ Roadmap                                                                                     |

> Leyenda: ✅ completo · ◑ mínimo/condicional (contrato definido) · ○ diferido. Mapearlos cuesta cero; implementarlos completos está fuera de las 4 semanas — esto completa el diseño, no infla el alcance.

---

## 6 · Pieza 3 ➕✏️ — La ablación cuántica ON/OFF como el WOW

La POC tiene `baseline_comparison` **como verificación** — y _es_ técnicamente la ablación. El reframe: subirla a **golpe de efecto narrativo**, no enterrarla como un check. Es la prueba viva de "CHIMERA da una ventaja que la IA cruda no da".

**Definir un corredor de ablación explícito:** el mismo pipeline con **cuántico ON** (QAOA/annealing + post-proceso M.3) vs **cuántico OFF** (clustering espectral clásico / CP-SAT). La UI muestra el lado-a-lado:

> _"IA normal / QAOA vanilla → esta respuesta confiada, no verificada, infactible. CHIMERA → esta verificada, factible, gap X% vs óptimo, con ablación y procedencia."_

Esto se construye con las piezas que la POC ya tiene (`classical_baseline_solver` + `constraint_checker` + `VerificationResult`); solo se agrega el _encuadre_ y un panel de comparación. **La suite de test cases (entregable b) genera este material automáticamente** — cada caso es una demostración cuántico-vs-clásico.

---

## 7 · Pieza 4 ➕ — La frontera Plan A/B/C y los puntos de pivote

La POC es Plan A, pero su **`DistributionManifest` es exactamente el mecanismo del pivote** (agents + tools + verifiers + prompts + datasets empaquetados). El Engine no cambia; cambia la distribución.

**Core invariante (compartido por A/B/C):** el loop de investigación verificada (formular → enrutar a herramienta → ejecutar → verificar contra ancla → reportar con procedencia) + el harness de verificación + MCP + el Studio + la procedencia. Todo lo de §2–6.

**El delta por plan (solo Zona B):**

| Componente               | Plan A (Challenge 1)                      | Plan B (Challenge 3 — TFIM, corregido S-E)                                        | Plan C (Challenge 2)         |
| ------------------------ | ----------------------------------------- | --------------------------------------------------------------------------------- | ---------------------------- |
| Herramienta MCP          | `qubo_solver` (ya en el demo)             | `dynamics_simulator` (Trotter — reusa el builder de capas ZZ+X del QAOA)          | `qml_kernel`                 |
| Plantilla de formulación | _islanding_ → QUBO                        | TFIM 1D: H = −J Σ ZᵢZᵢ₊₁ − h Σ Xᵢ → circuito de Trotter (ángulos J·dt, h·dt)      | imputación+PCA → feature map |
| Ancla clásica            | Gurobi/CP-SAT                             | diagonalización exacta — ED (SciPy/PySCF), criterio oficial ≤5% en N=8            | RandomForest/XGBoost         |
| Dataset ground-truth     | IEEE 9/14/30 (+ cr8/cr6 del ICE, P0-7)    | cadenas N ∈ {6, 8, 12}; barrido h/J ∈ {0.5, 1.0, 2.0}; ⟨Z⟩ y ⟨ZᵢZⱼ⟩ vs tiempo     | Kaggle Water Potability      |
| Verifier                 | `qubo-constraint` + `baseline-comparison` | `observables-vs-ED` (attestation `differential` con tolerancia — textual del PDF) | `f1-vs-classical`            |
| Narrativa ODS            | 7/9/13                                    | 7/9/12/13 (transmisión/almacenamiento sin pérdidas)                               | 6                            |

**Punto de inserción del pivote (qué se toca):** (1) registrar la nueva herramienta MCP, (2) cambiar la plantilla de formulación, (3) apuntar el ancla/verifier, (4) cargar el dataset, (5) reconfigurar Formulador/Verificador por prompt — **todo dentro del `DistributionManifest`.** El Engine (runtime, registro, eventos, verificación, Studio) **no se toca.** Eso hace el pivote "limpio".

> **Corrección S-E (2026-07-18, Δ9 del stress test):** esta tabla recetaba el Reto 3 como VQE/química — el **Challenge 3 oficial es TFIM/Trotter** (columna corregida arriba; ficha completa en el post-scriptum del reporte S-D y `knowledge/quantum/02` ya corregida). Y la regla de activación cambió: ya no es "pivote ante fallo" sino **segundo reto condicional** — C1 es EL reto; el kit C3 se activa SOLO con la entrega de C1 COMPLETA contra el checklist oficial (gate duro; LEAN = recorte de ceremonia de entrega, JAMÁS de rigor de ejecución). Plan C (C2/QSVM) queda **descartado como segundo reto** (sin ancla exacta — es el modo amortizado: historia de inversión, no de jueces), con línea de respaldo si preguntan. El mecanismo del `DistributionManifest` de abajo sigue vigente tal cual — es lo que hace barato el kit C3.

---

## 8 · Arreglo ✏️ — El contrato de identidad (anotación)

Los flags de permiso del `AgentManifest` (`canCallTools`, `canUseNetwork`, etc.) están bien para 1 tenant. **Anotar el contrato de identidad** para no reescribir en producción: cada agente recibe un JWT con claims _scoped_; un sub-agente solo puede **reducir** permisos, nunca expandirlos ("permission intersection"). Esa es la forma de SPIFFE + RFC 8693 (patrón Kagenti). El JWT lite del demo respeta la forma; producción enchufa SPIRE/Keycloak sin cambiar el modelo.

> **⚠️ A investigar (Dylan):** validar que el JWT del demo lleve claims scoped + intersección de permisos. Limitación conocida de SPIRE (pre-registro de workloads, malo para sub-agentes efímeros) → roadmap.

---

## 9 · Qué construir primero (orden de-riskeado, reconciliado)

Merge del roadmap de 4 semanas de la POC con el orden de-riskeado. **Dos carriles en paralelo:** el Engine (TS) y la formulación cuántica (Python). El cuántico arranca el día 1 porque es el cuello de botella.

**Carril Engine (Geo + Steven, TS):**

1. Monorepo + Docker Compose + Postgres + Redis + Engine API + Studio base. Projects/Runs CRUD + Run Events visibles. _(Sem 1)_
2. Tool Registry + Tool Execution + Model Router + un agente simple llamando una herramienta HTTP, todo registrado. _(Sem 2)_
3. El loop con retroalimentación (§2.3) + la compuerta de verificación inline. _(Sem 2–3)_
4. Studio: timeline en vivo + panel de verificación + panel de ablación. _(Sem 3–4)_

**Carril Cuántico (Sebas, Python — desde el día 1):**

1. Formulación QUBO de _islanding_ + validación en IEEE 9/14/30 contra Gurobi. _(Sem 1–2, lo más urgente)_
2. `qubo_solver` + `classical_baseline_solver` + `constraint_checker` como servicios FastAPI. _(Sem 2)_
3. Post-proceso M.3 + corredor de ablación. _(Sem 3)_
4. (Si sobra) kit C3: capability `dynamics_simulator` (TFIM/Trotter sobre el builder QAOA) + adapter ED. _(Sem 4, bonus — gate duro Δ9: solo con C1 entregado completo)_

**Integración (Dylan, conector):** contrato agente, exposición MCP de las herramientas, transmisión de eventos al Studio, el `DistributionManifest` de CHIMERA. _(continuo)_

**Semana 4 (todos):** pulido, manejo de errores, Docker Compose reproducible, demo script, datos de ejemplo, narrativa.

**Errores a evitar (de ambos docs):** intentar el Engine completo; quantum-washing (vender "llamar Qiskit"); UI bonita sin sustancia (flujo real primero); herramienta cuántica inestable (tener simulador/clásico reproducible; hardware real solo bonus); demasiados agentes; tratar la verificación como gate de una vez en vez de inline.

---

## 10 · Preguntas abiertas por dueño (consolidado)

**Sebas (cuántica/datos/evento) — crítico:** receta QUBO exacta de REGRID-QAOA → código + validación IEEE esta semana; SDK según hardware; instancia/dataset/métrica del evento al revelarse; conseguir problemas de Quantathons pasadas (alimenta el entregable b).

**Steven + Geo (Engine/infra, TS):** el loop con retroalimentación en Orchestration; transmisión de eventos al Studio (WS/SSE/AG-UI); Docker Compose + acceso a QPU + credenciales.

**Dylan (conector/identidad/frontend/PM):** contrato del agente final; JWT con claims scoped (forma SPIFFE/RFC 8693); `DistributionManifest` de CHIMERA con los puntos de pivote A→B/C; set mínimo de vistas del Studio.

---

> **Nota original:** entregable (a) — arquitectura reconciliada tal como se propuso originalmente. Sigue (b) la suite de test cases (corpus, oráculos, casos, criterios de aceptación, loop de afinamiento — el material que valida CHIMERA _y_ es la evidencia del demo) y (c) el plan de hackathon.
