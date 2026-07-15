# Nota 06 — Soluciones ganadoras de quantathons pasadas: análisis de repos, patrones y licencias

**Ítem del plan (§4, Sebas):** cerrar el pendiente №5 del README del directorio — "Soluciones ganadoras de quantathons pasadas: solo links (nota 00 §5), sin análisis". Esta nota analiza los cuatro repos linkeados en la nota 00 §5 y los ganadores concretos minados desde ellos.
**Fecha:** 2026-07-14 · **Estado:** investigación de consolidación (Dylan) — pendiente validación y ratificación de Sebas
**Fuentes:** repos `MauriceDHanisch/ethz_qhack_24`, `XanaduAI/QHack2023`, `XanaduAI/QHack2022`, `CDL-Quantum/Hackathon2020` — READMEs, árboles y licencias **verificados en vivo 2026-07-14 vía `gh api`**; ganadores de QHack 2023 desde el blog oficial de PennyLane ("QHack 2023 Highlights", lista completa con repos) y de QHack 2022 desde el AWS Quantum Technologies Blog — ambos **verificados en vivo 2026-07-14**.

---

## 1 · Patrón / mecanismo

### 1.1 ETH QHack 2024 — `MauriceDHanisch/ethz_qhack_24` (ganador challenge NVIDIA + 1er lugar general)

- **Problema:** Vehicle Routing Problem → QUBO (arXiv:2002.01351) → traducción a Max-Cut (agregando un qubit extra con s=1 para absorber los términos lineales h_i como h_i·s_i·s_extra) → QAOA. Luego pivotean a **escalar Max-Cut en grafos 3-regulares** con divide-and-conquer (arXiv:2205.11762).
- **Stack:** NVIDIA CUDA-Q (simulación GPU, 2×A100), **Gurobi como baseline exacto**, Python plano (src/ = 4 archivos), resultados en CSV.
- **Resultados:** Max-Cut exacto (100% del óptimo Gurobi) hasta 26 qubits; 260× speedup GPU vs CPU; divide-and-conquer hasta 64 qubits manteniendo ~80% del óptimo.
- **Formato de entrega (esto es lo que ganó, tanto como la técnica):** `Final_Submission.ipynb` (UN notebook final ejecutable) + `FINAL_QHACK.pptx` (la presentación DENTRO del repo) + `results/` (CSVs congelados) + `src/` mínimo + README que narra problema→método→resultados con referencias numeradas.
- **Honestidad explícita en el README:** _"there is `no guarantee of quantum advantage`"_ — lo dicen textual, con formato de énfasis, y ganaron igual. La honestidad científica no restó puntos; estructuró la narrativa.

### 1.2 QHack 2023 — `XanaduAI/QHack2023` (repo organizador; ganadores minados del blog de PennyLane)

El repo del link de la nota 00 §5 es **andamiaje del evento** (las submissions viven como issues que apuntan a repos de los equipos; sin código propio). Ganadores relevantes para CHIMERA (lista completa verificada en el blog oficial):

| Equipo                                    | Proyecto                                                                                         | Relevancia CHIMERA                                                                                                 | Licencia del repo                   |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ | ----------------------------------- |
| **Avocados** (3º QC-Today + top-3 Braket) | "Wisely Encoding Constrained Combinatorial Optimization Problems on Quantum Devices" (portfolio) | **la más alta**: manejo de restricciones en QUBO — el tema exacto de la Ruta A/B (nota 02 §1.3) es tópico premiado | ⚠️ sin LICENSE (verificado en vivo) |
| **Durchmusterung** (2º NVIDIA)            | QSVM + QCNN para clasificación estelar                                                           | patrón completo del Reto 2: kernel cuántico sobre dataset real con baseline                                        | **Apache-2.0** (verificado en vivo) |
| **jetix** (1º Química + top-3 Braket)     | Molecular Energy Landscapes (VQE/HEA para carbon capture)                                        | patrón del Reto 3: VQE con narrativa de impacto                                                                    | **MIT** (verificado en vivo)        |
| Qumpula Quantum (1º Híbrido)              | "MatriQ" (multiplicación de matrices, estilo AlphaTensor cuántico)                               | menor                                                                                                              | ⚠️ sin LICENSE                      |

### 1.3 QHack 2022 — `XanaduAI/QHack2022` (repo organizador; ganadores vía AWS Quantum blog)

Mismo carácter: andamiaje (coding challenges + open hackathon por issues; sin LICENSE en el repo). Ganadores del Braket Challenge (los documentados públicamente con detalle): **Quantum RNA folding** (QUBO resuelto por annealing en D-Wave Advantage, extendiendo Fox et al. 2021 con un modelo de puentes de hidrógeno — mejor accuracy que el trabajo previo publicado), **quantum autoencoders para detección de anomalías** (mejor experimento en simuladores) y **optimización de workflows de datos en cloud** (más creativo). Patrón visible: formular como QUBO, ejecutar en hardware/simulador, y **compararse contra literatura previa publicada, no contra un strawman**.

### 1.4 CDL Quantum Hackathon 2020 — `CDL-Quantum/Hackathon2020`

- **Formato:** mono-repo con los 16 proyectos de equipos (24 h) como directorios; challenges de D-Wave (QUBO híbrido a escala), Xanadu (GBS/QML), IBM Q y Zapata (benchmarking de componentes VQA en Orquestra).
- **El dato de gobernanza más útil:** la licencia MIT era **regla del evento**, textual del README: _"teams will need to upload their code to a repository under MIT License"_ — por eso es de los pocos corpus de hackathon completos y legalmente reutilizables.
- **Criterios de judging publicados:** dificultad técnica, creatividad, utilidad/potencial de negocio, calidad de presentación — los cuatro ejes que un demo debe cubrir, escritos por los organizadores.

### 1.5 Patrones comunes de los ganadores (síntesis)

1. **Un problema, un pipeline cerrado de punta a punta:** problema → formulación (QUBO/Hamiltoniano) → circuito → métrica contra referencia. Nadie ganó con dos problemas a medias. (Coincide con la recomendación estratégica del doc CHIMERA §0 que la nota 00 §5 ya intuía.)
2. **Baseline clásico fuerte con óptimo exacto donde alcanza:** Gurobi (ETH), FCI/literatura (química), trabajo previo publicado (RNA folding). La métrica ganadora es "% del óptimo", no "funciona".
3. **Honestidad explícita sobre los límites cuánticos** — el ganador general de ETH niega quantum advantage en su propio README. El jurado técnico premia la claridad, no el hype.
4. **Reproducibilidad material:** UN notebook final + resultados congelados (CSV) + la presentación dentro del repo. El repo ES el entregable; el pitch solo lo narra.
5. **La narrativa de escala se construye sobre validación en chico:** exacto ≤26 qubits primero, divide-and-conquer a 64 después — nunca al revés.
6. **El manejo de restricciones/factibilidad es tema premiado recurrente** (Avocados 2023, RNA folding 2022, y REGRID 2026 en la nota 05): CHIMERA compite exactamente en la conversación donde los jurados ya están mirando.

**Implicación para el demo de CHIMERA:** el diferenciador de verificación no es un extra sobre el patrón ganador — **ES el patrón ganador, institucionalizado**. Los ganadores hacen a mano (baseline exacto, honestidad, evidencia congelada, trazabilidad de resultados) lo que el engine hace por contrato (`ExactSolverVerifier`, `evidence`, event log append-only). El formato de entrega a copiar es el de ETH: notebook único ejecutable + CSVs de evidencia + presentación en el repo.

---

## 2 · Decisión

| Referencia                                                                          | Decisión                                              | Racional                                                                                                                                                       |
| ----------------------------------------------------------------------------------- | ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ethz_qhack_24` — formato de entrega (notebook final + results/ CSV + pptx en repo) | **integrar** al plan del demo                         | es el formato del ganador general; costo cero, encaja con la evidencia congelada que el engine ya produce                                                      |
| `ethz_qhack_24` — patrón "Gurobi baseline + % del óptimo"                           | **inspirar** (ya cubierto)                            | nuestro equivalente es brute force n≤16 / CP-SAT + `approximation_ratio` (notas 00 §1.4, 04); Gurobi es propietario — no adoptar                               |
| `ethz_qhack_24` — código CUDA-Q / divide-and-conquer                                | **descartar** (demo)                                  | CUDA-Q está fuera del stack (nota 03 §5, Fase 2); divide-and-conquer no aplica a n≤14                                                                          |
| `XanaduAI/QHack2023` y `QHack2022` (repos org)                                      | **descartar como fuente de código; usar como índice** | sin LICENSE (verificado) y sin código propio; su valor es el mapa de ganadores                                                                                 |
| Avocados — encoding de restricciones (QHack 2023)                                   | **inspirar, NO portar**                               | tema idéntico a la ablación Ruta A/B, pero el repo no tiene licencia → prohibido copiar código (regla open-core); leer las ideas, implementar desde la nota 02 |
| Durchmusterung — pipeline QSVM (Apache-2.0)                                         | **inspirar** para el Reto 2                           | mismo patrón kernel+dataset real+baseline de la nota 02 §2; licencia sí permitiría vendorizar, pero no hace falta — PennyLane `qml.kernels` ya lo cubre        |
| `CDL-Quantum/Hackathon2020`                                                         | **inspirar** (formato + criterios de judging)         | corpus MIT completo de proyectos de 24 h; útil para calibrar el nivel esperado y los 4 ejes de evaluación                                                      |
| Honestidad explícita tipo ETH ("no guarantee of quantum advantage") en README/pitch | **integrar**                                          | coincide con la línea "Power of data"/anti quantum-washing (nota 00 §2.3.4 y §7.5) — ahora con evidencia de que gana hackathons                                |

---

## 3 · Licencias

Verificadas en vivo 2026-07-14 contra el LICENSE de cada repo (vía `gh api repos/{owner}/{repo}/license`):

| Repo                                                 | Licencia                           | Nota                                   |
| ---------------------------------------------------- | ---------------------------------- | -------------------------------------- |
| `MauriceDHanisch/ethz_qhack_24`                      | **MIT**                            | reutilizable con atribución            |
| `XanaduAI/QHack2023`                                 | **sin LICENSE** (404)              | copyright por defecto → no copiar nada |
| `XanaduAI/QHack2022`                                 | **sin LICENSE** (404)              | ídem                                   |
| `CDL-Quantum/Hackathon2020`                          | **MIT** (regla del evento, README) | corpus completo reutilizable           |
| `edenian/Durchmusterung`                             | **Apache-2.0**                     | reutilizable                           |
| `Gopal-Dahale/Molecular-Energy-…-Carbon-Capture`     | **MIT**                            | reutilizable                           |
| `alejomonbar/clever-portfolio-optimization-encoding` | **sin LICENSE** (404)              | solo lectura/inspiración               |
| `valterUo/QHack23-MatriQ`                            | **sin LICENSE** (404)              | solo lectura/inspiración               |

**Regla derivada (cierra la advertencia del encabezado de la nota 00):** la recomendación de "vendorizar código de demos de terceros" queda acotada a repos con licencia permisiva verificada (MIT/Apache-2.0). Un repo de hackathon **sin archivo LICENSE es copyright cerrado por defecto** aunque sea público — de ahí solo se toman ideas, nunca código.

---

## 4 · Impacto en contrato

- **Ninguno directo** — esta nota es de formato, estrategia y licencias, no de formulación.
- Refuerza (sin modificar) los campos ya propuestos: `approximation_ratio` (nota 04) es exactamente la métrica que los ganadores reportan; `evidence` congelada + event log son la versión por-contrato del "results/ CSV" de ETH.
- El formato de entrega (notebook único + evidencia + presentación en repo) toca el **plan del demo**, no el contract freeze.

---

## 5 · Reconciliación contra la base lógica

- **Sin contradicciones con `docs/invariants.md`:** nada de lo adoptado toca gateway, verificación, egreso ni eventos. El único punto de contacto es indirecto: los patrones ganadores №2–4 (baseline exacto, honestidad, evidencia reproducible) son la versión manual de los Invariants 2 y 5 — validación externa de que la arquitectura apunta a lo que los jurados premian.
- **Regla open-core / licencias:** la sección 3 convierte el "⚠️ sujeto a verificación de licencia previa" del encabezado de la nota 00 en una regla operativa (solo vendorizar desde MIT/Apache verificado). Coherente con la postura de la nota 03.
- **ADR-029:** los nombres de dominio de los proyectos analizados (VRP, RNA, estelar) quedan en esta nota de KB; nada entra a manifiestos.
- **Ratificación de Sebas: PENDIENTE** — en particular la adopción del formato de entrega tipo ETH para el demo y la regla de licencias de §3.
