# Mejorado — saneamiento documental y de cimientos (precondición de la Fase 0)

> **Estado: VIGENTE (2026-07-30, decisión #107).** Mandato de Dylan: antes de seguir
> con la ejecución de Mejorado hay que ordenar, podar y ajustar la base de
> conocimiento y la documentación — mucha información está atada a features muy
> específicos (el plano de confianza/verificación) y a la resolución de UN problema
> (reto 1), y la rigidez documental degrada mantenibilidad y escalabilidad. La
> sesión de control VALIDÓ el diagnóstico (§1) y NO ejecuta la limpieza: este doc es
> el plan + los prompts. **La Fase 0 de contratos queda BLOQUEADA hasta que S4
> cierre**; la ola 0 del plan paralelo se funde en S3.

## 1 · Validación del diagnóstico (evidencia de la propia sesión de planning)

El diagnóstico es **cierto**, con una precisión al final. Lo que esta sesión chocó
al generar los planes de la fase:

1. **Casi cada ítem del backlog choca con una letra congelada** — el ciclo produjo
   15 conflictos de contrato (C-1…C-15, `02-cobertura.md` §5) cuya resolución exigió
   ceremonia explícita. El síntoma exacto que Dylan nombra.
2. **El freeze §13 describe un sistema que ya no existe**: afirma «pipeline fijo
   Fase 1» + set hardcodeado mientras el loop agéntico corre desde Planeado (C-1).
   La regla del propio índice de specs («una spec jamás contradice el freeze») está
   siendo violada por `harness-agentico.md`.
3. **Vocabulario muerto en specs que deberían ser implementables**: `trust/11` (la
   spec del RuleVerifier) está escrita ENTERA en `rung 1/4` — vocabulario que el
   freeze eliminó; la receta C3 vigente en la KB es la de química, SUPERSEDIDA desde
   el 18-jul; `trust/12` usa `subject.step_id` que no coincide con el modelo real;
   `DESIGN.md` §4 aún describe 5 barras cuando hay 3.
4. **Nombres divergentes nunca reconciliados**: `MODEL_ROUTER_BACKEND` (freeze) vs
   `CHIMERA_MODEL_BACKEND` (código); IDs reservados `cr{6,8}-flujo@v1` (freeze
   §15.3) vs archivos reales `-voltaje`; el ledger vive en `docs/mvp/` tres fases
   después del MVP.
5. **Acoplamiento reto-1 FUERA de la capa de datos** (donde la doctrina lo permite):
   `resolve_verifiers` e `_resolve_mission_inputs` son Reto-1-only en el api;
   `ExactSolverVerifier` es Max-Cut por construcción; `AblationMetric.variant` es
   `quantum|classical` cerrado; `baselines` cerrado a `cpsat/greedy/gw`; el corpus y
   su guard solo entienden grafos. (La ADR-029 protegió los manifests — pero el
   borde api/schemas se escapó.)
6. **El plano de confianza tiene contradicciones internas congeladas**:
   `run.metrics.recorded` tiene DOS payloads incompatibles (campos de confianza en
   freeze §3 vs campos científicos en el consumidor — C-4); `superficie-visual.md`
   §5 pinnea una fuente que el Studio ya rechazó con divergencia registrada (C-9);
   el anexo de canonicalización manda un recompute de sub-run que `verify-bundle`
   no hace.
7. **Sprawl e índices rotos**: `docs/README.md` (el punto de entrada) no lista
   `docs/mejorado/` ni `docs/studio/` y dice que specs tiene 1 archivo cuando hay 7;
   el árbol vendorizado `knowledge/quantum/quantathon/` rompe el gate de docs de CI
   (671 errores — cualquier PR con un `.md` falla); `CODEOWNERS` y
   `docs/ratificaciones/` + `docs/decisiones-delegadas-*` pertenecen a la era de
   dueños que la #94 mató; `.env.example` incumple su propia promesa de completitud.
8. **El costo operativo es real y medible**: cada ítem de este planning exigió
   arqueología multi-doc (freeze + anexo + 7 specs + 18 notas de trust + ledger de
   500+ líneas + docs de 3 generaciones) para saber qué está vigente. Eso es
   exactamente la degradación de mantenibilidad del mandato.

**La precisión**: los cimientos ARQUITECTÓNICOS no son el blocker — el research de
la Etapa 2 validó event-sourcing/replay, el registry por entry-points, DSSE offline
y la canonicalización como estado del arte, y los 15 conflictos se resolvieron TODOS
como extensiones aditivas (la arquitectura aguanta; la LETRA no la alcanza). El
blocker real es (a) la **capa documental** (drift, vocabulario muerto, sprawl,
autoridad ambigua), (b) las **fugas de reto-1 en capas de borde** (ya backlogueadas
como G3/V/C-15 — código, no docs), y (c) los **cimientos de proceso de la era
hackathon** (ratificaciones por dueño, guion del día D, docs TS heredados) que ya no
gobiernan nada. El saneamiento ataca (a) y (c); (b) se queda en el backlog de código
donde ya está — hacerlo dos veces sería el error.

**Línea roja del saneamiento** (no negociable): los contratos congelados NO se
«limpian» — solo se tocan por ceremonia de supersede con causa; JAMÁS se re-digesta
nada estampado (§15.3, fixtures, vectores); el ledger de decisiones es
solo-anexar — registro histórico intocable. Podar mal el freeze rompería la
verificabilidad que es EL diferenciador.

## 2 · Alcance / NO-alcance

**Alcance**: todo `docs/` + `knowledge/` + READMEs + índices + estados de docs;
higiene de repo atada a docs (gate de CI, `.prettierignore`, `CODEOWNERS`,
`.env.example`, árbol vendorizado); aplicación de los supersedes YA decididos
(#102 §13/§14, C-9 §5, C-10 §15.3, N12 env var, M9 enunciado); traducción de
vocabulario muerto en specs de knowledge; jerarquía de autoridad documental
explícita.

**NO-alcance**: refactors de código (G3 dispatch por clase, C-15 baselines, etc. —
ya viven en `04-consolidacion.md` §4); cambios de forma de contratos (eso es la
Fase 0 con su ceremonia); reescritura del ledger; re-digest de cualquier cosa
estampada; borrar historia (lo histórico se ARCHIVA con marca, no se elimina).

## 3 · El plan (S1 → S4)

| Etapa                     | Qué                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Quién                            | Salida                                 |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------- | -------------------------------------- |
| **S1 · Censo**            | Exploración paralela SOLO LECTURA de todo el corpus documental: clasificar cada doc en {VIGENTE / VIGENTE-CON-DRIFT (letra ≠ código, con el delta exacto) / SUPERSEDIDO-SIN-MARCAR / HISTÓRICO-ERA-HACKATHON / VENDORIZADO-AJENO / HUÉRFANO}, censar vocabulario muerto, referencias rotas, duplicados, y el acoplamiento reto-1 en docs supuestamente genéricos                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | sesión censo (prompt §4.1)       | `docs/mejorado/07-censo-documental.md` |
| **S2 · Diseño del orden** | Con Dylan (AskUserQuestion, opciones analizadas): (a) jerarquía de autoridad ÚNICA y explícita (propuesta: constitución = invariants+freeze+anexo → specs de costura → docs de fase → knowledge = research de entrada, JAMÁS autoridad → archivo); (b) política de estados obligatoria en header (VIGENTE / SUPERSEDIDO-POR-X / HISTÓRICO + fecha) y regla «el supersede marca al doc viejo, no solo al ledger»; (c) destino del freeze mono-doc: aplicar supersedes pendientes y mantenerlo único vs modularizarlo (análisis en §5); (d) destino de los cimientos de proceso muertos (ratificaciones, decisiones-delegadas, guion día-D, contratos TS v1/v2, CODEOWNERS); (e) ubicación/encabezado del ledger; (f) vendorizado quantathon: desvendorizar vs excluir; (g) política de idioma confirmada; (h) el hueco S3↔código (07-censo §8.5): vocabulario muerto y terminología de evento en ~40 archivos de código — decidir si S3 gana alcance quirúrgico de docstrings/comentarios (cero efecto runtime, gates verdes lo prueban) o si entra como ítem nuevo del backlog; (i) TOP-10 de research huérfana (07-censo §7.1): destino por ítem {ítem nuevo de backlog / KB curada / descarte CON causa registrada} — dejan de ser huérfanos; (j) los 4 hallazgos de diseño sin backlog (07-censo §8.5: registry de lentes del Studio, gate de agnosticismo multi-capa, evaluador de policy incompleto, guards de datos estampados): registrarlos como ítems o diferirlos con causa | sesión de control + Dylan        | decisiones #108+                       |
| **S3 · Ejecución**        | Aplicar TODO lo decidido: estados/moves/archives, supersedes pendientes, índices reconstruidos (`docs/README.md` como mapa de autoridad), traducciones de vocabulario muerto (trust/11 a clase+AL; marca de supersede en la receta química; nota TFIM stub), fix del gate de docs + CI en ramas, `.env.example` honesto, CODEOWNERS. Absorbe la ola 0 completa del plan paralelo                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | sesión saneamiento (prompt §4.2) | commits + tabla de interacciones       |
| **S4 · Validación**       | La sesión de control verifica contra checklist (§6) con evidencia (gates + greps citados), registra el cierre en el ledger, y desbloquea la Fase 0                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | sesión de control                | decisión de cierre                     |

## 4 · Prompts generadores

### 4.1 · Prompt — Sesión CENSO (S1, solo lectura)

```text
Eres la sesión de CENSO DOCUMENTAL de la fase Mejorado (repo
~/projects/blite/hackathons/2026/Quantathon/Chimera, rama mejorado/base, SOLO
LECTURA — no editas nada). Contexto: docs/mejorado/06-saneamiento.md (el mandato y
la línea roja) + 02-cobertura.md §5 (los 15 conflictos ya detectados — tu punto de
partida, no lo re-descubras).

MISIÓN: censo exhaustivo del corpus documental para el saneamiento. Produce
docs/mejorado/07-censo-documental.md (es tu ÚNICO entregable escrito) con:

1. INVENTARIO clasificado — para CADA archivo de docs/ (todas las subcarpetas),
   knowledge/ (las 6 áreas + README), READMEs de paquetes, y archivos de gobernanza
   (.github/, CONTRIBUTING, GOVERNANCE, CODEOWNERS): clasificación {VIGENTE /
   VIGENTE-CON-DRIFT / SUPERSEDIDO-SIN-MARCAR / HISTÓRICO-ERA-HACKATHON /
   VENDORIZADO-AJENO / HUÉRFANO} + una línea de justificación + para los DRIFT, el
   delta exacto (qué dice el doc vs qué dice el código, con refs archivo:línea de
   ambos lados).
2. CENSO DE VOCABULARIO MUERTO: rung, MODEL_ROUTER_BACKEND, 5 barras, VQE/química
   como C3, pipeline fijo, PENDIENTE-{persona}, y los que descubras — cada uno con
   TODAS sus apariciones (ruta:línea) y el vocabulario vigente que lo reemplaza.
3. CENSO DE ACOPLAMIENTO RETO-1 EN DOCS GENÉRICOS: docs/specs y docs raíz que
   mezclan contrato genérico con ejemplos/campos islanding/MaxCut sin marcar cuál
   es cuál.
4. GRAFO DE AUTORIDAD REAL: qué doc cita a cuál como autoridad, dónde hay ciclos o
   ambigüedad (dos docs reclamando la misma autoridad), y qué docs no cita nadie
   (huérfanos).
5. DUPLICADOS Y HERENCIAS: especificacion-contratos v1/v2 (TS), arquitectura-* (3
   variantes), esquema-datos v1/v2 — qué contiene cada uno que NO esté ya en el
   vigente.
6. PROPUESTA de destino por archivo (mantener / marcar / archivar / fusionar /
   traducir / desvendorizar) — SIN ejecutar nada.

REGLAS: solo lectura (excepto tu entregable); verificación antes de afirmar (cada
drift con ambas refs); el ledger docs/mvp/decisiones.md se CENSA pero jamás se
propone reescribir (solo-anexar, línea roja); el codename de marca interna no se
escribe en tu entregable (hay hook que lo bloquea); paraleliza con subagentes
Explore si el volumen lo pide. Commit único convencional en minúscula ≤100 chars:
"docs(mejorado): censo documental para saneamiento (s1)".
```

### 4.2 · Prompt — Sesión SANEAMIENTO (S3, ejecuta lo decidido)

```text
Eres la sesión de SANEAMIENTO DOCUMENTAL de Mejorado (worktree mejorado/saneamiento
desde mejorado/base). Insumos OBLIGATORIOS: docs/mejorado/06-saneamiento.md (plan y
línea roja), 07-censo-documental.md (el censo S1) y las decisiones #108+ del ledger
(el diseño S2 — NO improvises destinos que no estén decididos).

ALCANCE en orden:
1. Aplicar la política de estados: header obligatorio en cada doc según su
   clasificación decidida; los SUPERSEDIDOS ganan la marca apuntando a su sucesor.
2. Archivar lo decidido (git mv a la ruta de archivo acordada — la historia se
   conserva, jamás rm) y reconstruir docs/README.md como EL mapa de autoridad
   (jerarquía completa, todas las carpetas, estados).
3. Aplicar los supersedes YA decididos: #102 (freeze §13 [MEJORADO] + eventos #68
   al catálogo §14), C-9 (superficie-visual §5), C-10 (tabla §15.3: cr6/cr8
   -voltaje@v1 + nota de procedencia), N12 (nota de reconciliación
   MODEL_ROUTER_BACKEND→CHIMERA_MODEL_BACKEND), M9 (Langfuse = perfil opcional en
   el enunciado del backlog) + las marcas restantes de 07-censo §1.7-B que ya
   tienen decisión registrada (#103/#105/#106: checklist 7→8 puntos, Rekor
   re-entra, C-4/C-5/C-6, nota de estado del manifest v2 en §1).
4. Traducciones de vocabulario muerto SEGÚN lo decidido en S2: trust/11 a clase+AL
   (sin cambiar su contenido normativo — es traducción, no rediseño), marca de
   supersede en la receta química de KB2-02 §3 + stub de la nota TFIM que la
   reemplaza, DESIGN.md §4 (3 barras), y el resto del censo.
5. Higiene de repo: gate de docs verde SOBRE TODO EL REPO (vendorizado según
   decisión S2 — excluir o desvendorizar), CI en push a mejorado/*, CODEOWNERS
   alineado a #94, .env.example completo y honesto.
6. Accionar de las extensiones del censo SEGÚN lo decidido en S2 (decisiones
   h/i/j): (a) anexar a docs/mejorado/04-consolidacion.md los ítems aceptados del
   TOP-10 de research huérfana (07-censo §7.1) y de los 4 hallazgos de diseño
   (§8.5), cada uno con su dominio y orden; registrar los descartes CON causa en
   la tabla de interacciones (dejan de ser huérfanos: pasan a descarte-con-causa);
   (b) marcar los docs de research según su destino decidido; (c) SOLO si S2
   aprobó la decisión (h): traducción quirúrgica de vocabulario muerto y
   terminología de evento en docstrings/comentarios de código (diff
   solo-comentarios, cero efecto en runtime ni contratos — los gates verdes lo
   prueban); si NO la aprobó, ese frente queda como ítem de backlog y el código
   NO se toca.
7. Tabla de interacciones de tu sesión en docs/mvp/decisiones.md.

LÍNEA ROJA (del plan, no negociable): contratos congelados solo por la ceremonia ya
decidida — si descubres un cambio de contrato NO decidido, lo REPORTAS al handoff,
no lo haces; jamás re-digestar nada estampado; el ledger es solo-anexar; cero
cambios de código de features (eso vive en el backlog G/P/C/V/O; ÚNICA excepción
posible: el alcance quirúrgico de docstrings/comentarios del punto 6c SI la
decisión (h) de S2 lo aprobó — jamás lógica ni contratos); el codename de
marca interna jamás en texto del repo. Gates verdes antes de cada commit (uv run
pytest && uv run lint-imports && uv run ruff check && uv run pyright + pnpm -C
apps/studio run test:run + lint) — los docs no los rompen, pero se corren igual
(verificación, no fe) + el gate de docs: npx markdownlint sobre el repo según la
exclusión decidida + prettier --check. Commits convencionales en minúscula ≤100,
uno por bloque del alcance. Nada de push. DoD: checklist §6 de 06-saneamiento.md
completo con evidencia citada.
```

## 5 · Análisis para S2 — el destino del freeze (opciones, sin decidir)

- **(a) Mantener mono-doc + aplicar supersedes + marcas [MEJORADO]** (recomendación
  inicial de la sesión de control): mínimo churn, la autoridad no se mueve, el
  costo de arqueología baja con el índice nuevo y las marcas de estado. KISS.
- **(b) Modularizar en contratos por plano** (eventos/verificación/certificado/
  gateway/…): mejor navegación a largo plazo, pero re-escribir la constitución a
  mitad de fase multiplica el riesgo de drift durante la transición y rompe cientos
  de referencias `freeze §N` en specs, knowledge, ledger y CÓDIGO (docstrings).
- **(c) Híbrido**: mono-doc intacto + un índice-mapa nuevo por plano que apunte a
  las secciones (cero referencias rotas, navegación ganada). Compatible con (a).

La sesión de control lleva (a)+(c) como recomendación a S2; (b) solo si Dylan
quiere pagar el costo ahora.

## 6 · Checklist de cierre (S4 valida con evidencia)

- [ ] Todo doc de `docs/` y `knowledge/` tiene header de estado y aparece en el
      índice de autoridad (`docs/README.md`).
- [ ] Grep de vocabulario muerto = 0 hits fuera de docs marcados HISTÓRICO.
- [ ] Los 5 supersedes pendientes aplicados (#102, C-9, C-10, N12, M9) + las
      marcas restantes de 07-censo §1.7-B con decisión registrada.
- [ ] Extensiones del censo con destino aplicado: TOP-10 de research huérfana y
      4 hallazgos de diseño anexados al backlog o descartados con causa (cero
      huérfanos sin registro); hueco de docstrings resuelto según la decisión (h).
- [ ] Gate de docs de CI verde sobre TODO el repo (markdownlint + prettier) y CI
      corriendo en ramas `mejorado/*`.
- [ ] `CODEOWNERS`, `.env.example` y `docs/ratificaciones/`+
      `decisiones-delegadas` con destino aplicado según S2.
- [ ] Cero contratos tocados fuera de ceremonia; cero re-digests; ledger
      solo-anexado (diff lo prueba).
- [ ] Gates de código citados con números (sin regresión respecto del baseline
      804/90.96%/13/221).
- [ ] Fase 0 desbloqueada por decisión registrada.
