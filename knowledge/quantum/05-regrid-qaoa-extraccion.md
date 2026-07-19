# Nota 05 — REGRID-QAOA: extracción de ecuaciones exactas y mapeo contra la formulación CHIMERA

**Ítem del plan (§4, Sebas):** cerrar el pendiente №4 del README del directorio — "REGRID-QAOA a medias: citado y usado como justificación de la Ruta A, pero sin extracción de sus ecuaciones específicas". Esta nota extrae la formulación completa (ecuaciones, pipeline, setup, métricas) y la mapea pieza por pieza contra la nota 02 §1.
**Fecha:** 2026-07-14 · **Estado:** investigación de consolidación (Dylan) — pendiente validación y ratificación de Sebas
**Fuentes:** arXiv:2606.15083 **v2** (título v2: _"REGRID-QAOA: A Resource-Efficient Graph-Reduced Hybrid QAOA Framework for Physics-Constrained Power System Islanding"_; Jiang, Zhang, Liang, Guan, Li, Venayagamoorthy; v1 2026-06-13, v2 2026-06-28) — abs y HTML completo **verificados en vivo 2026-07-14**. Licencia del paper: arXiv non-exclusive license. **Sin repositorio de código público** (buscado en vivo 2026-07-14: ni el abstract ni los comments declaran código; la búsqueda web tampoco lo encuentra) — todo lo de abajo se extrajo del texto, y cualquier código derivado se implementa desde las ecuaciones.

> Convención de esta nota: numeración de ecuaciones = la del paper (v2, versión HTML). Notación matemática/pseudocódigo únicamente — **no es código de producción**.

---

## 1 · Patrón / mecanismo

### 1.1 El problema como lo formula REGRID (Eqs. 11–17)

Grafo de la red G = (V, E) con buses particionados en generadores V_G, cargas V_L y tránsito V₀. Variables de decisión **one-hot**: y_{i,k} ∈ {0,1}, "el bus i está en la isla k", con K islas.

**Objetivo (Eq. 11) — minimizar la potencia activa interrumpida** por las líneas cortadas:

```
min  Σ_{k≠h} Σ_{i∈V_k, j∈V_h, (i,j)∈E}  (|p_ij| + |p_ji|)/2
```

donde p_ij es el flujo de potencia activa por la línea (i,j) **de un flujo de potencia ya resuelto** (los pesos NO son topológicos: salen de la física del punto de operación).

**Restricciones:**

| Eq. | Restricción                  | Forma                                                                 |
| --- | ---------------------------- | --------------------------------------------------------------------- |
| 12  | Partición exacta             | V_k ∩ V_h = ∅ ∀k≠h; ⋃_k V_k = V                                       |
| 13  | Tamaño mínimo de isla        | \|V_k\| ≥ N_min ∀k                                                    |
| 14  | Generadores mínimos por isla | \|V_k ∩ V_G\| ≥ N_{G,min} ∀k                                          |
| 15  | Cargas mínimas por isla      | \|V_k ∩ V_L\| ≥ N_{L,min} ∀k                                          |
| 16  | Coherencia                   | generadores del mismo grupo coherente van a la misma isla             |
| 17  | **Conectividad**             | 𝒞(G[V_k]) = 1 ∀k (cada isla es un subgrafo conexo, chequeado por DFS) |

### 1.2 Codificación QUBO (Eqs. 22–33)

**Objetivo de corte (Eq. 22)** — nótese que cuenta las aristas _cortadas_ como costo (minimización):

```
H_cut = Σ_{(i,j)∈E} w_ij · (1 − Σ_{k=1}^{K} y_{i,k} · y_{j,k})      con  w_ij := (|p_ij| + |p_ji|)/2
```

**Penalizaciones algebraicas** (todas con slacks binarios para las desigualdades):

```
One-hot (Eq. 24):       H_h    = λ_h  · Σ_{i∈V} ( Σ_k y_{i,k} − 1 )²
Tamaño (Eq. 25):        H_s    = λ_M  · Σ_k ( Σ_i y_{i,k} − N_min − s_k^(M) )²
Generadores (Eq. 26):   H_gen  = λ_G  · Σ_k ( Σ_{g∈V_G} y_{g,k} − N_{G,min} − s_k^(G) )²
Cargas (Eq. 27):        H_load = λ_L  · Σ_k ( Σ_{ℓ∈V_L} y_{ℓ,k} − N_{L,min} − s_k^(L) )²
```

**Coherencia (Eq. 28)** — dos términos: castiga separar un grupo coherente y castiga juntar grupos distintos:

```
H_coh = λ_coh · [ Σ_c Σ_k Σ_{g<g' ∈ V_G^(c)} (y_{g,k} − y_{g',k})²
                + Σ_k Σ_{c<c'} Σ_{g∈V_G^(c), g'∈V_G^(c')} y_{g,k} · y_{g',k} ]
```

**Slacks binarios (Eqs. 29–31)** — codificación logarítmica; por isla:

```
s_k^(M) = Σ_{b=0}^{B_M−1} 2^b · u_{k,b}^(M)      con  B_M = ⌈log₂(N − N_min + 1)⌉
(análogo: B_G = ⌈log₂(|V_G| − N_{G,min} + 1)⌉,  B_L = ⌈log₂(|V_L| − N_{L,min} + 1)⌉)
```

**Surrogate de conectividad (Eq. 32)** — la conexidad exacta NO se codifica (no admite representación binaria polinómica compacta — el mismo argumento de Lucas que la nota 02 §1.3 ya usa); en su lugar, un surrogate cuadrático suave que penaliza nodos "aislados de sus vecinos de isla":

```
H_c = μ · Σ_k Σ_{i∈V} ( y_{i,k} − Σ_{j∈𝒩(i)} y_{i,k} · y_{j,k} )
```

**Hamiltoniano completo (Eq. 33):**

```
H_prob = H_cut + λ_h·H̄_h + λ_M·H̄_s + λ_G·H̄_gen + λ_L·H̄_load + λ_coh·H̄_coh + μ·H̄_c
```

⚠️ **El paper NO da fórmula de tuning para los λ**: solo exige λ > 0 y los fija empíricamente. Las cotas de la nota 02 §1.3 (λ > W/τ̂² de suficiencia + banda de Glover 0.75–1.5×) siguen siendo aporte propio de CHIMERA, no corrección de REGRID.

### 1.3 Ising y ansatz QAOA (Eqs. 34–37)

Cambio de moneda estándar (mismo de la nota 01): `z_{i,k} = 1 − 2·y_{i,k}` ∈ {±1}. Mixer transverso H_B = Σ_q σ_q^x, estado inicial |ψ₀⟩ = superposición uniforme, ansatz de p capas:

```
|ψ(γ,β)⟩ = Π_{ℓ=1}^{p} e^{−iβ_ℓ·H_B} · e^{−iγ_ℓ·H_prob} |ψ₀⟩
```

Optimizador clásico: COBYLA. El paper **no** declara estrategia de warm-start/inicialización de (γ,β) — INTERP (nota 00 §1.3) sigue siendo delta nuestro.

### 1.4 El truco central: energía modificada por DFS dentro del lazo (Eqs. 39–40)

No existe un "λ_cut" con ese nombre en el paper; el truco real es **λ_C**: la conectividad exacta entra como penalización _post-medición_, calculada clásicamente sobre cada bitstring muestreado:

```
H̃_prob(z) := H_prob(z) + λ_C · (1 − χ_C(z))        χ_C(z) ∈ {0,1}: 1 sii TODAS las islas son conexas (DFS)

Ẽ(γ,β) = E_{z ~ P_{γ,β}} [ H̃_prob(z) ]             ← lo que COBYLA minimiza, estimado sobre los S shots
```

Es decir: **el verificador de conectividad corre dentro del lazo de optimización, sin costar un solo qubit extra**. La factibilidad realimenta la actualización de parámetros, pero la restricción nunca se codifica en el circuito. Esta es una **tercera vía** que la nota 02 §1.3 no contempla: ni Ruta A pura (verificar solo post-hoc) ni Ruta B (codificar como penalización cuántica) — llamémosla provisionalmente **"Ruta A+"** (verificación clásica en el lazo).

### 1.5 Post-procesamiento / reparación: los cinco métodos M.1–M.5

Definiciones: Q(z) = energía QUBO; C(z) = Σ_k (ω(G[V_k(z)]) − 1) con ω = número de componentes conexas (C=0 ⇔ factible en conectividad); ganancia de flip (Eq. 45): **Δ_j(z) := Q(z ⊕ e_j) − Q(z)** (y análogamente Δ_jC(z) para conectividad), donde z ⊕ e_j flipea solo la variable j.

| Método                             | Mecanismo                                                                                                                                       | Garantía                                                                       |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| **M.1** QUBO-only descent          | greedy: j*= argmin_j Δ_j(z) mientras Δ_{j*} < 0                                                                                                 | ninguna sobre C(z*)=0                                                          |
| **M.2** two-stage sin restricción  | etapa 1: descenso QUBO; etapa 2 (si C>0): acepta CUALQUIER flip con Δ_jC < 0 aunque suba Q; reinicia; ≤ K iteraciones externas                  | factibilidad probable, Q puede degradarse                                      |
| **M.3** two-stage restringido      | igual a M.2 pero la etapa 2 solo flipea si además Δ_{j*}(z) < 0 (descenso estricto de Q)                                                        | termina siempre; falla si todo flip pro-conectividad sube Q                    |
| **M.4** penalty-relaxation descent | por ronda r: Q^(r)(z) = H_cut(z) + λ^(r)·Σ_m H_m(z) con **λ^(r) = λ / (1 + ρ·(r−1))** — relajar λ desbloquea reparaciones que M.3 tenía vedadas | **alcanza el óptimo de Gurobi en LOS SEIS casos**                              |
| **M.5** unified-energy descent     | descenso único sobre Q(z) + μ·C(z) con μ > max_{z,j} \|Δ_j(z)\|                                                                                 | factibilidad garantizada; riesgo de sesgo pro-conectividad (cortes subóptimos) |

**Pseudocódigo de M.3 (Algorithm 3 del paper):**

```
loop:
  while ∃j: Δ_j(z) < 0:            # etapa 1: descenso QUBO puro
    j* ← argmin_j Δ_j(z);  z ← z ⊕ e_{j*}
  if C(z) = 0: return z            # factible: listo
  j* ← argmin_{j ∈ J(z)} Δ_j(z)    # J(z) = {j : Δ_jC(z) < 0}
  if Δ_{j*}(z) < 0:  z ← z ⊕ e_{j*}   # solo si TAMBIÉN baja Q
  else: return z                   # atascado: se reporta como está
```

### 1.6 Reducción de recursos ("Graph-Reduced" del título)

Grupos de generadores coherentes cuyo subgrafo inducido es conexo se colapsan a un **super-bus** v_k* antes de construir el QUBO ("sin alterar el conjunto factible ni el objetivo de corte"). Ahorro: ΔQ = K · Σ(|V_G^(k)|−1) qubits de asignación. Presupuesto por caso (Tabla 2 del paper; sin→con reducción):

| Caso IEEE | Asignación | Auxiliares (slacks) | **Total** |
| --------- | ---------- | ------------------- | --------- |
| 9-bus     | 18→18      | 14→14               | 32→32     |
| 14-bus    | 28→24      | 22→20               | 50→44     |
| 24-bus    | 72→60      | 39→36               | 111→96    |
| 30-bus    | 60→58      | 26→26               | 86→84     |
| 39-bus    | 117→117    | 39→39               | 156→156   |
| 57-bus    | 114→104    | 30→26               | 144→130   |

Nótese el costo del one-hot: hasta el 9-bus con K=2 gasta 32 qubits. (Comparar con la bisección de CHIMERA: 1 qubit por nodo, sin slacks — 8 qubits para el grid CR. Ver §1.8.)

### 1.7 Setup experimental y métricas

- **Casos:** IEEE 9, 14, 24, 30, 39, 57 buses. K=2 (9/14/30/57) y K=3 (24/39). Pesos = flujos activos (§1.2).
- **Backends:** hardware real **ibm_marrakesh** (Heron r2, 156 qubits) + simulador con ruido **FakeMarrakesh**.
- **QAOA:** p = 1–4 según caso; shots S = 100–3000; COBYLA con presupuesto I_max = 2–3 iteraciones clásicas.
- **Baselines:** Gurobi (óptimo de referencia) y QAOA "vanilla" (sin post-procesamiento).
- **Métricas:** calidad del corte (potencia interrumpida total) vs óptimo de Gurobi; runtime cuántico; factibilidad (DFS + chequeos algebraicos post-medición).
- **Resultados titulares:** QAOA vanilla queda a **154%–3000% del óptimo** (p. ej. corte 7544.8 vs óptimo 229 en 39-bus); **M.4 recupera el óptimo de Gurobi en los seis casos** (M.3 en todos menos 24-bus) con overhead de ~3–4 s (12.4 s vs 9.4 s en 39-bus).
- **Cita textual del enfoque:** _"Post-processing addresses this gap by applying classical procedures after quantum measurement to convert these raw samples into feasible, high-quality solutions, for instance, by repairing constraint violations, selecting the best sample among measured outcomes, or applying local search corrections."_

### 1.8 Mapeo pieza por pieza contra la nota 02 §1 — ¿REGRID valida la Ruta A?

| Pieza CHIMERA (nota 02)                                                     | Pieza REGRID                                                                                                         | Veredicto                                                                                                                                                                                                                                                                                                                                  |
| --------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| §1.3 conectividad: "NO se codifica, se verifica post-hoc" (argumento Lucas) | Eq. 17 nunca se codifica exacta; surrogate suave (Eq. 32) + DFS clásico en el lazo (Eq. 39) y en la reparación       | ✅ **Valida la Ruta A** en su pieza más fuerte, con el mismo argumento matemático                                                                                                                                                                                                                                                          |
| §1.3 Ruta A: balance no codificado, verificar/reparar post-hoc              | Restricciones de conteo (tamaño/gen/carga) SÍ codificadas como penalizaciones con slacks (Ruta B)                    | ⚠️ **Matiza**: REGRID es híbrido A/B — algebraicas dentro, conectividad fuera. La ablación A-vs-B de la nota 02 queda MÁS justificada, no menos                                                                                                                                                                                            |
| §1.3 "si hace falta, se repara clásicamente" (sin especificar cómo)         | M.1–M.5 con Δ_j(z), garantías formales y ablación; M.4 = óptimo en todos los casos                                   | ✅ **Agrega lo que faltaba**: el recetario concreto de reparación. Es la especificación que la Ruta A no tenía                                                                                                                                                                                                                             |
| — (no existe en la nota 02)                                                 | Energía modificada H̃_prob en el lazo COBYLA (Eqs. 39–40): verificación clásica DENTRO del entrenamiento, cero qubits | ➕ **Aporte nuevo** ("Ruta A+"): candidato a extensión del proponente                                                                                                                                                                                                                                                                      |
| §1.1 objetivo Max-Cut (maximizar corte)                                     | Eq. 11 minimiza el flujo cortado (min-cut ponderado por física)                                                      | ✅ **RESUELTO por el enunciado oficial (2026-07-18): el reto se modela como Max-Cut (maximizar)** — la formulación de la nota 02 §1 es la del reto tal cual; el min-cut físico de REGRID queda como capa de realismo/extensión (los chequeos físicos se re-scopan a la sección de limitaciones + la extensión oficial "constraint mixers") |
| Bisección: x_i ∈ {0,1}, 1 qubit/nodo, 8 qubits                              | One-hot y_{i,k}: K qubits/nodo + slacks (32 qubits para 9-bus/K=2)                                                   | ✅ Para K=2 nuestra codificación es estrictamente más eficiente; el aparato de REGRID paga su costo solo para K≥3                                                                                                                                                                                                                          |
| §1.3 cotas de λ (W/τ̂², Glover)                                              | λ empíricos, sin fórmula                                                                                             | ✅ Nuestras cotas quedan como aporte propio                                                                                                                                                                                                                                                                                                |
| Pesos del grafo: sintéticos (grid CR)                                       | w_ij = (\|p_ij\|+\|p_ji\|)/2 de un flujo de potencia resuelto                                                        | ➕ Receta adoptable para los casos IEEE (pandapower da el flujo — nota 03 §6)                                                                                                                                                                                                                                                              |
| Tesis del engine: "lo cuántico propone, lo clásico verifica"                | Vanilla QAOA a 154–3000% del óptimo; con verificación+reparación → óptimo exacto                                     | ✅ **La validación externa más fuerte disponible**: sin la capa clásica de verificación/reparación, el pipeline cuántico ni siquiera es competitivo — con ella, iguala a Gurobi                                                                                                                                                            |

**Respuesta corta a la pregunta del plan:** sí — REGRID valida la Ruta A donde más importa (conectividad jamás codificada + reparación clásica como metodología con resultados óptimos), la matiza en las restricciones algebraicas (que REGRID sí codifica, reforzando el valor de nuestra ablación A/B), y agrega dos piezas que la nota 02 no tenía: el recetario formal de reparación M.1–M.5 y la verificación clásica dentro del lazo (λ_C).

---

## 2 · Decisión

| Referencia                                                                  | Decisión                                                  | Racional                                                                                                                                          |
| --------------------------------------------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Formulación K-way one-hot + slacks (Eqs. 22–31)                             | **descartar** (demo)                                      | bisección de la nota 02 usa 1 qubit/nodo; el one-hot cuadruplica el presupuesto en K=2 sin ganancia. Anotar para Fase 2 si aparece K≥3            |
| Reparación M.3/M.4 (greedy descent con Δ_j + relajación λ^(r)=λ/(1+ρ(r−1))) | **portar** (desde las ecuaciones — no hay código público) | es la especificación concreta del "reparar clásicamente" de la Ruta A; M.4 demostró óptimo en los 6 casos IEEE. Vive del lado proponente (ver §5) |
| Energía modificada por DFS en el lazo, λ_C·(1−χ_C) (Eqs. 39–40)             | **portar como candidato** (segunda prioridad tras M.x)    | feasibility feedback sin qubits extra; reutiliza el mismo chequeo `island_connectivity` de la nota 12 como función clásica del proponente         |
| Pesos w_ij = (\|p_ij\|+\|p_ji\|)/2 desde flujo de potencia                  | **integrar** para los casos IEEE                          | "validamos con la misma receta de pesos que el estado del arte" (nota 00 §1.5); pandapower ya está en el stack                                    |
| Reducción por coherencia (super-buses)                                      | **descartar** (demo)                                      | sin presión de qubits a n≤14; anotar Fase 2                                                                                                       |
| Surrogate cuadrático de conectividad H_c (Eq. 32)                           | **descartar**                                             | a nuestra escala el DFS post-hoc basta; el surrogate agrega términos sin garantía y complica la traza                                             |
| Cita del paper en la presentación                                           | **integrar** (ya decidido en nota 00 §7.3)                | ahora con las ecuaciones y números específicos (154–3000% → óptimo) como munición                                                                 |
| Tuning de λ                                                                 | **mantener** las cotas propias de la nota 02 §1.3         | REGRID no aporta fórmula; nuestras cotas son el diferencial                                                                                       |

---

## 3 · Licencias

- **Paper:** arXiv non-exclusive license (verificado en vivo 2026-07-14 en la página abs). Permite leer y citar; **no** es una licencia de redistribución libre — el checklist RAG de la nota 00 §6 (descargar el PDF e indexarlo) es uso interno aceptable, pero **no re-publicar el PDF** en artefactos públicos del repo.
- **Código:** el paper **no publica repositorio** (verificado en vivo 2026-07-14). Consecuencia doble: (a) cero riesgo de licencia de código — todo lo que se implemente sale de las ecuaciones de esta nota; (b) no hay implementación de referencia contra la cual diffear: los tests contra G6/IEEE-9 son nuestra única red.
- **Gurobi** (baseline del paper) es propietario — NO replicar ese rol: nuestro ancla exacta es brute force n≤16 / CP-SAT (notas 00 §1.4 y trust/10), ya decidido.

---

## 4 · Impacto en contrato

- Si se porta M.3/M.4, la evidencia del claim del Reto 1 gana campos aditivos naturales: `repair.method` (id M.1–M.5), `repair.flips` (número de flips aplicados), `repair.pre_value` / `repair.post_value` (corte antes/después de reparar) y `connectivity_violations` (C(z) del bitstring crudo). **REGISTRADO (S-E 2026-07-18): `docs/contract-freeze.md` §11** — los campos `repair.*`/`connectivity_violations` viven en la extensión de limitaciones/constraint-mixers (Δ1), no en el core Max-Cut.
- λ_C, ρ y el schedule de relajación son **datos versionados** en `knowledge/islanding/` con digest, igual que λ (patrón ADR-029 / nota 02 §1.3.4) — nunca constantes en código del engine.
- El hallazgo "vanilla QAOA a 154–3000% del óptimo" refuerza el campo `approximation_ratio` propuesto por la nota 04: es exactamente la métrica donde ese gap se ve.

---

## 5 · Reconciliación contra la base lógica

- **Invariant 2 (el verificador nunca es un modelo):** compatible — DFS, Δ_j(z) y los descensos M.x son cómputo determinista no-modelo. **Pero con una separación crítica:** la reparación y el λ_C-en-el-lazo son mejoras del **proponente** (transforman el claim antes de emitirlo), NO funciones del verificador. El `ExecutionVerifier` (nota 12) verifica el claim final; no repara. Si el proponente repara, la traza debe mostrar el bitstring crudo Y el reparado (Invariant 5: ambos eventos, append-only) — la reparación silenciosa sería exactamente el tipo de opacidad que el engine existe para impedir.
- **ADR-029 (manifiestos genéricos):** las capacidades siguen hablando de "QUBO → asignación binaria" y "reparación local greedy sobre QUBO"; islanding/buses/coherencia son vocabulario del KB, no del manifest. La formulación de esta nota vive en `knowledge/`, no en el core.
- **Tesis central ("lo cuántico propone, las anclas no-modelo verifican"):** REGRID es la validación externa publicada más directa — un framework independiente, sobre el mismo problema, llegó a la misma arquitectura (muestrear cuántico + verificar/reparar clásico) y demostró que la capa clásica es la que convierte muestras a 30× del óptimo en soluciones óptimas.
- **Punto a ratificar por Sebas:** ~~la dirección del objetivo~~ (RESUELTA por el enunciado oficial 2026-07-18: el reto es Max-Cut — ver §1.8) y la adopción de "Ruta A+" (λ_C en el lazo) como extensión del recetario de la nota 02. **Decidido (S-E 2026-07-18): Ruta A+ adoptada como parte de la extensión constraint-mixers — ratificación final de Sebas, ajustable bajo su criterio.**
