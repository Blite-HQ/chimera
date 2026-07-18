# Nota 02 (KB2-02) — Recetario de formulación por reto: del problema al circuito, con la matemática completa

**Rol:** las derivaciones paso a paso que convierten cada reto en algo ejecutable. El lado _proponente_ (cuántico/heurístico); el lado _verificador_ ya está especificado en las notas trust/10–12 y NO se repite aquí — solo se referencia.
**Convención:** se reutilizan los vectores de prueba de la nota trust/10 (G1–G6) como ejemplos, para que la formulación cuántica y el verificador compartan la misma verdad.
**Prerrequisito:** nota 01 (fundamentos).
**Fecha:** 2026-07-14 · **Estado:** vigente — movida de `docs/kb2-02…` a `knowledge/quantum/` en la consolidación (2026-07-14); el template de nota se aplica en la sección final.

---

## 1 · RETO 1 — Red eléctrica: grafo → QUBO → Ising → circuito QAOA

### 1.1 Del grafo al objetivo Max-Cut

Grafo ponderado G = (V, E, w). Variable binaria xᵢ ∈ {0,1} = zona del nodo i. La arista (i,j) aporta al corte sii xᵢ ≠ xⱼ:

```
xᵢ ⊕ xⱼ = xᵢ(1−xⱼ) + xⱼ(1−xᵢ) = xᵢ + xⱼ − 2·xᵢxⱼ
C(x) = Σ_(i,j)∈E  w_ij · (xᵢ + xⱼ − 2·xᵢxⱼ)          ← a MAXIMIZAR
```

### 1.2 Regla de construcción de la matriz Q (convención simétrica, maximización)

```
Q_ii = Σ_{j : (i,j)∈E} w_ij        (grado ponderado del nodo i)
Q_ij = Q_ji = −w_ij                 (por cada arista)
⇒  C(x) = xᵀ Q x
```

**Ejemplo trabajado — G6 de la nota 10** (triángulo pesado: w₀₁=1, w₁₂=2, w₀₂=3; óptimo a mano = 5):

```
      ⎡ 4  −1  −3 ⎤            diag: Q₀₀=1+3=4, Q₁₁=1+2=3, Q₂₂=3+2=5
Q  =  ⎢−1   3  −2 ⎥
      ⎣−3  −2   5 ⎦

Chequeo por enumeración (los 2³ estados — hacelo una vez a mano, es el hábito rung-1):
x=000→0 · 001→5 · 010→3 · 011→4 · 100→4 · 101→3 · 110→5 · 111→0
máx = 5 en x=[0,0,1] (canónico con x₀=0) ✓ coincide con la nota 10.
Verificación puntual: x=[0,0,1] ⇒ xᵀQx = Q₂₂ = 5 ✓ ; x=[0,1,1] ⇒ Q₁₁+Q₂₂+2Q₁₂ = 3+5−4 = 4 ✓
```

### 1.3 Restricción de balance de carga: las DOS rutas y su matemática

Sea dᵢ la demanda (MW) del nodo i, D = Σdᵢ, y τ la tolerancia de desbalance.

**Ruta A — no codificar, verificar/reparar (la que CHIMERA ya adopta):** el QUBO queda Max-Cut puro; el balance y la conectividad los chequea el `ExecutionVerifier` post-hoc (nota 12) y, si hace falta, se repara clásicamente. Es el patrón validado por la literatura de islanding con QAOA (REGRID, en KB-fuentes §1.2). Ventaja: circuito mínimo. Costo: el muestreador puede proponer soluciones infactibles (y eso es _información_, no vergüenza — queda en la traza).

**Ruta B — codificar el balance como penalización** (para comparar en la ablación, o si el jurado pregunta "¿y las restricciones dónde están?"):

```
F(x) = C(x) − λ·( Σᵢ dᵢxᵢ − D/2 )²
```

Expansión usando x² = x (todo queda cuadrático — por eso las igualdades lineales SÍ son QUBO-friendly):

```
( Σ dᵢxᵢ − D/2 )² = Σᵢ dᵢ(dᵢ−D)·xᵢ + 2·Σ_{i<j} dᵢdⱼ·xᵢxⱼ + D²/4
⇒  Q_ii += λ·dᵢ·(D − dᵢ)          Q_ij += −λ·dᵢ·dⱼ          (+ constante, ignorable)
```

En moneda Ising queda aún más limpio (con x=(1−s)/2): la penalización = (λ/4)·(Σ dᵢsᵢ)² ⇒ **agrega un término J_ij = λ·dᵢdⱼ/2 entre TODO par de nodos** (grafo completo) y ningún término lineal (porque el target es exactamente D/2). Consecuencia de circuito: una capa extra de RZZ todos-contra-todos por capa QAOA → n(n−1)/2 RZZ adicionales. En 8 nodos: +28 RZZ/capa. Es el costo real de "codificar la restricción".

**Elección de λ (el hiperparámetro que rompe demos):**

1. **Normalizar primero:** usar d̂ᵢ = dᵢ/D (adimensional, Σd̂=1). Sin normalizar, con demandas en MW la escala de λ queda absurda (10⁻⁴) y el paisaje se descalibra.
2. **Cota de suficiencia:** violar el balance en δ cuesta λδ²; la ganancia máxima posible de corte es ≤ W (peso total). Para que ninguna violación > τ̂ sea rentable: **λ > W / τ̂²**. Con el grid de ejemplo del doc CHIMERA (W = 5.9, τ̂ = 0.3): λ > 65.6.
3. **Cota de cordura:** λ demasiado grande aplana el paisaje (el espectro lo domina la penalización y QAOA deja de "ver" el corte). Guía práctica del tutorial de QUBO de Glover et al. (arXiv:1811.11538): penalización del orden de 0.75–1.5× la magnitud estimada del objetivo, y ajuste empírico: resolver → correr el constraint checker → si infactible, λ×2; si factible con margen, probar λ/2.
4. **λ es dato, no código:** vive en `knowledge/islanding/` con digest (corrección #4 / nota 11) y se registra en la evidencia — sin eso, dos corridas con λ distinto no son comparables.

**Conectividad de islas — por qué NO se codifica:** la conexidad es una propiedad _global_ del subgrafo; expresarla en un QUBO exige variables auxiliares de flujo o de árbol generador (O(n·|E|) qubits extra — Lucas, arXiv:1302.5843, ya en KB-fuentes). A escala NISQ nadie lo hace: se verifica post-hoc (chequeo `island_connectivity` de la nota 12). Tener esta razón matemática a mano evita que alguien "mejore" el QUBO agregando 40 qubits.

### 1.4 QUBO → Ising → Hamiltoniano (con el ejemplo G6 cerrado)

Fórmulas generales (Q simétrica, **minimización** — para maximizar C usá Q′ = −Q):

```
x = (1−s)/2 ⇒   J_ij = Q_ij/2 (i<j)     hᵢ = −(Q_ii + Σ_{j≠i} Q_ij)/2     offset = ½ΣQ_ii + ½Σ_{i<j}Q_ij
H = Σ hᵢ·Zᵢ + Σ_{i<j} J_ij·Zᵢ Zⱼ   (+ offset·I)
```

Para **Max-Cut puro** las fórmulas colapsan a la forma clásica (verificalo: h se cancela):

```
C(x) = W/2 − ⟨H_C⟩      con   H_C = Σ_(i,j)∈E (w_ij/2)·Zᵢ Zⱼ ,   W = Σ w_ij
```

**G6 cerrado de punta a punta:** H_C = 0.5·Z₀Z₁ + 1.0·Z₁Z₂ + 1.5·Z₀Z₂ ; W/2 = 3.
Estado fundamental: s = (+1,+1,−1) → ⟨H_C⟩ = 0.5 − 1 − 1.5 = **−2** → C = 3 − (−2) = **5** ✓.
En Qiskit (little-endian: el carácter de la derecha es el qubit 0):

```python
H = SparsePauliOp(["IZZ", "ZZI", "ZIZ"], coeffs=[0.5, 1.0, 1.5])   # (0,1), (1,2), (0,2)
```

Este mini-pipeline (Q → H → mínimo autovalor con NumPy → 5) es un **test unitario perfecto**: valida la formulación cuántica contra el mismo vector que valida a CP-SAT. Una sola verdad, dos formulaciones.

### 1.5 El circuito QAOA resultante (p capas)

```
1. H en cada qubit                                  (superposición uniforme)
2. por capa k = 1..p:
     por arista (i,j):  RZZ(γ_k · w_ij)  en (i,j)   (costo)
     [Ruta B: además RZZ(γ_k · λ · d̂ᵢ d̂ⱼ) en todo par]
     por qubit i:       RX(2·β_k)                    (mixer)
3. medir todos
```

- **Qubits = nodos** (8 para el grid CR de ejemplo; 3 para G6).
- **Profundidad** ≈ p·(2|E| CNOT + |E| RZ + n RX) tras compilar (RZZ = CX·RZ·CX, KB2-01 §3).
- **Parámetros:** 2p. Con p ∈ {1,2} y semillas INTERP (KB2-01 §7) el demo converge en decenas de iteraciones.

### 1.6 Decodificación (donde se pierden los puntos)

1. **Endianness:** el bitstring de Qiskit lista q_{n−1}…q₀. Asignación del nodo i = `int(bitstring[::-1][i])`. Congelar esta función con G6 como vector: la muestra dominante debe decodificar a corte 5.
2. **Recomputar SIEMPRE el corte clásicamente** sobre cada bitstring muestreado — jamás confiar en la "energía" del optimizador (es exactamente el paso 1 del `ExactSolverVerifier`, nota 10 §1.1, aplicado por el proponente a sí mismo).
3. **Canonicalizar la simetría de complemento** (x ↔ 1−x da el mismo corte): flipear cada muestra para que x₀=0 antes de agrupar/comparar — coherente con la ruptura de simetría de la nota 10 y necesario para las estadísticas de KB2-04 §4.
4. Lo que se reporta como claim: la **asignación** + el **valor recomputado** (+ backend, p, shots, seeds). El resto es trabajo de los verificadores.

---

## 2 · RETO 2 — Potabilidad del agua: del CSV al kernel cuántico

### 2.1 Pipeline de datos (el orden importa: fuga de datos)

```
split estratificado (train/test)  →  imputar mediana (fit SOLO en train)
→ seleccionar k=4 features (importancia RF, fit SOLO en train; registrar cuáles)
→ MinMaxScaler a [0, π] (fit SOLO en train)  →  submuestrear train a 100–200
```

⚠️ Ajustar imputador/selector/scaler sobre TODO el dataset antes del split es **data leakage**: infla las métricas de ambos modelos y contamina la comparación cuántico-vs-clásico. La regla: todo `fit` ocurre dentro del fold de train; el pipeline (con sus parámetros ajustados) es parte de la evidencia.

**Por qué escalar a [0, π] exactamente:** con AngleEmbedding, RY(x)|0⟩ tiene ⟨Z⟩ = cos(x), y cos es inyectiva **solo** en [0, π]. Escalar a [0, 2π] hace que x y 2π−x produzcan estados con igual ⟨Z⟩ (colisión de datos distintos); no escalar deja features gigantes dando vueltas al círculo. Es una línea de código con un teorema detrás.

### 2.2 El kernel de fidelidad: circuito, costo y presupuesto

Circuito para k(x, x′): preparar U(x)|0⟩⁴, aplicar U†(x′), medir; **k = Pr(observar |0000⟩)**. Con simulador statevector el valor es exacto; con shots, es una proporción muestral (estadística en KB2-04 §2).

**Aritmética del presupuesto (la razón matemática del submuestreo):** la matriz de Gram es simétrica con diagonal k(x,x)=1 gratis ⇒

```
m_train = 150  →  150·149/2 = 11 175 circuitos (bloque train)
m_test  = 50   →  50·150    =  7 500 circuitos (bloque test×train)
                              ≈ 18 675 evaluaciones de kernel en total
```

Con 3 276 muestras completas serían ~5.4 millones — de ahí el límite duro. El bloque train se **cachea** (`np.save`) con su digest: recomputarlo en vivo es opcional, verificar su hash no.

### 2.3 Del kernel al clasificador (y la reparación PSD)

El SVM con kernel precomputado resuelve el dual estándar; lo único cuántico que entra es la matriz K. Detalles que importan:

- **Desbalance de clases (61/39):** `class_weight="balanced"` implementa w_c = m/(2·m_c) — reponderación matemática, no cosmética; sin ella el clasificador trivial "todo no-potable" ya da ~61% de accuracy (por eso accuracy sola miente; métricas correctas en KB2-04 §6).
- **PSD bajo ruido de shots:** K es PSD en teoría (KB2-01 §9.4), pero el ruido muestral puede producir autovalores levemente negativos. Reparación estándar: clip espectral `K ← V·max(Λ,0)·Vᵀ`. Registrar λ_min(K) antes de reparar — es una propiedad rung-4 perfecta (receta en KB2-04 §5) y evidencia de calidad del kernel.

### 2.4 La alternativa VQC y por qué el kernel gana en costo (con números)

VQC: f_θ(x) = ⟨Z₀⟩ tras AngleEmbedding(x) + StronglyEntanglingLayers(θ); pérdida L(θ) = media[(f_θ(x) − y±)²] con y± = 2y−1; gradiente por parameter-shift (KB2-01 §10).

Conteo de parámetros: StronglyEntanglingLayers con L capas y n qubits tiene **L·n·3** parámetros → L=3, n=4 ⇒ 36. Costo de UNA época con parameter-shift: 2·36 evaluaciones de circuito **por muestra** ⇒ con m=100: 7 200 circuitos/época ⇒ 50 épocas ≈ **360 000 circuitos**, contra ~19 000 del kernel completo. La elección "Quantum Kernel primero, VQC como stretch" del doc CHIMERA no es gusto: es un orden de magnitud.

### 2.5 Feature map alternativo (si sobra tiempo): ZZFeatureMap

Forma de Havlíček et al. (ya citado en KB-fuentes): capa H + fases e^(i·φ(x)) con φᵢ = xᵢ y φᵢⱼ = (π−xᵢ)(π−xⱼ) sobre pares (entrelaza los features). Más expresivo que AngleEmbedding y clásicamente más difícil de simular — pero recordar KB2-01 §9.6: más profundidad/qubits ⇒ riesgo de concentración del kernel. Con 4 qubits, 1–2 repeticiones máximo, y comparar contra AngleEmbedding en la ablación (dos feature maps = diversidad también del lado proponente).

---

## 3 · RETO 3 — Simulación de materiales: de la molécula al VQE

> **Nota de drift (2026-07-18, contra el enunciado oficial de la Quantathon CR 2026):** esta
> sección se escribió ANTES de los enunciados. El Challenge 3 oficial NO es química
> molecular/VQE: es **TFIM (Ising de campo transversal) con Trotterización** — circuito de
> Trotter eficiente; corrección física = ⟨Zᵢ⟩ y ⟨ZᵢZᵢ₊₁⟩ dentro de **5%** de la diagonalización
> exacta (ED vía PySCF/SciPy); barrido h/J ∈ {0.5, 1, 2}; análisis del error de Trotter;
> escalado en número de espines; ODS 7/9/12/13. Todo lo de abajo queda como conocimiento de
> química (Fase 2 / referencia), NO como receta del reto. La receta TFIM se escribe como nota
> nueva si se activa el segundo reto condicional (= C3, decisión 2026-07-18; el patrón de doble
> ancla NumPy/ED se traslada tal cual — la ED del TFIM juega el mismo rol FORMAL_EXACT). Si
> alguna vez se retomara el Reto 2: el baseline oficial es SVM-RBF con validación cruzada de 5
> particiones, 5 métricas + matriz de confusión — la §2 (split único estratificado) difiere de
> ese protocolo.

### 3.1 El Hamiltoniano electrónico (segunda cuantización)

Bajo Born–Oppenheimer (núcleos fijos a distancia r), el problema es electrónico:

```
H = Σ_pq h_pq · a†_p a_q  +  ½ Σ_pqrs g_pqrs · a†_p a†_q a_r a_s   (+ E_NN)
```

- h_pq: integrales de un electrón (cinética + atracción nuclear); g_pqrs: repulsión electrón-electrón. Los calcula PySCF a partir de la geometría y la **base**.
- E_NN: repulsión núcleo-núcleo — una **constante clásica** que NO entra al Hamiltoniano de qubits (ver §3.5, la trampa).
- a†/a: operadores fermiónicos con anticonmutación {a_p, a†_q} = δ_pq — esa anticonmutación es lo que el mapeo a qubits debe preservar.

**Base STO-3G (mínima) y presupuesto de qubits (JW: qubits = spin-orbitales = 2 × orbitales espaciales):**

| Molécula | Orbitales espaciales       | Qubits (JW) | Qubits (Parity + reducción) |
| -------- | -------------------------- | ----------- | --------------------------- |
| H₂       | 2 (1s de cada H)           | 4           | **2**                       |
| LiH      | 6 (Li: 1s,2s,2p×3 + H: 1s) | 12          | 10 (menos con active space) |
| BeH₂     | 7                          | 14          | 12                          |

### 3.2 Mapeo fermión → qubit

**Jordan–Wigner:** a†_p = (⊗_{q<p} Z_q) ⊗ (X_p − iY_p)/2. La "cola de Z" preserva la anticonmutación; el precio es que operadores locales se vuelven Pauli strings largas. Resultado para H₂/STO-3G: un `SparsePauliOp` de ~15 términos con X, Y, Z (ya no diagonal — por eso VQE mide agrupando bases, a diferencia del H_C diagonal del Reto 1).

**Parity + two-qubit reduction:** explota que el número de partículas por sector de spin se conserva ⇒ dos qubits llevan información redundante y se eliminan. H₂ pasa de 4 a **2 qubits** — el VQE de 2 qubits converge en segundos y es el mejor candidato a demo en vivo. Para LiH/BeH₂, el complemento es `ActiveSpaceTransformer` (congelar el core 1s): reduce orbitales activos antes de mapear.

### 3.3 Hartree–Fock y el ansatz UCCSD

- **HF:** solución de campo medio; en la representación de qubits es un **bitstring** (orbitales ocupados = 1). Es el estado inicial del ansatz y un ancla barata: **UCCSD con θ=0 debe reproducir E_HF exactamente** — chequeo rung-4 de una línea antes de optimizar nada.
- **UCCSD:** |ψ(θ)⟩ = e^(T(θ) − T†(θ)) |HF⟩ con T = T₁ + T₂ (excitaciones simples y dobles que conservan spin), Trotterizado a circuito. Conteo para H₂ (2 electrones, 2 orbitales): 2 simples + 1 doble = **3 parámetros** — un paisaje trivial de optimizar (SLSQP, decenas de iteraciones).
- **Loop VQE:** minimizar ⟨H_qubit⟩(θ). Por el principio variacional (KB2-01 §5) el resultado acota E₀ desde arriba — la desigualdad E_VQE ≥ E_exacta es en sí un verificador (KB2-04 §5).

### 3.4 Las anclas exactas del Reto 3 (el análogo del CP-SAT)

1. **FCI (Full Configuration Interaction):** diagonalización exacta en la base — el "óptimo exacto" de la química. Lo da PySCF.
2. **`NumPyMinimumEigensolver` sobre el MISMO H_qubit:** diagonaliza la matriz 2ⁿ×2ⁿ (para H₂ reducido: 4×4 — trivial). Es el ancla rung-1 **sin PySCF y air-gapped**: si VQE y NumPy discrepan, el bug es del VQE; si NumPy y FCI discrepan, el bug es del mapeo. Dos anclas independientes = el mismo principio de diversidad de la nota 10 §1.1 (CP-SAT ↔ fuerza bruta), trasladado a química.

### 3.5 La trampa contable №1: energía electrónica vs total

El autovalor del Hamiltoniano de qubits es la energía **electrónica**; la energía **total** = electrónica + E_NN. PySCF (`fci.FCI(...).kernel()`) devuelve la **total**. Comparar el eigenvalue crudo del VQE contra el FCI de PySCF sin sumar E_NN produce un "error" de ≈ +0.72 Ha en H₂ — quinientas veces la precisión química, y es pura contabilidad.

**Valores de referencia estándar para H₂/STO-3G @ 0.735 Å** (regenerarlos con PySCF y congelarlos como vectores del corpus, mismo rol que G1–G6 de la nota 10; no citarlos de memoria en el pitch):

```
E_NN ≈ +0.7200 Ha      E_HF(total) ≈ −1.1167 Ha      E_FCI(total) ≈ −1.1373 Ha
⇒ energía de correlación ≈ 20.5 mHa  — HF solo NO alcanza precisión química (1.6 mHa);
  UCCSD sí debe recuperarla casi completa en esta base (esa ES la demo).
```

### 3.6 La curva de disociación (el visual + verificador de forma)

Protocolo: barrer r ∈ [0.3, 2.5] Å, correr VQE y FCI en cada punto, graficar E(r). Propiedades verificables de la curva (rung 4, forma de la física):

1. Mínimo cerca de r_eq ≈ 0.735 Å (H₂).
2. E_VQE(r) ≥ E_FCI(r) en TODO punto (variacional — un solo punto violado ⇒ bug).
3. Límite disociado: E(r→∞) → 2·E(átomo H). RHF falla célebremente aquí (disociación incorrecta); FCI/UCCSD no — mostrar ese contraste en la misma gráfica es la narrativa "por qué correlación importa" en una imagen.

Unidades y precisión química (tabla completa en KB2-04 §7): trabajar TODO en Hartree, convertir solo al presentar.

---

## 4 · Mapa de conexión con el resto del corpus

| Este doc produce                         | Lo consume                                                                    |
| ---------------------------------------- | ----------------------------------------------------------------------------- |
| Q, H_C, circuito, claim del Reto 1       | `ExactSolverVerifier` (nota 10) y `ExecutionVerifier` (nota 12) los verifican |
| λ, features seleccionados, scaler, seeds | `knowledge/` versionado + campos de `evidence` (notas 03/11)                  |
| decodificación canónica x₀=0             | estadísticas de consenso rung 5 (KB2-04 §4) y corpus rung 3                   |
| anclas FCI/NumPy del Reto 3              | mismo patrón de diversidad de anclas de la nota 04 §1.1                       |
| conteos de circuitos/presupuestos        | planificación del demo + `runtime_ms` esperado                                |

---

## Template de nota (consolidación 2026-07-14)

- **Patrón / mecanismo:** las derivaciones proponente por reto (§1–3) con G6 cerrado de punta a punta como verdad compartida con el verificador.
- **Decisión:** Ruta A (no codificar restricciones; verificar/reparar post-hoc) como default del Reto 1, Ruta B solo para la ablación (§1.3); kernel primero / VQC como stretch en el Reto 2 (§2.4, justificado con números, no con gusto).
- **Licencias:** N/A directo (derivación matemática); las licencias de las librerías del stack corresponden a la nota 03.
- **Impacto en contrato:** produce los claims que consumen `ExactSolverVerifier` (trust/10) y `ExecutionVerifier` (trust/12); λ/features/scaler/seeds viven en `knowledge/` versionado con digest y se registran en `evidence` (§4). **PENDIENTE:** los valores de referencia H₂ de §3.5 deben regenerarse con PySCF y congelarse como vectores del corpus — el corpus de benchmarks todavía no existe (ver README del directorio).
- **Reconciliación contra la base lógica:** revisada en la consolidación — respeta la separación proponente/verificador (trust/10–12) y ADR-029 (λ es dato versionado en `knowledge/islanding/`, no código del engine). **Ratificación de Sebas: PENDIENTE.**
