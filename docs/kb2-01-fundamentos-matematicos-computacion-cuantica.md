# KB2-01 — Fundamentos matemáticos de computación cuántica (lo mínimo indispensable para CHIMERA)

**Rol:** base teórica del equipo. Todo lo que aparece en los retos (QAOA, VQE, kernels) se reduce a lo de este documento.
**No repite:** contratos/arquitectura (notas 01–18) ni fuentes externas (KB-fuentes). Aquí está *la matemática*, no los links ni los adapters.
**Convención:** notación Dirac + unicode; verificable a mano con los vectores de la nota 10.

---

## 1 · Álgebra lineal esencial

Todo estado cuántico de n qubits es un **vector complejo unitario** en dimensión 2ⁿ; toda operación es una **matriz unitaria** (U†U = I); toda cantidad medible es una **matriz hermitiana** (H† = H).

- **Producto interno** ⟨φ|ψ⟩: número complejo; |⟨φ|ψ⟩|² ∈ [0,1] es el "solapamiento" (base del kernel cuántico del Reto 2).
- **Autovalores/autovectores:** H hermitiana ⇒ autovalores **reales** λ_k y autovectores ortonormales |k⟩. Descomposición espectral: H = Σ λ_k |k⟩⟨k|. Los tres retos son, en el fondo, "encontrá el autovalor mínimo de una H".
- **Producto tensorial (Kronecker) ⊗:** compone sistemas. dim(A⊗B) = dim(A)·dim(B) ⇒ n qubits viven en ℂ^(2ⁿ). Es la razón del muro exponencial de la simulación clásica (ver KB2-03 §6 para la tabla de memoria).

## 2 · El qubit y la medición

|ψ⟩ = α|0⟩ + β|1⟩ con |α|² + |β|² = 1.

**Postulado de medición (base computacional):** medir da `0` con probabilidad |α|² y `1` con |β|²; el estado colapsa al resultado. Consecuencias operativas:

1. Un circuito cuántico es una **fábrica de distribuciones de probabilidad** sobre bitstrings — por eso QAOA "muestrea candidatos" en vez de "devolver la respuesta".
2. Repetir el circuito N veces ("shots") estima las probabilidades con error estadístico ~1/√N (la matemática exacta está en KB2-04 §2 — es lo que llena `evidence` honestamente).

**Multi-qubit y entrelazamiento:** |ψ⟩ = Σ_z c_z |z⟩ sobre los 2ⁿ bitstrings z. Un estado es *entrelazado* si no se factoriza como producto de qubits individuales (ej. Bell: (|00⟩+|11⟩)/√2). El entrelazamiento es lo que las capas ZZ de QAOA y los feature maps entrelazantes de QML introducen.

## 3 · Compuertas que CHIMERA realmente usa

| Compuerta | Matriz / acción | Dónde aparece |
| --- | --- | --- |
| X | intercambia \|0⟩↔\|1⟩ | mixer de QAOA (vía RX) |
| Z | \|1⟩ → −\|1⟩ (fase) | Hamiltonianos de costo |
| H | \|0⟩ → (\|0⟩+\|1⟩)/√2 | superposición inicial de QAOA; feature maps |
| RY(θ) = e^(−iθY/2) | rotación en Y | AngleEmbedding (Reto 2) |
| RX(θ), RZ(θ) | rotaciones análogas | mixer QAOA; ansätze |
| CNOT (CX) | flip del target si control=1 | entrelazamiento; compilación de RZZ |
| **RZZ(θ) = e^(−i(θ/2)·Z⊗Z)** | fase condicional a la paridad de 2 qubits | **la capa de costo de QAOA** |

Identidad de compilación clave (para leer circuitos transpilados): `RZZ(θ) = CX · RZ(θ)_target · CX`. Cada arista del grafo = 2 CNOT + 1 RZ por capa QAOA — de ahí la estimación de profundidad.

## 4 · Observables, valores esperados y Pauli strings

Un observable H hermitiano tiene valor esperado ⟨H⟩ = ⟨ψ|H|ψ⟩. Cualquier H de n qubits se escribe como combinación real de **Pauli strings** (productos tensoriales de {I,X,Y,Z}):

```
H = Σ_k c_k · P_k ,   c_k ∈ ℝ,  P_k ∈ {I,X,Y,Z}^⊗n
```

Los Hamiltonianos de los Retos 1 y (mapeado) 3 viven aquí; en Qiskit es literalmente `SparsePauliOp` (KB2-03 §2).

**El truco que hace todo medible:** si H contiene solo I y Z (Hamiltoniano **diagonal**, caso Max-Cut), entonces cada bitstring z es autovector y ⟨H⟩ se estima **contando bitstrings**: medí en base Z, evaluá la función de costo clásica sobre cada muestra, promediá. No hay magia — es un promedio muestral (estadística en KB2-04 §2).

## 5 · Hamiltonianos, estado fundamental y el principio variacional

**El teorema que sostiene QAOA y VQE** (2 líneas): expandiendo |ψ⟩ = Σ c_k|k⟩ en autovectores de H,

```
⟨ψ|H|ψ⟩ = Σ |c_k|² · E_k  ≥  E₀ · Σ |c_k|²  =  E₀
```

⇒ **ningún estado da energía menor que la del fundamental**. Corolarios operativos:

1. Minimizar ⟨H(θ)⟩ sobre parámetros θ acota E₀ **desde arriba** — VQE/QAOA solo pueden sobreestimar, nunca subestimar.
2. **Regla de verificación gratis (Reto 3):** si `E_VQE < E_FCI − tol` ⇒ hay un **bug**, no un descubrimiento (unidades mezcladas, Hamiltoniano distinto, energía nuclear omitida). Es el espejo exacto del caso "candidato mejor que el óptimo probado ⇒ error fail-loud" de la nota 10 §1.2, ahora para química.

## 6 · Ising y QUBO: el mismo objeto en dos monedas

- **QUBO** (variables binarias x ∈ {0,1}ⁿ): minimizar (o maximizar) `xᵀ Q x`, con lo lineal en la diagonal porque x² = x.
- **Ising** (spines s ∈ {−1,+1}ⁿ): `E(s) = offset + Σᵢ hᵢ sᵢ + Σ_{i<j} J_ij sᵢ sⱼ`.

**Cambio de moneda exacto:** `x = (1−s)/2` ⇔ `s = 1−2x` (convención: x=0 ↔ s=+1). Para Q **simétrica** en minimización:

```
J_ij   = Q_ij / 2                       (i<j)
h_i    = −(Q_ii + Σ_{j≠i} Q_ij) / 2
offset = (Σ_i Q_ii)/2 + (Σ_{i<j} Q_ij)/2
```

(Derivación completa y ejemplo numérico con el grafo G6 de la nota 10: KB2-02 §1.4.)

**El puente a lo cuántico:** reemplazá cada spin sᵢ por el operador Zᵢ → `H = Σ hᵢ Zᵢ + Σ J_ij Zᵢ Zⱼ`. Como H es diagonal, sus autovectores son los bitstrings y su autovalor mínimo ES la solución del QUBO. "Resolver el QUBO" = "encontrar el estado fundamental de H". Esa identificación es todo el Reto 1.

⚠️ **Trampa de convenciones (fuente #1 de bugs de factor 2):** hay tres convenciones de Q en circulación — simétrica completa, triangular superior (Q_ij^tri = 2·Q_ij^sim), y "maximizar vs minimizar" (Q vs −Q). Nunca mezclar fórmulas de fuentes distintas sin re-derivar; el chequeo de sanidad es siempre evaluar xᵀQx a mano contra los vectores G1–G6 de la nota 10.

## 7 · QAOA: la teoría en una página

**Intuición adiabática:** si evolucionás lentamente desde el fundamental de un H fácil (el *mixer* H_M = Σ Xᵢ, cuyo fundamental es la superposición uniforme |+⟩^⊗n) hacia el H_C del problema, terminás en el fundamental de H_C (teorema adiabático). QAOA discretiza esa evolución en p pasos parametrizados.

**El ansatz:**

```
|ψ(γ,β)⟩ = [ e^(−iβ_p H_M) e^(−iγ_p H_C) ] ⋯ [ e^(−iβ_1 H_M) e^(−iγ_1 H_C) ] · H^⊗n |0⟩^⊗n
```

- 2p parámetros reales (γ₁..γ_p, β₁..β_p).
- Capa de costo: e^(−iγ H_C) = Π_{aristas} e^(−iγ (w_ij/2) Zᵢ Zⱼ) = Π **RZZ(γ·w_ij)** por arista.
- Capa mixer: e^(−iβ H_M) = Π **RX(2β)** por qubit.
- Loop híbrido: el circuito estima ⟨H_C⟩; un optimizador clásico (COBYLA/SPSA) ajusta (γ,β); al final se **muestrea** y cada muestra se evalúa clásicamente (nunca confiar solo en la energía reportada — nota 10 §1.1 paso 1 aplica igual al proponente cuántico).

**Hechos teóricos para calibrar expectativas (y para el pitch):**

- p→∞ recupera el algoritmo adiabático exacto; p finito es una aproximación.
- Cota conocida: en grafos 3-regulares, QAOA con p=1 garantiza approximation ratio ≈ **0.6924** (Farhi et al., ya en KB-fuentes) — compárese con el **0.878** garantizado clásicamente por Goemans–Williamson (SDP, 1995). Moraleja honesta: en instancias chicas el clásico gana o empata; el argumento cuántico es de escalamiento, no de instancia chica. Esto es exactamente la narrativa que el doc CHIMERA §16 ya adopta — aquí están los números que la respaldan.
- **Concentración y transferencia de parámetros** (Zhou et al., arXiv:1812.01041): los ángulos óptimos varían suavemente con p y se parecen entre instancias de la misma familia ⇒ heurísticas tipo INTERP (extrapolar los ángulos de p−1 como semilla de p) y warm-starts entre grafos similares. Útil para que el demo converja rápido y reproducible.
- **Simetrías del paisaje:** β es periódico en [0, π); con pesos enteros γ es periódico; y la simetría de complemento x↔1−x del Max-Cut implica soluciones degeneradas por pares (consecuencias prácticas en KB2-04 §4 y en la ruptura de simetría x₀=0 de la nota 10).

## 8 · VQE: la generalización de QAOA

Mismo principio variacional, pero: (a) H es **arbitrario** (no diagonal — el molecular tiene términos X e Y tras el mapeo), (b) el ansatz es libre (UCCSD, hardware-efficient) en vez de la alternancia costo/mixer. Se mide ⟨H⟩ agrupando Pauli strings por base de medición y se minimiza sobre θ. La matemática específica de moléculas (segunda cuantización, Jordan–Wigner, UCCSD) está en KB2-02 §3.

## 9 · QML: feature maps y kernels en 6 fórmulas

1. **Feature map** = preparar un estado que depende del dato: x ↦ |φ(x)⟩ = U(x)|0⟩^⊗n. Es el análogo cuántico de "mapear a un espacio de features".
2. **AngleEmbedding:** U(x) = ⊗ᵢ RY(xᵢ) — un feature por qubit, por eso el Reto 2 selecciona 4 features para 4 qubits. Requiere x escalado a [0, π] (la razón exacta en KB2-02 §2.2).
3. **Kernel de fidelidad:** k(x, x′) = |⟨φ(x′)|φ(x)⟩|². Circuito: aplicar U(x), luego U†(x′), medir; k = probabilidad de observar |0…0⟩.
4. **Por qué es un kernel válido:** k(x,x′) = Tr[ρ(x)·ρ(x′)] con ρ = |φ⟩⟨φ| — es un producto interno (Hilbert–Schmidt) entre matrices densidad ⇒ la matriz de Gram es **simétrica y semidefinida positiva** por construcción. Eso es lo que el SVM clásico necesita; el "quantum" entra SOLO por el kernel. (PSD es además una propiedad verificable rung-4 — receta en KB2-04 §5.)
5. **VQC** (la alternativa variacional): f_θ(x) = ⟨0|U†(x)W†(θ) · M · W(θ)U(x)|0⟩ con M = Z₀; se entrena minimizando una pérdida sobre etiquetas ±1.
6. **Advertencia teórica — concentración exponencial de kernels** (Thanasilp et al., arXiv:2208.11060): con muchos qubits o feature maps muy expresivos/profundos, k(x,x′) → constante para casi todo par ⇒ Gram ≈ identidad ⇒ el modelo no generaliza. Con 4 qubits y embedding de 1 capa CHIMERA está lejos del problema; es el argumento matemático para **no** "mejorar" el demo agregando qubits/capas al feature map.

## 10 · Gradientes de circuitos: parameter-shift y barren plateaus

- **Regla de parameter-shift** (Mitarai et al. arXiv:1803.00745; Schuld et al. arXiv:1811.11184): para una compuerta e^(−iθP/2) con P Pauli,

```
∂⟨H⟩/∂θ = ½ · [ f(θ + π/2) − f(θ − π/2) ]
```

**Exacta** (no es diferencia finita) y evaluable con el mismo circuito en 2 puntos — es lo que PennyLane usa por debajo cuando entrenás el VQC. Costo: 2 evaluaciones por parámetro por paso ⇒ el VQC del Reto 2 es caro por diseño (otra razón matemática para preferir el kernel, que no entrena circuito).
- **Barren plateaus** (McClean et al., arXiv:1803.11173): en circuitos aleatorios profundos, la varianza del gradiente decae exponencialmente con n ⇒ paisajes planos inentrenables. A la escala CHIMERA (4–12 qubits, p≤2, ansätze someros) **no es bloqueante**, pero es la respuesta técnica si un juez pregunta "¿y esto entrena a escala?": mitigaciones conocidas = circuitos someros, costos locales, inicialización estructurada (HF en VQE; INTERP en QAOA).

## 11 · Glosario relámpago ES/EN

| ES | EN | Una línea |
| --- | --- | --- |
| escalón / peldaño | rung | nivel de la escalera de verificación (nota 03) |
| estado fundamental | ground state | autovector de energía mínima |
| valor esperado | expectation value | ⟨ψ\|H\|ψ⟩ |
| recocido | annealing | evolución hacia el fundamental (simulado o cuántico) |
| ansatz | ansatz | familia parametrizada de circuitos |
| capa / profundidad | layer / depth | repeticiones p; # de compuertas secuenciales |
| muestreo / disparos | sampling / shots | ejecuciones repetidas del circuito |
| mapeo fermión→qubit | fermion-to-qubit mapping | Jordan–Wigner, Parity (Reto 3) |
| brecha de optimalidad | optimality gap | \|cota − incumbente\| (nota 10 §1.3) |
| razón de aproximación | approximation ratio | valor obtenido / óptimo (KB2-04 §1) |

---

### Referencias nuevas introducidas por este doc (no están en KB-fuentes ni en las notas)

- Zhou, Wang, Choi, Pichler, Lukin — *QAOA: Performance, Mechanism, and Implementation on Near-Term Devices* — arXiv:1812.01041 (concentración/transferencia de parámetros, INTERP).
- Mitarai et al. — *Quantum Circuit Learning* — arXiv:1803.00745 · Schuld et al. — *Evaluating analytic gradients on quantum hardware* — arXiv:1811.11184 (parameter-shift).
- McClean et al. — *Barren plateaus in quantum neural network training landscapes* — arXiv:1803.11173.
- Thanasilp et al. — *Exponential concentration in quantum kernel methods* — arXiv:2208.11060.
- Goemans & Williamson 1995 (JACM) — cota clásica 0.878 para Max-Cut vía SDP.
