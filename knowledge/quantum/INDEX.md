# INDEX — ruteo rápido reto → algoritmo → nota → evidencia

> **Estado: VIGENTE (2026-07-30).** Actualizado en el saneamiento S3: fila del corpus puesta al
> día (14 instancias, 3 convenciones de peso), alta de `kb2-05` y del árbol vendorizado
> `quantathon/` (decisión #113) — ambos invisibles hasta hoy. La regla de subordinación del
> párrafo siguiente («gana la nota») queda intacta.

**Qué es esto:** tabla de una sola pantalla para decidir qué leer primero, dado un reto o una
pregunta. No reemplaza las notas — es el mapa para no tener que abrirlas todas. Pensado para
consulta humana Y de agente (Claude Code u otro) en tiempo de desarrollo. Fuente de verdad: las
notas numeradas de este directorio; si algo acá contradice una nota, gana la nota.

## Reto 1 — Red eléctrica (islanding / Max-Cut / QUBO)

| Pregunta                                       | Ir a                                                | Una línea                                                                                                                    |
| ---------------------------------------------- | --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| ¿Cómo formulo el grafo como QUBO?              | [02](02-recetario-formulacion-por-reto.md) §1.1-1.2 | Q_ii = grado ponderado, Q_ij = −w_ij; ejemplo G6 cerrado a mano                                                              |
| ¿Cómo meto la restricción de balance?          | [02](02-recetario-formulacion-por-reto.md) §1.3     | Ruta A (verificar/reparar post-hoc, la adoptada) vs Ruta B (penalización); cotas de λ con cross-ref al bootcamp              |
| ¿Cómo paso QUBO → Ising → Hamiltoniano?        | [02](02-recetario-formulacion-por-reto.md) §1.4     | fórmulas cerradas + ejemplo G6                                                                                               |
| ¿Qué algoritmo cuántico/clásico elijo?         | [07](07-catalogo-algoritmos.md) §1.2 (Clase A)      | tabla completa: cuándo sí/no, madurez NISQ, estado en Chimera, ancla de verificación                                         |
| ¿Por qué no Grover para esto?                  | [07](07-catalogo-algoritmos.md) §1.5                | descartado con causa: oráculo + √(2ⁿ) cuesta más que enumerar a n≤30 (confirmado por bootcamp Day 7 — ver `_triage-map.md`)  |
| ¿Cuáles son los baselines obligatorios?        | [07](07-catalogo-algoritmos.md) §1.2                | Goemans-Williamson (CVXPY, 0.878) y greedy (~0.5) — obligatorios por enunciado oficial                                       |
| ¿Hay un paper que valide este approach exacto? | [05](05-regrid-qaoa-extraccion.md)                  | REGRID-QAOA (arXiv:2606.15083): mismo patrón muestreo+verificación, IEEE 9-57 buses, hardware real                           |
| ¿Cuál es el corpus de benchmarks?              | `knowledge/islanding/01-corpus-benchmarks.md`       | 14 instancias con óptimo exacto: ieee6/9/14/30 + cr6/cr8 + ice, 3 convenciones de peso (uniforme/flujo/voltaje), doble ancla |

## Reto 2 — Potabilidad del agua (QML)

| Pregunta                         | Ir a                                           | Una línea                                                                                               |
| -------------------------------- | ---------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| ¿Kernel cuántico o VQC?          | [07](07-catalogo-algoritmos.md) §1.3 (Clase B) | kernel+SVM es el camino principal (~19k circuitos); VQC solo stretch (~360k circuitos, barren plateaus) |
| ¿Cómo armo el pipeline completo? | [02](02-recetario-formulacion-por-reto.md) §2  | features, submuestreo, kernel matrix, baseline clásico bajo las mismas condiciones                      |
| ¿Qué accuracy es realista?       | `00-kb-fuentes.md` §2.1                        | dataset sintético difícil, clásico ronda 65-70%; no prometer 95%                                        |

## Reto 3 — TFIM/Trotter (condicional, segundo reto solo si C1 está completo)

| Pregunta                              | Ir a                                               | Una línea                                                                                       |
| ------------------------------------- | -------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| ¿Qué cambió del VQE/química original? | [07](07-catalogo-algoritmos.md) §1.4 nota de drift | C3 oficial es TFIM+Trotter, no química molecular — la tabla de VQE queda como referencia Fase 2 |
| ¿Cuál es el ancla de verificación?    | [07](07-catalogo-algoritmos.md) §1.4 nota de drift | ED del mismo Hamiltoniano (SciPy/PySCF) → FORMAL_EXACT; criterio ⟨Zᵢ⟩/⟨ZᵢZᵢ₊₁⟩ dentro de 5%     |

## Transversal — verificación, honestidad, formato de entrega

| Pregunta                                                  | Ir a                                         | Una línea                                                                                                                                                                   |
| --------------------------------------------------------- | -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ¿Cómo elige el planner entre candidatos?                  | [07](07-catalogo-algoritmos.md) §1.7         | problema→clase→catálogo filtrado; la verificación NUNCA cambia al cambiar de candidato (INV-2)                                                                              |
| ¿Qué formato de entrega usan los ganadores?               | [06](06-quantathons-ganadores.md) §1.5       | un notebook final ejecutable + resultados congelados (CSV) + presentación en el repo                                                                                        |
| ¿Cómo reporto límites sin quedar mal?                     | [06](06-quantathons-ganadores.md) §1.5 pt.3  | honestidad explícita sobre no-ventaja-cuántica es lo que premian los jueces, no debilidad                                                                                   |
| ¿Qué stack/idioms uso?                                    | [03](03-lenguajes-frameworks-stack.md)       | Qiskit/PennyLane/OpenQASM3/dimod-neal, 5 idioms, frontera de simulación ~28-30 qubits                                                                                       |
| ¿Qué métricas/estadística reporto?                        | [04](04-estadistica-evidencia.md)            | approximation ratio, shots, baselines, seeds — checklist completo                                                                                                           |
| ¿De dónde saco papers/tutoriales/repos citables?          | [00](00-kb-fuentes.md)                       | fuente de fuentes, por reto, con gotchas de versión de librerías                                                                                                            |
| ¿Ya se revisaron las clases del bootcamp?                 | [`_triage-map.md`](_triage-map.md)           | sí, 11/16 QWorld — cobertura fuerte, sin gaps críticos; resto pendiente                                                                                                     |
| ¿Qué es la plataforma obligatoria del C1 (H2/Nexus/TKET)? | [kb2-05](kb2-05-plataforma-quantinuum-h2.md) | brief operativo Quantinuum H2/emuladores/pytket/Nexus; complementa la nota [08](08-ruta-quantinuum-guppy.md) (nombre fuera de convención — renombre/fusión diferido, #118)  |
| ¿Cuál es la receta vigente del reto 3 (C3)?               | [11](11-receta-c3-tfim-trotter.md)           | STUB S3: TFIM + Trotterización con ancla ED ≤5% — reemplaza la receta de química de la nota [02](02-recetario-formulacion-por-reto.md) §3 (supersedida S-E); G1 la completa |
| ¿Y el material crudo del evento (árbol de 81 archivos)?   | `quantathon/`                                | VENDORIZADO-AJENO — «insumo de trabajo próximo» (decisión #113); licencia/atribución de terceros PENDIENTE (N11) antes del flip OSS (O2/M26); excluido del gate de docs     |

## Regla de oro (la que no cambia nunca)

Ningún algoritmo del catálogo es el verificador de otro (INV-2/PR2). Un candidato que reporte
mejor que el óptimo probado por el ancla FORMAL_EXACT es un bug del proceso, nunca un
descubrimiento — aplica a todos por igual.
