# Nota 11 — Receta C3: TFIM + Trotterización (STUB — la escribe G1)

**Fecha:** 2026-07-30 · **Estado:** **STUB (placeholder del saneamiento S3).**
Esta nota existe para que la receta C3 vigente tenga un destino con nombre: la
receta de química/VQE de la nota 02 §3 está **SUPERSEDIDA desde el 2026-07-18**
(supersede S-E) y hasta hoy no existía la nota que la reemplaza. El contenido
completo lo escribe el ítem **G1** del backlog
(`docs/mejorado/04-consolidacion.md`) al implementar el reto 3. Hasta entonces,
lo normativo ya decidido es lo de abajo — NO usar la receta de química de 02 §3.

## Lo ya decidido (supersede S-E 2026-07-18 + C-14/#106)

- **C3 = TFIM (Ising de campo transversal) + Trotterización** — circuito de
  Trotter eficiente; NO química molecular/VQE.
- **Cadenas N ∈ {6, 8, 12}**, barrido h/J ∈ {0.5, 1, 2}.
- **Ancla = diagonalización exacta (ED)**: ⟨Zᵢ⟩ y ⟨ZᵢZᵢ₊₁⟩ dentro de **≤5%** de
  la ED (criterio oficial, en N=8 como referencia del enunciado).
- **Verificador**: `ExactDiagonalizationVerifier` por la clase `formal_exact` —
  C-14 (#106) extiende `FormalExactPredicate` con el literal
  `EXACT_DIAGONALIZATION` + campo de tolerancia relativa que entra al
  `verifier_params_digest`.
- **Corpus C3**: series de ED como referencia, con digests (mismo patrón que el
  corpus de islanding).
- **Capabilities**: `blite.quantum.trotter_evolve` + `blite.numeric.exact_evolve`
  (materializa el stub `numeric.matrix_ops` o capability hermana).
- **Doble ancla TFIM (stretch, G6)**: `blite.numeric.tfim_freefermion`
  (BdG analítico) replica el patrón AL4 del reto 1.

## Qué falta (lo escribe G1)

La matemática completa al estilo de la nota 02 (Hamiltoniano TFIM, descomposición
de Trotter, cotas de error por paso, mapeo a circuito, análisis de escalado en
espines), el diseño del corpus con digests, y los controles negativos.
