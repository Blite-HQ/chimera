# Mejorado — plan paralelo (Etapa 4)

> **Estado: VIGENTE (2026-07-30).** Salida de la Etapa 4 del playbook. Ejecuta el
> backlog de `04-consolidacion.md` (dominios G/P/C/V/O, decisiones #101–#106) en
> sesiones paralelas sobre worktrees, con Fase 0 de contratos que BLOQUEA la
> implementación. **Rama base: `mejorado/base`** (creada desde la punta validada de
> `planeado/base`; gates baseline citados en el ledger). La sesión de control
> coordina: merges por checkpoint, decisiones #107+, huecos delegados con brief
> quirúrgico.

## 0 · Las 5 reglas duras (no negociables, heredadas de Planeado)

1. **Cero mocks silenciosos**: toda superficie sin productor real muestra
   honest-empty o «Replay» etiquetado con banner — jamás datos fabricados sin
   etiqueta.
2. **DoD = integración viva contra compose**: un ítem no está «hecho» cuando sus
   tests pasan, sino cuando su efecto se observa en el stack real
   (`docker compose up` + smoke). Cada sesión cierra con su verificación viva.
3. **Tabla de interacciones por sesión**: toda interfaz tocada se registra en
   `docs/mvp/decisiones.md` (interfaz / dominio afectado / estado del contrato).
4. **Checkpoints de costura incrementales**: merge a `mejorado/base` SOLO cuando
   AMBOS lados del contrato están verdes contra el MISMO fixture single-origin
   (origen Python, espejo exacto en el Studio — regla de `docs/specs/README.md`).
5. **Presupuesto de sesión con handoff**: si una sesión no cierra su alcance, deja
   handoff explícito (estado, gates corridos con números, siguiente paso) — jamás
   trabajo a medias sin registro.

**Transversales**: TDD (test primero, siempre); gates verdes antes de CADA commit
(`uv run pytest` + `uv run lint-imports` + `uv run ruff check` + `uv run pyright` +
`pnpm -C apps/studio run test:run` + `lint`); commits convencionales en minúscula
≤100 chars; **nada de push** (lo coordina Dylan); si GateGuard bloquea el primer
edit: declarar importadores/API/gate/instrumentación y reintentar idéntico; la regla
de marca interna está vigilada por hook local — el codename JAMÁS se escribe en
texto del repo; agnosticismo ADR-029 (denylist de escenario) aplica a toda capability
nueva.

**Gotchas de worktrees — los dos corregidos por la sesión O (2026-08-05):**

1. ~~`uv sync` en un worktree NO instala los editables~~ — **caduco**:
   `uv sync --locked --all-packages --all-extras` DENTRO del worktree crea un
   `.venv` completo con los editables apuntando al worktree. Los gates corren con
   `uv run` a secas; la receta vieja (venv del principal + `PYTHONPATH`) además
   ocultaba errores de tipo de módulos nuevos (#149).
2. **`git` no corre NINGÚN hook en un worktree recién creado**: `core.hooksPath`
   apunta a `.husky/_`, que lo genera `prepare` y no está versionado. Sin error y
   sin aviso, los commits dejan de revisarse. **Correr `npx husky` una vez** al
   abrir el worktree. Es la causa de los 21 archivos sin formatear que dejaron la
   CI roja (#156).

**El bloque de gates está incompleto** (#156): `ruff check` NO es
`ruff format --check`, y `depcruise` no aparece. Los dos fallan en CI y ningún
gate local los cubre — corre también `uv run ruff format --check .` y
`pnpm -C apps/studio exec depcruise src` antes de dar por cerrada una sesión.

## 1 · Fase 0 — contratos de costura (BLOQUEA la implementación)

Ninguna sesión de Fase 1 implementa una costura cuya spec + fixture single-origin +
test anti-drift no existan. Sesión única de contratos (worktree `mejorado/contratos`)
produce:

| Spec                                                  | Contenido                                                                                                                                                                                                                                                                                                                                                            | Consume                 |
| ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| S-A `docs/specs/chat-conversacion.md` (NUEVA)         | `mission.message` ↔ `●MissionMessage` (catálogo §14 vía #102), `POST /runs/{id}/messages` (202/409), `POST /runs/{id}/cancel`, `run.created.{thread_id?,project_id?}` aditivos, `TurnContext.pending_messages`, `PROMPT_PROTOCOL` v2 con historial, wire de approvals (fixtures ya existen — falta Zod espejo). Fixtures `contract/endpoints/` + `contract/harness/` | P3, P6                  |
| S-B supersedes del freeze                             | §13 [MEJORADO] + §14 eventos (#102 — ola 0); §3: `discarded_streams` en el wire de `GET /runs` (#104) + payload extendido de `run.metrics.recorded` (C-4, `variant`×4); `GatewayContext` aditivo con ceremonia (C-5); regla `independence_group` compartido en punto 7 (C-6); reconciliación `MODEL_ROUTER_BACKEND`→`CHIMERA_MODEL_BACKEND` (N12)                    | P2, C2, C4, V2          |
| S-C `docs/specs/generalidad-retos.md` (NUEVA)         | claim_types C2/C3 + registro en perfil STEM (anexo aditivo), `FormalExactPredicate` extendido (C-14: `EXACT_DIAGONALIZATION` + tolerancia relativa), formato de corpus C2 (folds sellados, digests) y C3 (series ED de referencia), policies por reto, dispatch instancia→verificadores por clase. Fixtures `contract/generalidad/`                                  | G1–G4                   |
| S-D supersede de `superficie-visual.md`               | §5 supersedido (C-9: rvsp con eje p reemplaza AblationMetric[] como fuente), convención de branch-ids (C-8 híbrida) + regla de verdict per-isla, `GET /runs/{id}/rvsp` como fila nueva de `endpoints-studio.md`, `variant`×4 en ablation. Fixtures `contract/superficie/` (hoy NO existen)                                                                           | V1–V4                   |
| S-E manifest v2 en el SDK                             | los 4 campos §1 congelados aterrizan en `blite_capability.manifest` + plan de migración de las 13 capabilities + gate de genericidad extendido                                                                                                                                                                                                                       | C1 (y desbloquea G, O5) |
| S-F `docs/specs/observabilidad-proyeccion.md` (NUEVA) | mapeo evento→span (OTel GenAI pinneado y estampado), trace/span-id DETERMINISTA (replay ⇒ trazas idénticas), el proyector como consumer standalone (C-11)                                                                                                                                                                                                            | O3                      |

## 2 · Fase 1 — sesiones paralelas por dominio

Cada sesión = worktree propio + prompt generador (§4). Alcances = ítems de
`04-consolidacion.md` §4, en su orden interno.

| Sesión               | Worktree               | Alcance                                                                       | Depende de                   |
| -------------------- | ---------------------- | ----------------------------------------------------------------------------- | ---------------------------- |
| Contratos            | `mejorado/contratos`   | Fase 0 completa (S-A…S-F) + ola 0 restante                                    | —                            |
| G · Generalidad      | `mejorado/generalidad` | G1→G7                                                                         | S-C, S-E                     |
| P · Producto-runtime | `mejorado/producto-rt` | P1→P5 (frontera proposer, skip honesto, chat E-side, sesión real, onboarding) | S-A, S-B                     |
| P · Producto-studio  | `mejorado/producto-ui` | P6→P10 (workspaces, router, branding, distribution root, papers)              | S-A                          |
| C · Confianza-1      | `mejorado/confianza-1` | C1→C2 (manifest v2, gateway por step + AX1 + JWT)                             | S-E, S-B                     |
| C · Confianza-2      | `mejorado/confianza-2` | C3→C11 (RuleVerifier, attestation por isla, M8 piezas 1-5, OverrideEvent)     | S-B; C4 depende de C-8 (S-D) |
| V · Visual/ciencia   | `mejorado/visual`      | V1→V8                                                                         | S-D, S-B                     |
| O · Plataforma       | `mejorado/plataforma`  | O2→O7 (O1 va en ola 0)                                                        | S-F para O3                  |

**Extensiones al alcance (reconciliación #120, tras el saneamiento)**: los 14 ítems
del §7 de `04-consolidacion.md` (#116/#117) y el triage de los hallazgos de handoff
S3 quedan asignados así — G += G8 (+ fix enum `gurobi`, hallazgo 12); P-rt += P11,
P12 (+ ruta fantasma `/invoke`, hallazgo 7); P-ui += P13 (+ hallazgos 4/5/6: fixtures
`capability.job.invoked`, meta de index.html, strings de describe); C-2 += C12–C15;
V += V9; O += O8–O12 (O8/O11 TEMPRANOS — O11 es el que hace irreversibles los demás)

- hallazgos 9/10; Contratos += decisión de inmunización V6 del anexo (hallazgo 1,
  doc CONGELADO ⇒ ceremonia). Detalle por ítem en `04-consolidacion.md` §7.

### Checkpoints de costura (la sesión de control mergea)

| CP  | Qué se verifica VIVO antes del merge                                                                                                                                     | Lados         |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------- |
| CP1 | Chat wire: misión por texto libre → `mission.message` en el stream → hilo D6 muestra mensajes sucesivos; cancel corta con `run.cancelled`; approval card responde        | P-rt ↔ P-ui   |
| CP2 | Reto 3 punta a punta: misión → `trotter_evolve` → `exact_evolve` verifica ≤5% → certificado con attestation `formal_exact` → `verify-bundle` offline                     | G ↔ contratos |
| CP3 | Reto 2 punta a punta: pipeline sellado → kernel → SVM → GROUND_TRUTH + PROPERTY_RULE → certificado                                                                       | G             |
| CP4 | Manifest v2: registry vivo carga 13 capabilities migradas (smoke 2.5) + matriz dispatch fail-closed                                                                      | C-1 ↔ todos   |
| CP5 | Gateway por step: un run vivo cruza las 8 etapas; xfail AX1 VOLTEADO con `IdentityStage` real (jamás borrado); actor del JWT en los eventos                              | C-1           |
| CP6 | Productores visuales: partición pintada sobre el mapa ICE con badges por isla + ablación con datos del stream + curva rvsp — los honest-empty mueren DONDE hay productor | V ↔ P-ui      |
| CP7 | Confianza extendida: `verify-bundle` gana hash-chain + DSSE por attestation + punto 9 (sub-run) SIN perder los 8 puntos existentes sobre bundles viejos                  | C-2           |

### Fase 2 — auditoría E2E viva de Mejorado

Compose reconstruido desde cero + guion NUEVO: «un tercero resuelve el reto 2 y el
reto 3 sin nosotros» (quickstart → misión → certificado → `verify-bundle` offline),
las 3 llaves del cierre de fase verificadas con evidencia (git + gates + stack vivo),
hallazgos → backlog de la fase siguiente. La ejecuta la sesión de control al final.

## 3 · Ola 0 — ABSORBIDA por el saneamiento documental (#107)

> **Precondición nueva (decisión #107, 2026-07-30)**: la Fase 0 de contratos NO
> arranca hasta que el saneamiento documental (`06-saneamiento.md`, etapas S1–S4)
> cierre. Los ítems de esta ola 0 se ejecutan DENTRO de su etapa S3 — se listan aquí
> solo como referencia de origen.

1. #102: supersede [MEJORADO] en `contract-freeze.md` §13 + eventos al §14.
2. O1: gate de docs de CI (excluir el árbol vendorizado quantathon de
   markdownlint/prettier o desvendorizarlo — hoy CUALQUIER PR con `.md` falla) + CI
   en ramas de trabajo + CODEOWNERS alineado a #94.
3. O6/M30: estampar §15.3 (cr6/cr8 `-voltaje@v1` + nota de procedencia) — C-10.
4. C-9: supersede de `superficie-visual.md` §5 (puede ir con S-D).
5. M9: corregir el enunciado (Langfuse = perfil opcional) en el backlog.
6. N12: nota de reconciliación del nombre de la env var en el freeze.

## 4 · Prompts generadores (copy-paste)

Cada prompt asume: repo `~/projects/blite/hackathons/2026/Quantathon/Chimera`, rama
base `mejorado/base`, y que la sesión LEE PRIMERO `docs/mejorado/01-criterio.md` +
`04-consolidacion.md` + este plan. El bloque de reglas es idéntico para todas:

> **REGLAS (bloque común)**: TDD estricto; gates verdes antes de cada commit
> (`uv run pytest && uv run lint-imports && uv run ruff check && uv run pyright` +
> `pnpm -C apps/studio run test:run` + lint cuando toques el Studio); commits
> convencionales en minúscula ≤100 chars; NADA de push; cero mocks sin etiqueta
> (honest-empty o Replay con banner); toda interfaz tocada va a la tabla de
> interacciones de tu sesión en `docs/mvp/decisiones.md`; si no cierras el alcance,
> handoff explícito con gates citados; el codename de marca interna JAMÁS se escribe
> en texto del repo (hay hook que lo bloquea); worktree: los gates se corren con el
> python del venv del repo principal + `PYTHONPATH` del worktree; ADR-029: cero
> vocabulario de escenario en manifests/código (denylist en
> `tests/invariants/scenario_denylist.txt`); verificación antes de afirmar — números
> citados, jamás «debería pasar».

### Asignación de modelos por sesión (#121) — calidad individual y global

Doble garantía decidida por Dylan (2026-07-31): la calidad GLOBAL la garantiza la
sesión de control (Fable: valida cierres, mergea checkpoints, registra); la calidad
INDIVIDUAL la garantiza el modelo de cada sesión según su riesgo:

| Sesión                              | Modelo                                          | Por qué                                                                                                  |
| ----------------------------------- | ----------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| **Contratos** (Fase 0)              | **FABLE**                                       | ceremonias sobre docs CONGELADOS; un error se propaga a todas las demás                                  |
| **C-1** (manifest v2 + gateway/AX1) | **FABLE**                                       | supersede de contrato congelado + flip de invariante + JWT — el chokepoint                               |
| **C-2** (verificadores + M8)        | **FABLE**                                       | el diferenciador criptográfico (hash-chain/DSSE/StatusList); C15 cambia veredictos de bundles estampados |
| G · Generalidad                     | Opus orquesta → Sonnet implementa → Opus valida | alcance quirúrgicamente especificado por S-C                                                             |
| P-runtime                           | Opus → Sonnet → Opus                            | ídem por S-A/S-B                                                                                         |
| P-studio                            | Opus → Sonnet → Opus                            | ídem por S-A + stack fijado                                                                              |
| V · Visual/ciencia                  | Opus → Sonnet → Opus                            | ídem por S-D                                                                                             |
| O · Plataforma                      | Opus → Sonnet → Opus                            | piezas independientes, ideal para delegación                                                             |

Al pegar cada prompt, añade DESPUÉS del prompt su bloque MODO correspondiente
(además del bloque REGLAS):

**MODO para sesiones FABLE:**

> MODO (#121): sesión RIGUROSA — corres en Fable y ejecutas tú misma con TDD;
> puedes delegar exploración/lectura a subagentes, pero todo diseño de contrato,
> ceremonia y código de costura lo escribes y verificas tú.

**MODO para sesiones Opus→Sonnet→Opus (patrón #100 «valida-hace»):**

> MODO (#121): eres el ORQUESTADOR-VALIDADOR (Opus). Por cada ítem del alcance:
> (1) redacta un brief quirúrgico (spec exacta, archivos, tests a escribir primero,
> criterios de aceptación); (2) delégalo a un subagente SONNET que implementa con
> TDD y SIN commitear; (3) valida TÚ la salida — corre los gates completos, revisa
> el diff contra la spec y los criterios, rechaza y re-briefa si no cumple;
> (4) commitea TÚ solo lo validado. Jamás commitees salida de subagente sin
> validarla; jamás implementes tú lo que puede delegarse (tu contexto es para
> validar). Los ítems con ceremonia de contrato NO se delegan: repórtalos al
> handoff para la sesión de control.

### Prompt · Sesión Contratos (Fase 0 + ola 0)

```text
Eres la sesión de CONTRATOS de la fase Mejorado (worktree mejorado/contratos desde
mejorado/base). NO implementas features: escribes specs de costura, fixtures
single-origin y tests anti-drift, y ejecutas la ola 0 documental. Lee PRIMERO
docs/mejorado/{01-criterio,04-consolidacion,05-plan-paralelo}.md y
docs/specs/README.md (reglas de fixtures single-origin).

ALCANCE en orden: (1) ola 0 — YA EJECUTADA por la sesión de saneamiento S3 y
validada en S4 (decisión #119 en el ledger): supersedes del freeze, estampado
§15.3, gate de docs, CI en mejorado/**, CODEOWNERS y N12 están HECHOS — verifica
en el ledger y NO lo repitas; tu alcance real empieza en (2).
(2) S-A chat-conversacion.md. (3) S-B supersedes §3 (discarded_streams #104 +
metrics C-4) + GatewayContext aditivo (C-5) + regla independence_group (C-6).
(4) S-C generalidad-retos.md. (5) S-D supersede superficie-visual §5 + branch-ids
C-8 + rvsp C-9 + fixtures contract/superficie/. (6) S-E manifest v2 en el SDK.
(7) S-F observabilidad-proyeccion.md. Cada spec con su fixture generado DESDE
Pydantic (script gen-contract-fixtures-*) + espejo en apps/studio/src/fixtures/
contract/ + test anti-drift en ambos lados.

EXTENSIÓN (#120): decide además la inmunización V6 del anexo de canonicalización
(hallazgo 1 del handoff S3 — es doc CONGELADO: solo por ceremonia registrada).

[REGLAS: bloque común]. DoD: specs mergeables + fixtures byte-idénticos en ambos
lados + los supersedes registrados con causa + tabla de interacciones. Commits
docs/spec separados de commits de fixtures/tests.
```

### Prompt · Sesión G (Generalidad — retos 2/3)

```text
Eres la sesión GENERALIDAD de Mejorado (worktree mejorado/generalidad). Tu meta es
la llave 1 del cierre de fase: los retos 2 y 3 corren punta a punta EN la
plataforma con diff del runtime = 0. Lee PRIMERO docs/mejorado/{01-criterio,
03-research,04-consolidacion}.md (§4 dominio G), docs/specs/generalidad-retos.md
(S-C, tu contrato), knowledge/quantum/02-recetario-formulacion-por-reto.md §2 (C2;
OJO: la §3 de química está SUPERSEDIDA — el C3 oficial es TFIM/Trotter) y
07-catalogo-algoritmos.md §1.4/§1.6.

ALCANCE en orden (G1→G7 de 04-consolidacion §4): reto 3 primero (trotter_evolve +
exact_evolve sobre el STUB numeric + ExactDiagonalizationVerifier formal_exact con
tolerancia relativa C-14 + corpus C3 + receta TFIM como nota KB nueva), luego reto 2
(tabular_prep con folds sellados por compromiso previo en el plan + fidelity_kernel
statevector con λ_min/método PSD como datos + svm_precomputed sobre el STUB ml +
classifier_baseline SVM-RBF CV-5 + GroundTruthVerifier + PropertyRuleVerifier +
corpus C2 con CSV CC0 sellado y caveats de proveniencia), dispatch por clase
(resolve_verifiers e inputs de misión dejan de ser Reto-1-only), policies por reto,
M11 SA (method sa vía neal: seed pinneada, signo invertido — dimod minimiza,
extensión coordinada C-15), stretch tfim_freefermion (doble ancla BdG), y
challenges/reto{2,3}/ punta a punta. Capabilities SIEMPRE genéricas (la denylist
bloquea potabilidad/water/etc. — el conocimiento de escenario va a knowledge/).
Implementaciones proponente/verificador INDEPENDIENTES (espejo fail-loud: error
0.0000 con dt grande = sospecha).

EXTENSIONES (#120): la receta TFIM ya tiene STUB en knowledge/quantum/11 —
complétala, no la crees. Además: G8 (reparación M.3/M.4 de REGRID-QAOA +
feasibility-feedback DFS + pesos desde flujo — 04-consolidacion §7.1) y el fix del
drift código-manifest de solvers (el enum expone "gurobi" que invoke rechaza —
hallazgo 12 del handoff S3).

[REGLAS: bloque común]. DoD: CP2 y CP3 vivos (misión → capability → verificador →
certificado → verify-bundle offline) contra compose.
```

### Prompt · Sesión P-runtime (Producto — lado engine/api)

```text
Eres la sesión PRODUCTO-RUNTIME de Mejorado (worktree mejorado/producto-rt). Tu meta
es la llave 2: un tercero usa la plataforma sin nosotros. Lee PRIMERO
docs/mejorado/{01-criterio,03-research,04-consolidacion}.md (§4 dominio P),
docs/specs/chat-conversacion.md (S-A, tu contrato) y docs/studio/product-model.md.

ALCANCE en orden (P1→P5): (P1/M32) wrap del proposer en loop.py:610 — try/except
Exception con plan.item_updated{failed} ANTES del terminal (patrón #100.1, cuidado
con el doble-terminal si step_id is None) + guard de nivel task en BackgroundTasks +
test de regresión «proposer que levanta ⇒ run.failed en el stream»; decide el destino
del centinela PROTOCOL_VIOLATION y regístralo. (P2/#104) skip honesto en GET /runs:
la RUTA DE LECTURA descarta streams envenenados + discarded_streams en el wire
(extensión S-B) + test con la píldora #96; el camino de escritura NO se toca.
(P3/M1) chat real lado E: POST /runs/{id}/messages (mission.message, 409
post-terminal), POST /runs/{id}/cancel (run.cancelled ya congelado), emisor de
approval.requested en el loop + POST de respuesta validada contra json_schema,
TurnContext.pending_messages drenado al siguiente turno, PROMPT_PROTOCOL v2 con
historial, thread_id/project_id aditivos en run.created. (P4/M31) model.call.*
emitidos (congelados en §3, hoy nadie los emite) + conductor de
find_replay_divergences + SessionManifest con versión/digest + key vía *_FILE +
fail-fast del modo record efímero de la API. La grabación real de la sesión queda
bloqueado-por-Dylan — deja el runbook listo. (P5/M27) generate-secrets.sh +
quickstart 5-min que termina en verify-bundle + doc de USO + fix compose up (worker) +
.env.example completo + install-dev.sh sin efectos en ~/.claude sin preguntar.

EXTENSIONES (#120): P11 (Procrastinate detrás del puerto JobQueue — dep y servicio
ya pagados; sin cola, interaction:job no tiene dónde correr), P12 (ingesta RAG/KB
con procedencia DSSE — frontera congelada: recuperado⇒assumptions, jamás
Attestation; coordina con O), y la ruta fantasma /invoke (gatewayClient postea,
nginx proxea, nadie la sirve — hallazgo 7: implementarla o matarla, con registro).

[REGLAS: bloque común]. DoD: CP1 (con P-ui) vivo contra compose; un run live con
proposer que falla muere con run.failed (jamás colgado).
```

### Prompt · Sesión P-studio (Producto — lado Studio)

```text
Eres la sesión PRODUCTO-STUDIO de Mejorado (worktree mejorado/producto-ui). Lee
PRIMERO docs/mejorado/{01-criterio,04-consolidacion}.md (§4 dominio P),
docs/specs/chat-conversacion.md (S-A), docs/studio/product-model.md (#78 — la
autoridad de workspaces/routing) y apps/studio/DESIGN.md.

ALCANCE en orden (P6→P10 + lado D de P3): (P3-D) UI de chat: textarea de misión
libre (muere la plantilla hardcodeada de mutations.ts), mensajes sucesivos en el
hilo D6, botón cancelar en RunDetail, card inline bloqueante de approval (Zod espejo
de los fixtures harness que ya existen), lista de runs viva con refetchInterval
mientras haya en_curso. (P6/M15) project como fila relacional fuera del event store
+ selector real en el sidebar + colapsable (aire en potencias de 2) + bloque user;
organización NO (hasta 2º usuario real). (P7/M17) router real con árbol anidable
/w/:ws/p/:proj/runs/:id/:tab desde el día 1 (letra #78) — propone la librería con
análisis corto ANTES de instalar (TanStack Router es el candidato natural del stack,
pero la decisión se registra), Tabs controlado, go-back en
Artifacts/Papers/Knowledge, verifica SPA fallback en docker/studio-nginx.conf.
(P8/M16) branding: pide a Dylan las 21 referencias (bloqueado-por-Dylan si no
llegan), decide red-de-nodos vs 3-barras con él, sistema de marca 16px
claro/oscuro + supersede de DESIGN.md §7/§4 registrado. (P9/M14) distribution root:
distributions/chimera/pyproject.toml con extras curados + Dockerfile --package +
policy_digest byte-idéntico verificado + smoke 2.5 verde + medir la imagen antes y
después. (P10/M24) endpoint de archivos + listado para Papers (reusa capability
ingesta).

EXTENSIONES (#120): P13 (registry de lentes de dominio — la letra YA existe en
product-model.md §38-45 y el código la contradice: RedSlot hardcodeado, props
obligatorias por dominio) + hallazgos 4/5/6 del handoff S3: traducir los fixtures
que emiten capability.job.invoked→submitted junto con la whitelist SSE del cliente
(censo §8.3), la meta description de index.html («escalera de verificación»), y los
strings de describe() con «MVP task N»/«checkpoint 5».

[REGLAS: bloque común]. Stack fijado: shadcn base de todo, charts solo vía wrapper,
TanStack+Zod, sin tRPC, dark-first, ustedeo. DoD: CP1 (con P-rt) y tu parte de CP6
vivos contra compose.
```

### Prompt · Sesión C-1 (Confianza — manifest v2 + gateway/AX1)

```text
Eres la sesión CONFIANZA-1 de Mejorado (worktree mejorado/confianza-1). Lee PRIMERO
docs/mejorado/{01-criterio,04-consolidacion}.md (§4 dominio C, ítems C1-C2),
02-cobertura.md (M2 y manifest v2), la spec S-E y el supersede C-5 de S-B.

ALCANCE en orden: (C1) manifest v2 — los 4 campos §1 (side_effects,
required_permission, interaction, execution_profile) aterrizan en
blite_capability.manifest con la migración COORDINADA de las 13 capabilities (el
docstring-workaround de ingesta muere), gate de genericidad extendido, smoke 2.5
verde. (C2/M2) gateway por step: GatewayContext aditivo (ceremonia C-5 YA decidida
en S-B), las 6 etapas reales, Pipeline INYECTADO en execute_run (jamás import
runtime→gateway — añade el contrato layers), mapeo Rejection→run.step.failed/
run.failed, UN cruce por invocación (interpretación §13 registrada), JWT en cookie
(freeze §9 P1-9 — la sesión de seguridad del api), IdentityStage estampa actor real,
y SOLO ENTONCES el xfail AX1 se voltea (test_types.py:96 — endurecer la aserción a
procedencia del actor, JAMÁS borrar el test), _API_ACTOR muere, invariants.md
actualizado. Rollback de la decisión #6 (claim del body) SOLO si el cruce lo
habilita — registrar aparte.

[REGLAS: bloque común]. DoD: CP4 y CP5 vivos contra compose (run real cruzando las
8 etapas con actor del JWT en los eventos).
```

### Prompt · Sesión C-2 (Confianza — verificadores + M8)

```text
Eres la sesión CONFIANZA-2 de Mejorado (worktree mejorado/confianza-2). Lee PRIMERO
docs/mejorado/{01-criterio,03-research,04-consolidacion}.md (§4 dominio C, C3-C15),
knowledge/trust/11 (YA traducida a clase+AL por el saneamiento #103 — léela como
spec, no la re-traduzcas) y 12, docs/contract-freeze-anexo-canonicalizacion.md.

ALCANCE en orden: (C3/M3/#103) RuleVerifier: puerto RuleBackend con Z3 (rlimit,
jamás timeout) + RuleSet como datos SMT-LIB versionados con digest + diseño de la
salida proof (cvc5/Alethe/Carcara) aunque la v1 sea Z3-solo + registro en
trust-registry. (C4/M4/C-6) verify_all() con default compat + step_id=island_id
estable (usa la convención C-8 de S-D) + verdict per-isla + independence_group
compartido por corrida + punto de checklist de coherencia + supersede de la
diferición. (C5) hash-chain en el writer único (corte [stress-final]: head = evento
terminal) + M28 reconciliación sub_run_provenance_hash + punto 9 del checklist
(recompute del sub-run — el anexo CONGELADO ya lo manda) + stream del sub-run en el
bundle. (C6) DSSE por attestation con predicate sobre VSA/SVR + supersede del punto
7. (C7) StatusList forma Bitstring como artefacto estático firmado + verify-bundle
--status-list opcional + ●CertificateRevoked. (C8) OpenBao Transit single-node:
assemble/dsse cablean el puerto KeyProvider (hoy NO lo usan) + adapter. (C9/#105)
Rekor v2 posix como perfil opcional + stapled proofs. (C10/M29) OverridePayload
Pydantic + chequeo override:apply con match EXACTO (estampado) + Stage emite antes
de aplicar (INV-4) + test AX2. Los bundles YA emitidos siguen verificando 8/8 —
extensión aditiva SIEMPRE.

EXTENSIONES (#120, tras C10): C12 (registro de guardrail-adapters + convención
{etapa}.{mecanismo} + HHEM-2.1-Open con AlignScore fallback — GuardrailsStage sigue
faltando), C13 (Cedar Analysis sobre el SET de políticas + forma de bundle firmado
OPA — «probar que la regla nueva no es menos estricta»), C14 (puerto
ExecutionHarness prepare/run/collect/dispose + guarda PASS_TO_PASS — abre EXECUTION
a dominios no-eléctricos), C15 (evaluador de policy COMPLETO en bundle_check: hoy
ignora side_effects y NO comprueba min_level — ~15 líneas PERO cambia el veredicto
de bundles estampados ⇒ ceremonia obligatoria antes de tocar).

[REGLAS: bloque común]. DoD: CP7 vivo (verify-bundle extendido sin perder los 8
puntos sobre bundles viejos).
```

### Prompt · Sesión V (Visual/ciencia — productores)

```text
Eres la sesión VISUAL/CIENCIA de Mejorado (worktree mejorado/visual). Tu meta: los
honest-empty del Studio mueren DONDE exista productor real. Lee PRIMERO
docs/mejorado/{01-criterio,04-consolidacion}.md (§4 dominio V), 02-cobertura.md
(M18-M20 y el inventario honest-empty), S-D y el supersede C-4 de S-B.

ALCANCE en orden: (V1/M18) branch-ids híbrida (edge_id_property en geojson_to_graph
+ id canónico L{min}-{max}[-k]) + verdict per-isla desde los checks island-{k}:* +
productor de partition en verification.completed + step_id top-level (M23a — mata
attestations:[]) + getTopology/query/Zod + overlay sobre el mapa ICE con
reconciliación honesta 68/70 + fixture contract/superficie. (V2/M19) payload
extendido C-4 + dos brazos como SUB-RUNS (§13) + verification_latency_ms
instrumentado en orchestrator + puente ciencia→stream con digest. (V3/M20) ángulos
Nexus ingeridos con digest (extensión del importador — hoy solo viven en el espejo
reto1-vanilla) + optimize:false/initial_angles en QAOA (expected_energy ya existe) +
curva con Aer multi-semilla ETIQUETADA + GET /runs/{id}/rvsp. (V4/M6-ZNE) capability
propia folding+extrapolación + control negativo garbage-folding como test de primera
clase + bloque mitigation.* emitido (§11) + panel 4 barras. (V5) warm-start/INTERP
aditivo en QAOA. (V6/M5) adapter qnexus vivo bajo el gateway (side_effects correcto,
§13 no-retry escala a humano vía approvals) + egress policy + separación
corrida-viva/artefacto-congelado. (V7) QEC/Iceberg al final (tradeoff medido — el
enunciado advierte degradación). (V8/M23b) deliverables= a assemble_bundle + rutas
nivel proyecto.

EXTENSIÓN (#120, tras V7): V9 (corrector AI-QEM — ML-QEM RF/GBM, dataset CDR,
control negativo garbage-folding, certificado del corrector en modo amortizado;
04-consolidacion §7.1).

[REGLAS: bloque común]. DoD: CP6 vivo contra compose (mapa con badges + ablación +
rvsp con datos del stream real).
```

### Prompt · Sesión O (Plataforma/publicación)

```text
Eres la sesión PLATAFORMA de Mejorado (worktree mejorado/plataforma). Lee PRIMERO
docs/mejorado/{01-criterio,03-research,04-consolidacion}.md (§4 dominio O) y S-F.

ALCANCE en orden (O1 ya lo hizo la ola 0): (O2/M26) la regla de marca interna pasa
a enforcement VERSIONADO que viaja con el repo — diseña el mecanismo SIN delatar el
patrón (candidatos: regla genérica en pre-commit o semgrep con lista externa no
versionada; discútelo con Dylan antes de implementar) + sanitización del árbol
vendorizado de terceros (decidir: desvendorizar vs excluir del flip) + gitleaks
local en pre-commit. (O3/M9) proyector OTel como consumer standalone en perfil del
compose (C-11) según S-F (trace-id determinista: replay ⇒ trazas idénticas) +
Langfuse como perfil opcional documentado. (O4/M10) export Croissant con dualidad
de digests declarada (C-13) + licencia ICE investigada y estampada + ruta de
catálogo de instancias. (O5/M13) manifest genérico envolvente para MCP ajeno
(C-12) + DistributionManifest materializado (allowlist + egress + pins) +
DispatchStrategy de red + attestation de importación (builder.id mcp://…) —
qnexus-mcp como primer caso. (O7/M12) SOLO si el umbral definido se cumple — no es
compromiso.

EXTENSIONES (#120): O11 y O8 van TEMPRANOS — O11 (gate de agnosticismo multi-capa
engine/api/studio con excepciones declaradas) es el ítem que hace irreversibles los
demás; O8 (corpus runner forma-Inspect + KPI over-refusal C/I/P/N + marco «tres
planos») es la forma de medir si el sistema MEJORA. Después: O9 (protocolo de
convergencia simulada↔real empaquetado como herramienta), O12 (verify_corpus_digests
a CI + guard nuevo para knowledge/nexus/), O10 (1-pager SEPs — tardío, doble destino
KB). Y del handoff S3: hallazgo 9 (re-evaluación vencida del ignore de CVE en ci.yml
+ URL rota de ISSUE_TEMPLATE/config.yml) y hallazgo 10 (pin frágil 68af0c1 — solo
nota pre-flip, no podar esa rama sin traer el doc al árbol).

[REGLAS: bloque común]. DoD: cada pieza demostrada viva (proyector exportando un
run real a un collector local; un tool MCP externo invocado como capability
gobernada en compose).
```
