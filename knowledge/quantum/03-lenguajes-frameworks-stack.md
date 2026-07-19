# Nota 03 (KB2-03) — Lenguajes y frameworks del stack cuántico: modelos mentales, APIs mínimas y trampas

**Rol:** dominio operativo de las herramientas. Qué es cada pieza, cómo se piensa, los 5 idioms de API que el equipo va a escribir, y las trampas de convención entre frameworks.
**No repite:** tutoriales/links/pinning de versiones (KB-fuentes §0.4 y §1–3, nota 00) ni las decisiones de adapters (notas trust/04/10/12). Aquí está el _cómo se usa y cómo se piensa_.
**Fecha:** 2026-07-14 · **Estado:** vigente — movida de `docs/kb2-03…` a `knowledge/quantum/` en la consolidación (2026-07-14); el template de nota se aplica en la sección final.

---

## 1 · Qué es un "lenguaje cuántico" (para responderlo en 30 segundos)

En la práctica NISQ no se programa "en cuántico": se **construyen circuitos desde Python** con DSLs embebidos (Qiskit, PennyLane, Cirq) y se ejecutan en simuladores o hardware. El "assembly" portable entre vendors es **OpenQASM 3** (texto plano que describe el circuito). Capas:

```
Problema → formulación (KB2-02) → circuito (DSL Python) → transpilación → backend (simulador / QPU)
                                        ↓
                               OpenQASM 3 (artefacto textual portable)
```

**Gancho de procedencia (propio de CHIMERA):** `qiskit.qasm3.dumps(circuito)` produce los _bytes exactos_ del circuito ejecutado → SHA-256 → `circuit_digest` en la evidencia (Regla 1 del anexo de canonicalización: artefacto versionado, como `policy_digest`). El circuito deja de ser una anécdota y se vuelve auditable — un campo aditivo natural para `evidence` que ninguna nota tiene aún.

## 2 · Qiskit: el mapa del ecosistema y los 3 idioms

**Modelo mental:** `qiskit` (core) = circuitos + `quantum_info` (estados, `SparsePauliOp`) + transpiler + **primitives V2**. Todo lo demás son paquetes satélite: `qiskit-aer` (simulación con shots/ruido), `qiskit-optimization` (QuadraticProgram → Ising → QAOA), `qiskit-nature` (química), `qiskit-machine-learning` (kernels/QNNs), `qiskit-ibm-runtime` (hardware real — fuera de alcance air-gapped este mes).

**Primitives V2 — la abstracción central:** dos verbos, entrada en "PUBs" (tuplas):

- `Estimator` = "dame ⟨H⟩": PUB = `(circuito, observables, valores_de_parámetros)`.
- `Sampler` = "dame bitstrings": PUB = `(circuito,)` + `shots`.

```python
# Idiom 1 — energía exacta (statevector) del H_C del Reto 1
from qiskit.primitives import StatevectorEstimator
ev = StatevectorEstimator().run([(qc, H_C)]).result()[0].data.evs

# Idiom 2 — muestrear candidatos con seed y shots explícitos (¡a la evidencia!)
from qiskit.primitives import StatevectorSampler
res = StatevectorSampler(seed=42).run([(qc_medido,)], shots=4096).result()
counts = res[0].data.meas.get_counts()          # 'meas' = nombre del registro de measure_all()

# Idiom 3 — el circuito como artefacto de procedencia
from qiskit import qasm3
circuit_qasm = qasm3.dumps(qc)                   # → SHA-256 → evidence["circuit_digest"]
```

**Piezas específicas que el Reto 1 toca:** `QAOAAnsatz` (en `qiskit.circuit.library`; recibe `cost_operator=SparsePauliOp` y arma las capas RZZ/RX solo), y en `qiskit-optimization`: `QuadraticProgram` + `to_ising()` (devuelve el `SparsePauliOp` + offset — comparalo contra tu derivación a mano de KB2-02 §1.4: si difieren, alguien tiene la convención al revés).

**Aer en una línea:** `AerSimulator` agrega métodos (`statevector`, `matrix_product_state`, `automatic`) y **modelos de ruido** — irrelevante esta fase, pero es la palanca de "realismo NISQ" si un juez pide ver el algoritmo bajo ruido (Fase 2 honesta, no promesa).

## 3 · PennyLane: el modelo mental de la diferenciación

**Idea central:** un circuito es una **función diferenciable**. Se declara con `@qml.qnode(device)` y se puede pedir su gradiente (`qml.grad`) — PennyLane aplica parameter-shift (KB2-01 §10) o backprop del simulador por debajo, con interfaces autograd/PyTorch/JAX. Por eso es la casa natural del Reto 2 (entrenamiento) mientras Qiskit lo es del 1 y 3 (solvers/química).

```python
# Idiom 4 — kernel de fidelidad + matriz de Gram con utilidades incluidas
import pennylane as qml
dev = qml.device("lightning.qubit", wires=4)          # backend C++ rápido

@qml.qnode(dev)
def fid(x1, x2):
    qml.AngleEmbedding(x1, wires=range(4), rotation="Y")
    qml.adjoint(qml.AngleEmbedding)(x2, wires=range(4), rotation="Y")
    return qml.probs(wires=range(4))

kernel = lambda a, b: fid(a, b)[0]                    # Pr(|0000⟩)
K_train = qml.kernels.square_kernel_matrix(X_tr, kernel)      # explota simetría
K_test  = qml.kernels.kernel_matrix(X_te, X_tr, kernel)
```

`qml.kernels` trae además `target_alignment` (métrica de calidad del kernel — buen número para la ablación) — evita reimplementar el doble loop del doc CHIMERA a mano.

**Devices que importan:** `default.qubit` (referencia, backprop), `lightning.qubit` (C++, el caballo de batalla), `default.mixed` (ruido). Interop: el plugin `pennylane-qiskit` permite correr QNodes sobre backends Qiskit/Aer — útil si se quiere UN solo simulador en la evidencia de ambos retos.

## 4 · La tabla de trampas de convención (donde mueren las horas)

| Convención                  | Qiskit                                                                  | PennyLane                                                                       | Consecuencia                                                                                                           |
| --------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Orden de bits en resultados | **little-endian**: el string lista q_{n−1}…q₀ (el qubit 0 a la DERECHA) | wire 0 = bit MÁS significativo (a la izquierda, según el orden de `wires`)      | La misma medición se lee al revés entre frameworks. Congelar `decode()` por framework con G6 como vector (KB2-02 §1.6) |
| Pauli string "ZZI"          | actúa Z en q₁ y q₂ (¡leído de derecha a izquierda!)                     | los operadores se declaran por wire explícito (`qml.PauliZ(0) @ qml.PauliZ(1)`) | Construir `SparsePauliOp` con un helper que reciba (i, j) y arme el string — nunca a mano                              |
| Ángulo de rotación          | RZZ(θ) = e^(−i(θ/2)ZZ)                                                  | `qml.IsingZZ(φ)` = e^(−i(φ/2)ZZ) — igual, pero verificar SIEMPRE al portar      | Factores de 2 silenciosos entre papers/frameworks: validar contra el mínimo autovalor NumPy                            |
| Semillas                    | `seed=` en el primitive + `algorithm_globals.random_seed`               | `np.random.seed` / seed del optimizador                                         | Una capa sin semilla = corrida no replayable (checklist completo en KB2-04 §8)                                         |

## 5 · El resto del paisaje (qué es cada cosa y por qué NO este mes)

| Herramienta                     | Qué es                                                                         | Postura CHIMERA                                                                                                                      | Licencia                                         |
| ------------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------ |
| **OpenQASM 3**                  | IR textual estándar de circuitos                                               | **usar como artefacto de evidencia** (§1) — costo cero                                                                               | Apache-2.0 (spec; verificada en vivo 2026-07-14) |
| **dimod + neal** (D-Wave Ocean) | `BinaryQuadraticModel` = contenedor QUBO/Ising agnóstico + simulated annealing | **candidato liviano**: un baseline heurístico extra (diversidad, nota 04 §1.1) y un QUBO portable entre solvers, sin hardware D-Wave | Apache-2.0 (verificada en vivo 2026-07-14)       |
| Cirq                            | DSL de Google, momentos explícitos                                             | descartar: duplica a Qiskit sin ganancia aquí                                                                                        | Apache-2.0 ⚠️                                    |
| CUDA-Q                          | simulación acelerada por GPU (NVIDIA)                                          | anotar Fase 2 si crecen las instancias; nada que ganar ≤ 14 qubits                                                                   | ⚠️ verificar                                     |
| Amazon Braket / cloud QPUs      | acceso cloud multi-vendor                                                      | **descartar: rompe air-gap** (misma lógica que Sigstore en nota 02 §1.2)                                                             | —                                                |
| Qulacs / qsim                   | simuladores C++ ultrarrápidos                                                  | innecesario a esta escala; `lightning`/`Aer` sobran                                                                                  | ⚠️                                               |
| Yao.jl                          | el stack cuántico de Julia                                                     | fuera del stack Python del freeze                                                                                                    | ⚠️                                               |

```python
# Idiom 5 — el QUBO portable + tercer baseline en 6 líneas (si se adopta dimod/neal)
import dimod, neal
bqm = dimod.BinaryQuadraticModel.from_qubo(Q_dict)            # {(i,j): coef}
ss  = neal.SimulatedAnnealingSampler().sample(bqm, num_reads=1000, seed=42)
best = ss.first                                                # .sample, .energy
```

## 6 · Los compañeros clásicos (una línea de modelo mental cada uno; el contrato vive en las notas)

- **OR-Tools CP-SAT** (nota 10 es la spec): solver **entero** basado en SAT/CP — piensa en booleanos y propagación, no en gradientes; de ahí el escalado entero y el `max_deterministic_time`. Modelo mental: "le describís restricciones lineales sobre enteros; te devuelve óptimo PROBADO o cota".
- **pandapower** (nota 12): resuelve el **flujo de potencia** con Newton–Raphson sobre las ecuaciones no lineales de la red; "convergió" = el método iterativo encontró el punto de operación físico. No-convergencia ⇒ la isla propuesta puede no tener punto de operación — información física real, mapeada a `inconclusive` (nota 12 §1.3).
- **NetworkX:** teoría de grafos de referencia; aquí: construcción del grafo, `connected_components` (conectividad), `cut_size` (recomputar cortes), Kernighan–Lin (baseline).
- **SciPy optimizers** (los que mueven QAOA/VQE): `COBYLA` — sin gradientes, aproximaciones lineales en región de confianza; determinista dado el mismo punto inicial; parámetros que importan: `maxiter`, `rhobeg`, `tol`. `SPSA` — estocástico, 2 evaluaciones por paso sin importar la dimensión; el correcto bajo ruido de shots; **exige semilla**. `SLSQP` — con gradientes; solo tiene sentido en simulación exacta (VQE Reto 3).

## 7 · Cuánto se puede simular: la aritmética del statevector

Un statevector de n qubits = 2ⁿ amplitudes complex128 = **16 · 2ⁿ bytes**:

| n           | Memoria | Veredicto para el demo |
| ----------- | ------- | ---------------------- |
| 8 (grid CR) | 4 KB    | instantáneo            |
| 12 (LiH JW) | 64 KB   | instantáneo            |
| 20          | 16 MB   | fácil                  |
| 24          | 256 MB  | laptop ok              |
| 28          | 4 GB    | frontera de laptop     |
| 30          | 16 GB   | no en vivo             |

Regla derivada: **todo lo del hackathon (≤14 qubits) es territorio de simulación exacta** — lo que convierte al `StatevectorSampler/Estimator` en un cuasi-oráculo y hace reproducibles los verdicts. La frontera ~28–30 qubits es el número honesto para la pregunta "¿por qué simulan en vez de usar hardware?": debajo de ella el simulador es _mejor_ evidencia (exacto, determinista, air-gapped).

> **Nota (2026-07-18, enunciado oficial):** para el evento manda otra cifra: el **emulador H2 de
> Quantinuum ofrece tratamiento exacto hasta 26 qubits** (única disponibilidad confirmada;
> hardware real sin confirmar). La tabla de arriba sigue valiendo para simulación local
> (Aer/Selene). Consecuencia para la escalera de instancias: ieee30 (30 nodos) queda fuera del
> emulador — solo clásico.

## 8 · Recursos de estudio de fundamentos (nuevos — no están en KB-fuentes)

- **Quantum Country** (Matuschak & Nielsen) — <https://quantum.country> — el mejor onboarding conceptual corto (memoria espaciada) para quien entra de cero.
- **PennyLane Codebook** — <https://pennylane.ai/codebook> — ejercicios interactivos exactamente sobre las piezas del Reto 2.
- **IBM Quantum Learning: "Basics of Quantum Information"** (curso de J. Watrous) — <https://learning.quantum.ibm.com> — el formal riguroso; el viejo Qiskit Textbook quedó deprecado a favor de esta plataforma.
- **Nielsen & Chuang**, _Quantum Computation and Quantum Information_ — la referencia canónica de escritorio (capítulos 1–2 y 4 bastan para CHIMERA).
- **Docs de OpenQASM 3** — <https://openqasm.com> — para el artefacto de evidencia de §1.

---

## Template de nota (consolidación 2026-07-14)

- **Patrón / mecanismo:** modelos mentales + 5 idioms de API (Qiskit/PennyLane/OpenQASM 3/dimod-neal), trampas de convención entre frameworks (§4), y la frontera honesta de simulación statevector (§7).
- **Decisión:** la tabla §5 fija posturas por herramienta (usar / candidato / descartar / Fase 2) — en particular: OpenQASM 3 **integrar** como artefacto de evidencia; dimod+neal **candidato**; Cirq/Qulacs/Yao **descartar**; Braket/cloud QPUs **descartar por air-gap**; CUDA-Q **Fase 2**.
- **Licencias:** **verificadas en vivo en la consolidación (2026-07-14, contra el LICENSE del repo oficial de cada una):** Qiskit, qiskit-aer, qiskit-optimization, qiskit-nature, PennyLane, dimod, dwave-neal, PySCF y la spec de OpenQASM 3 — todas **Apache-2.0**. Sin conflicto con la postura open-core. Ratificación de Sebas pendiente.
- **Impacto en contrato:** propone `evidence.circuit_digest` (aditivo — `qasm3.dumps` → SHA-256, alineado con el anexo de canonicalización). **REGISTRADO (S-E 2026-07-18): `docs/contract-freeze.md` §11** — dejó de ser contrato fantasma; dueño [confianza/ciencia].
- **Reconciliación contra la base lógica:** revisada en la consolidación — sin contradicciones; el descarte de Braket usa la misma lógica air-gap de trust/02. Observación de alcance: el plan decía "No frameworks" para Sebas — esta nota se justifica por las trampas de convención y la procedencia, pero las posturas integrar/descartar tocan vocabulario del plano de confianza: coordinar formato con Dylan. **Decidido (S-E 2026-07-18) — ratificación final de Sebas, ajustable bajo su criterio.**
