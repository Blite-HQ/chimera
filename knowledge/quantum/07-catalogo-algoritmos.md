# Nota 07 — Catálogo de algoritmos (clásicos y cuánticos) del que elige el planner

**Ítem del plan:** cerrar el gap "catálogo amplio de algoritmos" detectado en el bootcamp — la Quantathon CR insiste en "múltiples algoritmos" por reto, y hasta hoy el knowledge tenía recetas profundas (notas 01–02) pero ningún catálogo transversal del que un planner pueda ELEGIR.
**Fecha:** 2026-07-17 · **Estado:** investigación de consolidación (Dylan) — ratificación final de Sebas.
**Fuentes:** `docs/convergencia-diseno-v32.md` §2.1 (clases decisorias FORMAL_EXACT/EXECUTION/GROUND_TRUTH/PROPERTY_RULE/CONSENSUS_REPLICATION/HUMAN_EXPERT + niveles AL0–AL4 — el vocabulario de verificación de esta nota) · notas `quantum/01–04` (teoría, recetas, stack, estadística) · `knowledge/islanding/01-corpus-benchmarks.md` (doble ancla CP-SAT + fuerza bruta) · Egger, Mareček, Woerner — _Warm-starting quantum optimization_ — arXiv:2009.10095, Quantum 5, 479 (2021) — **verificado en vivo 2026-07-17** · Herrman et al. — _Multi-angle Quantum Approximate Optimization Algorithm_ — arXiv:2109.11455, Sci. Rep. (2022) — **verificado en vivo 2026-07-17** · Bravyi, Kliesch, König, Tang — _Obstacles to variational quantum optimization from symmetry protection_ (introduce RQAOA) — Phys. Rev. Lett. 125, 260505 (2020) — **verificado en vivo 2026-07-17** · Zhou et al. arXiv:1812.01041 (INTERP) y Goemans–Williamson 1995 (cota 0.878) — ya citados y referenciados en la nota 01 (no se re-verifican).

---

## 1 · Patrón / mecanismo

### 1.1 Qué es este catálogo y qué NO es

La plataforma es **agnóstica**: los algoritmos (cuánticos o clásicos) solo PROPONEN candidatos; las
anclas no-modelo VERIFICAN (INV-2/PR2). Este catálogo es la mitad proponente hecha explícita: por
**clase de problema**, la lista de algoritmos candidatos con su madurez honesta, su estado en
Chimera y — la columna que ningún catálogo de quantathon trae — **el ancla de verificación que le
corresponde**, expresada en el vocabulario vigente de la spec v3.2 (clase decisoria → nivel AL).

No es un ranking ("el mejor algoritmo") ni una promesa ("ventaja cuántica"): en instancias chicas
el clásico exacto gana o empata siempre (nota 01 §7), y eso está escrito en la columna de madurez
sin maquillaje. El "múltiples algoritmos" del bootcamp sale casi gratis en esta arquitectura,
porque cambiar de proponente no toca la verificación (ver §1.7).

**Regla transversal fail-loud** (hereda de trust/10 §1.2 y nota 01 §5): cualquier proponente que
reporte un valor _mejor_ que el óptimo probado por el ancla FORMAL_EXACT ⇒ **bug del proceso**,
jamás un descubrimiento. Aplica idéntica a QAOA, a neal, a Kernighan–Lin y a VQE (versión química:
`E < E_FCI − tol` ⇒ bug).

### 1.2 Clase A — Optimización combinatoria (Reto 1: islanding · **nuestro reto**)

El problema canónico: grafo ponderado → QUBO/Ising (nota 02 §1). Todo lo de esta tabla consume la
misma formulación y se verifica contra el mismo corpus (`islanding/01`).

| Algoritmo                                               | Qué resuelve                                                                       | Cuándo usarlo / cuándo NO                                                                                                                                                                | Madurez NISQ honesta                                                                                   | Estado en Chimera                                                              | Ancla (clase decisoria)                                                                             |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| **CP-SAT / ILP exacto** (OR-Tools)                      | óptimo PROBADO de QUBO/Max-Cut entero                                              | siempre que n lo permita (≤~30 aquí); NO cuando la instancia excede el presupuesto determinista                                                                                          | N/A (clásico maduro)                                                                                   | **implementado** (generador del corpus, `islanding/01` §1.4; spec en trust/10) | ES el ancla: FORMAL_EXACT → AL4 con checker independiente                                           |
| **Fuerza bruta / enumeración**                          | óptimo por enumeración 2^(n−1)                                                     | n ≤ 14; NO más allá (explosión exponencial)                                                                                                                                              | N/A                                                                                                    | **implementado** (ancla 2 del corpus)                                          | el checker independiente que habilita AL4 (convergencia §2.1)                                       |
| **QAOA** (p ∈ {1,2})                                    | muestreo sesgado hacia cortes altos del H_C diagonal                               | el proponente cuántico del demo; NO esperar superar al clásico en n=8–30                                                                                                                 | garantía p=1 ≈ 0.6924 en 3-regulares; sin ventaja probada; ≤14 qubits = simulación exacta (nota 03 §7) | **recetado** (nota 02 §1) → se implementa este mes                             | FORMAL_EXACT (corpus) + EXECUTION (pandapower, trust/12) + PROPERTY_RULE (metamórficas, nota 04 §5) |
| **QAOA warm-start** (Egger et al., arXiv:2009.10095)    | inicializa QAOA desde la relajación continua del QUBO (o una solución redondeada)  | cuando QAOA vanilla converge mal; NO en el demo mínimo (complejidad extra sin narrativa)                                                                                                 | hereda garantías clásicas de la relajación; literatura sólida (Quantum 2021)                           | **catalogado** (ablación stretch)                                              | las mismas del QAOA — el ancla no cambia con la variante                                            |
| **QAOA INTERP** (Zhou et al., arXiv:1812.01041)         | semillas de parámetros: extrapolar ángulos de p−1 hacia p                          | siempre que se corra p ≥ 2 (convergencia rápida y reproducible); sin contra conocida a esta escala                                                                                       | heurística estándar de la literatura                                                                   | **recetado** (nota 01 §7) → acompaña al QAOA del mes                           | las mismas del QAOA                                                                                 |
| **RQAOA** (Bravyi et al., PRL 125, 260505)              | reduce el grafo recursivamente usando QAOA como subrutina para fijar correlaciones | grafos donde QAOA p=1 se estanca por simetría; NO este mes (complejidad ≫ ganancia en n≤30)                                                                                              | supera a QAOA nivel-1 en las familias estudiadas; sigue siendo heurística                              | **catalogado**                                                                 | las mismas del QAOA                                                                                 |
| **MA-QAOA** (Herrman et al., arXiv:2109.11455)          | un ángulo por término (no por capa): más parámetros, menos profundidad             | cuando la profundidad es el cuello (hardware real); NO en simulador exacto (no hay cuello)                                                                                               | +33% de ratio en una familia de Max-Cut; 1 capa MA ≈ 3 capas vanilla                                   | **catalogado**                                                                 | las mismas del QAOA                                                                                 |
| **Recocido simulado** (clásico, vía `neal` sobre Ising) | heurística térmica sobre el MISMO BQM                                              | tercer baseline de diversidad en 6 líneas (nota 03 idiom 5); NO como ancla (no prueba nada)                                                                                              | N/A (clásico maduro); exige `seed` explícita                                                           | **recetado** (nota 03 §5, candidato → se adopta como baseline del mes)         | FORMAL_EXACT (corpus) — mismo óptimo, misma vara                                                    |
| **Kernighan–Lin** (NetworkX)                            | heurística de intercambio para particionamiento balanceado                         | baseline clásico de una línea; balance de cardinalidad gratis; NO da garantía de calidad                                                                                                 | N/A (1970, madurísimo)                                                                                 | **recetado** (nota 03 §6 lo lista como baseline)                               | FORMAL_EXACT (corpus) + EXECUTION (mismos chequeos post-hoc)                                        |
| **Particionamiento espectral** (vector de Fiedler)      | bisección vía el segundo autovector del Laplaciano                                 | baseline determinista sin azar (bueno para replay); NO optimiza el corte ponderado directamente                                                                                          | N/A                                                                                                    | **catalogado**                                                                 | FORMAL_EXACT (corpus)                                                                               |
| **Goemans–Williamson SDP**                              | relajación semidefinida + redondeo aleatorio; **garantía 0.878** del óptimo        | **BASELINE OBLIGATORIO del enunciado oficial (2026-07-18)** vía CVXPY (herramienta oficial del C1); la brecha QAOA-vs-GW se reporta como parte de las limitaciones honestas obligatorias | N/A (clásico, JACM 1995); el número 0.878 ya calibra el pitch (nota 01 §7)                             | **a implementar este mes (obligatorio por enunciado)**                         | FORMAL_EXACT donde el corpus alcanza; su propia cota es PROPERTY_RULE sobre el certificado del SDP  |
| **Greedy Max-Cut**                                      | asignación voraz nodo a nodo al lado que más corte suma                            | **BASELINE OBLIGATORIO del enunciado oficial (2026-07-18)**, ratio ~0.5 — el piso que todo lo demás debe superar; NO como ancla (no prueba nada)                                         | N/A (clásico elemental)                                                                                | **a implementar este mes (obligatorio por enunciado)**                         | FORMAL_EXACT (corpus) — mismo óptimo, misma vara                                                    |
| **Quantum annealing en hardware** (D-Wave)              | Ising nativo en QPU de recocido                                                    | NO: rompe el air-gap (misma causa que Braket, nota 03 §5); `neal` cubre la formulación sin hardware                                                                                      | hardware real con ruido/embedding no trivial                                                           | **descartado con causa** (air-gap)                                             | —                                                                                                   |

### 1.3 Clase B — Clasificación / ML (Reto 2: potabilidad de agua)

| Algoritmo                                               | Qué resuelve                                                                  | Cuándo usarlo / cuándo NO                                                                                                                   | Madurez NISQ honesta                                               | Estado en Chimera                                                     | Ancla (clase decisoria)                                                                                                                  |
| ------------------------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **Quantum kernel (fidelidad) + SVM**                    | matriz de Gram cuántica K(x,x′)=\|⟨φ(x′)\|φ(x)⟩\|² alimentando un SVM clásico | el camino cuántico principal del reto (~19 k circuitos, nota 02 §2.2); NO con muchos qubits/capas (concentración exponencial, nota 01 §9.6) | competitivo en datasets chicos; ninguna ventaja general demostrada | **recetado** (nota 02 §2)                                             | GROUND_TRUTH (test set held-out = corpus `curated_internal` → máx AL3) + PROPERTY_RULE (PSD, diagonal, etiquetas barajadas — nota 04 §5) |
| **VQC** (circuito variacional)                          | clasificador entrenado por parameter-shift                                    | solo como stretch: ~360 k circuitos vs ~19 k del kernel (nota 02 §2.4); NO como camino principal                                            | entrenable a 4 qubits; barren plateaus al escalar (nota 01 §10)    | **recetado como stretch** (nota 02 §2.4)                              | GROUND_TRUTH + CONSENSUS_REPLICATION (réplicas con seeds pinned → AL2)                                                                   |
| **QNN** (Estimator/SamplerQNN, qiskit-machine-learning) | redes neuronales con capas cuánticas                                          | variante del VQC con más ingeniería; NO aporta sobre el VQC a 4 qubits                                                                      | mismos límites del VQC (barren plateaus, costo de gradiente)       | **catalogado**                                                        | las mismas del VQC                                                                                                                       |
| **SVM clásico (RBF)**                                   | el baseline directo: mismo pipeline, kernel gaussiano                         | SIEMPRE — sin él la comparación cuántico-vs-clásico no existe (McNemar, nota 04 §6)                                                         | N/A (clásico maduro)                                               | **recetado** (baseline obligatorio del pipeline, sklearn ya en stack) | GROUND_TRUTH (mismo test set, mismas métricas)                                                                                           |
| **Random Forest**                                       | baseline no lineal + selector de las k=4 features (importancias)              | doble rol ya recetado; NO tocar el pipeline de features sin re-registrar seeds                                                              | N/A                                                                | **recetado** (nota 02 §2.1)                                           | GROUND_TRUTH + PROPERTY_RULE (detector de leakage por etiquetas barajadas)                                                               |
| **XGBoost**                                             | baseline de boosting (suele ser el techo clásico en tabulares)                | si se quiere el baseline clásico MÁS fuerte para la honestidad del claim; NO es dependencia del stack aún (§3)                              | N/A                                                                | **catalogado**                                                        | GROUND_TRUTH                                                                                                                             |

### 1.4 Clase C — Simulación química / materiales (ya NO es el Reto 3 — ver nota de drift)

> **Nota de drift (2026-07-18):** el C3 oficial es **TFIM + Trotterización**, no química
> molecular. Clase nueva a catalogar si se activa el segundo reto condicional (= C3):
> proponente = circuito de Trotter (orden 1/2, n_t pasos — capas ZZ + X, la misma familia de
> compuertas del QAOA con ángulos dictados por la física J·dt, h·dt); ancla = **ED del MISMO
> Hamiltoniano (SciPy/PySCF) → FORMAL_EXACT**, criterio oficial: ⟨Zᵢ⟩ y ⟨ZᵢZᵢ₊₁⟩ dentro de 5%;
> PROPERTY_RULE = conservación de simetrías + convergencia del error de Trotter O(dt²). La
> tabla de abajo queda como conocimiento de química (Fase 2 / referencia).

| Algoritmo                                        | Qué resuelve                                                               | Cuándo usarlo / cuándo NO                                                                                                                     | Madurez NISQ honesta                                                       | Estado en Chimera                        | Ancla (clase decisoria)                                                                                         |
| ------------------------------------------------ | -------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- | ---------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| **VQE + UCCSD**                                  | cota superior variacional de E₀ molecular con ansatz químicamente motivado | el proponente del reto (H₂ a 2 qubits, nota 02 §3); NO en moléculas grandes (crecimiento de términos/parámetros)                              | H₂/LiH rutinario en simulador; precisión química alcanzable en base mínima | **recetado** (nota 02 §3)                | FORMAL_EXACT (FCI + NumPy, doble ancla §3.4) + PROPERTY_RULE (cota variacional, forma de la curva — nota 04 §5) |
| **VQE hardware-efficient** (p. ej. EfficientSU2) | mismo loop con ansatz genérico de capas                                    | solo si UCCSD no cupiera (no es el caso a 2–12 qubits); NO por defecto: sin estructura física, riesgo de estados no físicos y paisajes planos | popular en hardware por profundidad; menos interpretable                   | **catalogado**                           | las mismas del VQE                                                                                              |
| **Hartree–Fock**                                 | campo medio; estado inicial del ansatz                                     | siempre como ancla barata: UCCSD(θ=0) debe reproducir E_HF exacta ANTES de optimizar                                                          | N/A (clásico centenario)                                                   | **recetado** (ancla, nota 02 §3.3)       | PROPERTY_RULE (chequeo de identidad de una línea)                                                               |
| **FCI** (PySCF)                                  | diagonalización exacta en la base — el "óptimo probado" de la química      | siempre que la base lo permita (todo el reto); cuidado contable E_NN (nota 02 §3.5)                                                           | N/A (exacto por definición en la base)                                     | **recetado** (ancla 1, nota 02 §3.4)     | FORMAL_EXACT                                                                                                    |
| **NumPyMinimumEigensolver**                      | autovalor mínimo del MISMO H_qubit, sin PySCF y air-gapped                 | siempre (H₂ reducido: matriz 4×4); NO escala más allá de ~14 qubits (2ⁿ×2ⁿ)                                                                   | N/A                                                                        | **recetado** (ancla 2, nota 02 §3.4)     | FORMAL_EXACT — checker independiente que habilita AL4 (triangula VQE↔NumPy↔PySCF)                               |
| **QPE** (phase estimation)                       | E₀ con precisión exponencial                                               | NO: exige circuitos profundos coherentes (tolerancia a fallos); es la respuesta honesta a "¿y a futuro?"                                      | fuera de NISQ                                                              | **descartado con causa** (FTQC, no NISQ) | —                                                                                                               |

### 1.5 Clase D — Sampling / otros

| Algoritmo             | Qué resuelve                                                       | Cuándo usarlo / cuándo NO                                                                                                                                                                                                                                                                  | Madurez NISQ honesta                                              | Estado en Chimera                                                                                                         | Ancla (clase decisoria)                                                                                                              |
| --------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **Muestreo uniforme** | el baseline que mantiene honesto al proponente: P(óptimo por azar) | SIEMPRE que se reporte un resultado de muestreo (enriquecimiento = p_QAOA/p_uniforme, nota 04 §3)                                                                                                                                                                                          | N/A                                                               | **recetado** (nota 04 §3)                                                                                                 | es parte de la estadística del claim, no un proponente a verificar                                                                   |
| **Grover**            | búsqueda no estructurada con speedup cuadrático (O(√N))            | **caveat honesto:** exige un ORÁCULO que reconozca la solución — para optimización eso equivale a ya saber evaluar/acotar el objetivo, y a escala NISQ el circuito del oráculo + √(2ⁿ) iteraciones coherentes cuesta más que enumerar (n≤30). NO aporta nada aquí sobre CP-SAT/enumeración | speedup probado en teoría; sin instancia práctica NISQ donde gane | **descartado con causa** para los retos (queda en el catálogo como conocimiento: es la respuesta a "¿por qué no Grover?") | si alguna vez corriera: FORMAL_EXACT (el resultado es un elemento verificable directamente)                                          |
| **HHL**               | sistemas lineales Ax=b con speedup exponencial _condicionado_      | **caveat NISQ:** la letra chica es larga — preparación del estado \|b⟩, número de condición κ, y la salida es \|x⟩ (leer el vector completo mata el speedup); profundidad fuera de todo alcance NISQ                                                                                       | no ejecutable útilmente en NISQ                                   | **descartado con causa** (NISQ; sin caso de uso en los 3 retos)                                                           | si alguna vez corriera: PROPERTY_RULE/EXECUTION (residual ‖Ax−b‖ recomputado clásico) — nótese que hasta HHL tendría ancla no-modelo |

### 1.6 Lectura transversal de la columna de anclas

Tres hechos que la tabla hace visibles y el pitch debe explotar:

1. **Ningún ancla es un modelo** — todas las clases decisorias que aparecen (FORMAL_EXACT,
   EXECUTION, GROUND_TRUTH, PROPERTY_RULE, CONSENSUS_REPLICATION) son procesos deterministas
   no-modelo. HUMAN_EXPERT no aparece: ninguno de los 3 retos lo necesita este mes.
2. **El ancla depende de la CLASE de problema, no del algoritmo.** Las cuatro variantes de QAOA,
   neal, Kernighan–Lin y el espectral comparten fila de verificación: el corpus con doble ancla.
3. **AL4 ya está habilitado donde importa:** la doble ancla del corpus (CP-SAT + fuerza bruta) y
   la doble ancla de química (FCI + NumPy) son exactamente el "FORMAL_EXACT con checker
   independiente" del mapa de convergencia §2.1. El techo GROUND_TRUTH → máx AL3 aplica al Reto 2
   (test set = corpus `curated_internal`), y el consenso de muestreo con seeds pinned es
   CONSENSUS_REPLICATION → AL2 decisorio (ajuste a la nota 04 §4 ya decidido en convergencia §2.1).

### 1.7 Cómo elige el planner (el diferenciador agnóstico hecho concreto)

```
problema  →  clase (A/B/C/D, la define la formulación del claim, no el algoritmo)
clase     →  candidatos del catálogo (filtrados por estado y presupuesto; la madurez
             honesta ordena, jamás promete)
SIEMPRE   →  el plan de verificación sale de la clase de problema + criticidad (C0–C3),
             y NO cambia al cambiar de candidato
```

1. **El problema define la clase.** "Particionar esta red" es Clase A por su formulación
   (grafo→QUBO), independientemente de si lo ataca QAOA, neal o Kernighan–Lin.
2. **El catálogo da los candidatos.** El planner puede proponer varios en paralelo (la ablación
   A/B ya recetada es exactamente eso: múltiples proponentes sobre la misma instancia) — y eso
   responde literalmente el énfasis "múltiples algoritmos" del bootcamp.
3. **La verificación no cambia jamás.** El ancla, el corpus, las propiedades y el certificado son
   los mismos para todo candidato de la clase. Intercambiar el proponente es una operación barata
   y segura; tocar el verificador está prohibido por construcción (INV-2). Esto es lo que hace a
   la plataforma agnóstica de verdad, y no "agnóstica" por eslogan: el catálogo crece por arriba
   (proponentes) sin que la confianza se mueva por abajo (anclas).

## 2 · Decisión (qué se implementa este mes vs catalogado vs descartado)

- **Se implementa este mes (carril Reto 1, el nuestro):** QAOA p∈{1,2} con semillas INTERP +
  los baselines clásicos de diversidad — CP-SAT (ya implementado como ancla/generador del corpus),
  recocido simulado vía `neal` (idiom 5, 6 líneas), Kernighan–Lin (NetworkX), muestreo uniforme,
  y — **obligatorios por el enunciado oficial (2026-07-18)** — **Goemans–Williamson (CVXPY) y
  greedy (~0.5)**.
  Mínimo cuatro proponentes sobre el mismo corpus = "múltiples algoritmos" con evidencia comparable.
- **Recetado, se implementa solo si el equipo toma el reto:** kernel cuántico + SVM/RF/SVM-RBF
  (Reto 2) y VQE/UCCSD + anclas HF/FCI/NumPy (química — **ya no es el Reto 3**: el C3 oficial es
  TFIM/Trotter, ver nota de drift en §1.4; la clase TFIM se cataloga si se activa el segundo
  reto condicional) — las recetas completas ya están (nota 02); el catálogo solo las posiciona.
- **Catalogado (stretch/ablación, sin compromiso):** warm-start QAOA, RQAOA, MA-QAOA, espectral,
  QNN, XGBoost, VQE hardware-efficient. **Goemans–Williamson salió de esta lista (2026-07-18):
  es baseline obligatorio del enunciado — ver su fila en §1.2 y la licencia en §3.**
- **Descartado con causa:** Grover (oráculo/escala — §1.5), HHL (letra chica NISQ — §1.5), QPE
  (FTQC), quantum annealing en hardware y todo QPU cloud (air-gap, nota 03 §5).

## 3 · Licencias (solo de librerías NUEVAS que propone esta nota)

**Actualización 2026-07-18 — UNA librería nueva SÍ entra al stack este mes: cvxpy (+ su solver
SDP), porque Goemans–Williamson pasó a baseline obligatorio del enunciado oficial (fila en §1.2,
licencia abajo).** El resto de lo que se implementa usa el stack ya
verificado en la nota 03 (Qiskit/PennyLane/dimod/neal/PySCF — Apache-2.0, verificadas en vivo
2026-07-14) más OR-Tools/NetworkX/sklearn que ya son parte del plano vigente (trust/10, nota 03 §6).
Dos candidatos catalogados introducirían dependencia nueva SI se activaran:

- **XGBoost** (baseline Reto 2) — licencia esperada Apache-2.0; chequeo declarado: verificación en
  vivo contra el LICENSE oficial SOLO si el C2/QSVM se reabriera (descartado como segundo reto en
  S-E — el condicional es C3/TFIM, que no lo usa).
- **Solver SDP para Goemans–Williamson** (p. ej. cvxpy + SCS) — licencias esperadas Apache-2.0/MIT,
  **verificación en vivo AHORA BLOQUEANTE (2026-07-18): GW dejó de ser catalogado — es baseline
  obligatorio del enunciado (CVXPY es herramienta oficial del C1)**; cerrar esta fila de licencia
  en el PR único de deps (S-G) antes de implementar.

Regla: ningún "catalogado" pasa a "implementado" sin cerrar su fila de licencia primero (misma
disciplina de la nota 03).

## 4 · Impacto en contrato

**Ninguno.** El catálogo es knowledge que consume el planner (datos versionados, como λ o el
corpus — ADR-029: el conocimiento de escenario vive aquí, los manifests siguen genéricos). No
propone campos nuevos de `evidence` ni toca el freeze: la identidad del algoritmo proponente ya
viaja en el claim (backend, p, shots, seeds — nota 02 §1.6) y el mapeo clase→ancla usa el
vocabulario ya adoptado en `docs/convergencia-diseno-v32.md` §2.1 sin extenderlo.

## 5 · Reconciliación contra la base lógica (`docs/invariants.md`)

- **INV-2 / PR2 (el verificador jamás es un modelo):** la columna de anclas lo cumple por
  construcción — solo aparecen clases decisorias de proceso no-modelo (§1.6.1); ningún algoritmo
  del catálogo se propone como verificador de otro.
- **ADR-029 (manifests genéricos):** el catálogo entero es conocimiento de escenario en
  `knowledge/` — el planner lo consume; las capabilities siguen exponiendo verbos genéricos
  ("resolver un QUBO", "clasificar con kernel precomputado").
- **ADR-008 (capabilities fuera del core):** los proponentes que se implementen entran como
  capabilities plugin; elegir del catálogo no acopla el engine a ningún algoritmo.
- **Regla fail-loud** (espejo de trust/10 §1.2, transversal en §1.1): superar el óptimo probado
  por FORMAL_EXACT ⇒ bug del proceso, para todo proponente sin excepción.
- Sin contradicciones detectadas con los invariantes congelados. **Decidido (S-E 2026-07-18) —
  ratificación final de Sebas, ajustable bajo su criterio** (incluye el corte implementar/catalogar
  de §2 y los dos caveats de §1.5).
