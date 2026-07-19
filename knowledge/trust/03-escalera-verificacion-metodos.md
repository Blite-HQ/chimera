# Nota 03 — La escalera de verificación formalizada + el puerto `Verifier`

**Ítem del plan (§4 Dylan):** Métodos de la escalera → puerto `Verifier` + forma de `evidence` + registro de escalón
**Fecha:** 2026-07-02 · **Estado:** **SUPERSEDIDA (2026-07-18, cierre S-E)** — la escalera 1–7 quedó reemplazada por los tres ejes de la spec v3.2 (`docs/spec-confianza-v3-2.md`): **clase decisoria** (el método) + **AL0–AL4** (la fuerza, con techos) + **criticidad C0–C3** (la exigencia). El mapa de traducción escalón→clase/techo vive en `docs/convergencia-diseno-v32.md` §2.1 y el contrato vigente en `docs/contract-freeze.md` §4. Los MÉTODOS aquí descritos siguen siendo el diseño de los adapters — solo cambia la etiqueta (los escalones 5–6 "no producen attestation" hoy se dice: son `Detector`/`Signal`, S1).
**Fuentes:** base lógica (D18/PR2/ADR-027, congelada) · CHIMERA-Studio-Frontend §2 · CHIMERA-Arquitectura-Python §6 (correcciones #2/#3/#5) · compass deep-dive de verificación (PRM/ORM, verdictos AWS AR) · verificación en vivo de licencias (2026-07-02)

---

## 1 · Patrón / mecanismo

### 1.1 La escalera como registro de escalones (rungs)

La escalera ya existe en los docs del equipo como lista informal ("solver / ejecución / verdad conocida / propiedad / consenso / detección / humano"). Lo que faltaba es **formalizarla como dato del contrato**: cada attestation declara en qué escalón se apoya, y la confianza agregada de un run es **el escalón más débil del camino crítico — nunca un promedio** (un promedio ponderado esconde el eslabón débil; corrección #3 de Arquitectura-Python).

| Rung | Nombre                   | AnchorKind  | ¿Produce `Attestation`? | Ejemplo CHIMERA                                                   |
| ---- | ------------------------ | ----------- | ----------------------- | ----------------------------------------------------------------- |
| 1    | Óptimo exacto / solver   | `solver`    | ✅                      | CP-SAT (OR-Tools) resuelve el QUBO exacto en IEEE-14 y se compara |
| 2    | Ejecución / factibilidad | `execution` | ✅                      | pandapower corre el flujo de potencia sobre cada isla propuesta   |
| 3    | Verdad conocida          | `dataset`   | ✅                      | corpus IEEE con partición óptima conocida (Sebas)                 |
| 4    | Propiedad / regla        | `rule`      | ✅                      | Hypothesis: propiedades del corte; relaciones metamórficas        |
| 5    | Consenso entre muestras  | —           | ❌ → `GuardrailSignal`  | self-consistency de salidas cuánticas muestreadas                 |
| 6    | Detección por modelo     | —           | ❌ → `GuardrailSignal`  | HHEM / semantic entropy (Fase 2, capa guardrails)                 |
| 7    | Juicio humano            | `human`     | ✅                      | aprobación puntual en el borde irreversible                       |

**La observación estructural clave:** los escalones 5 y 6 **no tienen `AnchorKind`** — son detección probabilística, no verificación. El tipo lo hace irrepresentable: `AnchorKind = Literal["solver","execution","dataset","rule","human"]` no tiene valor para consenso ni detección. Un paso que solo tiene señales de rung 5–6 queda **"no anclado"** y el Studio lo muestra explícitamente (la honestidad ES el diferenciador — Studio doc §3). Esto convierte la distinción D18/D21 en propiedad del sistema de tipos, no en disciplina.

**Agregación:** `aggregate_rung = max(rung de las attestations del camino crítico)` (numéricamente: más alto = más débil). Si un paso del camino crítico no tiene attestation → el certificado reporta `unanchored_steps > 0` y el nivel agregado se marca como no-anclado. Nunca promedio, nunca score compuesto.

### 1.2 Métodos por escalón y la forma de su `evidence`

La evidencia no puede ser `unknown`/`dict` amorfo: cada método tiene una forma auditable ("qué anchor, qué regla, qué traza" — semilla TS §5). Formas propuestas (discriminadas por `method`):

- **Verificación diferencial (rung 1):** contraste contra una implementación/solver independiente y exacto.
  `{method: "differential", reference: {solver: "ortools-cpsat", version, params_digest}, reference_value, candidate_value, gap, tolerance, solver_status: "OPTIMAL|FEASIBLE|TIMEOUT"}`
  El estado del solver importa: CP-SAT que devuelve `FEASIBLE` (no `OPTIMAL`) **no** es ancla de rung 1 — es cota. El evidence lo registra para que el verdict pueda ser `inconclusive`.
- **Ejecución / factibilidad (rung 2)** — patrón HumanEval/SWE-bench (correr de verdad y observar):
  `{method: "execution", harness: "pandapower-powerflow", input_digest, checks: [{name: "island_connectivity", passed}, {name: "power_balance", passed, measured, limit}], runtime_ms, environment: {package, version}}`
- **Verdad conocida (rung 3):**
  `{method: "known_truth", dataset_id: "ieee14-partitions-v1", case_id, expected_digest, observed_digest, match: true|false, tolerance}`
  El dataset es **conocimiento versionado en el repo** (lo produce Sebas); el evidence referencia su versión — sin eso el ancla no es reproducible.
- **Property-based (rung 4, Hypothesis):**
  `{method: "property", properties: [{name: "cut_cost_nonnegative", passed, examples_run, counterexample?}], seed, generator_version}`
  El `seed` hace la corrida **replayable** — evidencia reproducible, no anécdota. Hypothesis imprime y fija seeds; se registra siempre.
- **Metamorphic (rung 4):** para claims sin oráculo directo (Chen et al. 1998; survey Chen et al. 2018, ACM CSUR). Relaciones para CHIMERA: renombrar nodos no cambia el costo del corte; escalar todos los pesos por k escala el costo por k; agregar un nodo aislado no cambia la partición óptima.
  `{method: "metamorphic", relations: [{name, transform_digest, expected_relation: "equal|scaled|invariant", held: true|false}]}`
- **Juicio humano (rung 7):**
  `{method: "human", reviewer: actor_id, decision, rationale, reviewed_digest}` — atribuible (AX1), nunca anónimo.

### 1.3 Verificación de proceso, no solo de resultado (PRM vs ORM)

"Let's Verify Step by Step" (Lightman et al., arXiv:2305.20050): la supervisión **por paso** localiza el error exacto, es más interpretable y evita el caso "razonamiento incorrecto que llega al resultado correcto". Para el contrato: la `Attestation` lleva un **`subject` con `step_id` opcional** — se puede atestar el resultado del run Y cada paso intermedio. El evento `verification.completed` referencia el paso que verificó. El Studio ya lo exige (inspector de paso con badge por paso); el flywheel Fase 2 lo necesitará como señal de proceso.

### 1.4 El verdict honesto: tri-estado, no booleano

La semilla TS dice `verdict: 'pass' | 'fail'`. **Se cambia a tri-estado:** `pass | fail | inconclusive`.

Justificación:

1. **Precedente de mercado:** AWS Automated Reasoning devuelve `TOO_COMPLEX`, `TRANSLATION_AMBIGUOUS`, `NO_TRANSLATIONS` además de VALID/INVALID (verificado en docs AWS 2026-07-02). Un solver que agota timeout, una propiedad con cobertura insuficiente, un caso fuera del corpus — no son `fail`, y reportarlos como `pass` sería mentir.
2. **La honestidad es el diferenciador:** "un sistema que dice 'este paso no lo pude anclar' es más confiable que uno que finge" (Studio doc §3). `inconclusive` es la representación de esa honestidad en el tipo.
3. **Imposibilidad teórica** (Xu et al., arXiv:2401.11817): la verificación perfecta no existe en mundo abierto; el diseño debe representar la abstención. En el mundo cerrado de CHIMERA (optimización) `inconclusive` será raro — pero el contrato no debe hacerlo irrepresentable.

`inconclusive` **no relaja nada**: para efectos del certificado cuenta como no-anclado; para el estado del run, la política decide (nota 05). Y el egreso sigue gobernado SOLO por authz (Inv-E) — el verdict jamás lo satisface.

---

## 2 · Decisión

| Referencia                                 | Decisión                                                             | Racional                                                            |
| ------------------------------------------ | -------------------------------------------------------------------- | ------------------------------------------------------------------- |
| La escalera 1–7 como registro formal       | **portar** (es nuestra; se formaliza como contrato Pydantic)         | No existe en ningún repo externo; es el diferenciador               |
| Hypothesis (property-based)                | **integrar** (dependencia del grupo de verificación/test)            | Madura, determinista con seed, estándar de facto en Python          |
| Verificación diferencial                   | **portar** (patrón, sin librería)                                    | Es un patrón de uso de OR-Tools (nota 04), no una dependencia nueva |
| Metamorphic testing                        | **portar** (patrón de la literatura, relaciones propias del dominio) | No hay lib útil; las relaciones son conocimiento CHIMERA versionado |
| PRM (verificación por paso)                | **inspirar** (la forma: attestation por paso)                        | El entrenamiento con señal de proceso es Fase 2 (flywheel)          |
| Verdictos estilo AWS AR (`TOO_COMPLEX`...) | **inspirar** (colapsados en `inconclusive` + detalle en evidence)    | Su taxonomía exacta es específica de SMT sobre políticas            |

## 3 · Licencias

| Pieza                                                     | Licencia                           | Verificado | Implicación                                                                                                                                                            |
| --------------------------------------------------------- | ---------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Hypothesis                                                | **MPL-2.0** (v6.156.0, 2026-07-02) | ✅ en vivo | Copyleft a nivel de archivo: OK como dependencia sin modificar. NO vendorizar ni parchear su código. Como dep de test/verificación no contamina la licencia del Engine |
| Chen et al. (metamorphic), Lightman et al. (PRM)          | literatura                         | —          | Sin dependencia de código                                                                                                                                              |
| OR-Tools / pandapower (las anclas que estos métodos usan) | ver nota 04                        | ✅         | Apache-2.0 / BSD-3                                                                                                                                                     |

## 4 · Impacto en contrato

Contra la **semilla TS** (`Especificacion-Contratos.md §5`) y los **stubs Python actuales** (`engine/src/blite/verification/__init__.py` está vacío):

1. **`AnchorKind`** — se mantiene `Literal["solver","execution","dataset","rule","human"]`, sin `"model"` (ya verificado por pyright según §2 del plan maestro). Sin cambios: la escalera lo confirma.
2. **`Verifier`** (nuevo en Python, Protocol):
   ```python
   class Verifier(Protocol):
       anchor_kind: AnchorKind
       rung: int  # 1..7; consistente con anchor_kind (5-6 irrepresentables aquí)
       def verify(self, claim: Claim, ctx: InvocationContext) -> Attestation: ...
   ```
3. **`Attestation`** (Pydantic) — CAMBIA respecto de la semilla TS:
   - `+ rung: int` (nuevo — registro del escalón)
   - `verdict: Literal["pass","fail","inconclusive"]` (era pass|fail — **tri-estado**)
   - `evidence` deja de ser `unknown`: unión discriminada por `method` (formas de §1.2)
   - `+ subject: {run_id, step_id | None, claim_digest}` (verificación de proceso, PRM)
   - La tabla `attestations` de la semilla SQL gana columnas `rung SMALLINT NOT NULL` y `verdict` con CHECK tri-estado.
4. **`TrustCertificate`** — `+ aggregate_rung: int` y `+ unanchored_steps: int` (consumido por nota 02; el agregado es el escalón más débil del camino crítico).
5. **Evento `verification.completed`** — payload = la attestation completa (incluye rung/verdict); una por paso verificado, no solo al final del run.
6. **Escalones 5–6** quedan fuera del puerto `Verifier` por construcción → van al contrato `GuardrailSignal` (nota 04).

**Frontera con Steven:** el pipeline del gateway invoca la etapa de verificación por el contrato (`GatewayStage` → `Verifier`); este documento define el lado `Verifier`/`Attestation`, no la mecánica del pipeline.

## 5 · Reconciliación contra la base lógica

- **PR2/ADR-027/INV-2 (el verificador nunca es un modelo):** REFORZADO — la formalización hace los escalones con-modelo (5–6) irrepresentables como attestation, no solo prohibidos por import-linter.
- **Inv-E (egreso solo por authz):** INTACTO — `verdict` (incluso `pass`) jamás satisface un egreso; `inconclusive` tampoco lo bloquea por sí mismo: informa el estado del run y el certificado.
- **D20 (confianza = propiedad del proceso):** REALIZADO — `aggregate_rung` + attestation por paso son la materialización medible.
- **Ninguna referencia contradijo la base lógica.** El único ajuste fue a la semilla TS (verdict binario → tri-estado), que es semilla, no constitución.
