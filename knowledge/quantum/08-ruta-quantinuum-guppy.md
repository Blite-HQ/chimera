# Nota 08 — Ruta Quantinuum/Guppy: transpilación, emulador con ruido y plan B

**Ítem del plan:** contingencia Quantathon CR (~1 ago 2026): con ~80% de certeza el evento usará el emulador de **Quantinuum** y probablemente pida **Guppy**. Esta nota fija la ruta de transpilación desde nuestro stack (Qiskit Reto 1 / PennyLane Reto 2), el veredicto sobre el modelo de ruido del emulador (gate del feature AI-QEM de la nota 09) y el plan B.
**Fecha:** 2026-07-17 · **Estado:** investigación de consolidación (Dylan) — ratificación final de Sebas.

> **Actualización oficial (2026-07-18, PDFs del evento):** confirmado **emulador H2, tratamiento
> exacto hasta 26 qubits** (única disponibilidad confirmada; hardware real SIN confirmar — vale
> 10% de la rúbrica si aparece). SDK de libre elección con **Guppy "encarecidamente
> recomendado"** — NO obligatorio; la ruta §2.1 (Qiskit→pytket sin Guppy) sigue siendo válida
> pero es una elección consciente contra una recomendación oficial fuerte: se defiende en el
> **statement de SDK ≤200 palabras** (entregable oficial nuevo) o se reconsidera activando el
> puente `guppy.load_pytket()` de §1.2 (decisión de equipo 2026-07-18: core QAOA en Guppy
> nativo, Qiskit para baselines/statevector). El tope de 26 qubits confirma la escalera de
> instancias: cr8/ieee9/ieee14 en emulador; ieee30 solo clásico. Pendientes REALES restantes:
> ver el bloque PENDIENTE al final de §2.3.

**Fuentes:** (todas **verificadas en vivo 2026-07-17**)

- Modelo de ruido del emulador — <https://docs.quantinuum.com/systems/user_guide/emulator_user_guide/noise_model.html> (fuente primaria del veredicto §1.3)
- Emuladores H1/H2 — <https://docs.quantinuum.com/systems/trainings/h2/getting_started/emulators.html> · <https://docs.quantinuum.com/systems/user_guide/emulator_user_guide/emulators/h2_emulators.html>
- Guppy: docs <https://docs.quantinuum.com/guppy/> · guía de migración pytket→Guppy <https://docs.quantinuum.com/guppy/migration_guide.html> · repo <https://github.com/Quantinuum/guppylang>
- Selene — <https://docs.quantinuum.com/selene/user_guide/overview.html> · repo <https://github.com/Quantinuum/selene> · Selene en Nexus <https://docs.quantinuum.com/nexus/trainings/notebooks/basics/selene_examples.html>
- Stack next-gen (Helios/Nexus) — <https://docs.quantinuum.com/systems/trainings/helios/getting_started/index.html>
- Convenciones pytket (ángulos, gates) — <https://docs.quantinuum.com/tket/api-docs/optype.html>; orden de bits (BasisOrder) — <https://docs.quantinuum.com/tket/api-docs/circuit.html> y FAQs TKET
- Gate set nativo — <https://docs.quantinuum.com/systems/trainings/helios/getting_started/parameterized_angle_2_qubit_gates.html>
- pytket-quantinuum — <https://docs.quantinuum.com/tket/extensions/pytket-quantinuum/>
- Versiones PyPI (JSON API, 2026-07-17): pytket **2.18.1** (2026-07-06) · pytket-qiskit **0.77.0** (2026-02-02) · pytket-pennylane **0.21.0** (2026-01-07) · pytket-quantinuum **0.59.1** (2026-05-13) · guppylang **0.21.16** (2026-06-04) · selene-sim **0.2.18** (2026-07-16) · qnexus **0.46.0** (2026-06-30)
- Licencias y estado de repos: `gh api repos/Quantinuum/{guppylang,tket,pytket-qiskit,pytket-pennylane,selene,pytket-quantinuum}` (§3)

---

## 1 · Patrón / mecanismo

### 1.1 El mapa del stack Quantinuum (julio 2026)

```
Qiskit (Reto 1) ──qiskit_to_tk──┐
                                 ├─ pytket (TKET, el compilador) ── rebase a gate set nativo
PennyLane (Reto 2) ──(vía QASM/──┘        │
  pennylane-qiskit; ver §2)               ├─ pytket-quantinuum → emulador H1/H2 (ruido H-series)
                                          └─ guppy.load_pytket() → Guppy → HUGR → Selene / Nexus (Helios)
```

- **pytket/TKET**: el compilador de Quantinuum. Un circuito TKET se rebasea automáticamente al gate set nativo al enviarse; `pytket-quantinuum` "requiere un circuito TKET como entrada… y envía el circuito como QIR al recurso Quantinuum especificado". Activamente mantenido (pytket 2.18.1, jul 2026).
- **pytket-qiskit** (0.77.0): conversión bidireccional `qiskit_to_tk` / `tk_to_qiskit`. Mantenido (último release feb 2026, repo activo).
- **pytket-pennylane** (0.21.0): expone backends pytket como device de PennyLane. ⚠️ **El repo fue ARCHIVADO** (último push 2026-04-09, `archived: true` vía gh api) — funciona hoy pero está descontinuado. **No apoyar la ruta principal en él** (§2).
- **Guppy (guppylang 0.21.16)**: lenguaje cuántico-clásico embebido en Python. Compila a **HUGR** (Hierarchical Unified Graph Representation, IR de grafo jerárquico, open source). Exige lo que pytket no: **qubits lineales** (no se pueden copiar ni descartar implícitamente — el compilador lo rechaza), medición explícita en el código, y habilita control de flujo dependiente de medición (if/for/while sobre resultados).
- **Emuladores** (tres nombres, tres cosas):
  1. **Emuladores H-series (H1/H2)**: hosteados por Quantinuum, reciben circuitos vía pytket-quantinuum/Nexus, corren "el modelo de ruido físico específico de los sistemas Quantinuum", con "fidelidad verificada comparando salidas de emulador y hardware".
  2. **Selene** (`selene-sim`, PyPI, open source): emulador **local** de programas Guppy/HUGR. Backends: statevector (QuEST), stabilizer (Stim), coinflip, classical replay, quantum replay. Modelos de error: `IdealErrorModel`, `DepolarizingErrorModel`, `SimpleLeakageErrorModel`.
  3. **Nexus** (`qnexus`): la PaaS cloud — acceso a Helios, emuladores H-series e instancias Selene cloud. Flujo next-gen: Guppy → HUGR → upload → `qnx.start_execute_job()`.

### 1.2 ¿Guppy es obligatorio? **NO — RESUELTO por el enunciado oficial (2026-07-18): SDK libre, Guppy "encarecidamente recomendado"**

Veredicto técnico verificado:

- Los **emuladores H1/H2 aceptan circuitos TKET directamente** vía pytket-quantinuum (o Nexus) — sin Guppy.
- Para el stack **next-gen (Helios/Selene)** Guppy es la vía principal, pero la propia doc lista alternativas (QIR, CUDA-Q, Qiskit en H2) y, crucialmente, existe el puente oficial **`guppy.load_pytket()`**: convierte un `Circuit` de pytket en una función Guppy invocable. Nuestra lógica ya existe en Qiskit/PennyLane; si el evento exige Guppy es **traducción, no reescritura**:

```python
# Esqueleto del mapeo (verificado contra la guía de migración oficial)
from pytket.passes import AutoRebase, DecomposeBoxes
from pytket.circuit import OpType
from guppylang import guppy

tkc = qiskit_to_tk(qc)                     # 1. Qiskit → pytket (pytket-qiskit)
DecomposeBoxes().apply(tkc)                # 2. sin cajas opacas
AutoRebase({OpType.H, OpType.Rz, OpType.CX}).apply(tkc)   # 3. solo ops del set soportado por Guppy
qaoa_func = guppy.load_pytket("qaoa", tkc) # 4. circuito → función Guppy
# 5. mediciones y post-proceso clásico se escriben EN Guppy; ejecutar en Selene
```

Limitación documentada: circuitos pytket grandes se cargan "desenrollados" (sin la compresión de loops de Guppy) — irrelevante a nuestra escala (≤14 qubits, nota 03 §7). Advertencia de la guía: el caso ideal de `load_pytket` son circuitos unitarios; mediciones y lógica clásica van en Guppy.

### 1.3 El modelo de ruido del emulador — **el gate de la nota 09: ABIERTO (sí hay ruido realista, y es configurable)**

Fuente primaria (Emulator Noise Model, docs.quantinuum.com, verificada en vivo 2026-07-17). El emulador modela:

- **Infidelidades de compuerta 1q y 2q** como canales de **despolarización asimétrica** (parámetros `p1`, `p2`, con escalas `p1_scale`, `p2_scale`).
- **SPAM**: error de inicialización (`p_init`) y de medición (`p_meas`, con sesgos diferenciados por estado).
- **Crosstalk** en medición e inicialización.
- **Dephasing / error de memoria**: Pauli-Z aplicado durante transporte e inactividad de qubits, con términos cuadrático y lineal en la duración (`quadratic_dephasing_rate`, `linear_dephasing_rate`).
- **Leakage** (solo emuladores Helios): salida del espacio computacional y retorno ("seepage").

Configurabilidad (citas de la doc): los defaults "representan un entorno de ruido que se asemeja de cerca al hardware respectivo"; "solo los parámetros especificados se sobreescriben"; **"para apagar ciertos parámetros de error, fijarlos explícitamente en 0"** — y fijando el `scale` en 0 se anulan todos a la vez. Además, la doc general de emuladores confirma que "pueden correrse con o sin el modelo de ruido del dispositivo físico; el default es con el ruido encendido".

**Consecuencia para la nota 09 (AI-QEM):** existe (a) ruido realista de H-series que mitigar, (b) un knob documentado para generar pares {corrida ruidosa, corrida ideal} del MISMO circuito — exactamente el dataset que AI-QEM necesita, y (c) parámetros escalables (`pN_scale`) para barrer niveles de ruido. El gate queda abierto. En local, Selene replica el patrón con `DepolarizingErrorModel` vs `IdealErrorModel`.

### 1.4 Gate set nativo: RZZ paramétrico ES nativo (conecta kb2-01 §3)

Gate set nativo Quantinuum: **{Rz, PhasedX, ZZMax, ZZPhase}** — con ZZPhase = RZZ de ángulo arbitrario, nativo también en Helios ("parameterized angle 2-qubit gates"). Consecuencia directa para el Reto 1: la capa de costo de QAOA (un RZZ por arista, nota 02 §1.5) compila **1:1 a compuerta nativa** — no se descompone en CX·RZ·CX como en kb2-01 §3. La cuenta de profundidad mejora: p·(|E| ZZPhase + n PhasedX) en vez de p·(2|E| CX + …). Es un punto a favor de esta ruta que se puede decir en el pitch con fuente.

### 1.5 Trampas de convención — la tabla de kb2-03 §4 extendida con la columna pytket/Quantinuum

| Convención                  | Qiskit                         | PennyLane                   | **pytket/Quantinuum**                                                                                                                                    | Consecuencia                                                                                                                                                                  |
| --------------------------- | ------------------------------ | --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Ángulos                     | radianes; RZZ(θ)=e^(−i(θ/2)ZZ) | radianes; IsingZZ(φ) igual  | **HALF-TURNS (múltiplos de π) en TODOS los ángulos**: ZZPhase(α)=e^(−½iπα·Z⊗Z), Rz(α)=e^(−½iπα·Z)                                                        | **α_pytket = θ_qiskit/π**. Al portar QAOA a mano: RZZ(γ·w) → ZZPhase(γ·w/π). `qiskit_to_tk` lo convierte solo — el peligro es el circuito escrito a mano en pytket/Guppy      |
| Orden de bits en resultados | little-endian: q₀ a la DERECHA | wire 0 = MSB (izquierda)    | default **ILO-BE**: q[0] a la IZQUIERDA (MSB); toggle `BasisOrder.dlo` reproduce la lectura estilo Qiskit                                                | Tres frameworks, tres lecturas. **Congelar `decode()` POR BACKEND con G6 como vector** (§2 y nota 02 §1.6): la muestra dominante debe decodificar a corte 5 en las TRES rutas |
| Pauli string                | "ZZI" leído derecha→izquierda  | operador por wire explícito | `QubitPauliString` por qubit explícito (estilo PennyLane)                                                                                                | mismo helper (i,j)→operador de kb2-03 §4; nunca strings a mano                                                                                                                |
| Compuerta 2q "natural"      | CX (RZZ se descompone)         | —                           | **ZZPhase nativa** (§1.4)                                                                                                                                | la métrica honesta de profundidad cambia de "conteo CX" a "conteo ZZPhase" según backend — reportar ambas en evidence                                                         |
| Semillas                    | `seed=` en primitive           | seeds numpy/optimizador     | Selene: seed en la corrida (statevector QuEST/Stim); Aer: `seed_simulator`. **Emulador H-series remoto: PENDIENTE confirmar parámetro de seed expuesto** | sin seed no hay pata AL2 de CONSENSUS_REPLICATION (§2.3); si el emulador remoto no pinnea seed, esa pata aporta estadística, no réplica exacta                                |

## 2 · Decisión

### 2.1 Ruta principal (si el evento da acceso al emulador Quantinuum)

**Qiskit → `qiskit_to_tk` (pytket-qiskit) → pytket → emulador H-series/Nexus (pytket-quantinuum o qnexus), SIN Guppy.** Es la ruta con menos piezas nuevas, todas mantenidas, y conserva nuestro artefacto de procedencia (el circuito Qiskit y su QASM 3 siguen siendo la fuente; el circuito rebaseado se registra como artefacto derivado, §4). Para el Reto 2, la matriz de Gram NO se recomputa en el emulador (≈19 000 circuitos, nota 02 §2.2 — inviable en cola remota): se corre en emulador solo un subconjunto demostrativo de kernels + el circuito QAOA del Reto 1 completo.

**PennyLane:** no depender de pytket-pennylane (archivado, §1.1). Puente: exportar el circuito del QNode a Qiskit/QASM (plugin `pennylane-qiskit`, mantenido por PennyLane) y entrar por la misma puerta `qiskit_to_tk`. Una sola puerta de entrada a pytket = una sola tabla de convenciones que congelar.

**Si el evento exige Guppy explícitamente:** aplicar el esqueleto §1.2 (`load_pytket` tras `DecomposeBoxes` + `AutoRebase`) y ejecutar en Selene/Nexus. La lógica de negocio (QUBO→Ising, decodificación, verificación) NO se toca: es la misma función `decode()` congelada leyendo bitstrings. Presupuestar medio día de traducción + revalidación con G6.

### 2.2 Plan B (sin acceso, o si el emulador remoto falla en vivo)

**Selene local** (`pip install selene-sim`, open source, air-gap compatible): corre el mismo programa Guppy/HUGR con `DepolarizingErrorModel` (ruido) o `IdealErrorModel` (exacto), backends QuEST/Stim. Cubre tanto la demo "estilo Quantinuum" como el gate de la nota 09 sin depender de la nube. Fallback final: Aer/Statevector (stack actual, nota 03) — nada del diseño depende de Quantinuum para funcionar.

### 2.3 Decisión multi-emulador: patas de CONSENSUS_REPLICATION

Correr el **mismo circuito** (mismo QASM fuente, seeds pinned) en ≥2 emuladores independientes — mínimo **Aer + (Selene o emulador H-series)** — y tratar cada corrida como una pata de **CONSENSUS_REPLICATION** (clase decisoria, techo **AL2**, convergencia v3.2 §2.1): son **procesos no-modelo con seeds pinned**, exactamente el caso que la spec admite como decisorio. El reporte de primera clase es el **balance entre el resultado más favorable y el más pesimista** entre patas (p.ej. mejor corte hallado y su frecuencia, con y sin ruido): la banda [pesimista, favorable] es evidencia, no adorno. La verificación del corte sigue siendo backend-agnóstica (§5) — el consenso solo suma fuerza, nunca sustituye al verificador exacto (FORMAL_EXACT/AL4 del corpus).

**PENDIENTE (actualizado 2026-07-18 — el enunciado oficial resolvió parte):** RESUELTO: emulador = **H2** (tratamiento exacto hasta 26 qubits) y Guppy NO obligatorio (SDK libre, "encarecidamente recomendado" — nota al inicio). SIGUEN pendientes: créditos/acceso Nexus; parámetro de seed del emulador H-series remoto (§1.5 — los organizadores darán detalles finos en el evento); si habrá acceso a hardware real (10% de la rúbrica). Revalidar esta nota la semana del evento — el stack next-gen se mueve rápido (selene-sim publicó release el 2026-07-16).

## 3 · Licencias

Verificadas en vivo 2026-07-17 vía `gh api` contra el repo oficial (org **Quantinuum**; los paths CQCL redirigen allí): **guppylang, tket (pytket), pytket-qiskit, pytket-pennylane, selene, pytket-quantinuum — todas Apache-2.0.** Sin conflicto con la postura open-core (misma situación que la nota 03 §5). Único flag: pytket-pennylane está **archivado** (licencia sana, mantenimiento muerto) — razón adicional para excluirlo de la ruta principal. qnexus (SDK del servicio cloud): el paquete es instalable desde PyPI; el servicio Nexus en sí es propietario/comercial — es dependencia de acceso, no de código.

## 4 · Impacto en contrato

La ruta agrega campos **aditivos** a `evidence`/provenance, alineados con `Artifact`/ContentStore (convergencia §4.1) y con el `circuit_digest` de la nota 03 §1:

1. **`transpiled_circuit_digest` por backend-leg:** el QASM 3 fuente ya produce `circuit_digest`; el circuito **rebaseado al gate set nativo** (pytket tras `AutoRebase`/compilación, o el HUGR compilado si la ruta es Guppy) es un artefacto derivado distinto → serializarlo (QASM del circuito pytket compilado; bytes del HUGR en la ruta Guppy) → SHA-256. Sin esto, "corrimos el mismo circuito en dos emuladores" no es verificable: lo que corre cada backend NO son los mismos bytes.
2. **`backend_id` + versiones** por pata (p.ej. `aer@x.y`, `selene-sim@0.2.18`, `H2-emulator`) — ya implícito en nota 02 §1.6.4; aquí se vuelve lista (una entrada por pata de consenso).
3. **`noise_config_digest`:** el dict de parámetros de error efectivos (o `ideal`) por pata, canonicalizado → digest. Es el análogo de λ ("dato, no código", nota 02 §1.3): dos corridas con ruido distinto no son comparables sin esto. Gate de la nota 09: AI-QEM se entrena/evalúa contra pares identificados por este digest.
4. Las patas de consenso (§2.3) se registran como claims con clase `CONSENSUS_REPLICATION`/AL2 en el vocabulario nuevo — cuelgan del run raíz (Run jerárquico, convergencia §4.2).

**PENDIENTE:** registrar 1–3 en `docs/contract-freeze.md` junto con el `circuit_digest` de la nota 03 (que sigue siendo contrato fantasma sin dueño en el freeze).

## 5 · Reconciliación contra la base lógica

- **La verificación es backend-agnóstica — sin cambios en `docs/invariants.md`:** el corte se **recomputa clásicamente del bitstring** (nota 02 §1.6.2, `ExactSolverVerifier` trust/10). Ningún emulador — Aer, Selene o H-series — participa en el veredicto; solo propone muestras. Cambiar de backend no toca un solo verificador: exactamente la separación proponente/verificador que la base lógica congela.
- **Regla congelada extendida:** `decode()` se congela **con G6 como vector también para esta ruta** (tercera columna de §1.5): un test por backend-leg donde la muestra dominante del QAOA sobre G6 decodifica a corte 5. Si un port a pytket/Guppy rompe endianness o half-turns, lo atrapa G6 antes que el jurado.
- **Coherencia con las clases decisorias (v3.2):** el multi-emulador de §2.3 usa CONSENSUS_REPLICATION exactamente dentro de su techo (AL2, procesos no-modelo, seeds pinned) — consistente con el AJUSTE a quantum/04 §4 de la convergencia. No compite con las anclas no-modelo (INV-2): el corpus con doble ancla sigue siendo la única fuente AL4.
- **Air-gap:** la ruta principal (emulador remoto/Nexus) es la ÚNICA pieza online de esta nota y existe solo porque el evento la provee; el plan B (Selene local + Aer) preserva el descarte de cloud-por-defecto (nota 03 §5, misma lógica que Braket). Sin contradicciones detectadas. **Ratificación de Sebas: PENDIENTE.**
