# Nota 00 — KB-fuentes: fuentes, repositorios, papers y gotchas por reto

**Ítem del plan (§4, Sebas):** la capa de fuentes del plano cuántico — URLs, versiones, migraciones de API y gotchas operativos. Las notas 01–04 la referencian como "KB-fuentes" y no repiten su contenido.
**Fecha:** 2026-07-08 · **Estado:** vigente como capa de fuentes — importada desde `docs/research/` en la consolidación del knowledge base (2026-07-14).
**Fuentes:** este documento ES la capa de fuentes; ninguna verificada en vivo durante la consolidación.

> **Nota de consolidación (Dylan, 2026-07-14):** anterior al template de notas (no tiene los 4 campos ni
> reconciliación — ver el README del directorio para los pendientes). Advertencia de vocabulario: varias
> secciones usan nombres de la arquitectura pre-reconciliación ("Verification Service", `quantum_agent`,
> `run_events`, rutas `distributions/chimera/datasets/docs/`) que no existen en el layout vigente
> (`blite.gateway/verification/serving/...`) — leer los conceptos, no los nombres. La recomendación de
> vendorizar código de demos de terceros (§1–3) queda sujeta a verificación de licencia previa (regla open-core).

---

> Documento fuente para el RAG de CHIMERA y para el equipo. Complementa
> `CHIMERA_Proyecto_Quantathon_CR2026` y el set de arquitectura del engine
> (hoy consolidado en `docs/` — ver `docs/README.md`).
> Última actualización: julio 2026.

---

## 0. Advertencias críticas de compatibilidad (leer ANTES de codear)

Estas son las trampas que más tiempo queman en hackathons cuánticos. Tu documento de
proyecto ya tiene código de ejemplo, pero parte de él usa APIs viejas.

### 0.1 `quantum_instance` ya no existe

El código del doc CHIMERA (`_solve_with_qaoa`) instancia `QAOA(optimizer=..., reps=..., quantum_instance=simulator)`.
El parámetro `quantum_instance` fue eliminado hace varias versiones: los algoritmos
modernos reciben **primitives** (`Sampler`/`Estimator`), no `QuantumInstance`.

- Migración oficial: <https://quantum.cloud.ibm.com/docs/migration-guides/qiskit-algorithms-module>
- Migración a V2 primitives: <https://quantum.cloud.ibm.com/docs/en/guides/v2-primitives>
- Forma correcta hoy (con `qiskit-optimization` 0.7+, que ya trae QAOA integrado):

```python
from qiskit.primitives import StatevectorSampler
from qiskit_optimization.minimum_eigensolvers import QAOA
from qiskit_optimization.optimizers import COBYLA
from qiskit_optimization.algorithms import MinimumEigenOptimizer

qaoa = QAOA(sampler=StatevectorSampler(seed=42), optimizer=COBYLA(maxiter=300), reps=2)
result = MinimumEigenOptimizer(qaoa).solve(qubo)
```

### 0.2 `qiskit-algorithms` está en modo mantenimiento

Qiskit Optimization 0.7 eliminó la dependencia de `qiskit-algorithms` y migró
VQE, QAOA, SamplingVQE, NumPyMinimumEigensolver, COBYLA, SPSA, etc. directamente
a `qiskit_optimization.*`, con soporte de primitives V1 y V2.

- Release notes: <https://qiskit-community.github.io/qiskit-optimization/release_notes.html>
- **Recomendación**: para el Reto 1 importar los solvers desde `qiskit_optimization`,
  no desde `qiskit_algorithms`. Para el Reto 3, `qiskit-nature` todavía usa
  `qiskit_algorithms.VQE` — funciona, pero fijar versiones (ver §0.4).

### 0.3 El bug silencioso de los shots (V1 → V2)

Hay un experience report entero sobre esto: al migrar QAOA de Qiskit 1.x a 2.x,
circuitos idénticos daban resultados drásticamente distintos porque los V1 primitives
usaban statevector "ilimitado" mientras los V2 muestrean con un default finito de shots.

- Paper: _Migrating QAOA from Qiskit 1.x to 2.x: An experience report_ — <https://arxiv.org/abs/2512.08245>
- **Lección para CHIMERA**: usar `StatevectorSampler` (exacto) para grafos ≤ 10 nodos,
  documentar el número de shots en la traza de eventos (es evidencia de verificación),
  y fijar seeds para reproducibilidad del demo.

### 0.4 Pinning de versiones sugerido (`requirements.txt`)

Fijar TODO. Qiskit rompe APIs entre minors.

```
qiskit==1.4.*            # 1.x es la zona estable para qiskit-nature/ML actuales
qiskit-aer==0.15.*
qiskit-optimization==0.7.*
qiskit-nature==0.7.*
qiskit-machine-learning==0.8.*
qiskit-algorithms==0.4.*   # solo como dependencia de nature
pennylane==0.38.*
pennylane-lightning==0.38.*
networkx==3.3.*
scikit-learn==1.5.*
pyscf==2.6.*             # ¡solo Linux/macOS! usar Docker en Windows
```

### 0.5 PySCF no corre en Windows nativo

Si alguien del equipo usa Windows: PySCF (Reto 3) solo compila en Linux/macOS.
Solución: WSL2 o el Docker Compose del proyecto. Verificar esto el Día 1, no el Día 7.

---

## 1. RETO 1 — Red eléctrica: partición por zonas de falla (QAOA / Max-Cut)

### 1.1 Tutoriales canónicos (implementación)

| Recurso                                                              | URL                                                                                                 | Por qué                                                                                                                                                                                         |
| -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| IBM Quantum — QAOA Max-Cut (workflow moderno con Runtime/primitives) | <https://quantum.cloud.ibm.com/docs/en/tutorials/quantum-approximate-optimization-algorithm>        | El tutorial de referencia actualizado: mapeo QUBO→Hamiltoniano, sesión de optimización con Estimator+COBYLA, extracción del bitstring                                                           |
| Qiskit Optimization — Max-Cut & TSP                                  | <https://qiskit-community.github.io/qiskit-optimization/tutorials/06_examples_max_cut_and_tsp.html> | Usa `Maxcut` application class + `QuadraticProgram.to_ising()`; es exactamente el pipeline que CHIMERA necesita para trazabilidad (la matriz QUBO y el SparsePauliOp son artefactos mostrables) |
| Qiskit Algorithms — QAOA notebook                                    | <https://qiskit-community.github.io/qiskit-algorithms/tutorials/05_qaoa.html>                       | Compara QAOA vs brute force — patrón directo para tu `baseline_comparison`                                                                                                                      |
| PennyLane — QAOA for MaxCut                                          | <https://pennylane.ai/qml/demos/tutorial_qaoa_maxcut>                                               | Derivación matemática limpia del Hamiltoniano de costo; útil para la narrativa/slides                                                                                                           |
| NVIDIA CUDA-Q — Max-Cut with QAOA                                    | <https://nvidia.github.io/cuda-quantum/latest/examples/python/tutorials/qaoa.html>                  | Implementación alternativa clara; buena para entender el circuito capa por capa                                                                                                                 |
| IBM Learning — Utility-scale QAOA                                    | <https://learning.quantum.ibm.com/course/quantum-computing-in-practice/utility-scale-qaoa>          | Contexto de escala y transpilación; munición para la pregunta del jurado "¿y esto escala?"                                                                                                      |

### 1.2 Papers directamente sobre TU problema (partición de redes eléctricas)

Esto es oro para la narrativa: no es un Max-Cut genérico, ya hay literatura de
partición de redes eléctricas con QUBO/QAOA.

1. **REGRID-QAOA: A Resource-Efficient Hybrid QAOA Framework for Physics-Constrained Power System Islanding** (2026) — <https://arxiv.org/abs/2606.15083>
   - El paper más cercano a tu reto: islanding de redes eléctricas con QAOA,
     validado en sistemas IEEE de 9 a 57 buses en hardware real de IBM.
   - Su idea central coincide con la tesis de CHIMERA: las salidas cuánticas muestreadas
     se convierten en decisiones factibles mediante verificación/reparación clásica
     (penalizaciones QUBO + chequeo clásico de restricciones). **Cítalo en la presentación.**
2. **Quantum Annealing based Power Grid Partitioning for Parallel Simulation** — <https://arxiv.org/abs/2408.04097>
   - Formula la partición de red como QUBO (corte mínimo + subgrafos de igual tamaño)
     y discute los límites de tamaño en hardware actual (<200 buses en D-Wave).
   - Justifica tu restricción de balance de carga como término del QUBO.
3. **Ising formulations of many NP problems** (Lucas, 2014) — <https://arxiv.org/abs/1302.5843>
   - LA referencia estándar para codificar restricciones como penalizaciones en QUBO/Ising.
     Sección de graph partitioning aplica directo.
4. **A Quantum Approximate Optimization Algorithm** (Farhi et al., 2014) — <https://arxiv.org/abs/1411.4028>
   - El paper original de QAOA. Referencia obligatoria.
5. **Quantum annealing computing for grid partition in large-scale power systems** (IEEE) — <https://ieeexplore.ieee.org/document/9846717>
   - Variante con relajación Lagrangiana/ADMM para transformar IQP→QUBO. Bonus de contexto.

### 1.3 Repositorios de referencia

| Repo                          | URL                                                       | Qué tomar                                                                                                                                                                      |
| ----------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| OpenQuantumComputing/QAOA     | <https://github.com/OpenQuantumComputing/QAOA>            | Librería modular de QAOA (problemas, mixers, estados iniciales). Su heurística INTERP para inicializar ángulos capa a capa evita malas convergencias — replicable en tu solver |
| leonardoLavagna/qaoa          | <https://github.com/leonardoLavagna/qaoa>                 | Framework Max-Cut con Qiskit + app Streamlit; buen ejemplo de estructura pequeña y limpia                                                                                      |
| MauriceDHanisch/ethz_qhack_24 | <https://github.com/MauriceDHanisch/ethz_qhack_24>        | Proyecto ganador del challenge NVIDIA en ETH QHack 2024: VRP→QUBO→QAOA con enfoque divide-and-conquer. Ejemplo de cómo se presenta un proyecto QAOA ganador                    |
| GitHub topic `qaoa`           | <https://github.com/topics/qaoa>                          | Índice general para minar más ejemplos                                                                                                                                         |
| Qiskit Optimization (source)  | <https://github.com/qiskit-community/qiskit-optimization> | Leer `applications/max_cut.py` y los converters — tu `quantum_agent` puede loggear cada transformación                                                                         |

### 1.4 Baselines clásicos para el Verification Service

- **NetworkX `kernighan_lin_bisection`** (el que ya usa tu doc): bisección balanceada.
  Nota: KL fuerza particiones ~iguales; Max-Cut puro no. Si comparas contra KL, compara
  también factibilidad de balance de carga o el jurado técnico puede objetar.
- **NetworkX approximation `one_exchange`** (`networkx.algorithms.approximation.maxcut`):
  baseline local-search específico de Max-Cut.
- **Brute force**: para n ≤ 16 nodos es trivial (2^n) y te da el **óptimo exacto** →
  tu score de verificación puede ser `cut_qaoa / cut_óptimo` (approximation ratio),
  que es la métrica estándar de la literatura QAOA. Para el demo de 6-8 nodos, hazlo siempre.
- **Goemans-Williamson (SDP, ratio garantizado 0.878)**: implementable con `cvxpy`;
  baseline "serio" si quieren impresionar. Opcional.

### 1.5 Datasets

- Tu grafo sintético de 8 subestaciones CR está bien para el demo (control total + narrativa local).
- Para credibilidad extra: **sistemas de prueba IEEE (9, 14, 30 buses)** vía
  `pandapower.networks` (`pip install pandapower`, `pn.case14()`) o MATPOWER.
  REGRID-QAOA usa exactamente estos — puedes decir "validamos en el mismo benchmark que el estado del arte".

### 1.6 Gotchas específicas del Reto 1

- QAOA con p=1–2 en grafos de 6-8 nodos frecuentemente **empata o pierde** contra
  clásico. Está bien: tu sistema es de verificación honesta. La narrativa correcta
  ya está en tu doc ("escala mejor en grafos grandes") y coincide con la literatura.
- `AerSimulator(method="statevector")` con más de ~25 qubits explota en RAM. Irrelevante
  para 8 nodos, pero no prometan demos de 50 nodos en vivo.
- COBYLA se atasca en mesetas (barren plateaus suaves incluso en p bajo): correr con
  3-5 seeds y quedarse con la mejor energía; loggear cada intento como evento (¡más trazabilidad!).

---

## 2. RETO 2 — Potabilidad del agua (QML)

### 2.1 Dataset

- **Kaggle Water Potability**: <https://www.kaggle.com/datasets/adityakadiwal/water-potability>
  (3,276 muestras, 9 features, target binario).
- **Gotchas del dataset (importantes)**:
  - Es un dataset **sintético** y "difícil": los modelos clásicos típicos rondan
    **65-70% accuracy** (los notebooks top de Kaggle lo confirman). No prometan 95%.
  - ~15-24% de NaN en `ph`, `Sulfate`, `Trihalomethanes` → imputación con mediana (ya lo tienes).
  - Clases desbalanceadas (~61/39) → usar `stratify=y` y reportar **F1 y matriz de
    confusión**, no solo accuracy. Tu `QMLClassifierResponse` ya lo contempla. Bien.
- Alternativa/backup: **Water Quality and Potability** (versión de MissikaCode en Kaggle)
  o el **Wine/Iris** de sklearn como sanity check del pipeline antes de tocar el dataset real.

### 2.2 Tutoriales canónicos

| Recurso                                     | URL                                                                                                   | Por qué                                                                                                                       |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Qiskit ML — Quantum Kernel Machine Learning | <https://qiskit-community.github.io/qiskit-machine-learning/tutorials/03_quantum_kernel.html>         | El tutorial base de QSVC/FidelityQuantumKernel; workflow completo de clasificación con kernel cuántico enchufado a sklearn    |
| Qiskit ML — Pegasos QSVC                    | <https://qiskit-community.github.io/qiskit-machine-learning/tutorials/07_pegasos_qsvc.html>           | Alternativa de entrenamiento sub-gradiente más rápida si el kernel completo tarda                                             |
| Qiskit ML — Quantum Kernel Trainer          | <https://qiskit-community.github.io/qiskit-machine-learning/tutorials/08_quantum_kernel_trainer.html> | Kernels entrenables (QKA) — stretch goal con buena historia                                                                   |
| Qiskit ML — Migración 0.8 (V2 primitives)   | <https://qiskit-community.github.io/qiskit-machine-learning/migration/02_migration_guide_0.8.html>    | Cómo instanciar `FidelityQuantumKernel` con `StatevectorSampler` + `ComputeUncompute` — el snippet exacto que van a necesitar |
| PennyLane — Variational classifier          | <https://pennylane.ai/qml/demos/tutorial_variational_classifier>                                      | El demo VQC de referencia (AngleEmbedding + StronglyEntanglingLayers, igual a tu diseño)                                      |
| PennyLane — Kernel-based training           | <https://pennylane.ai/qml/demos/tutorial_kernel_based_training>                                       | Kernel cuántico + SVM en PennyLane, con análisis de cuándo conviene kernel vs variacional                                     |
| PennyLane — Kernels module                  | <https://pennylane.ai/qml/demos/tutorial_kernels_module>                                              | `qml.kernels`: target alignment, mitigación del kernel — te ahorra escribir `build_kernel_matrix` a mano                      |

### 2.3 Papers de fundamento (para README y presentación)

1. **Supervised learning with quantum-enhanced feature spaces** (Havlíček et al., Nature 2019) — <https://arxiv.org/abs/1804.11326>
   - El paper que introduce el quantum kernel estimator y el VQC. Es la referencia
     citada por los propios tutoriales de Qiskit ML.
2. **Quantum Machine Learning in Feature Hilbert Spaces** (Schuld & Killoran, 2018) — <https://arxiv.org/abs/1803.07128>
3. **Supervised quantum machine learning models are kernel methods** (Schuld, 2021) — <https://arxiv.org/abs/2101.11020>
   - Justifica teóricamente elegir kernel methods sobre VQC (tu "Estrategia 2").
4. **Power of data in quantum machine learning** (Huang et al., Nature Comm. 2021) — <https://arxiv.org/abs/2011.01938>
   - CRÍTICO para honestidad científica: demuestra que con suficientes datos los modelos
     clásicos igualan muchos "quantum advantages". Citarlo te protege del quantum-washing
     — exactamente el riesgo 19.2 de tu doc de arquitectura.
5. **Training Quantum Embedding Kernels on Near-Term Quantum Computers** — <https://arxiv.org/abs/2105.02276>
   - Base del demo de kernels de PennyLane (target alignment).

### 2.4 Repos de referencia

- `qiskit-community/qiskit-machine-learning` — <https://github.com/qiskit-community/qiskit-machine-learning> (notebooks en `docs/tutorials/`)
- `PennyLaneAI/demos` — <https://github.com/PennyLaneAI/demos> (todos los demos descargables como .py — puedes vendorizar el de kernels)
- Proyectos clásicos de water potability para baseline y EDA:
  <https://github.com/Shrawan662000/Water-potability-prediction-using-Machine-Learning>
  (pipeline sklearn completo: DT, LR, XGBoost, RF, SVM, KNN — copia sus baselines)

### 2.5 Gotchas específicas del Reto 2 (los que rompen demos)

- **El kernel cuántico es O(n²) en muestras**: con 3,276 muestras son ~5.4M de
  evaluaciones de circuito. Imposible en vivo. **Submuestrear: 100-200 train / 50 test**
  (estratificado). Documentarlo como decisión explícita en la traza.
- Con 4 qubits solo codificas 4 features con AngleEmbedding → tu selección por
  importancia de Random Forest está bien; loggear qué features quedaron (trazabilidad).
- El VQC con `np.array([circuit(x) for x in X])` por época es lentísimo — por eso tu
  doc ya recomienda Quantum Kernel SVM como estrategia principal. Confirmado: es la
  decisión correcta para demo. VQC solo como stretch.
- Comparación justa: el baseline clásico debe ver **las mismas 4 features y las mismas
  100-200 muestras** que el cuántico. Si no, la verificación es inválida y un juez
  técnico lo va a notar.
- Precomputar y **cachear la matriz de kernel** (np.save) para el demo en vivo; recalcular
  en vivo solo si sobra tiempo. El fallback pre-computado es tu seguro anti-demo-effect.

---

## 3. RETO 3 — Simulación de materiales (VQE) — BONUS

### 3.1 Tutoriales canónicos

| Recurso                                | URL                                                                                       | Por qué                                                                                                                                             |
| -------------------------------------- | ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Qiskit Nature — Ground State Solvers   | <https://qiskit-community.github.io/qiskit-nature/tutorials/03_ground_state_solvers.html> | El pipeline exacto de tu doc: PySCFDriver → mapper → HartreeFock+UCCSD → VQE, incluyendo `NumPyMinimumEigensolver` como verificador exacto          |
| Qiskit Nature — tutoriales completos   | <https://qiskit-community.github.io/qiskit-nature/tutorials/index.html>                   | Mappers, active space, electronic structure                                                                                                         |
| Qiskit Nature — AdaptVQE howto         | <https://qiskit-community.github.io/qiskit-nature/howtos/adapt_vqe.html>                  | Variante que reduce parámetros; stretch                                                                                                             |
| PennyLane — A brief overview of VQE    | <https://pennylane.ai/qml/demos/tutorial_vqe>                                             | VQE de H2 en ~50 líneas; buen plan B si Qiskit Nature da problemas de versiones                                                                     |
| PennyLane — Quantum Chemistry datasets | <https://pennylane.ai/datasets>                                                           | Hamiltonianos moleculares pre-computados (H2, LiH, BeH2...) con energías FCI de referencia — te ahorra PySCF entero si hay problemas de instalación |

### 3.2 Papers

1. **Hardware-efficient VQE for small molecules and quantum magnets** (Kandala et al., Nature 2017) — <https://arxiv.org/abs/1704.05018>
   - El experimento clásico de VQE en H2, LiH, BeH2 — las mismas moléculas de tu tabla.
2. **Ground-State Energy Estimation on Current Quantum Hardware through VQE: A Practical Study** (2025) — <https://pmc.ncbi.nlm.nih.gov/articles/PMC12288014/>
   - Estudio práctico de BeH2 con Qiskit 1.2 comparando ansätze UCCSD vs hardware-efficient
     en simulación y hardware real: UCCSD confiable en condiciones ideales, HEA más
     robusto ante ruido. Código funcional incluido — casi un template para tu Reto 3.
3. **Ground state property calculations of LiHn complexes using IBM Qiskit's quantum simulator** (AIP Advances 2024) — <https://pubs.aip.org/aip/adv/article/14/3/035047/3278854>
   - VQE/UCCSD vs FCI para LiH: exactamente tu esquema de verificación
     (energy_error vs FCI, precisión química). Compara mappers Jordan-Wigner vs Parity.
4. **The theory of variational hybrid quantum-classical algorithms** (McClean et al., 2016) — <https://arxiv.org/abs/1509.4279> (arXiv:1509.04279)

### 3.3 Gotchas específicas del Reto 3

- **Precisión química = 1.6 mHa** (1 kcal/mol ≈ 1.594 mHa). Tu doc usa umbral de 1.0 mHa —
  más estricto que el estándar; considera relajarlo a 1.6 y citarlo como "chemical accuracy".
- H2/STO-3G en Jordan-Wigner son 4 qubits; con **ParityMapper + two-qubit reduction**
  baja a 2 qubits y converge en segundos — mejor para demo en vivo.
- LiH (12 qubits JW) con UCCSD completo puede tardar minutos: usar
  `ActiveSpaceTransformer` (congelar core) para bajar a ~6-8 qubits.
- `Estimator` de `qiskit.primitives` (V1) está deprecado → usar `StatevectorEstimator`
  (mismo cambio que en el howto de AdaptVQE).
- Si PySCF falla en la máquina de alguien: fallback = datasets de PennyLane con
  FCI pre-computado, o `NumPyMinimumEigensolver` sobre el mismo Hamiltoniano de qubits
  (diagonalización exacta = verificador perfecto para moléculas pequeñas, sin PySCF).

---

## 4. Transversal — Verificación, benchmarking y "quantum honesto"

Fuentes que respaldan el diferenciador central de CHIMERA (verificar, no confiar):

1. **REGRID-QAOA** (ver §1.2) — post-procesamiento y verificación clásica de salidas
   cuánticas como metodología, no como parche. Es literalmente tu Verification Service
   con otro nombre; úsalo como validación externa de la tesis del engine.
2. **Power of data in QML** (ver §2.3, punto 4) — por qué reportar baselines clásicos
   fuertes es requisito científico, no cortesía.
3. **Migrating QAOA 1.x→2.x** (ver §0.3) — por qué loggear shots/seeds/versiones en los
   `run_events` importa: parámetros ocultos dominan los resultados híbridos.
4. **Métricas estándar a reportar por reto**:
   - Reto 1: approximation ratio (cut/cut_óptimo por brute force), factibilidad, gap vs baseline.
   - Reto 2: accuracy, F1, matriz de confusión, mismas condiciones para quantum y clásico.
   - Reto 3: error absoluto vs FCI en mHa, ¿< 1.6 mHa?, número de parámetros e iteraciones.
5. **Benchmarks de comunidad** (para contexto/roadmap, no para el POC):
   - QED-C Application-Oriented Benchmarks: <https://github.com/SRI-International/QC-App-Oriented-Benchmarks>
     (incluye Max-Cut/QAOA y VQE como benchmarks estandarizados — tu `benchmarks/` de la
     distribución CHIMERA puede inspirarse en su estructura).

---

## 5. Ejemplos de proyectos de hackathon (formato y presentación)

- **ETH QHack 2024, ganador NVIDIA** — <https://github.com/MauriceDHanisch/ethz_qhack_24>
  Estructura de repo, notebook final y presentación de un proyecto QAOA ganador.
- **QHack (Xanadu) open hackathons** — <https://github.com/XanaduAI/QHack2023> y
  <https://github.com/XanaduAI/QHack2022> — cientos de submissions enlazadas en los issues;
  minar los premiados de las categorías QAOA/QML para ver el nivel esperado.
- **CDL Quantum Hackathon** — <https://github.com/CDL-Quantum/Hackathon2020> — proyectos
  completos de 24h con VQA/QAOA benchmarking.
- Patrón común de los ganadores: **un problema, bien resuelto, con comparación clásica
  honesta y demo reproducible** — exactamente la recomendación estratégica de tu doc §0.

---

## 6. Checklist de incorporación al RAG de CHIMERA

Documentos a descargar/convertir e indexar en `distributions/chimera/datasets/docs/`:

- [ ] arXiv 2606.15083 (REGRID-QAOA) — PDF
- [ ] arXiv 2408.04097 (QA grid partitioning) — PDF
- [ ] arXiv 1302.5843 (Ising formulations, Lucas) — PDF
- [ ] arXiv 1411.4028 (QAOA, Farhi) — PDF
- [ ] arXiv 1804.11326 (Quantum-enhanced feature spaces) — PDF
- [ ] arXiv 2101.11020 (QML = kernel methods) — PDF
- [ ] arXiv 2011.01938 (Power of data) — PDF
- [ ] arXiv 1704.05018 (Kandala, hardware-efficient VQE) — PDF
- [ ] Tutorial IBM QAOA Max-Cut — export a markdown
- [ ] Qiskit Nature 03_ground_state_solvers — notebook
- [ ] Qiskit ML 03_quantum_kernel — notebook
- [ ] water_potability.csv (Kaggle) + notebook de EDA clásico
- [ ] Este documento

---

## 7. Resumen de recomendaciones (delta sobre tu plan actual)

1. **Actualizar el código QAOA del doc CHIMERA** a primitives V2 vía
   `qiskit_optimization.minimum_eigensolvers.QAOA` — el snippet con `quantum_instance`
   no corre en ningún Qiskit ≥ 1.0. (§0.1)
2. **Agregar brute force como tercer verificador** del Reto 1 (n≤16): te da el óptimo
   exacto y la métrica approximation ratio, más fuerte que solo comparar con Kernighan-Lin. (§1.4)
3. **Citar REGRID-QAOA en la presentación**: valida que "muestrear cuántico + verificar
   clásico" es metodología publicada en 2026 sobre el mismo problema de tu Reto 1. (§1.2)
4. **Reto 2: submuestrear a 100-200 muestras y cachear la matriz de kernel** — es la
   diferencia entre demo fluido y demo colgado. (§2.5)
5. **Citar "Power of data" para blindarse del quantum-washing**: tu sistema reporta
   honestamente cuándo el clásico gana — conviértelo en feature, no en debilidad. (§2.3)
6. **Reto 3: usar ParityMapper (2 qubits para H2) y umbral de 1.6 mHa**; fallback a
   datasets de PennyLane si PySCF no instala. (§3.3)
7. **Loggear shots, seeds y versiones de librerías en run_events**: es trazabilidad
   real y hay literatura que muestra que esos parámetros ocultos cambian resultados. (§0.3)
