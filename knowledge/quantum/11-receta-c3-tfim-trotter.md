# Nota 11 (KB2-11) — Receta C3: TFIM + Trotterización, con la matemática completa

**Rol:** la derivación paso a paso que convierte el Challenge 3 en algo ejecutable — el
análogo de la nota 02 §1 para el reto 1. El lado _proponente_ (circuito de Trotter) y el
lado _ancla_ (diagonalización exacta) se derivan POR SEPARADO: el contrato de S-C exige
implementaciones independientes, y esta nota mantiene esa separación en la propia
matemática (§1.3 vs §2).
**Prerrequisito:** nota 01 (fundamentos); nota 02 §1.4-§1.5 (de donde se reutiliza la
familia de compuertas RZZ+RX del QAOA).
**Fecha:** 2026-07-31 · **Estado:** VIGENTE — escrita por G1 (Fase 1 Mejorado); completa
el STUB que el saneamiento S3 dejó con nombre. **Es la receta C3 vigente**: la de
química/VQE de la nota 02 §3 quedó supersedida el 2026-07-18 (supersede S-E).
**Fuentes:** Childs, Su, Tran, Wiebe, Zhu — _Theory of Trotter Error with Commutator
Scaling_ — PRX 11, 011020 (2021) · Heyl, Hauke, Zoller — _Quantum localization bounds
Trotter errors in digital quantum simulation_ — Sci. Adv. 5, eaau8342 (2019) · Pfeuty —
_The one-dimensional Ising model with a transverse field_ — Ann. Phys. 57, 79 (1970)
(ancla analítica del stretch G6) · Lieb, Robinson — Commun. Math. Phys. 28, 251 (1972)
(cono de luz; sustenta §5.3) · `docs/mejorado/03-research.md` R1 (versiones verificadas
en vivo contra el venv: qiskit 2.5.0, qiskit-aer 0.17.2, scipy 1.18.0 — **cero
dependencias nuevas**).

> **Todos los números de esta nota se computaron en vivo** (venv del repo, 2026-07-31)
> con los tres experimentos de §6. Ninguno se cita de memoria.

---

## 1 · Patrón / mecanismo

### 1.1 El Hamiltoniano y la convención (lo primero que se congela)

Cadena **abierta** de N espines — el enunciado habla de cadenas, y el borde es física
que se mide, no un detalle a esconder con condiciones periódicas:

```
H  =  −J · Σ_{i=0}^{N−2} Z_i Z_{i+1}  −  h · Σ_{i=0}^{N−1} X_i
```

- **J > 0** (ferromagnético), fijado a **J = 1** como unidad: el barrido del enunciado es
  sobre el cociente adimensional **h/J ∈ {0.5, 1, 2}**, así que h numéricamente ES h/J.
  El tiempo queda en unidades de 1/J.
- **h/J = 1 es el punto crítico** de la cadena infinita (Pfeuty 1970). Los tres puntos
  del barrido cubren entonces fase ordenada (0.5), criticidad (1) y fase desordenada
  (2) — el barrido no es decorativo.
- **N ∈ {6, 8, 12}** ⇒ dimensiones 64, 256, **4096**. La ED cabe holgada: N=12 tarda
  **0.08 s** con `scipy.sparse.linalg.expm_multiply` (medido), determinista y air-gapped.

⚠️ **La convención NO es libre.** La literatura alterna entre `H = −J ΣXX − h ΣZ` y
`H = −J ΣZZ − h ΣX` (una es la otra conjugada por Hadamard en cada sitio). Se congela la
segunda porque los observables del enunciado son ⟨Zᵢ⟩ y ⟨ZᵢZᵢ₊₁⟩: con esta convención el
término de acoplamiento es diagonal en la misma base en que se mide — exactamente el
patrón del H_C del reto 1 (nota 02 §1.4). Cambiar de convención sin rotar los
observables produce números plausibles y equivocados.

### 1.2 El protocolo: quench desde el estado polarizado

**Estado inicial |ψ₀⟩ = |0⟩^⊗N** (todos los espines arriba en Z): el fundamental de la
parte ZZ a campo cero. Encender h de golpe es un **quench súbito** — el protocolo
estándar de dinámica fuera de equilibrio, y el único que hace de ⟨Zᵢ⟩ un observable con
dinámica no trivial.

> **Por qué NO |+⟩^⊗N:** el operador de paridad P = Π_i X_i conmuta con H, y |+⟩^⊗N es
> autoestado de P con autovalor +1. Como P Z_i P† = −Z_i, sobre un estado P-simétrico
> **⟨Z_i⟩ = 0 para todo tiempo, exactamente**. El observable estrella del enunciado sería
> idénticamente cero y cualquier proponente «acertaría». Es una trampa de diseño de
> corpus, no una sutileza — queda registrada.

**Tiempo de evolución t = 1.0** (unidades 1/J): dinámica visible, cono de luz sin tocar
el borde (§5.3), ED de N=12 instantánea.

**Observables** (los del enunciado, en el instante final t):

```
⟨Z_i⟩          i = 0 … N−1     (N valores — magnetización longitudinal por sitio)
⟨Z_i Z_{i+1}⟩  i = 0 … N−2     (N−1 valores — correlador de vecinos)
```

### 1.3 Trotterización: la descomposición y el circuito

H se parte en dos piezas que NO conmutan entre sí, pero cuyos términos internos SÍ
conmutan (todos los Z_iZ_{i+1} entre ellos; todos los X_i entre ellos) — por eso cada
pieza se exponencia **exactamente** y el único error es el de partir A de B:

```
A ≡ H_zz = −J Σ_i Z_i Z_{i+1}        (diagonal en la base Z)
B ≡ H_x  = −h Σ_i X_i                (diagonal en la base X)
```

**Lie–Trotter (orden 1)**, un paso de tamaño dt, y su producto de r pasos:

```
S₁(dt) = e^{−i·dt·A} · e^{−i·dt·B}        e^{−iH·t} ≈ [S₁(dt)]^r ,  dt = t/r
```

**Suzuki–Strang (orden 2)**, simétrica:

```
S₂(dt) = e^{−i·(dt/2)·B} · e^{−i·dt·A} · e^{−i·(dt/2)·B}
```

**Mapeo a compuertas (donde se pierden los puntos).** Con las convenciones de Qiskit
`RZZ(θ) = e^{−i(θ/2)·Z⊗Z}` y `RX(θ) = e^{−i(θ/2)·X}`:

```
e^{−i·dt·A} = Π_i exp(+i·J·dt·Z_iZ_{i+1})  ⇒  RZZ(θ_zz)  con  θ_zz = −2·J·dt
e^{−i·dt·B} = Π_i exp(+i·h·dt·X_i)         ⇒  RX(θ_x)    con  θ_x  = −2·h·dt
```

Los **signos negativos vienen del signo menos del Hamiltoniano** (ferromagnético). Un
`+2·J·dt` simula un antiferromagneto: números creíbles, física distinta. Este mapeo se
verificó en vivo — el camino por circuito (Qiskit `Statevector`) reproduce el Trotter
por operadores dispersos **a 5 decimales** en toda la malla (§6.2).

**Circuito por paso (orden 1), N qubits:**

```
por paso k = 1..r:
    por i = 0..N−2:   RZZ(−2·J·dt)  en (i, i+1)     ← capa de acoplamiento
    por i = 0..N−1:   RX(−2·h·dt)   en i            ← capa de campo
```

Profundidad ≈ r·(N−1 RZZ + N RX); tras compilar, RZZ = CX·RZ·CX (KB2-01 §3). **Es la
misma familia de compuertas del QAOA vivo** (nota 02 §1.5), con ángulos dictados por la
física (J·dt, h·dt) en vez de por un optimizador — de ahí que se reusen Aer, seeds y
digest de qasm3 sin tocar nada del runtime.

### 1.4 Cota de error genérica (y por qué no es la que manda aquí)

**Cota de conmutadores (Childs et al. 2021)** para orden 1 con r pasos:

```
‖ e^{−iHt} − [S₁(t/r)]^r ‖  ≤  (t²/2r)·‖[A,B]‖
```

Para el TFIM el conmutador se computa a mano:

```
[Z_iZ_{i+1}, X_j] = 0  salvo j ∈ {i, i+1};    [Z_i, X_i] = 2i·Y_i
⇒ [A,B] = J·h · Σ_i ( 2i·Y_iZ_{i+1} + 2i·Z_iY_{i+1} )
⇒ ‖[A,B]‖ ≤ 4·J·h·(N−1)
⇒ error ≤ 2·J·h·(N−1)·t·dt        (con dt = t/r)
```

Cota **lineal en dt y lineal en N**. Es correcta, y es **enormemente pesimista** para lo
que este reto mide — por la razón del punto siguiente.

### 1.5 El hallazgo: aquí el orden 1 converge O(dt²) y le GANA al orden 2

Medición (N=8, h/J=1, t=1, orden 1, error relativo de la serie ⟨Zᵢ⟩ — definición §4.1):

| pasos r | dt     | error       | razón vs. anterior |
| ------- | ------ | ----------- | ------------------ |
| 2       | 0.5    | 0.32550     | —                  |
| 4       | 0.25   | 0.07305     | 4.46               |
| 8       | 0.125  | 0.01780     | 4.10               |
| 16      | 0.0625 | 0.00442     | 4.03               |
| 32      | 0.031  | 0.00110     | 4.02               |

Razón **≈ 4 al partir dt ⇒ O(dt²)**, no el O(dt) que §1.4 promete para orden 1. Y el
orden 2 (Strang), en la misma malla y con el mismo número de pasos, es **~2× PEOR**
(0.60265 / 0.14425 / 0.03551 / 0.00884 / 0.00221) con idéntica pendiente O(dt²).

**El mecanismo (verificado, no conjeturado).** La corrección BCH líder de S₁ es
proporcional a **i[A,B]**, que para este H es un operador hermítico **puramente
imaginario** en la base Z (todos sus términos llevan exactamente una Y). Escribiendo
i[A,B] = i·M con M real y antisimétrico, sobre cualquier estado **real** ψ:

```
⟨ψ| i[A,B] |ψ⟩ = i · ψᵀ M ψ = 0        (forma cuadrática antisimétrica sobre vector real)
```

H es real-simétrico en la base Z y |0…0⟩ es real ⇒ ψ(t) permanece real salvo fase
global, y ⟨Zᵢ⟩/⟨ZᵢZᵢ₊₁⟩ son observables reales-diagonales. **El término O(dt) se cancela
idénticamente** y el primero que sobrevive es O(dt²).

**Control que cierra el argumento** (§6.3, medido): repitiendo la sonda con un estado
inicial **complejo** (|0…0⟩ + i|0…01⟩, normalizado), el valor esperado del conmutador
deja de anularse — **⟨i[A,B]⟩ = −2.000** contra **+0.000e+00** en el estado real — y la
razón de convergencia del orden 1 cae a **2.00** (O(dt), lo que la teoría genérica
predice). El efecto es de simetría, no una coincidencia numérica.

**Consecuencias operativas (decisiones §2):**

1. El circuito del proponente usa **orden 1**: más barato (una capa RX por paso en vez
   de dos) **y** más preciso para estos observables. Elegir Strang «porque es de orden
   superior» sería peor por ambos ejes.
2. La relación metamórfica «razón ≈ 4 al partir dt» **NO prueba que la fórmula sea de
   orden 2** en este montaje — la cumple también el orden 1. Se registra como
   `trotter_convergence_ratio` con esa semántica escrita, jamás como «verifica el
   orden». Escribirlo al revés sería un verificador que miente.

### 1.6 Umbral de Heyl: el barrido de dt es física, no numérica

Heyl, Hauke y Zoller (Sci. Adv. 2019) muestran que en simulación digital existe un
**umbral en dt**: por debajo, el error en observables locales queda acotado de forma
esencialmente independiente del tamaño del sistema y del tiempo simulado (el sistema
Trotterizado está localizado en el espacio de Floquet); por encima, una transición tipo
caos cuántico hace proliferar el error. La evidencia de la malla es consistente: a
r = 16 los errores son planos en N (§5.3) y el salto a r = 2 es de **dos órdenes de
magnitud** (0.0044 → 0.3255 a h/J=1; 0.0090 → **1.0339** a h/J=2), no una degradación
suave. Esto convierte el barrido de dt exigido por el enunciado en un experimento **con
predicción**, y le da al control negativo de §4.3 su justificación física.

---

## 2 · Decisión (qué se congela)

| Parámetro                    | Valor congelado                       | Causa                                                                 |
| ---------------------------- | ------------------------------------- | --------------------------------------------------------------------- |
| Hamiltoniano                 | `−J ΣZ_iZ_{i+1} − h ΣX_i`, abierto    | §1.1 — observables diagonales en la base de acoplamiento              |
| J                            | 1.0 (unidad)                          | el barrido es sobre h/J adimensional                                  |
| h/J                          | {0.5, 1, 2}                           | enunciado — ordenada / crítica / desordenada                          |
| N                            | {6, 8, 12}                            | enunciado; N=12 ⇒ 4096 dim, ED en 0.08 s                              |
| Estado inicial               | \|0⟩^⊗N                                | §1.2 — \|+⟩^⊗N anularía ⟨Zᵢ⟩ por paridad                               |
| t                            | 1.0                                   | dinámica visible; cono de luz sin tocar el borde (§5.3)               |
| Fórmula de Trotter           | **Lie–Trotter orden 1**               | §1.5 — más barata Y más precisa aquí                                  |
| Pasos del corpus             | **r = 16** (dt = 0.0625)              | §4.2 — margen ≈5.5× bajo el criterio oficial en el peor punto         |
| Control negativo             | **r = 2** (dt = 0.5)                  | §4.3 — falla el criterio de forma inequívoca                          |
| Tolerancia relativa          | **0.05** (criterio oficial ≤5%)       | C-14 (#106); entra al `verifier_params_digest`                        |
| Definición de error relativo | normalizada por la escala L∞ de la serie | §4.1 — la por-elemento es indefinida donde ⟨Zᵢ⟩ cruza cero           |

**Las anclas (el análogo del par CP-SAT + fuerza bruta del reto 1):**

1. **ED — `scipy.sparse.linalg.expm_multiply`** sobre el MISMO H, sin construir el
   propagador denso. Determinista, air-gapped, cero dependencias nuevas. Es el rol
   FORMAL_EXACT del criterio oficial → `ExactDiagonalizationVerifier` (`anchor_kind:
   solver`, recompute VIVO).
2. **Series congeladas del corpus** — la misma verdad grabada con digest, contrastada
   por `GroundTruthVerifier` (`anchor_kind: dataset`). **Grupo de independencia
   DISTINTO** al de la ED: recompute vivo y dato congelado son métodos distintos, no
   islas de una misma corrida (S-C §3). Son las dos patas que la policy C3 exige.
3. **Fermiones libres / BdG (stretch G6)** — Jordan–Wigner + Bogoliubov (Pfeuty 1970)
   da un checker independiente de la ED. **Alcance honesto y acotado**: en esta
   convención `⟨X_i⟩` y `⟨Z_iZ_{i+1}⟩` son cuadráticos en los fermiones (fáciles), pero
   **`⟨Z_i⟩` es un operador de cuerda** — exige Pfaffianos / determinantes de Toeplitz.
   El stretch entrega doble ancla para **⟨ZᵢZᵢ₊₁⟩, no para ⟨Zᵢ⟩**; prometer AL4 sobre
   ⟨Zᵢ⟩ por esta vía sería falso y queda escrito antes de implementarlo.

**Descartado con causa:** `TrotterQRTE` de qiskit-algorithms (envuelve lo mismo que ~10
líneas y quita el control fino por paso — research R1); quimb/TenPy/QuTiP (la ED con
scipy basta a N ≤ 12; TenPy queda catalogado como tercera ancla quasi-exacta si alguna
vez se va a N > 14); condiciones periódicas (§1.1).

---

## 3 · Licencias

**Ninguna dependencia nueva.** ED = `scipy` (BSD-3, ya en el stack vía
`blite-cap-numeric[full]`); circuito = `qiskit` + `qiskit-aer` (Apache-2.0, ya en
`blite-cap-quantum[qaoa]`, verificadas en vivo 2026-07-14, nota 03). El reto 3 es el
único de los tres que no mueve la fila de licencias de la nota 03.

---

## 4 · El criterio de aceptación, hecho preciso

### 4.1 Qué significa «dentro de 5%» (la definición que faltaba)

El enunciado dice «⟨Zᵢ⟩ y ⟨ZᵢZᵢ₊₁⟩ dentro de 5% de la ED». Leído como error relativo
**por elemento** el criterio está **mal planteado**, porque los observables cruzan cero.
Caso real medido — N=8, h/J=1, t=1: `⟨Z₀⟩ = −0.033022` mientras
`max_i|⟨Zᵢ⟩| = 0.343345`. Un criterio por elemento exigiría en ese sitio
|Δ| ≤ 0.00165: **33× más estricto** que en el sitio de máxima magnitud, por el mero
accidente de que la serie pasa por cero ahí. Un punto de la malla podría «fallar» por
ruido de redondeo.

**Definición congelada — error relativo a la escala de la serie (norma L∞):**

```
err(candidata, referencia) =  max_i |cand_i − ref_i|  /  max( max_i |ref_i| , ε )
```

con ε = 1e−12 (guarda contra serie idénticamente nula). Se evalúa **por separado** para
la serie ⟨Zᵢ⟩ y para la serie ⟨ZᵢZᵢ₊₁⟩, y **ambas** deben cumplir ≤ 0.05. Es una cota
uniforme sobre la serie, insensible a los ceros, y estrictamente más informativa que un
promedio (que escondería un sitio malo entre muchos buenos).

### 4.2 Márgenes reales en la malla (medido, r = 16, orden 1)

| N | h/J | err ⟨Zᵢ⟩    | err ⟨ZᵢZᵢ₊₁⟩ | margen vs. 5% |
| - | --- | ----------- | ------------ | ------------- |
| 6 | 0.5 | 0.00060     | 0.00101      | ~50×          |
| 6 | 1.0 | 0.00429     | 0.00295      | ~12×          |
| 6 | 2.0 | 0.00903     | 0.00489      | ~5.5×         |
| 8 | 0.5 | 0.00060     | 0.00102      | ~50×          |
| 8 | 1.0 | 0.00442     | 0.00321      | ~11×          |
| 8 | 2.0 | **0.00903** | 0.00496      | **~5.5×**     |

El peor punto de la malla es **h/J = 2** (campo fuerte ⇒ el término que no conmuta pesa
más). El margen mínimo es ~5.5×: suficiente para que el criterio no dependa de la
versión de BLAS, y ajustado para que el test siga siendo capaz de cazar una regresión
real — un criterio con margen 1000× no verifica nada.

### 4.3 El control negativo (parte del contrato, no opcional)

S-C §3 lo exige literalmente: «error 0.0000 con dt grande = sospecha de código
compartido». Con **r = 2 (dt = 0.5)** el proponente debe **FALLAR** el criterio:

| N | h/J | err ⟨Zᵢ⟩    | err ⟨ZᵢZᵢ₊₁⟩ | veredicto esperado     |
| - | --- | ----------- | ------------ | ---------------------- |
| 8 | 0.5 | 0.04569     | **0.07867**  | fail (por la serie ZZ) |
| 8 | 1.0 | **0.32550** | 0.23746      | fail                   |
| 8 | 2.0 | **1.03393** | 0.40682      | fail                   |

Nótese h/J = 0.5: la serie ⟨Zᵢ⟩ **pasaría** (0.04569 < 0.05) y solo el correlador lo
caza. **Las dos series se verifican, no una** — el punto más ordenado de la malla es
precisamente donde un verificador de una sola serie daría un falso «pass».

### 4.4 Propiedades verificables (PROPERTY_RULE — invariantes, no comparaciones)

Deterministas, independientes del ancla, computables sobre la salida del proponente:

| Propiedad                   | Enunciado                                          | Qué caza                                              |
| --------------------------- | -------------------------------------------------- | ----------------------------------------------------- |
| `norm_preserved`            | ‖ψ‖ = 1 (unitariedad)                              | compuerta mal armada / normalización rota             |
| `parity_conserved`          | ⟨Π_i X_i⟩ constante en el tiempo                   | bug — **jamás** error de Trotter (ver abajo)          |
| `observable_bounds`         | \|⟨Zᵢ⟩\| ≤ 1 y \|⟨ZᵢZᵢ₊₁⟩\| ≤ 1                       | salida fuera del espectro                             |
| `initial_condition`         | a t=0: ⟨Zᵢ⟩ = 1 y ⟨ZᵢZᵢ₊₁⟩ = 1                     | estado inicial equivocado                             |
| `echo_identity`             | U(−dt)·U(dt) = 1 a tolerancia numérica             | signo de ángulo invertido (§1.3)                      |
| `trotter_convergence_ratio` | err(dt/2)/err(dt) → ≈ 4                            | convergencia rota — **NO** «prueba orden 2» (§1.5)    |

`parity_conserved` es la más valiosa: la paridad Z₂ se conserva **exactamente** bajo cada
capa del circuito (ambas capas conmutan con P), así que una violación no admite la
excusa «es error de Trotter» — es un bug. Es el análogo del `island_connectivity` del
reto 1: una propiedad que el error de aproximación no puede explicar.

---

## 5 · El corpus C3 (identidad, forma y procedencia)

### 5.1 Identidad (regla generalizada de S-C §4)

```
dataset_id = "tfim-corpus/chain-n<N>-h<h/J×10, 2 dígitos>@v1"
```

Nueve puntos (3 N × 3 h/J): `chain-n6-h05`, `chain-n6-h10`, `chain-n6-h20`,
`chain-n8-h05`, **`chain-n8-h10`**, `chain-n8-h20`, `chain-n12-h05`, `chain-n12-h10`,
`chain-n12-h20`.

> La forma **no se elige aquí**: `tfim-corpus/chain-n8-h10@v1` ya está congelada por el
> fixture de costura `tests/fixtures/contract/generalidad/predicate-ground-truth.json`
> (S-C, Fase 0) y su test anti-drift. Esta nota la ADOPTA y la extiende a los otros
> ocho puntos; cambiarla exigiría ceremonia sobre el fixture.

Digest **EMBEBIDO** y self-consistente: SHA-256 del JSON canónico **sin el campo
`digest`**, con **el mismo algoritmo que el corpus de islanding**
(`json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=True)` — el que
`scripts/verify_corpus_digests.py` ya aplica) y la misma doctrina: **se reporta, no se
sobreescribe**. Una regeneración que no reproduzca el digest es un hallazgo, no una
actualización.

### 5.2 Qué guarda cada punto

Las series de ED de referencia (⟨Zᵢ⟩, ⟨ZᵢZᵢ₊₁⟩), los parámetros que las definen (N, J,
h, t, estado inicial, condición de borde) y **el método declarado** (`expm_multiply` +
versión de scipy) — sin el método, dos corridas no son comparables.

El corpus **NO guarda el circuito ni sus ángulos**: eso es del proponente, y mezclarlos
sería exactamente el «código compartido» que el control negativo de §4.3 busca.

### 5.3 Procedencia y la propiedad que la malla regala

**El corpus se GENERA, no se descarga**: la ED del propio Hamiltoniano es la verdad y el
generador es determinista y air-gapped. Procedencia = `curated_internal` con el script y
su digest ⇒ **techo AL3 sin `proof`** (decisión #103 intacta).

Hecho medido que sirve de chequeo de cordura del generador: a t = 1 los valores de
**borde** y de **bulk** coinciden a 6 cifras entre N = 6, 8 y 12 (⟨Z₀⟩ = 0.672315 y
⟨Z_bulk⟩ = 0.868053 a h/J = 0.5 en los tres N). Es el **cono de luz de Lieb–Robinson**:
a t = 1 la correlación todavía no distingue una cadena de 6 de una de 12. Si el
generador produjera dependencia en N a este tiempo, el bug está en el generador — y de
paso confirma que t = 1 no está midiendo artefactos de tamaño finito.

---

## 6 · Reproducibilidad de esta nota

Los tres experimentos que sostienen los números, todos en el venv del repo
(2026-07-31), todos deterministas:

1. **§4.2 / §4.3 — malla de errores**: ED (`expm_multiply` sobre H disperso) contra
   Trotter por operadores dispersos, órdenes 1 y 2, r ∈ {2,4,8,16,32}, N ∈ {6,8},
   h/J ∈ {0.5,1,2}.
2. **§1.3 — equivalencia circuito ↔ operadores**: el circuito Qiskit (`rzz(−2·J·dt)` +
   `rx(−2·h·dt)`, `Statevector`) reproduce el Trotter por operadores dispersos a 5
   decimales en toda la malla. Es la validación del **mapeo de ángulos**, NO una
   validación cruzada de implementaciones: comparten la fórmula, no el código.
3. **§1.5 — mecanismo del O(dt²)**: `⟨i[A,B]⟩` = +0.000e+00 sobre |0…0⟩ y −2.000 sobre
   un estado complejo; razón de convergencia 4.00 contra 2.00 respectivamente.

---

## 7 · Impacto en contrato

- **C-14 (#106) es la única extensión del kernel**: `Differential` gana el literal
  `EXACT_DIAGONALIZATION` (un status que NO es de proceso — mapea a verdict por
  comparación, como `OPTIMAL`) y `relative_tolerance: float | None`. La tolerancia
  **entra al `verifier_params_digest`**: dos corridas con tolerancia distinta jamás
  comparten digest de params.
- **Cero techos rotos** (decisión #103): `formal_exact` sin `proof` topa AL3. El AL4
  llegaría solo con el checker independiente del stretch G6 — y §2 registra que ese
  checker cubre ⟨ZᵢZᵢ₊₁⟩, no ⟨Zᵢ⟩.
- **Cero vocabulario de escenario en manifests** (ADR-029): las capabilities son
  `blite.quantum.trotter_evolve` (evolución temporal de un operador de espines dado como
  DATO) y `blite.numeric.exact_evolve` (evolución exacta del mismo operador). El TFIM, el
  barrido h/J y el protocolo de quench viven **aquí**, en `knowledge/`, y en los datos
  del corpus — jamás en el manifest.

## 8 · Reconciliación contra la base lógica (`docs/invariants.md`)

- **INV-2 / PR2 (el verificador jamás es un modelo):** la ED es un proceso numérico
  determinista y el corpus es un dato congelado. Ninguna de las dos anclas es un modelo.
- **Independencia proponente/verificador (S-C §3):** el proponente evoluciona un
  **circuito** (Qiskit: RZZ/RX + `Statevector`); el ancla evoluciona el **operador**
  (`scipy.sparse.linalg.expm_multiply`). Rutas de código, librerías y representaciones
  distintas. El control negativo de §4.3 es la prueba viva de que no comparten código:
  con dt grande **deben divergir**, y divergen por dos órdenes de magnitud.
- **Regla fail-loud transversal (nota 07 §1.1):** un proponente que reporte error 0.0000
  contra la ED con dt grande NO es un descubrimiento — es sospecha de código compartido,
  y el test que lo caza es de primera clase.
- **ADR-029 / ADR-008:** el conocimiento del reto vive en esta nota y en el corpus; las
  capabilities entran como plugins con manifests genéricos.
- Sin contradicciones detectadas con los invariantes congelados.
