# Nota 04 (KB2-04) — Estadística y matemática de la evidencia: los números correctos para cada campo de `evidence`

**Rol:** el puente entre la salida cuántica (probabilística) y el contrato de verificación (determinista). Las notas trust/03/04/10–12 definen las FORMAS (`evidence`, `GuardrailSignal`, verdicts); este doc da las FÓRMULAS para llenarlas sin mentir.
**No repite:** tolerancias float/`isclose`/escala entera (trust/10 §1.5), tri-estado (trust/03 §1.4), tipos disjuntos guardrail/attestation (trust/04 §1.3) — se referencian.
**Fecha:** 2026-07-14 · **Estado:** vigente — movida de `docs/kb2-04…` a `knowledge/quantum/` en la consolidación (2026-07-14); el template de nota se aplica en la sección final. **[S3 2026-07-30 — nota de vocabulario:** toda mención residual de «rung N»/escalera en este doc (§5, mapa rápido, template) es vocabulario supersedido por clase+AL (freeze §4; mapa en `convergencia-diseno-v32.md` §2.1) — las FÓRMULAS siguen vigentes; §4 ya lleva la traducción explícita (`consensus_replication` AL2 / `Signal`).**]**

---

## 1 · Razón de aproximación y brechas (el vocabulario del `differential`)

- **Approximation ratio:** `r = C(x_candidato) / C_óptimo` ∈ [0,1] — LA métrica estándar de la literatura QAOA; reportarla junto al `gap` absoluto de la nota 10. Con CP-SAT en `OPTIMAL`, el denominador es exacto ⇒ r es un hecho, no una estimación.
- **Contabilidad energía↔corte:** recordar C = W/2 − ⟨H_C⟩ (KB2-02 §1.4). Reportar "energía" y "corte" mezclados invierte el signo del gap. Regla: la evidencia habla en **valor de corte** (la magnitud del dominio); la energía es detalle del proponente.
- **Contexto teórico para leer r:** 0.878 es la garantía clásica (Goemans–Williamson); ≈0.6924 la garantía de QAOA p=1 en 3-regulares (KB2-01 §7). Un r = 1.0 en un grafo de 8 nodos es esperable y NO es "ventaja cuántica" — es una instancia chica (ver §3, el baseline uniforme).

## 2 · Estadística de shots: qué tan seguro es un número medido

Medir un circuito N veces estima una probabilidad p con proporción muestral p̂:

```
SE(p̂) = √( p(1−p)/N ) ≤ 1/(2√N)          (intervalo: Wilson para p cerca de 0/1)
⟨Z⟩ = 1 − 2p   ⇒   SE(⟨Z⟩) ≤ 1/√N
Para error ε en ⟨Z⟩:  N ≈ 1/ε²
```

| Precisión ε deseada | Shots N  |
| ------------------- | -------- |
| 0.1                 | 100      |
| 0.03                | ~1 100   |
| 0.01                | 10 000   |
| 0.003               | ~110 000 |

Para un Hamiltoniano H = Σ c_k P_k medido por términos, cota de propagación: `SE(⟨H⟩) ≤ Σ|c_k| / √N_k` — la razón matemática del hallazgo del paper de migración de shots (KB-fuentes §0.3): con N chico, el "mismo" algoritmo da otra cosa. **Regla de evidencia:** todo valor estimado por muestreo viaja con su `{shots, se_estimado}`; los valores por statevector se marcan `exact: true` (a ≤14 qubits, KB2-03 §7, ese es el default del demo).

Aplicación Reto 2: cada entrada del kernel es una probabilidad ⇒ con shots, K trae ruido ~1/(2√N) por celda — el origen de los autovalores negativos que §5 repara.

## 3 · El baseline que mantiene honesto al proponente: muestreo uniforme

En instancias chicas, hasta tirar monedas encuentra el óptimo. Si el óptimo tiene g bitstrings degenerados (g ≥ 2 siempre, por la simetría de complemento) en n qubits:

```
p_uniforme = g / 2ⁿ            P(hallarlo en K muestras) = 1 − (1 − p)^K
K para 99% de éxito ≈ 4.6 / p   (p chico)
```

Ejemplos con los vectores de la nota 10: **G6** (n=3, g=2): p = 0.25 ⇒ ~16 muestras _aleatorias_ bastan al 99%. **G2/C4** (n=4, g=2): p = 0.125 ⇒ ~35. Grid CR (n=8, g=2): p ≈ 0.008 ⇒ ~590 — todavía trivial con 4 096 shots. _(⚠️ SUPERSEDIDO [S-F 2026-07-20]: g = 2 y el ~590 son del grafo SINTÉTICO — cr8 nace de los datos del ICE y este cálculo de shots se rehace con su degeneración real, que se mide con el análisis de flips obligatorio de islanding/01 §1.8; el MÉTODO sigue vigente.)_

**Consecuencia de reporte (anti quantum-washing, la matemática detrás del riesgo 19.2 del doc CHIMERA):** "QAOA encontró el óptimo" no informa nada en n=8 si el uniforme también lo encuentra. La métrica honesta es el **enriquecimiento**: `p_QAOA(óptimo) / p_uniforme` — cuántas veces más probable es el óptimo bajo la distribución de QAOA que bajo azar. Ese cociente sí mide que el circuito aprendió estructura, y va perfecto en la evidencia/ablación.

> **[S3 2026-07-30]** El «enriquecimiento vs muestreo uniforme como parte del claim» de esta
> sección quedó registrado como **KB curada** (mención honorífica del censo, 07-censo §7) por
> decisión #116 — sin ítem propio de backlog; el método sigue vigente como conocimiento.

## 4 · Consenso entre muestras (antes «rung 5»): las fórmulas para `GuardrailSignal.detail`

> **[S3 2026-07-30] Traducción de vocabulario:** la escalera 1-7 murió (freeze §4); «rung 5» ya
> no nombra nada vigente. Lo vivo es exactamente lo que el AJUSTE S-E de abajo partió en dos —
> y así lo estampó el freeze (§11 y §4 :111) citando esta misma sección: el consenso de MUESTREO
> con seeds pinned es pata `consensus_replication` **decisoria** (techo AL2); la concordancia
> ENTRE MODELOS es `Signal` **no-decisoria** (§5 del freeze). Las fórmulas de esta sección
> siguen vigentes para ambas; solo el número de escalera muere.

La nota 04 fija el tipo (señal, jamás attestation) y la 16 el registro; aquí, el contenido numérico para `name: "self-consistency"` sobre salidas cuánticas:

**Paso 0 obligatorio — canonicalizar la simetría de complemento:** flipear cada bitstring muestreado para que x₀ = 0 (la misma ruptura de simetría de la nota 10 §1.5). Sin esto, la degeneración x↔1−x parte el consenso en dos y el acuerdo medido se desploma artificialmente.

Sobre R corridas con semillas distintas (o sobre la distribución de una corrida):

```
acuerdo   = #{corridas cuyo mejor corte == valor modal} / R
masa_top  = Pr(bitstring canónico más frecuente)
entropía  = −Σ_b p_b · log2(p_b)      (máx: n−1 bits tras canonicalizar; baja = distribución concentrada)
detail    = {n_runs, seeds[], modal_value, acuerdo, masa_top, entropia_bits, p_uniforme}
```

Lectura: entropía alta + acuerdo bajo = el optimizador no convergió a estructura (señal para revisar p/iteraciones); acuerdo alto NO prueba optimalidad (dos heurísticas pueden coincidir en lo sub-óptimo) — por eso es rung 5 e informa, y el ancla sigue siendo CP-SAT (exactamente la aclaración de nombre de la nota 10 §1.1).

> **AJUSTE S-E (2026-07-18, convergencia §2.1 — decidido, ratificación final de Sebas):** bajo la
> spec v3.2 este consenso se parte en dos con suerte distinta. (a) La **réplica de MUESTREO con
> seeds pinned** (mismas corridas de arriba, procesos no-modelo) SÍ es decisoria: constituye una
> pata `consensus_replication` con techo **AL2** (S7 — patas = clases de independencia). (b) La
> **concordancia entre modelos** (self-consistency de un modelo consigo mismo o entre familias)
> sigue siendo `Signal` no-decisoria, exactamente como esta sección la diseñó. Las fórmulas de
> `detail` sirven para ambas: en (a) alimentan la evidencia de la pata; en (b) el anexo de señales.

## 5 · Catálogo formalizado de propiedades y metamórficas (rung 4, listo para Hypothesis)

Complementa las relaciones ya enunciadas en la nota 03 §1.2 con su enunciado exacto y varias nuevas:

**Reto 1 (Max-Cut / islanding):**

1. _Permutación:_ ∀ permutación π de nodos: C(π(x); π·G) = C(x; G) y maxcut(π·G) = maxcut(G).
2. _Escala:_ C(x; k·w) = k · C(x; w) ∀x, k>0 ⇒ el argmax es invariante y el valor escala.
3. _Nodo aislado:_ maxcut(G + nodo aislado) = maxcut(G) — ya es el vector G5 de la nota 10; aquí queda como propiedad universal muestreable.
4. _Complemento:_ C(x) = C(1−x) ∀x. **Corolario operativo para el corpus rung 3:** las particiones "verdad conocida" deben guardarse **canonicalizadas (x₀=0) o compararse por VALOR de corte, nunca por bitstring crudo** — si no, la mitad de los matches legítimos fallan por degeneración. (Aviso directo para el corpus de Sebas.)
5. _Monotonía:_ agregar una arista de peso w ≥ 0 nunca reduce el óptimo: maxcut(G+e) ≥ maxcut(G).
6. _Cota trivial:_ 0 ≤ C(x) ≤ W ∀x; y maxcut ≥ W/2 en esperanza bajo asignación uniforme (test de cordura del generador de instancias).

**Reto 2 (kernel/clasificador):**

1. _Diagonal:_ K(x,x) = 1 (±tol de shots).
2. _Simetría:_ K = Kᵀ.
3. _PSD:_ λ_min(K) ≥ −ε(N_shots); si −ε < λ_min < 0 ⇒ reparar con clip espectral K ← V·max(Λ,0)·Vᵀ y **registrar λ_min pre-reparación** en la evidencia; si λ_min ≪ −ε ⇒ bug (fail-loud, no reparación silenciosa).
4. _Etiquetas barajadas (detector de fuga):_ re-entrenar con y permutado al azar debe rendir ≈ clase mayoritaria (~61%). Si rinde alto con etiquetas rotas, hay leakage en el pipeline (KB2-02 §2.1) — la propiedad más barata y letal del reto.
5. _Consistencia de duplicado:_ duplicar un punto de train no cambia la predicción sobre test más allá de tolerancia.

**Química/VQE (ya no es el Reto 3 — el C3 oficial es TFIM/Trotter, ver 02 §3; estas propiedades
quedan como conocimiento de química y su patrón se traslada tal cual a la ED del TFIM):**

1. _Cota variacional (unilateral, fail-loud):_ E_VQE ≥ E_exacta − tol_num. Violarla no es un `fail` del candidato: es `error` del proceso (unidades, E_NN omitida, Hamiltoniano distinto) — el espejo químico exacto del caso "mejor que el óptimo probado" de la nota 10 §1.2.
2. _Ancla HF gratis:_ UCCSD(θ=0) ⇒ E = E_HF exacta (chequeo previo a optimizar).
3. _Doble ancla exacta:_ NumPyMinimumEigensolver(H_qubit) ≡ FCI + E_NN dentro de tol — triangula VQE↔NumPy↔PySCF y localiza en qué capa vive un bug (KB2-02 §3.4).
4. _Forma de la curva:_ mínimo cerca de r_eq; E(r) ≥ E_FCI(r) punto a punto; límite disociado correcto (KB2-02 §3.6).

## 6 · Comparar cuántico vs clásico con significancia (Reto 2)

Fórmulas de reporte: precisión P = TP/(TP+FP); recall R = TP/(TP+FN); **F1 = 2PR/(P+R)**; **balanced accuracy = (TPR+TNR)/2** (la correcta bajo el 61/39 del dataset).

**Test de McNemar** (los dos modelos evaluados sobre el MISMO test set): sean b = casos que el clásico acierta y el cuántico falla, c = al revés:

```
χ² = (|b−c| − 1)² / (b+c)     con 1 g.l.  →  significativo al 5% si χ² > 3.84
(si b+c < 25: usar el binomial exacto sobre c ~ Bin(b+c, ½))
```

**Lenguaje de conclusión permitido** (la versión estadística de la honestidad del certificado): con test chico (~50 muestras) casi nunca habrá significancia ⇒ la frase defendible es "el modelo cuántico es **competitivo** (Δaccuracy = …, McNemar p = …)", no "supera". Reportar b, c y p en la evidencia hace la frase auditable.

## 7 · Unidades y tolerancias de energía (Reto 3)

| 1 Hartree (Ha) = | valor    |
| ---------------- | -------- |
| eV               | 27.2114  |
| kcal/mol         | 627.5095 |
| kJ/mol           | 2 625.50 |

**Precisión química = 1 kcal/mol ≈ 1.594 mHa ≈ 0.0434 eV.** Disciplina: computar y comparar TODO en Hartree; convertir solo en la capa de presentación. Dos tolerancias distintas y ambas explícitas en la evidencia: `tol_num` (≈1e-8 Ha — ruido de punto flotante, para las anclas exactas entre sí) y `tol_química` (1.6e-3 Ha — el estándar del dominio, para el claim "alcanzó precisión química"). Confundirlas infla o destruye el resultado. Para floats en general rige el `isclose` de la nota 10 §1.5.

## 8 · Checklist de semillas: la tabla de replay completa

Una corrida es _replayable_ solo si TODAS las fuentes de azar están fijadas y registradas (extiende el principio del `seed` de Hypothesis de la nota 03 y los params de CP-SAT de la nota 10 al lado proponente):

| Capa                              | Dónde se fija                             | Campo de evidencia            |
| --------------------------------- | ----------------------------------------- | ----------------------------- |
| NumPy global                      | `np.random.seed(s)`                       | `seeds.numpy`                 |
| Sampler/Estimator (Qiskit)        | `StatevectorSampler(seed=s)`              | `seeds.sampler` + `shots`     |
| Algoritmos Qiskit                 | `algorithm_globals.random_seed`           | `seeds.algorithm`             |
| Punto inicial del ansatz          | vector explícito (no aleatorio implícito) | `initial_point_digest`        |
| SPSA / optimizadores estocásticos | seed del optimizador                      | `seeds.optimizer`             |
| Split / selector RF (Reto 2)      | `random_state`                            | `seeds.data`                  |
| neal (si se adopta)               | `sample(..., seed=s)`                     | `seeds.annealer`              |
| Circuito ejecutado                | `qasm3.dumps` → SHA-256 (KB2-03 §1)       | `circuit_digest`              |
| Entorno                           | pinning KB-fuentes §0.4                   | `environment` (forma nota 03) |

Prueba de fuego (misma disciplina que el `params_digest` de la nota 10 §1.4): dos máquinas con el mismo checklist deben producir el MISMO claim byte-a-byte; si no, falta una fila en esta tabla.

## 9 · Convergencia del optimizador: cuándo abstenerse del lado proponente

Registrar la historia de energía (callback) y declarar plateau si |E_t − E_{t−k}| < ε durante k iteraciones. Si se agota `maxiter` sin plateau, el claim se emite igual pero **marcado** (`converged: false`) — el verdict lo ponen las anclas de todos modos, pero ocultar la no-convergencia sería la versión proponente del `pass` mentiroso. Buenas defaults del demo: COBYLA maxiter 200–500, ε = 1e-4 (en unidades del corte), k = 20; SPSA solo si se simula con shots.

---

### Mapa rápido fórmula → campo

| Fórmula de este doc                    | Campo/contrato que llena                                                 |
| -------------------------------------- | ------------------------------------------------------------------------ |
| §1 ratio r, contabilidad corte/energía | `evidence.differential` (nota 10) — aditivo `approximation_ratio`        |
| §2 SE/shots                            | `evidence` de todo valor muestreado (`shots`, `se_estimado`, `exact`)    |
| §3 enriquecimiento vs uniforme         | panel de ablación (nota 05 §4) + narrativa honesta                       |
| §4 acuerdo/entropía                    | `GuardrailSignal.detail` para `self-consistency` (notas 04/16)           |
| §5 catálogo                            | propiedades Hypothesis (`method:"property"/"metamorphic"`, nota 03 §1.2) |
| §6 McNemar                             | verificación del Reto 2 + copy del certificado                           |
| §7 unidades                            | tolerancias del Reto 3                                                   |
| §8 semillas                            | `params_digest`-equivalente del proponente                               |

---

## Template de nota (consolidación 2026-07-14)

- **Patrón / mecanismo:** las fórmulas para llenar `evidence` sin mentir — approximation ratio, estadística de shots, baselines de enriquecimiento, consenso rung 5, catálogo de propiedades rung 4, McNemar, unidades Hartree, checklist de semillas/replay.
- **Decisión:** N/A en el sentido del template (no evalúa repos externos); la decisión de fondo que fija: el consenso rung 5 es **señal, jamás attestation** (coherente con trust/04).
- **Licencias:** N/A — fórmulas; menciona Hypothesis/sklearn sin introducir dependencia nueva.
- **Impacto en contrato:** propone campos **aditivos** a `evidence` (`approximation_ratio`, `se_estimado`, `exact`, `seeds.*`) y detalle de `GuardrailSignal` para self-consistency. **REGISTRADO (S-E 2026-07-18): `docs/contract-freeze.md` §11** — dejaron de ser contratos fantasma; dueño [confianza/ciencia].
- **Reconciliación contra la base lógica:** revisada en la consolidación — respeta el verdict tri-estado (trust/03), la separación guardrail ≠ attestation (trust/04) y las tolerancias de trust/10. Es la nota kb2 más alineada con el plano de confianza. **Decidido (S-E 2026-07-18) — ratificación final de Sebas, ajustable bajo su criterio.**
