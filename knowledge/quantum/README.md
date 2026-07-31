# Knowledge — Quantum (plano cuántico / ciencia · Sebas)

> **Estado: VIGENTE (2026-07-30).** Índice actualizado en el saneamiento S3: alta de
> [`kb2-05`](kb2-05-plataforma-quantinuum-h2.md) (hasta hoy fuera de ambos índices) y del árbol
> vendorizado `quantathon/` con su marca (decisión #113) — ver las secciones nuevas abajo.

**¿Buscás algo rápido?** Empezá por [`INDEX.md`](INDEX.md) — tabla de ruteo reto → algoritmo →
nota, pensada para consulta veloz humana o de agente. Lo de abajo es el índice completo de notas.

Notas de la investigación del plano cuántico (serie "KB2", 2026-07-08/14), normalizadas a la
estructura del knowledge base en la consolidación (2026-07-14). La serie es deliberadamente
estratificada: la nota 00 ("KB-fuentes") es la capa de links/versiones/gotchas que las notas
01–04 referencian y no repiten.

Las notas 01–04 cierran con su sección **"Template de nota"** (decisión · licencias · impacto
en contrato · reconciliación); los huecos que quedaron de la investigación original se marcaron
ahí y se resumen abajo — no se rellenaron en la consolidación para no inventar validaciones que
no ocurrieron, y **quedaron cerrados en el barrido S-E (2026-07-18)**: cada uno dice hoy su
resolución (decidido — ratificación final del dueño, registrado en el freeze, o chequeo
declarado con disparador).

## Índice

| Nota                                         | Tema                                                                                                                                                                                                                                                                                                                                                                             | Contratos que toca                                                                                                                                         |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [00](00-kb-fuentes.md)                       | KB-fuentes: URLs, pinning de versiones, migraciones de API (primitives V2), gotchas por reto, repos de hackathons ganadores, checklist RAG                                                                                                                                                                                                                                       | ninguno; capa de fuentes (⚠️ vocabulario pre-reconciliación en varias secciones — leer su encabezado)                                                      |
| [01](01-fundamentos-matematicos.md)          | Fundamentos mínimos: estados/compuertas, principio variacional, QUBO↔Ising con cambio de moneda exacto, teoría QAOA/VQE/kernels, parameter-shift, barren plateaus, glosario ES/EN                                                                                                                                                                                                | ninguno directo; sostiene la regla fail-loud "mejor que el óptimo ⇒ bug" (espejo de trust/10) y alimenta la nota 04                                        |
| [02](02-recetario-formulacion-por-reto.md)   | Recetario proponente por reto: grafo→QUBO→Ising→circuito QAOA (G6 cerrado), pipeline kernel Reto 2, VQE/UCCSD/anclas de química (el C3 oficial es TFIM/Trotter — ver su §3, nota de drift)                                                                                                                                                                                       | produce los claims que consumen `ExactSolverVerifier` (trust/10) y `ExecutionVerifier` (trust/12); λ/features/seeds → `knowledge/` versionado + `evidence` |
| [03](03-lenguajes-frameworks-stack.md)       | Stack: modelos mentales y 5 idioms (Qiskit/PennyLane/OpenQASM 3/dimod-neal), trampas de convención entre frameworks, frontera honesta de simulación (~28–30 qubits)                                                                                                                                                                                                              | propone `evidence.circuit_digest` (aditivo, `qasm3.dumps` → SHA-256); posturas usar/descartar por herramienta                                              |
| [04](04-estadistica-evidencia.md)            | Estadística de la evidencia: approximation ratio, shots, baselines, consenso rung 5, propiedades rung 4, McNemar, unidades Hartree, checklist de semillas/replay                                                                                                                                                                                                                 | campos aditivos a `evidence` (`approximation_ratio`, `se_estimado`, `exact`, `seeds.*`); detalle de `GuardrailSignal` para self-consistency                |
| [05](05-regrid-qaoa-extraccion.md)           | REGRID-QAOA extraído (arXiv:2606.15083, verificado en vivo): objetivo Eq. 11 (w=(\|p_ij\|+\|p_ji\|)/2), penalizaciones con slacks logarítmicos, surrogate de conectividad, reparación M.1–M.5, setup IEEE — **valida la Ruta A** y refuerza la ablación A/B                                                                                                                      | alimenta la formulación (nota 02) y el corpus (`islanding/01`); posible `evidence.repair.*` si se adopta el recetario M.1–M.5                              |
| [06](06-quantathons-ganadores.md)            | Soluciones ganadoras de quantathons (ETH QHack 2024, QHack 2022/23, CDL 2020): patrón común = baseline clásico exacto + % del óptimo + honestidad de límites + reproducibilidad                                                                                                                                                                                                  | ninguno; material de pitch — el diferenciador de verificación de CHIMERA ES el patrón ganador institucionalizado                                           |
| [07](07-catalogo-algoritmos.md)              | Catálogo de algoritmos por clase de problema (27 filas: optimización/ML/química/sampling): cuándo usar cada uno, madurez NISQ, estado en Chimera, ancla correspondiente (vocabulario v3.2); cierra con "cómo elige el planner"                                                                                                                                                   | ninguno; knowledge que consume el planner — este mes ≥4 proponentes del Reto 1 sobre el mismo corpus; Grover/HHL/QPE descartados con causa                 |
| [08](08-ruta-quantinuum-guppy.md)            | Ruta Quantinuum (en vivo 2026-07-17): **Guppy NO obligatorio** (qiskit→pytket→emulador; puente `guppy.load_pytket()`); **modelo de ruido H-series configurable** (gate del corrector: ABIERTO); pytket-pennylane ARCHIVADO ⇒ PennyLane vía QASM; trampas half-turns/ILO-BE; multi-emulador = patas CONSENSUS_REPLICATION                                                         | provenance por backend-leg (`decode()` congelada con G6 por leg); licencias del stack pytket/guppy todas Apache-2.0                                        |
| [09](09-corrector-ai-qem.md)                 | El corrector AI-QEM: mitigación aprendida (RF/GBM, patrón CDR/ML-QEM verificado con números) evaluada contra el corpus de óptimos exactos — "el certificado del corrector"; controles negativos obligatorios (ZNE artefactual, arXiv jul-2026); Mitiq **GPL-3.0** solo dep opcional del harness de eval                                                                          | bloque aditivo `mitigation.*` del claim proponente (freeze §11); GO condicionado a Reto 1 core verde; S7 intacto (el corrector propone, jamás verifica)    |
| [10](10-adopcion-industrial.md)              | Adopción industrial de QC (web, jul 2026): mapa producción-vs-POC (certified randomness Quantinuum+JPMorgan = ÚNICA aplicación comercial limpia — y es una capa de confianza), mapa de ventaja demostrada/probable/activa/nunca, IA×QC desplegada (AlphaQubit, ML-QEM, transpilación IA), automatización (Qiskit Functions/QFaaS) y el hueco: tracking registra, nadie certifica | ninguno; munición de pitch/Q&A (S-P) y material inversor — procedencia por claim, slop descartado explícitamente                                           |
| [kb2-05](kb2-05-plataforma-quantinuum-h2.md) | Brief operativo de la plataforma obligatoria del C1 (2026-07-20): Quantinuum H2/emuladores (exacto ≤26 qubits), TKET/pytket y Nexus; mapea al contrato de evidencia congelado (freeze §11 / nota 08) y al air-gap del demo (freeze §15.4). Nombre fuera de convención (colisiona con `05-`): renombre/fusión con la nota 08 diferido al refactoring final (#118)                 | ninguno nuevo; llena campos de `evidence` ya congelados (freeze §11)                                                                                       |
| [11](11-receta-c3-tfim-trotter.md)           | **STUB (S3, 2026-07-30):** receta C3 = TFIM + Trotterización — el destino con nombre de la receta que reemplaza a la química de la nota 02 §3 (supersedida S-E); registra lo normativo ya decidido (cadenas N∈{6,8,12}, ancla ED ≤5%, C-14 `EXACT_DIAGONALIZATION`); el contenido completo lo escribe G1                                                                         | los del supersede S-E + C-14 (#106); receta de química de 02 §3 = solo referencia                                                                          |

> Las notas 05–09 son investigación de consolidación (Dylan, 2026-07-14/17) que cierra los
> huecos del plan y los del bootcamp; **pendientes de ratificación final de Sebas**, igual que
> el corpus de `knowledge/islanding/`. Las notas 07–09 ya usan el vocabulario de la spec v3.2
> (clases decisorias + AL — ver `docs/convergencia-diseno-v32.md`). La nota 10 (2026-07-23) es
> investigación dirigida post-charla industrial, para el track de pitch (S-P).

## Triage de fuentes externas (bootcamp / clases)

[`_triage-map.md`](_triage-map.md) — mapa de reconocimiento (no una nota numerada; no sigue el
template de decisión/licencias/reconciliación) sobre las clases del bootcamp pre-hackathon
(QWorld OQI 2026) usadas para preparar al equipo. Cruza el contenido de cada sesión contra las
notas 00/02/06/07 de este directorio para detectar gaps. **Resultado (2026-07-21):** cobertura
existente fuerte, sin gaps críticos — la única nuance detectada ya se incorporó a la nota 02 §1.3.
Cobertura parcial: 11/16 fuentes de la serie QWorld; la carpeta compartida "Quantathon Bootcamp
classes & materials" (el grueso restante de las clases) queda pendiente de triage — ver el archivo
para el detalle de qué falta y por qué.

## Árbol vendorizado `quantathon/`

**VENDORIZADO-AJENO — «insumo de trabajo próximo» (decisión #113, 2026-07-30).** El árbol
`quantathon/` es la copia completa del material dado durante la hackathon (81 archivos, ~16 MB;
no sigue el template de notas ni el idioma del corpus). Se queda en el repo como insumo del
refinamiento/ingesta RAG-KB próximo (conecta con la decisión #116); está **excluido del gate de
docs** (`.markdownlintignore`/`.prettierignore`) y su licencia/atribución de terceros queda
**PENDIENTE (N11) antes del flip OSS (O2/M26)**. Si el refinamiento no llega, se re-litiga la
desvendorización con la decisión #113 como registro de causa.

## Estado de los pendientes originales

1. **Corpus de benchmarks — RESUELTO en la consolidación (2026-07-14):** vive en
   `knowledge/islanding/` (nota 01 + `corpus/*.json`): IEEE 9/14/30 × {uniforme, flujo}, óptimos
   exactos con doble ancla (CP-SAT + fuerza bruta donde n≤14; cero conflictos), canonicalización
   x₀=0, digests SHA-256, script de regeneración inline. **Decidido (S-E 2026-07-18) —
   ratificación final de Sebas:** correr el script (la segunda ancla de ieee30 quedó decidida:
   enumeración vectorizada, freeze §15.3), comparar digests, y aportar cr8/cr6 desde los datos
   abiertos del ICE (islanding/01 §1.8 — P0-7).
2. **Licencias — RESUELTO:** verificadas en vivo 2026-07-14 (nota 03 §5 y su sección de template):
   Qiskit/PennyLane/dimod/neal/PySCF/OpenQASM 3, todas Apache-2.0.
3. **Campos aditivos de `evidence` — RESUELTO:** registrados en `docs/contract-freeze.md` **§11**;
   Sebas ratifica.
4. **REGRID-QAOA — RESUELTO:** extracción completa en la nota 05.
5. **Quantathons ganadores — RESUELTO:** análisis en la nota 06.
6. **Ratificar las reconciliaciones** de todas las notas (incluidas 05/06 y el corpus) — sigue
   siendo del autor del plano: Sebas.
