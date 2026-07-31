# Triage — QWorld OQI Pre-Hackathon Training 2026 (11/16 sesiones QWorld triadas)

> **Estado: HISTÓRICO (2026-07-30).** Triage pre-hackathon: su propósito (decidir qué extraer de
> las clases del bootcamp antes del evento) es del evento ya terminado. Queda como registro de
> metodología y cobertura; sus pendientes no son tareas vivas. Ver la nota fechada al final sobre
> la regla «VTT crudos NUNCA en el repo».

**Qué es esto:** mapa de reconocimiento (no destilación) sobre las clases de q-world/bootcamp,
producido para decidir qué vale la pena extraer a `knowledge/quantum/`. Metodología: captions de
YouTube (`yt-dlp --write-auto-subs`, gratis) + un agente por sesión que produce tema/resumen/tags,
sin tocar el repo con transcripts crudos. Ver `docs/research/arquitectura-ingesta-kg-fase2.md`
(rama `docs/ingesta-kg-fase2`) para el diseño completo de un proceso a escala, si se retoma.

**Estado del inventario completo (según Dylan, 2026-07-21):**

- **QWorld (16 fuentes) — 11/16 triadas en esta pasada:**
  - 11 YouTube = la serie "QWorld OQI Pre-Hackathon Training 2026-1" (Welcome + Day 1–10) → **triadas abajo**.
  - 5 Google Drive (videos sueltos, sin captions extraíbles vía yt-dlp) → **pendientes** (requieren
    descarga + whisper/Groq; no se hizo en esta pasada — ver tabla de pendientes al final).
- **Carpeta compartida "Quantathon Bootcamp classes & materials"** (Drive, compartida con Dylan el
  mismo día de este ejercicio) — **bloqueada por lag de indexación de Drive**, solo 1 de N subcarpetas
  visible vía búsqueda (`7. Introducción a Quantum Singular Value Transformation — Daniela Angulo`).
  Es casi seguro donde vive el grueso restante de las ~36 clases mencionadas originalmente. **No
  triada — pendiente de que el índice de Drive se ponga al día, o de un listado manual.**

---

## Tabla de triage — serie QWorld OQI (11 sesiones)

| #   | Sesión                                    | Tema                                                                                                     | Tags                                                                        | Relevancia reto                                       | Veredicto                                                                                                                                                                               |
| --- | ----------------------------------------- | -------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0   | Welcome                                   | Logística del programa (Canvas/Discord/certificación)                                                    | pedagogia-pura                                                              | ninguna                                               | skip                                                                                                                                                                                    |
| 1   | Day 1 — Prospects of QC                   | P/NP/BQP, "sweet spot" ventaja∩verificable∩NISQ, red eléctrica citada como ejemplo NP-complete           | seleccion-algoritmo, pedagogia-pura, matematica-fundamento                  | **C1 directa** (valida framing), C2 moderada          | ya cubierto conceptualmente (la tesis de verificación de Chimera es una versión más rigurosa de este mismo framing)                                                                     |
| 2   | Day 2 — Classical Systems                 | Bits probabilísticos, formalismo previo a qubits                                                         | pedagogia-pura, matematica-fundamento                                       | ninguna directa                                       | skip                                                                                                                                                                                    |
| 3   | Day 3 — Quantum Systems                   | Qubits, regla de Born, Hadamard, entrelazamiento                                                         | pedagogia-pura, matematica-fundamento                                       | ninguna directa                                       | skip                                                                                                                                                                                    |
| 4   | Day 4 — Quantum Operations and Circuits   | Compuertas, estado de Bell, interferencia                                                                | pedagogia-pura, matematica-fundamento                                       | débil, transversal                                    | skip                                                                                                                                                                                    |
| 5   | Day 5 — Quantum Programming and Protocols | Qiskit básico, superdense coding, teleportación                                                          | pedagogia-pura, matematica-fundamento                                       | débil (boilerplate ya cubierto por el stack, nota 03) | skip                                                                                                                                                                                    |
| 6   | Day 6 — Grover's Algorithm                | Oráculo, amplificación, difusión                                                                         | pedagogia-pura, matematica-fundamento                                       | ninguna directa                                       | skip                                                                                                                                                                                    |
| 7   | Day 7 — Max Cut via Grover                | Grover aplicado a Max-Cut, especulación O(√2ⁿ) vs heurístico QAOA, anécdota de "ventaja que desapareció" | seleccion-algoritmo, pedagogia-pura, matematica-fundamento                  | **C1 directa**                                        | **ya cubierto** — confirma la fila "Grover: descartado con causa" de `07-catalogo-algoritmos.md` §1.5. Anécdota de honestidad es corroborante de `06-quantathons-ganadores.md`, no gap. |
| 8   | Day 8 — QUBO                              | Formulación QUBO, penalizaciones, regla P > peso máx. de arista, TSP como 2do ejemplo                    | matematica-fundamento, receta-por-reto, seleccion-algoritmo, pedagogia-pura | **C1 directa**                                        | **nuance, no gap** — ver §"Hallazgo" abajo                                                                                                                                              |
| 9   | Day 9 — QUBO, Variational Quantum Alg     | Reducción a cuadrático, derivación QUBO→Ising para Max-Cut, intro VQE                                    | matematica-fundamento, pedagogia-pura                                       | **C1 directa**                                        | **ya cubierto** — `02-recetario-formulacion-por-reto.md` §1.4 tiene la misma derivación                                                                                                 |
| 10  | Day 10 — QAOA                             | Derivación QAOA (recocido→adiabático→Trotter→QAOA), H_C = H_Ising de Max-Cut                             | matematica-fundamento, receta-por-reto, seleccion-algoritmo                 | **C1 directa**                                        | **ya cubierto** — misma derivación estándar que nota 02                                                                                                                                 |

---

## Hallazgo del gap-diff (A3)

**Conclusión general: cobertura existente en `knowledge/quantum/` es fuerte. Cero gaps críticos**
en las 11 sesiones QWorld triadas. Dos de las tres coincidencias más directas con Challenge 1
(Day 7 "Max-Cut via Grover", Day 9/10 derivación QUBO→Ising→QAOA) **confirman** decisiones ya
tomadas y documentadas por Sebas/Dylan en `07-catalogo-algoritmos.md` y `02-recetario-formulacion-por-reto.md`,
no las cuestionan ni las amplían de forma sustantiva.

**Único punto con valor de cross-reference (no urgente, no bloqueante):**

- Day 8 enseña una regla de penalización simple: **P > peso máximo de una sola arista** (condición
  suficiente para que violar la restricción nunca convenga).
- `knowledge/quantum/02-recetario-formulacion-por-reto.md` §1.3 (línea 67) ya documenta una regla
  _distinta y más elaborada_, de la literatura (Glover et al., arXiv:1811.11538): λ ≈ 0.75–1.5× la
  magnitud estimada del objetivo, con loop de ajuste empírico (resolver → chequear factibilidad →
  λ×2 o λ/2).
- Ambas son válidas para propósitos distintos (Day 8 es una cota suficiente simple para un caso de
  restricción única; nota 02 es una heurística de sintonización para QUBOs con múltiples términos).
  **Aplicado (2026-07-21):** cross-reference agregada en `02-recetario-formulacion-por-reto.md`
  §1.3, punto 3, citando Day 8 como fuente — pendiente de que Sebas la revise en su próxima pasada
  de ratificación del plano (es su plano).

---

## Pendientes (no bloqueantes para este ejercicio)

| Fuente                                                                                                                            | Estado                                                                  | Acción sugerida si se retoma                                                                                                                                                                                                                                                            |
| --------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 5 videos QWorld en Drive (intro responsible QC, 2× Qai Ventures pitching, 2× "Recording" sin título)                              | sin transcribir                                                         | bajar + whisper/Groq solo si el checkpoint humano decide que vale la pena; los 2 sin título necesitan identificarse primero                                                                                                                                                             |
| Carpeta "Quantathon Bootcamp classes & materials" (~20-25 sesiones estimadas, folders numerados con tema+ponente ya en el título) | bloqueada por indexación de Drive (compartida 2026-07-21, el mismo día) | reintentar el listado en unas horas, o pedirle a Dylan que abra la carpeta y pegue la lista de subcarpetas — los títulos solos (p. ej. "7. Introducción a Quantum Singular Value Transformation") probablemente ya bastan para un triage de bajo costo antes de tocar ningún transcript |

---

## Nota metodológica

Modelo usado para el triage: heredado de la sesión (no se enrutó a Fable/Groq como proponía el
plan original — pendiente si se retoma a escala). Transcripts en inglés únicamente (captions en
español fueron parcialmente rate-limited por YouTube durante la descarga; el inglés cubrió 11/11
sin huecos). Archivos VTT crudos viven en el scratchpad de la sesión, NUNCA en el repo.

> **Nota (2026-07-30, saneamiento S3):** la regla de arriba («VTT crudos NUNCA en el repo») quedó
> contradicha de facto por el árbol vendorizado `knowledge/quantum/quantathon/` — material del
> evento que este triage no menciona. La decisión #113 acepta ese árbol como «insumo de trabajo
> próximo», con licencia/atribución de terceros PENDIENTE (N11) antes del flip OSS (O2/M26). La
> regla original no se borra: queda como registro de la metodología de esta pasada.
