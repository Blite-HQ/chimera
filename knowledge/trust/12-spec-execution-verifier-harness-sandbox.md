# Nota 12 — Anatomía del harness (HumanEval/SWE-bench) → checklist del `ExecutionVerifier` + costura al puerto Sandbox (A7)

**Ítem del plan (§4 Dylan / ficha A1):** Anclas duras — de decisión a diseño de adapter. Parte 3: el adapter rung 2 (ejecución/factibilidad) y su costura Fase 2.
**Fecha:** 2026-07-07 · **Estado:** spec de diseño — insumo de la sesión 11 (rung 2 = pandapower) + semilla de la ficha A7. **SOLO diseño; nada implementado.**
**Fuentes:** nota 03 §1.2 (forma `evidence` `execution`) · nota 04 §1.1 (pandapower rung 2, "correr y observar") y §2/§4 (E2B/Firecracker como forma, microVM Fase 2) · `contract-freeze.md` §4 y §9 (verificación POR ISLA) · anexo de canonicalización §2 (`C()` para `input_digest`) · anatomía de HumanEval (OpenAI) y SWE-bench (Princeton) · `docs/invariants.md` AX3 · `CHIMERA-Harness-Metodologias.md` (§1 def. de harness, §4–5 pool + árbol PEV, §6 mapeo Reto 1).

---

## 1 · Patrón / mecanismo

**Encuadre — dos sentidos de "harness" (para no confundirlos).** `CHIMERA-Harness-Metodologias.md` usa "harness" en el sentido **de agente** (ADR-004): el loop configurable _plan → execute → verify_ (PEV), con descomposición jerárquica + subagentes, cuyo **gate de verificación es el gateway** (carril de orquestación de Steven — [frontera]). Esta nota especifica el otro sentido, más angosto: el **harness de EJECUCIÓN** — la maquinaria de aislamiento/timeout/colección que _corre y observa_. Encaja como el **método rung 2 del paso "V" (verify)** de ese PEV: el árbol de decisión de ese doc (§5, DECISIÓN 2: "¿se puede ejecutar y medir? → escalón 2") baja hasta este adapter. Validación externa directa: ese doc §6 mapea el verify del Reto 1 a **OR-Tools → rung 1** (nota 10) + **pandapower → rung 2** (esta nota); su "restricción-como-ancla (validez, no optimalidad)" (§4.4 transversal) es exactamente lo que chequea el `ExecutionVerifier` — factibilidad, no óptimo; y su disciplina de "colección sin interpretación" (invariante #3, §1.2) es el mismo principio que el **pipeline fijo de Agentless** (localizar→generar→testear) de ese doc §2.

### 1.1 Por qué mirar HumanEval/SWE-bench

El rung 2 es "correr de verdad y observar, no opinar" (nota 03/04). Los dos harness de referencia del campo de la evaluación de código ejecutan **código no confiable** y lo **califican objetivamente** — exactamente la disciplina que un `ExecutionVerifier` necesita para ser un ancla y no una opinión. Se destila su anatomía en un checklist reutilizable; **no se integra su código** (son benchmarks, no librerías).

- **HumanEval** (OpenAI): cada problema = prompt + `entry_point` + un set de **tests unitarios ocultos**. Calificación = ejecutar la función candidata en un namespace fresco, correr los tests bajo un **timeout**; `pass@k` = fracción que pasa TODOS. Propiedades: (a) el código no confiable **se EJECUTA** (comportamiento, no inspección); (b) **timeout duro** acota código lento/no-terminante (context manager basado en señal + un _reliability guard_ que desactiva llamadas destructivas de `os`/`shutil`); (c) el chequeo es **binario y objetivo** — sin modelo en el loop.
- **SWE-bench** (Princeton): cada tarea = repo@`base_commit` + un `test_patch` (los sets `FAIL_TO_PASS` y `PASS_TO_PASS`) + el parche candidato. Calificación en un **contenedor aislado** (imagen Docker por-instancia, deps pineadas): aplicar parche → correr los tests especificados → resuelto sii `FAIL_TO_PASS` ahora pasan Y `PASS_TO_PASS` siguen pasando. Añade sobre HumanEval: (a) **aislamiento y reproducibilidad de entorno** (la imagen pineada ES parte del spec, no el host); (b) **separación harness/juicio** — el harness solo recolecta un reporte estructurado, no interpreta; (c) **guarda de regresión** (`PASS_TO_PASS`: el cambio no rompió lo que funcionaba — "no hagas trampa rompiendo otra cosa").

### 1.2 Los tres invariantes de un harness confiable (aislamiento · timeouts · colección)

Destilado — los tres que nombra la ficha:

1. **Aislamiento.** La ejecución no confiable corre en un entorno acotado: proceso/namespace fresco, sin estado ambiente del host, syscalls destructivos desactivados (el _reliability guard_ de HumanEval), **deps pineadas** (imagen de SWE-bench). El entorno es **parte de la evidencia** (`environment: {package, version}`, nota 03 §1.2).
2. **Timeouts (cota determinista).** Toda corrida va envuelta en un límite de tiempo duro; **el timeout es un desenlace distinto** (→ `inconclusive`, **NO** `fail` — una corrida que no terminó no prueba nada sobre la factibilidad), registrado como `runtime_ms` + un flag `timed_out`. (Paralelo exacto al punto de tiempo-determinista de nota 10 §1.4: un timeout es abstención, no verdict.)
3. **Colección (recolección estructurada, sin interpretación).** El harness emite un reporte de chequeos **nombrados y objetivos** (`{name, passed, measured, limit}`); el verdict se **deriva** del reporte por reglas fijas, y el harness **jamás opina**. Reproducible: mismo `input_digest` + mismo entorno → mismo reporte.

### 1.3 → Checklist del `ExecutionVerifier` (rung 2, pandapower hoy)

Para el islanding de CHIMERA, los "tests unitarios" son los chequeos de factibilidad física **por isla propuesta**. El `ExecutionVerifier` es el adapter rung 2 del puerto `Verifier`; su implementación (sesión 11) DEBE cumplir:

- [ ] **`input_digest`**: hashear la entrada exacta (grid + partición propuesta) con `C()` (anexo Regla 2) → reproducibilidad + enlace de evidencia.
- [ ] **Aislamiento**: pandapower corre **in-process este mes** (librería confiable y determinista — NO es código arbitrario no confiable), PERO el harness se escribe **detrás de la forma del puerto Sandbox** (§1.4) para que, cuando el código arbitrario sea un ancla (Fase 2), el MISMO checklist aplique con una microVM. **Pinear la versión de pandapower** y registrarla en `environment`.
- [ ] **Chequeos** (los "tests" de factibilidad), cada uno **nombrado + objetivo**:
  - `island_connectivity` — cada isla propuesta es un subgrafo conexo (chequeo de grafo).
  - `powerflow_converged` — el flujo de potencia **convergió** (no-convergencia → `inconclusive` para esa isla, **no** `fail`).
  - `power_balance` — generación vs carga dentro de tolerancia por isla (`measured` vs `limit`).
  - `voltage_limits` / `line_loading` — pandapower converge y se mantiene en banda (`measured` vs `limit`).
- [ ] **Timeout**: acotar la corrida de flujo; no-convergencia o timeout → el chequeo de esa isla es `inconclusive`, registrado, jamás pasado en silencio.
- [ ] **Colección**: emitir `checks: [{name, passed, measured?, limit?}]` + `runtime_ms` + `environment` (forma de nota 03 §1.2); **verdict derivado**: todos pasan → `pass`; algún hard-fail → `fail`; algún chequeo `inconclusive` (no-convergencia/timeout) sin hard-fail → `inconclusive`.
- [ ] **Granularidad POR ISLA**: el freeze §9 exige `verification` **por isla** (validado por el spike). La evidencia de ejecución es por-isla: una `Attestation` por isla (`subject.step_id = island_id`), de modo que el Studio ponga un badge por isla (alinea freeze §9 + PRM por-paso de nota 03 §1.3).
- [ ] **Reglas como datos**: los límites/tolerancias vienen de `knowledge/islanding/` (corrección #4), no hardcodeados — el `ExecutionVerifier` es genérico; los umbrales eléctricos son conocimiento versionado (input de los chequeos, cruza con nota 11).

### 1.4 Costura al puerto Sandbox (semilla de la ficha A7)

La forma tomada de E2B/Firecracker → un Protocol `ExecutionHarness` de ~4 métodos, con **CERO microVM este mes** (nota 04 §2/§4; plan maestro §1.E.3: el sandbox no se integra este mes):

```python
class ExecutionHarness(Protocol):
    def prepare(self, spec: HarnessSpec) -> Handle: ...          # materializar entorno (deps pineadas / imagen)
    def run(self, handle: Handle, payload: JsonValue, *,
            deterministic_budget: float) -> RunReport: ...        # ejecución acotada (timeout duro)
    def collect(self, handle: Handle) -> StructuredReport: ...    # juntar chequeos nombrados, SIN interpretar
    def dispose(self, handle: Handle) -> None: ...                # desmontar el aislamiento
```

- **Hoy:** un `InProcessHarness` (pandapower, confiable, in-process) satisface el puerto. El `ExecutionVerifier` habla con el puerto, no con pandapower.
- **Fase 2:** un `MicroVMHarness` (E2B/Firecracker) satisface el **MISMO** puerto para código no confiable — el código del `ExecutionVerifier` **no cambia**; solo cambia el binding del harness (misma lógica de adapter, ADR-008). Ese es el valor de especificar el puerto ahora: el salto a microVM es un drop-in, no un reescrito.
- **Cruce A7:** los _in-toto layouts_ ("la forma esperada del run") son la evolución Fase 2 del `StructuredReport` → semilla del certificado v1. Se **señala** la costura, no se construye.

---

## 2 · Decisión

| Referencia                                                              | Decisión                                                           | Racional                                                                      |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| Anatomía HumanEval / SWE-bench (aislamiento+timeout+colección objetiva) | **inspirar** (patrón; sin dep — son benchmarks)                    | Es la disciplina que hace la ejecución un ancla y no una opinión              |
| **pandapower** (rung 2, factibilidad)                                   | **integrar** (ya decidido nota 04; acá se especifica el checklist) | BSD-3, estándar Python de flujo de potencia; cruza con corpus de Sebas        |
| Puerto `ExecutionHarness` (forma E2B/Firecracker)                       | **inspirar** — forma hoy, microVM Fase 2                           | El puerto se especifica ahora; el sandbox no se integra este mes              |
| in-toto layout como "forma del run"                                     | **inspirar** (semilla A7, Fase 2)                                  | Evolución del `StructuredReport` → certificado v1; se señala, no se construye |
| Guarda de regresión estilo `PASS_TO_PASS`                               | **portar** (patrón)                                                | Para claims con estado previo: no "arreglar" rompiendo otra isla              |

## 3 · Licencias

| Pieza                                      | Licencia                                | Verificado                      | Implicación                                                  |
| ------------------------------------------ | --------------------------------------- | ------------------------------- | ------------------------------------------------------------ |
| pandapower                                 | **BSD-3-Clause**                        | ✅ nota 04 (en vivo 2026-07-02) | Dependencia rung 2; permisiva                                |
| HumanEval (OpenAI) / SWE-bench (Princeton) | MIT (patrones)                          | —                               | Sin dependencia de código — solo anatomía                    |
| E2B / Firecracker                          | ⚠️ verificar antes de depender (Fase 2) | —                               | Forma estudiada; microVM no se integra este mes (nota 04 §3) |

## 4 · Impacto en contrato

**Diseño detrás del puerto (sin acción de freeze):** el `ExecutionVerifier` es un adapter del `Verifier` congelado (freeze §4); el `ExecutionHarness` es un puerto **interno** del adapter (como `RuleBackend` en nota 11), no un contrato del engine. El engine no conoce pandapower ni microVM (ADR-008).

**A ratificar en el freeze** (operación regla 4 — coordinación, NO se editó el freeze):

1. **`method:"execution"` ya existe** en la unión (nota 03 §1.2) con la forma exacta `{harness, input_digest, checks[], runtime_ms, environment}` — este adapter la **usa tal cual**. Aditivo menor: un flag `timed_out` (o un `check` con `passed:null`/`status:"inconclusive"`) para que el timeout sea representable sin colapsarse a `fail`. Semántica de nota 03 §1.4 sobre la forma congelada.
2. **Granularidad por isla**: `subject.step_id = island_id` — ya soportado por el contrato (freeze §4 subject con `step_id?`); conviene un test de que un run de islanding emite N attestations de ejecución (una por isla) alineadas al `verification` por-isla del freeze §9.
3. **`ExecutionHarness` como puerto interno** — es diseño de adapter, NO contrato del engine; se documenta acá como semilla A7. No toca invariantes ni esquema.

## 5 · Reconciliación contra la base lógica

- **PR2 / INV-2 (el verificador nunca es un modelo):** INTACTO — la ejecución observa la realidad ("la realidad no negocia", nota 04); no hay modelo en el loop. El adapter vive en `verification/`, no importa `serving`.
- **AX3 (mediación de modelo · sandboxing exigible, no aspiracional):** REALIZADO estructuralmente — el puerto `ExecutionHarness` es exactamente lo que hace "el sandboxing exigible en vez de aspiracional" (racional de AX3 en `invariants.md`): cuando código no confiable corra (Fase 2), lo hace detrás del puerto, aislado.
- **Nota 03 §1.4 (tri-estado):** REALIZADO — timeout/no-convergencia → `inconclusive`, jamás un `fail` que finja información que no hay.
- **Inv-E:** INTACTO — un chequeo de factibilidad que pasa NO autoriza egreso; informa run + certificado.
- **Ninguna referencia contradice la base lógica.** HumanEval/SWE-bench son fuente de anatomía; su lección (ejecutar y observar objetivamente) confirma la escalera, no la contradice.
