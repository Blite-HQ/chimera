# Gap analysis Reto 1 — vanilla espejo vs Chimera (E2 del Plan Espejo)

**Fecha:** 2026-07-23 · **Insumo:** repo `reto1-vanilla` (hermano de este repo) — la "mejor
solución convencional" del Challenge 1, construida deliberadamente SIN Chimera para fijar la
barra empírica. **Regla del análisis:** solo se lista una brecha si compra puntos de rúbrica o
protege contra una deducción; lo que no puntúa se descarta explícitamente.

**Estado del espejo al escribir esto:** pipeline completo verde (41 tests; fuerza bruta + GW/
CVXPY con cota SDP + greedy + SA; QAOA Qiskit p=1..3 con estadística multi-semilla; cr8/cr6
generadas desde datos abiertos reales del ICE con doble ancla y digest; `reproduce.py` único;
**round-trips reales a Quantinuum Nexus verificados HOY**: H2-1LE (gratis, sin ruido) y
H2-Emulator (modelo de ruido H-series, ~10 HQC el job mínimo)).

---

## 1 · Tabla por criterio de rúbrica

| Criterio (peso)                                                              | Ya existe en Chimera                                                                                                            | Falta y PUNTÚA (acción E3)                                                                                                                                                                                                                                                                                                                                                                                                                                          | Falta y NO puntúa (descartado)                                                                                                                |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Línea base clásica (15%)                                                     | Corpus con óptimos doblemente anclados + digests (islanding/01); CP-SAT spec trust/10; CVXPY ya decidida en deps (freeze §15.4) | Proponentes GW/greedy/SA como claims verificados dentro de la plataforma (el espejo ya tiene las implementaciones de referencia con semillas y estadística — portar, no reinventar)                                                                                                                                                                                                                                                                                 | Solvers clásicos adicionales (Gurobi, etc.): la celda "Excellent" pide GW + ≥1, ya cubierto                                                   |
| Implementación cuántica (30% = 10 intento + 10 ejecución + 10 hardware real) | Ruta quantum/08 (qiskit→pytket→Nexus) — **DE-RIESGADA HOY con corridas reales**; recetario QAOA (quantum/02); seeds S-G         | (a) Capability `challenge1/` que corre el pipeline QAOA emitiendo claims + evidencia (ángulos, semillas, shots, circuit digest); (b) decode POR BACKEND congelada con vector (pytket ILO: `key[i]` = qubit i — implementada y testeada en el espejo); (c) **preguntar a la organización por acceso a H2 real** — la lista de devices de Nexus HOY no trae ninguna QPU (solo emuladores): sin esa gestión, el 10% de hardware es inalcanzable para TODOS los equipos | Guppy nativo para el core (el statement de SDK defiende la elección qiskit→pytket; el puente `load_pytket` queda documentado quantum/08 §1.2) |
| Comparación y escalado (20%)                                                 | Corpus ieee9/14/30 × 2 convenciones; estadística quantum/04; escalera congelada (freeze §15.3)                                  | r vs p multi-instancia + tabla clásico-vs-cuántico SOBRE LA MISMA instancia como salida de primera clase del run (el espejo tiene las figuras de referencia con barras de error); ieee30 solo clásico + extrapolación honesta (ya redactada en el espejo)                                                                                                                                                                                                           | Instancias extra fuera de la escalera                                                                                                         |
| Impacto ODS (5%)                                                             | Narrativa ODS 7/9/13 en docs; doctrina de soberanía de datos (freeze §15.2)                                                     | **cr8/cr6 REALES ya existen en el espejo** (corredor GAM desde ArcGIS ICE, 2 convenciones, doble ancla, provenance completa) → dárselas a Sebas como referencia para su ratificación/congelamiento en el corpus (decisión de peso: `voltaje` = suma kV, alternativa a sus 3 opciones; la `uniforme` es idéntica a su plan)                                                                                                                                          | —                                                                                                                                             |
| Reproducibilidad (10%, deducción GLOBAL si falta)                            | verify-bundle.py (S-G); compose air-gapped (camino dorado)                                                                      | `challenge1/reproduce.py` + requirements.txt del paquete de entrega (P0-6) — el espejo ES el prototipo funcionando; decisión de repo de entrega pendiente (post-E1, a más tardar dry-run 1)                                                                                                                                                                                                                                                                         | —                                                                                                                                             |
| Explicación (20%)                                                            | Guías de ratificación por dueño; knowledge base completo                                                                        | Material de teach-back por integrante + ensayo cronometrado en dry-runs (E5/S-P); el espejo es pequeño y explicable línea por línea — usarlo como material didáctico del equipo                                                                                                                                                                                                                                                                                     | —                                                                                                                                             |
| Extensiones (cuenta positivo)                                                | AI-QEM diseñada (quantum/09, gate "core verde"); ZNE catalogada                                                                 | El par {H2-Emulator ruidoso ↔ H2-1LE ideal} **confirmado operativo HOY** = exactamente el dataset que AI-QEM necesita (par ruidoso/ideal del MISMO circuito); análisis de ruido ideal-vs-ruidoso ya en el espejo (figura `ruido-h2`)                                                                                                                                                                                                                                | QEC/Iceberg (el propio enunciado advierte que puede degradar; ZNE/mitigación es la vía pragmática oficial)                                    |

## 2 · Intel operativa nueva (verificada en vivo hoy, para quantum/08)

1. **Devices Nexus visibles:** H2-Emulator/H1-Emulator (ruido H-series), H2-1LE/H1-1LE
   (sin ruido, gratis), H2-1SC/H1-1SC (syntax check), Selene/SelenePlus, Helios-1E-lite,
   Aer/Braket hosted. **Ninguna QPU real** → el 10% de hardware depende de gestión con la
   organización (canal del evento).
2. **Quirk del SDK:** `qnx.circuits.cost()` deriva `<device>SC` — funciona para nombres
   H-series cortos, revienta con alias (`H2-EmulatorSC` inválido). Workaround del espejo:
   fórmula HQC local pre-compilación como cota inferior etiquetada.
3. **Flujo confirmado:** `projects.get_or_create → circuits.upload → compile →
start_execute_job(valid_check=True) → jobs.wait_for → results[0].download_result()` —
   idéntico al patrón de qnexus-mcp (M2.2).
4. **El emulador remoto no expone seed** → la pata emulador de CONSENSUS_REPLICATION aporta
   estadística, no réplica exacta (confirma la advertencia de quantum/08 §1.5).
5. **Costo real de referencia:** job mínimo (6 qubits, p=1, 256 shots) en H2-Emulator ≈ 10 HQC
   (estimación local); el job corrió con la cuenta del evento sin rechazo de cuota.

## 3 · Cortes de scope que este análisis ratifica

- Nada de `ProblemAdapter`/`HybridSolverEngine` genéricos (planes LLM descartados): el freeze
  ya define los contratos; el espejo demuestra que la solución cabe en módulos concretos.
- El corpus NO se regenera (Δ1 del freeze intacto); cr8/cr6 del espejo entran como PROPUESTA
  para la ratificación de Sebas, no como sustitución.
- La física de islas sigue re-scopeada a limitaciones + extensión "constraint mixers"
  (freeze §15.3) — el espejo ya trae la sección de limitaciones redactada.

## 4 · Secuencia E3 resultante (solo lo que puntúa)

1. Paquete `challenge1/` reproducible en Chimera (P0-6) consumiendo los módulos de referencia
   del espejo — camino dorado run→claim→verificación→certificado→verify-bundle sobre cr8/ieee14.
2. Fixture de la falla sembrada (P0-4, vector congelado ieee14-flujo bus 1 → fail).
3. Claims GW/greedy/SA + QAOA con `mitigation.*` opcional (gate AI-QEM abierto si core verde).
4. Gestión Dylan: pregunta de acceso a QPU real en el canal (10% de la rúbrica, costo cero).
5. Entrega de cr8/cr6 del espejo a Sebas (ratificación + congelamiento en corpus con IDs ya
   reservados en freeze §15.3).
