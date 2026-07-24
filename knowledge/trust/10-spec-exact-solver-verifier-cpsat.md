# Nota 10 — Spec del `ExactSolverVerifier` (CP-SAT): status→verdict, determinismo, tolerancias, formulación de referencia

**Ítem del plan (§4 Dylan / ficha A1):** Anclas duras — de decisión a diseño de adapter. Parte 1: el adapter rung 1 (verificación diferencial contra CP-SAT).
**Fecha:** 2026-07-07 · **Estado:** **EJECUTADA fielmente (2026-07-24)** — `engine/src/blite/verification/exact_solver.py`: `map_optimality_verdict` (error≠fail, contradicción candidato-mejor-que-óptimo), determinismo `workers=1`/`random_seed=1`, ruptura de simetría `x0=0`, XOR linealizado, `verifier_params_digest`. Desviación consciente documentada en el código: siempre resuelve (el `Differential` congelado exige `status` real), en vez del paso-1 "energía mentida sin resolver" de §1.1. Los vectores G1–G6 viven como tests.
**Fuentes:** nota 03 §1.2 (forma `evidence` `differential`) y §1.4 (verdict tri-estado) · nota 04 §1.1 (CP-SAT como ancla estrella, diversidad) · `contract-freeze.md` §4 · anexo de canonicalización §5 (`claim_digest`) · docs OR-Tools CP-SAT (`CpSolverStatus`, parámetros de determinismo) · óptimos de Max-Cut calculados a mano · `CHIMERA-Harness-Metodologias.md` §4.4/§6 (ubicación del diferencial cuántico-clásico en escalón 5; verify Reto 1 → OR-Tools rung 1).

---

## 1 · Patrón / mecanismo

### 1.1 Qué verifica y cómo (verificación diferencial, rung 1)

El `ExactSolverVerifier` es el adapter rung 1 del puerto `Verifier` (nota 03 §1). No confía en el número que reportó el proponente (heurística cuántica/clásica): **resuelve el MISMO problema de forma exacta e independiente con CP-SAT (OR-Tools) y compara**. El claim que ataca es de la forma _"la asignación `x` es óptima para la instancia `I`"_ (o su variante más débil _"`x` alcanza valor objetivo `E`"_).

Tres pasos, todos deterministas:

1. **Recomputar el objetivo del candidato** directamente: `candidate_value = objective(x, I)`. Barato y sin solver — ya es un chequeo (que el `energy` reportado coincida con la asignación reportada; si no coincide, el proponente mintió sobre su propio número y el verdict es `fail` sin necesidad de resolver nada).
2. **Resolver `I` a optimalidad con CP-SAT** → `reference_value` + `solver_status` (+ cota si no probó óptimo).
3. **Comparar** dentro de tolerancia (§1.4) y **mapear** `(status × claim_type × comparación) → verdict` (§1.2).

El **segundo ancla independiente** para instancias chicas es la **fuerza bruta ≤ ~20 variables** (nota 04): enumeración completa, trivialmente auditable. Los vectores de prueba (§1.6) se validan por fuerza bruta — no por CP-SAT — de modo que CP-SAT queda a su vez verificado contra la enumeración. Esto es el principio de diversidad de nota 04 §1.1 llevado al propio verificador: dos anclas de rung 1 (CP-SAT exacto + enumeración) deben coincidir.

> **Aclaración de nombre — reconciliación con `CHIMERA-Harness-Metodologias.md` §4.4.** "Verificación diferencial" en esta nota = contraste contra un solver **exacto e independiente** (el oráculo) → **rung 1**. NO es lo mismo que la "verificación diferencial cuántico-vs-clásico" que ese documento ubica en el **escalón 5**: dos heurísticas **sin oráculo** que convergen son **consenso** (rung 5), y por construcción → `GuardrailSignal`, **no** `Attestation` (notas 03 §1.1 / 04 §1.3). El nombre está sobrecargado; **el tipo de ancla decide el rung**: oráculo exacto (rung 1) vs muestras que coinciden (rung 5). Ambos documentos coinciden bajo esta distinción — se anota, no se cede (el freeze §4 manda). Práctica: si el "diferencial" del run es cuántico-vs-clásico, ese paso es rung 5 (guardrail) y necesita ADEMÁS este adapter (CP-SAT exacto) para tener un ancla rung 1.

### 1.2 El mapeo EXACTO `CpSolverStatus → verdict` (el núcleo de la ficha)

Los 5 estados reales de CP-SAT (`CpSolverStatus`) son `OPTIMAL`, `FEASIBLE`, `INFEASIBLE`, `MODEL_INVALID`, `UNKNOWN`. El verdict tri-estado (nota 03 §1.4) NO es una biyección con el status: depende del status, del `claim_type` (¿optimalidad o factibilidad?) y de la comparación candidato↔referencia.

| `solver_status`                                                | claim = **optimalidad**                                                | claim = **factibilidad**                                 | Notas                                                                                                                                                                           |
| -------------------------------------------------------------- | ---------------------------------------------------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `OPTIMAL` · `candidate == reference` (±tol)                    | **`pass`** (el candidato ES óptimo)                                    | `pass`                                                   | El caso feliz del demo                                                                                                                                                          |
| `OPTIMAL` · `candidate` peor que `reference` (más allá de tol) | **`fail`** (`gap = reference − candidate`; el candidato es sub-óptimo) | `pass` si es factible; el objetivo no lo decide          | La optimalidad reclamada es falsa, pero puede seguir siendo una solución válida                                                                                                 |
| `OPTIMAL` · `candidate` **mejor** que el óptimo probado        | **`error` (fail-loud)**                                                | **`error`**                                              | Contradicción: CP-SAT PROBÓ que ese es el máximo. Un valor mejor ⇒ el modelo del verificador difiere del objetivo real (clase `MODEL_INVALID`). Jamás `pass` silencioso         |
| `FEASIBLE` (timeout con incumbente, óptimo NO probado)         | **`inconclusive`** — es **cota**, no ancla                             | `pass` (hay solución factible ⇒ factibilidad demostrada) | **La respuesta explícita de la ficha** — ver §1.3                                                                                                                               |
| `INFEASIBLE`                                                   | **`error` (fail-loud)**                                                | **`error`**                                              | Hay un candidato `x` en mano ⇒ el problema NO es infactible. Un QUBO/Max-Cut sin restricciones nunca es `INFEASIBLE`: su aparición es bug de modelado, no verdict del candidato |
| `MODEL_INVALID`                                                | **`error`** (no emite `Attestation`)                                   | **`error`**                                              | Falla del verificador (modelo mal construido), no del candidato. Un verificador roto NO produce verdict: levanta excepción                                                      |
| `UNKNOWN` (sin incumbente, sin prueba de infactibilidad)       | **`inconclusive`**                                                     | **`inconclusive`**                                       | Sin información; típicamente timeout sin encontrar nada                                                                                                                         |

Regla estructural: **`error` ≠ `fail`**. `fail` es un verdict sobre el candidato (se persiste como `Attestation` con `verdict:"fail"`); `error` es una falla del proceso de verificación (`MODEL_INVALID`, contradicciones) que **no** produce `Attestation` — levanta y se registra como incidente del run. Confundirlos sería reportar un bug del verificador como si el candidato hubiera fallado.

### 1.3 `FEASIBLE` por timeout = `inconclusive` para optimalidad, y **cota** en la evidencia

La pregunta literal de la ficha. Respuesta: para un claim de **optimalidad**, `FEASIBLE` es `inconclusive` — CP-SAT encontró una solución pero **no probó** que sea la mejor. NO es `pass` (sería sobre-afirmar) ni `fail` (el candidato podría ser óptimo; solo que no lo probamos dentro del presupuesto). Esto materializa la honestidad de nota 03 §1.4 y el precedente AWS AR (`TOO_COMPLEX`, nota 04 §1.2).

Pero `inconclusive` **no descarta la información**: la evidencia registra la **cota** — `objective_bound` (`BestObjectiveBound()`, el mejor valor alcanzable) y `best_objective` (`ObjectiveValue()`, el incumbente). El gap de optimalidad = `|objective_bound − best_objective|`. El Studio muestra _"no se pudo probar óptimo dentro del presupuesto; mejor cota = B, gap = g"_ — honesto y accionable, no un `pass` disfrazado. Si el `candidate_value` iguala o supera la cota, el certificado lo dice; sigue siendo `inconclusive` para optimalidad.

Un claim más débil de **factibilidad** SÍ puede ser `pass` bajo `FEASIBLE` (existe una solución factible) — pero la factibilidad de una _isla_ propuesta se ancla mejor en rung 2 (ejecución/pandapower, nota 12), no aquí. Este adapter es para el claim de optimalidad del corte.

### 1.4 Determinismo reproducible (workers=1, seed, tiempo DETERMINISTA)

Un verdict de rung 1 debe ser **reproducible byte-a-byte entre máquinas**, o el certificado no vale offline. Tres parámetros no negociables al construir el solve de referencia (van al `params_digest` de la evidencia):

1. **`num_search_workers = 1`.** La búsqueda multi-worker de CP-SAT es una carrera entre estrategias; qué solución/orden gana depende del scheduling. Un solo worker fija una búsqueda determinista.
2. **`random_seed` fijo y explícito** (p.ej. `1`) — nunca el default implícito.
3. **`max_deterministic_time` en lugar de `max_time_in_seconds`.** Es la trampa sutil: un presupuesto en **tiempo de reloj** hace que el status dependa de la máquina — una CPU rápida devuelve `OPTIMAL`, una lenta `FEASIBLE` sobre la MISMA instancia ⇒ **verdicts distintos en máquinas distintas** (`pass` vs `inconclusive`). El tiempo determinista de CP-SAT (unidad reproducible de trabajo, no segundos de pared) hace que el punto de corte — y por lo tanto el status y el verdict — sea idéntico en todas partes.

Observación de robustez: para un resultado `OPTIMAL`, el **valor** óptimo es único aunque el argmax no lo sea (puede haber varias asignaciones óptimas). Por eso `pass`/`fail` sobre `OPTIMAL` es machine-independent sin más; solo la **frontera del `inconclusive`** (¿terminó dentro del presupuesto?) necesita tiempo determinista para ser reproducible. Aun así se fijan los tres — un `params_digest` estable es lo que hace la corrida _replayable_ (misma lógica que el `seed` de Hypothesis en nota 03 §1.2).

### 1.5 Tolerancias float para QUBO + formulación Max-Cut→CP-SAT de referencia

**El problema de los floats.** CP-SAT es un solver **entero/CP**; el objetivo de un QUBO son floats (`x^T Q x`). Dos caminos:

- **Max-Cut con pesos enteros:** exacto, `scale = 1`, `abs_tol = 0`. El caso del demo (islanding IEEE con pesos enteros/racionales simples) cae acá casi siempre.
- **QUBO float general:** _escalar y redondear_ a enteros con un factor `S` (p.ej. `10^6`), resolver exacto sobre enteros, des-escalar. El error de redondeo sobre el objetivo está acotado por `(#términos) · (0.5 / S)`; el `abs_tol` de la comparación **debe** ser ≥ esa cota. Regla de spec: elegir `S` tal que el error de redondeo sea **menor que el gap mínimo entre soluciones distintas** de la instancia (su "integralidad" efectiva) — así el escalado no colapsa dos valores objetivamente distintos.

Comparación: `is_match = |candidate_value − reference_value| ≤ max(abs_tol, rel_tol · |reference_value|)` (estilo `math.isclose`; `rel_tol` default `1e-9`). La evidencia registra `scale`, `tolerance` (el `abs_tol`/`rel_tol` usados) y el `gap` residual — un `pass` dentro de tolerancia pero no exacto muestra su residual. **`NaN`/`Inf` en `Q` ⇒ `error` fail-loud** (jamás un objetivo inestable — mismo espíritu que la regla 5 del anexo de canonicalización).

**Formulación Max-Cut → CP-SAT (el solver de referencia para el diferencial).** Grafo con peso `w = (V, E, w_ij)`. Variable binaria `x_i ∈ {0,1}` = lado del nodo `i`. La arista `(i,j)` está cortada sii `x_i ≠ x_j` (XOR). Se linealiza el XOR con una variable de arista `y_ij ∈ {0,1}` y cuatro restricciones que la fuerzan a `x_i XOR x_j` exactamente sobre binarias:

```
maximize  Σ_(i,j)∈E  w_ij · y_ij
subject to  y_ij ≤ x_i + x_j
            y_ij ≤ 2 − x_i − x_j
            y_ij ≥ x_i − x_j
            y_ij ≥ x_j − x_i
            x_i ∈ {0,1},  y_ij ∈ {0,1}
            x_0 = 0                      # ruptura de simetría (ver abajo)
```

- Con `w_ij ≥ 0` bastan las dos cotas superiores (el objetivo empuja `y` hacia arriba); las cuatro se dejan para un modelo **exacto y agnóstico al signo** (pesos negativos, o claims que no sean de maximización).
- **Ruptura de simetría:** el corte es invariante al flip global `x → 1−x`, así que fijar `x_0 = 0` elimina la simetría trivial, **halve** el espacio de búsqueda y devuelve una asignación **canónica** (aporta a §1.4). Se registra en `params`.
- **QUBO↔Max-Cut:** `min x^T Q x` se reduce a Max-Cut por la reducción estándar (nodo ancilla) o se codifica el objetivo QUBO directo en CP-SAT con `Q` escalado a enteros. Para el demo (islanding como Max-Cut) el modelo de arriba es la referencia directa.

### 1.6 Vectores de prueba — grafos chicos con óptimo conocido **a mano**

Óptimos combinatorios calculados por enumeración manual (no por CP-SAT). **Son el gate de la sesión 11**: la implementación que no los reproduzca no entra (mismo rol que los vectores del anexo de canonicalización §6). Pesos unitarios salvo el último. Asignaciones con `x_0 = 0` (canónicas).

| #   | Grafo                   | Aristas                   | **Max-cut (a mano)** | Asignación óptima (`x_0=0`)      | Racional del óptimo                                            |
| --- | ----------------------- | ------------------------- | -------------------- | -------------------------------- | -------------------------------------------------------------- |
| G1  | Triángulo `K3`          | `(0,1)(1,2)(0,2)`         | **2**                | `[0,0,1]` corta `(0,2)(1,2)`     | Ciclo impar: imposible cortar las 3; máximo 2                  |
| G2  | Ciclo `C4`              | `(0,1)(1,2)(2,3)(3,0)`    | **4**                | `[0,1,0,1]` corta las 4          | Bipartito ⇒ se cortan todas                                    |
| G3  | Completo `K4`           | las 6                     | **4**                | `[0,0,1,1]` (split 2–2)          | 2–2 corta `2·2=4`; 1–3 corta 3                                 |
| G4  | Camino `P3` `0–1–2`     | `(0,1)(1,2)`              | **2**                | `[0,1,0]`                        | Bipartito, 2 aristas                                           |
| G5  | `K3` + nodo aislado `3` | `(0,1)(1,2)(0,2)`         | **2**                | `[0,0,1,·]` (nodo 3 indiferente) | Metamórfica nota 03: agregar nodo aislado NO cambia el óptimo  |
| G6  | Triángulo **pesado**    | `(0,1)=1 (1,2)=2 (0,2)=3` | **5**                | `[0,0,1]` aísla el nodo 2        | Aislar el 2: `3+2=5`, mayor que aislar el 0 (`4`) o el 1 (`3`) |

Casos negativos y de frontera derivados de los mismos grafos (verdict esperado):

| Caso                                    | Candidato                         | Status esperado del ref | Verdict esperado                         |
| --------------------------------------- | --------------------------------- | ----------------------- | ---------------------------------------- |
| G1 óptimo                               | `[0,0,1]` (cut 2)                 | `OPTIMAL`, ref 2        | **`pass`**                               |
| G1 sub-óptimo                           | `[0,0,0]` (cut 0)                 | `OPTIMAL`, ref 2        | **`fail`**, `gap=2`                      |
| G2 sub-óptimo                           | `[0,0,1,1]` (cut `(1,2)+(3,0)=2`) | `OPTIMAL`, ref 4        | **`fail`**, `gap=2`                      |
| G6 óptimo                               | `[0,0,1]` (cut 5)                 | `OPTIMAL`, ref 5        | **`pass`**                               |
| «energía mentida»                       | `[0,0,0]` reportando `energy=2`   | — (falla en paso 1)     | **`fail`** (recompute ≠ reportado)       |
| presupuesto agotado en instancia grande | cualquiera                        | `FEASIBLE`, cota `B`    | **`inconclusive`** + `objective_bound=B` |

### 1.7 Forma del `evidence` (discriminante `method:"differential"`, nota 03 §1.2)

```python
{
  "method": "differential",
  "reference": {"solver": "ortools-cpsat", "version": "9.15", "params_digest": "<sha256>"},
  "reference_value": <int|float>,
  "candidate_value": <int|float>,
  "gap": <number>,                 # |candidate − reference|
  "tolerance": {"abs_tol": <number>, "rel_tol": <number>},
  "scale": <int>,                  # factor de escalado entero (1 si pesos enteros)
  "solver_status": "OPTIMAL|FEASIBLE|INFEASIBLE|MODEL_INVALID|UNKNOWN",
  "objective_bound": <number>      # SOLO presente si status==FEASIBLE (la cota)
}
```

`subject = {run_id, step_id?, claim_digest}` con `claim_digest = SHA-256("blite/claim/v1\n" ‖ C(claim))` (anexo §5). El `params_digest` cubre `workers=1`, `random_seed`, `max_deterministic_time`, `scale` y la ruptura de simetría — es lo que hace la verificación replayable.

---

## 2 · Decisión

| Referencia                                                               | Decisión                                                        | Racional                                                                 |
| ------------------------------------------------------------------------ | --------------------------------------------------------------- | ------------------------------------------------------------------------ |
| OR-Tools CP-SAT como solver de referencia rung 1                         | **integrar** (ya decidido nota 04; acá se especifica su USO)    | Apache-2.0, exacto y subsegundo en el tamaño del reto                    |
| Verificación diferencial (candidato ↔ solve exacto independiente)        | **portar** (patrón, sin librería nueva)                         | Es un patrón de uso de OR-Tools, no una dependencia                      |
| Fuerza bruta ≤20 vars como **oráculo de los vectores** y backstop rung 1 | **portar** (utilidad propia trivial)                            | Valida los vectores sin confiar en CP-SAT; auditable por inspección      |
| `max_deterministic_time` sobre `max_time_in_seconds`                     | **portar** (parámetro de CP-SAT)                                | Sin él, el verdict `inconclusive` no es reproducible entre máquinas      |
| Ruptura de simetría `x_0=0` + `workers=1` + `random_seed`                | **portar** (patrones de uso)                                    | Búsqueda determinista + asignación canónica                              |
| Escalar-y-redondear para QUBO float                                      | **portar** (técnica estándar)                                   | CP-SAT es entero; la cota de error va documentada en `scale`/`tolerance` |
| Verdictos estilo AWS AR (`TOO_COMPLEX`)                                  | **inspirar** (colapsados en `inconclusive` + cota en evidencia) | `FEASIBLE`-por-timeout es nuestro `TOO_COMPLEX`                          |

## 3 · Licencias

| Pieza                    | Licencia       | Verificado                      | Implicación                                              |
| ------------------------ | -------------- | ------------------------------- | -------------------------------------------------------- |
| OR-Tools (v9.15, CP-SAT) | **Apache-2.0** | ✅ nota 04 (en vivo 2026-07-02) | Dependencia del grupo de verificación; sin contaminación |
| (fuerza bruta)           | —              | —                               | Utilidad propia, sin dependencia                         |

Sin dependencias nuevas respecto del freeze — esta nota es diseño del adapter detrás del puerto ya congelado.

## 4 · Impacto en contrato

**Diseño detrás del puerto (sin acción de freeze):** el `ExactSolverVerifier` es un adapter del `Verifier` congelado (freeze §4); el engine no conoce OR-Tools directamente (ADR-008). El `params_digest`/`scale`/símetría son detalles del adapter.

**Refinamientos ADITIVOS del `evidence.differential` a ratificar en el freeze** (operación regla 4: un cambio de contrato va a discusión de freeze, no se edita solo — se listan como coordinación, NO se tocó el freeze):

1. **`solver_status` debe usar el enum REAL de CP-SAT** `OPTIMAL|FEASIBLE|INFEASIBLE|MODEL_INVALID|UNKNOWN`. La forma en nota 03 §1.2 lo simplificó a `"OPTIMAL|FEASIBLE|TIMEOUT"`; `TIMEOUT` no es un `CpSolverStatus` y oculta `INFEASIBLE`/`MODEL_INVALID`, que deben mapear a `error` (no a un verdict). Corrección del literal.
2. **Campos aditivos opcionales:** `objective_bound` (presente solo en `FEASIBLE`), `scale`, y `tolerance` como objeto `{abs_tol, rel_tol}` en vez de escalar. Aditivos; no rompen consumidores existentes.
3. **Distinción `error` vs `fail`:** un `MODEL_INVALID`/`INFEASIBLE`/contradicción NO produce `Attestation` — levanta. El contrato de `Verifier.verify()` debería documentar que puede **abstenerse por error de proceso** (excepción), distinto de emitir `verdict:"fail"`. Semántica, no campo.

Ninguno cambia `AnchorKind` ni el puerto; son precisiones de la unión discriminada `evidence` que la implementación de la sesión 11 va a necesitar.

## 5 · Reconciliación contra la base lógica

- **PR2 / INV-2 (el verificador nunca es un modelo):** INTACTO — CP-SAT es un solver, no un modelo; rung 1 legítimo. El adapter vive en `verification/` y no importa `serving`.
- **Nota 03 §1.4 (verdict tri-estado):** REALIZADO — el mapeo `FEASIBLE→inconclusive` (para optimalidad) es la abstención honesta hecha regla; `error` fail-loud sobre `MODEL_INVALID`/contradicción impide el `pass` mentiroso.
- **Inv-E:** INTACTO — ningún verdict (ni `pass`) satisface un egreso; solo informa run + certificado.
- **D20 (confianza = propiedad del proceso):** el `params_digest` + tiempo determinista hacen el verdict **reproducible**, no anecdótico.
- **Ninguna referencia contradice la base lógica.** El único hallazgo "incómodo" (candidato _mejor_ que el óptimo probado ⇒ `error`) REFUERZA el fail-loud: preferimos gritar una contradicción a pasarla por alto.
