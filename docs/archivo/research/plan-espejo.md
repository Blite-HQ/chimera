# Plan Espejo — Reto 1: solución vanilla → gap analysis → Chimera verificando

> **Estado: HISTÓRICO (2026-07-30, archivado por #112).** Huérfano absoluto del censo
> (0 referencias entrantes en todo el repo). Su tracking HECHO/FALTA quedó congelado en un
> estado falso (E3/E5 marcados «FALTA» están construidos y cerrados) — el tracking NO se
> corrige, se declara congelado.

**Fecha:** 2026-07-23 · **Rama de trabajo:** `reto1/plan-espejo` · **Dueños:** Dylan + Claude.
Este doc es el plan aprobado el 23-jul y su registro de progreso, para que el equipo vea qué
está hecho y qué falta sin reconstruir la sesión.

## El dilema que resuelve

Cuatro planes candidatos (de varios LLMs) + el feedback de la charla industrial del 23-jul
(QC comercial, automatización profunda + IA) dejaban una tensión aparente: ¿ventaja real
validada por la industria hoy, o la innovación de la capa de verificación/confianza?

**La rúbrica disuelve la tensión:** baseline clásico 15% + comparación/escalado 20% +
reproducibilidad 10% + explicación 20% = **65% del puntaje es rigor de ingeniería híbrida** —
exactamente lo que la industria valida hoy — y la capa de confianza es el mecanismo que
maximiza esos criterios. Los jueces lo dicen textual: "rigor y honestidad por encima de la
ambición". Pitch en una línea: _no vendemos ventaja cuántica; vendemos confianza verificable
en resultados híbridos._

## Etapas (orden y dependencias, sin fechas)

1. **E1 — Solución vanilla en repo hermano** (`reto1-vanilla`), deliberadamente sin Chimera:
   la mejor solución convencional, mapeada 1:1 al checklist oficial. Fija la barra empírica.
2. **E2 — Gap analysis** contra Chimera, por criterio de rúbrica (tras E1).
3. **E3 — Chimera reproduce el reto BAJO verificación** (tras E2): camino dorado
   run → claim → verificación contra anclas → certificado DSSE → bundle → verify-bundle,
   walking skeleton de punta a punta + fixture de la falla sembrada.
4. **E4 — Investigación de adopción industrial** (paralela): munición de pitch/Q&A.
5. **E5 — Entregables del jurado** (cierre, se pule en dry-runs): informe ≤8 págs, deck 5 min,
   statement SDK ≤200 palabras, teach-back del equipo (explicación = 20%).

## Progreso

### HECHO

- **E1 COMPLETA** — repo `reto1-vanilla` (hermano de Chimera; 46 tests, 98% cobertura,
  `reproduce.py` único + `--figures-only` offline, requirements.txt del lock):
  - Instancias con óptimo doblemente anclado + digest SHA-256: IEEE 9/14/30 (del corpus) y
    **cr8/cr6 desde datos abiertos reales del ICE** (corredor GAM La Caja–Alajuelita–Anonos–
    Belén–Ribera–Colima–Heredia–Cóncavas; convenciones `uniforme` y `voltaje`=suma kV;
    snapshots crudos commiteados; derivación determinista auditable).
  - Clásicos: fuerza bruta exacta, **GW/CVXPY con cota SDP** (encuentra el óptimo exacto en
    TODAS las instancias, ieee30 incluida), greedy, recocido simulado — seeded, con estadística.
  - QAOA (Qiskit, statevector + Aer seeded, warm-start monótono en p), 5 semillas × p=1..3:
    r(p=1) entre 0.73–0.86 (todas ≥ 0.6, el umbral oficial); cr8: 0.861 → 0.904 → 0.931.
  - **19 corridas REALES vía Quantinuum Nexus:** matriz H2-1LE (gratis, sin ruido) con
    **r_best = 1.0 en todas las celdas** (el óptimo apareció en las muestras hasta en ieee14);
    cr8-uniforme p=1..3 en **H2-Emulator con modelo de ruido H-series**: 0.856/0.902/0.934
    (mejora monótona incluso con ruido; gasto ≈175 HQC). Figura de análisis de ruido
    statevector-vs-ideal-vs-ruidoso incluida.
- **E2 COMPLETA** — `docs/research/gap-analysis-reto1.md` (en esta rama): brechas por
  criterio, descartes explícitos, intel operativa de Nexus (ver "Hallazgos" abajo).
- **E4 COMPLETA** — `knowledge/quantum/10-adopcion-industrial.md` (en esta rama): mapa
  producción-vs-POC con procedencia por claim. Hallazgo estrella: la única aplicación
  comercial limpia de QC (certified randomness, Quantinuum+JPMorgan) **es una capa de
  confianza** — evidencia externa de la tesis.

### Hallazgos operativos clave (verificados en vivo contra Nexus)

- **Sin QPU real** en la lista de devices de la cuenta del evento → el 10% de la rúbrica por
  hardware real requiere preguntar a la organización (pendiente, dueño Dylan).
- Flujo de submission confirmado (upload → compile → execute → results, patrón qnexus-mcp);
  el endpoint de costo revienta con alias de device (`H2-EmulatorSC`); el emulador remoto no
  expone seed (la pata de réplica exacta multi-emulador queda como estadística).
- El ruido H2 casi no degrada circuitos de esta profundidad (fidelidad H-series) — el par
  {ruidoso ↔ ideal} por circuito quedó confirmado como generable (dataset del corrector AI-QEM).

### Decisiones tomadas (Dylan, 23-jul)

- Repo de entrega oficial: **se decide después de E1**, a más tardar en el primer dry-run
  (vanilla se construye con calidad de entrega; Chimera mantiene su plan de flip público).
- Hardware real: **sí se persigue** (Nexus + gestión con la organización).
- Investigación industrial: **amplia** (hecha, nota 10).
- El trabajo del Plan Espejo va en `reto1/plan-espejo` (worktree), sin tocar las ramas de
  trabajo paralelo del equipo.

### FALTA

- **E3** — el paquete `challenge1/` en Chimera corriendo el camino dorado sobre cr8/ieee14 +
  fixture de la falla sembrada (vector congelado: ieee14-flujo bus 1 → `fail`).
  **Dependencia declarada:** la rama de engine/runtime + confianza que está terminando Dylan
  en paralelo; E3 arranca sobre esa base cuando esté, usando el espejo como control externo
  (toda discrepancia Chimera↔espejo = bug de plataforma).
- **E5** — informe PDF, deck, statement SDK, teach-back; se pule en los dry-runs.
- **Gestiones abiertas:** pregunta de QPU real a la organización (Dylan); cr8/cr6 del espejo
  → ratificación de Sebas (los IDs `islanding-corpus/cr8-*` ya están reservados en el freeze);
  decisión del repo de entrega (dry-run 1).
