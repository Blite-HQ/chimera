# KB2-05 — La plataforma del enunciado: Quantinuum H2, emuladores, TKET/pytket y Nexus

**Rol:** brief operativo de la plataforma obligatoria del C1 ("emulador H2 de Quantinuum, exacto ≤26 qubits"). Qué es cada pieza, cómo mapea al contrato de evidencia ya congelado (freeze §11 / nota quantum-08), y cómo se reconcilia con el air-gap del demo (freeze §15.4).
**Fecha:** 2026-07-20 · **Estado:** VIGENTE como KB (marcado 2026-07-30, saneamiento S3 — hasta entonces sin header de estado y fuera de ambos índices del directorio).
**Fuentes:** docs.quantinuum.com (systems + nexus) y learn.microsoft.com/azure/quantum, consultadas en vivo 2026-07-20. Los ítems marcados ⚠️ requieren verificación con la cuenta/portal real antes de depender.
**Complementa:** KB2-02 (la formulación que se ejecuta aquí) · KB2-03 (Qiskit/PennyLane — este doc agrega la tercera pata: TKET) · KB2-04 §8 (semillas/replay).

> **Nota (2026-07-30, saneamiento S3):** nombre fuera de la convención `NN-` del directorio
> (colisiona con `05-regrid-qaoa-extraccion.md`). El renombre, o la fusión con
> `08-ruta-quantinuum-guppy.md` (deuda declarada desde S-G), quedó DIFERIDO al refactoring final
> (decisión #118). Registrado: su reconciliación (§5) se hizo contra el air-gap del demo (freeze
> §15.4) y no contra `docs/invariants.md`.

---

## 1 · El mapa de la plataforma en una pantalla

```
tu circuito (pytket, o Qiskit → qiskit_to_tk)
      │  compilación TKET (rebase a gates nativos H2)
      ▼
Quantinuum Nexus (cloud)  ──►  targets:
      H2-1     hardware real (56 qubits, iones atrapados QCCD)
      H2-1E    emulador cloud NOISY (statevector en GPU + modelo de ruido físico; consume HQCs, Fair Queue)
      opción noiseless sobre targets E (solo queda el shot noise)
      H2-1SC   syntax checker (valida el programa sin ejecutarlo, barato)
      Emulator/LE en Nexus  noiseless, tope ~20 qubits, cola FIFO propia
      LE local (extra `pecos`)  emulador LOCAL noiseless, recomendado <16 qubits, opción API offline
```

- **Stack de software:** TKET (compilador; paquete open-source `pytket`) + `qnexus` (cliente de la plataforma) + `pytket-quantinuum` (backend clásico) + `pytket-qiskit` (interop: `qiskit_to_tk` convierte el circuito QAOA que ya tenemos en Qiskit).
- **Jerga de targets:** sufijo **E** = emulador cloud con ruido (desactivable) · **SC** = syntax checker · **LE** = emulador local noiseless.
- **El "exacto ≤26 qubits" del enunciado** es coherente con la guía oficial del emulador: la emulación es statevector (exacta salvo shot noise cuando se apaga el ruido) y Quantinuum recomienda mantener las emulaciones statevector por debajo de ~28 qubits (con ruido se ralentiza fuerte desde ~25). Nuestras instancias (ieee14 = 14, ieee30 = 30) implican: **ieee14 entra cómodo en cualquier target; ieee30 NO va al camino cuántico** — exactamente lo que el freeze ya decidió ("IEEE-30 cuántico" está en la lista NO-va; su ancla es la enumeración clásica).

## 2 · Por qué H2 le queda como anillo al dedo a NUESTRO QAOA (el argumento técnico para el pitch)

1. **RZZ es gate nativo.** El gate de dos qubits de H2 es `ZZPhase(θ)` — ángulo parametrizado, es decir, literalmente el RZZ(γ·w_ij) de la capa de costo (KB2-02 §1.5). En plataformas de superconductores el RZZ se descompone en 2 CNOT + RZ; aquí es **una** operación nativa. El gate de un qubit nativo es `PhasedX` (cubre el mixer RX).
2. **Conectividad todos-contra-todos.** En la arquitectura QCCD los iones se transportan físicamente a zonas de compuerta, así que cualquier par de qubits puede interactuar **sin SWAPs**. Consecuencia directa: (a) el grafo del grid se implementa tal cual sin overhead de ruteo; (b) la Ruta B (penalización de balance = capa ZZ todos-contra-todos, KB2-02 §1.3) también sería nativa — el costo extra es solo #gates, no profundidad de swaps. Es el argumento de por qué la extensión "constraint mixers" es creíble en esta plataforma en particular.
3. **La compilación TKET cambia el circuito** (rebase a ZZPhase/PhasedX, optimización con niveles 0–2 por defecto): el circuito **ejecutado ≠ el circuito escrito**. Esa es exactamente la razón de existir del campo `transpiled_circuit_digest` (nota quantum-08 / freeze §11) — ver §4.

## 3 · Operativa real: colas, créditos, ruido

- **HQCs (Hardware Quantum Credits):** los emuladores cloud E consumen créditos y entran por una _Fair Queue_ cuya espera depende de la prioridad/consumo del grupo. Jobs con muchos shots se parten automáticamente en tandas. Implicación de planificación: **presupuestar los ≥5×(corridas del enunciado) con margen de cola**, y correr TODO antes del día D (ver §5).
- **Ruido configurable:** el modelo físico del emulador (depolarización asimétrica del ZZ, dephasing por transporte/idle, emisión espontánea — documentado en el H2 Emulator Product Data Sheet) se puede **sobreescribir por parámetro** (`error_params`) o **apagar** (opción noiseless: queda solo shot noise). Regla de la doc: los parámetros no especificados se mantienen; para apagar uno, se pone explícitamente en 0. Todo esto es exactamente lo que el campo `noise_config_digest` debe capturar: el dict de `error_params` canonicalizado + la versión del modelo.
- **⚠️ Determinismo del muestreo:** no encontré garantía documentada de una semilla de usuario para el muestreo de los emuladores cloud E. Consecuencia doble: (a) el reporte del enunciado (media±std de ≥5 corridas) es EL tratamiento estadístico correcto para esos runs — no hay "replay exacto" que prometer sobre el cloud; (b) la pata CONSENSUS_REPLICATION con "seeds pinned" aplica limpio a los backends locales (statevector propio / LE si expone semilla), y para el emulador cloud la réplica es "misma config, N corridas, distribución reportada". Verificar en el portal/API si `seed` existe como opción del target E antes de prometer replay byte-a-byte de esos jobs.
- **Syntax checker (H2-1SC) primero, siempre:** valida gate set/tamaño sin gastar HQCs ni cola — el "compile check" barato que debería ser un paso fijo del pipeline de jobs.

## 4 · Mapeo plataforma → contrato de evidencia (freeze §11)

| Campo congelado             | Con qué se llena en Quantinuum                                                                                                                               |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `circuit_digest`            | SHA-256 del circuito FUENTE (pytket/QASM antes de compilar)                                                                                                  |
| `transpiled_circuit_digest` | SHA-256 del circuito que devuelve `get_compiled_circuit()` (post-rebase a ZZPhase/PhasedX, con el nivel de optimización registrado)                          |
| `backend_id` + versiones    | nombre del target (`H2-1E`, `H2-1LE`, …) + versiones de pytket/qnexus/pytket-quantinuum + metadata del backend                                               |
| `noise_config_digest`       | canónico de `error_params` usado (o el marcador `noiseless`) + versión del data sheet/modelo                                                                 |
| `approximation_ratio`       | media±std de ≥5 corridas (enunciado) — la lista por-corrida completa viaja en la evidencia; jamás solo "la mejor" (KB2-04 §1/§3)                             |
| `seeds.*`                   | semillas donde el backend las soporte; donde no (⚠️ cloud E), el campo registra explícitamente `seed: unsupported` — honestidad sobre el límite, no silencio |
| runtime/costos              | HQCs consumidos + tiempo de cola como metadata operativa del job                                                                                             |

## 5 · Reconciliación con el air-gap (cómo se usa la plataforma SIN romper el freeze §15.4)

El freeze ya puso "emulador en vivo" en la lista NO-va del demo. La plataforma encaja así, en tres capas:

1. **Antes del evento (con red):** todas las corridas H2-1E (con y sin ruido, ≥5 seeds/config) se ejecutan por Nexus, y se archivan resultados + TODOS los digests de §4. El día D esos runs se sirven en modo `replay` — el certificado los referencia con procedencia completa; nada en vivo depende de la nube.
2. **Demo en vivo (air-gapped):** el hallazgo útil — el **emulador local LE** (extra `pecos`, noiseless, recomendado <16 qubits, con opción de API offline) puede correr **en la laptop**: ieee14 = 14 qubits entra. Eso permitiría, si el equipo quiere, un "esto mismo corre aquí" usando el emulador _de la plataforma oficial_ sin conexión. ⚠️ Dos verificaciones antes de prometerlo: los términos exigen haber aceptado T&C en el portal (¿la opción offline elimina el login en la práctica?) y la licencia del componente local — verificar en vivo, estilo casa.
3. **Fallback siempre disponible:** el statevector propio (Qiskit/PennyLane, KB2-03 §7) sigue siendo el cuasi-oráculo local; el LE agrega la fidelidad de "gate set y compilación reales de H2", no reemplaza nada.

## 6 · Baseline obligatorio del enunciado: GW con CVXPY (nota corta)

Goemans–Williamson = relajación SDP (matriz 14×14/30×30 — trivial para CVXPY) + redondeo por hiperplano aleatorio ⇒ **es aleatorizado: exige semilla y también se reporta como media±std**, simétrico con el cuántico (misma vara = comparación honesta). Garantía teórica 0.878 (KB2-01 §7). El valor SDP antes de redondear es además una **cota superior** del óptimo — gratis para la evidencia (sanity: óptimo_CP-SAT ≤ cota_SDP).

## 7 · Checklist de adopción (lo ejecutable cuando toque la fase de seeds)

1. Cuenta/organización en el portal de Quantinuum + aceptar T&C; crear Project en Nexus.
2. `pip install pytket qnexus pytket-quantinuum pytket-qiskit` (+ `pecos` para LE) — pinnear versiones y registrar (KB-fuentes §0.4 se extiende con estas).
3. Humo: circuito G6 (3 qubits, KB2-02 §1.4) → H2-1SC (syntax) → LE local → comparar distribución contra el statevector propio. Si G6 no da corte 5 dominante en ambos, la convención de decode está rota ANTES de gastar un HQC.
4. ieee14: compilar (registrar nivel de optimización), correr noiseless y noisy en H2-1E, ≥5 corridas por config, archivar digests §4.
5. Medir HQCs/tiempos reales del paso 4 → alimenta el presupuesto del dry-run 1.
