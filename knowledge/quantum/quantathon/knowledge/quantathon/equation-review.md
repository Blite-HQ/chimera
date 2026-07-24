# Equation Review Checklist

Punch-list of slides where the extracted text likely mangled or dropped an equation (prose survived, math didn't). Verify each against the original slide deck — use `source_ref` in the session's front-matter to locate it — before trusting the math. Generated during the text-only notes pass; nothing here has been fixed, only flagged.

## bootcamp/b01 — Fundamentos de mecánica cuántica (slides, `s02.md`) — Felipe Montealegre

Pattern: garbled/corrupted extracted characters (not blank gaps) — matrix brackets and symbols mis-recognized.

- [ ] Slide 54 — transformation matrix U = (1/√2)·[[1, 1], [1, -1]]: extracted as "1 p 2 ✓1 1 1 -1 ◆"; "p" is likely a mis-OCR'd "√", "✓"/"◆" are corrupted matrix brackets.
- [ ] Slide 56 — measurement matrix M = [[1, 0], [0, -1]]: same corrupted bracket pattern ("✓1 0 0 -1 ◆").
- [ ] Slide 64 — tensor product symbol extracted as "⌦" instead of "⊗" (Ψ⊗Φ = (ψ₁Φ₁, ψ₁Φ₂, ψ₂Φ₁, ψ₂Φ₂)).
- [ ] Slide 65 — ψ subscripts lost in extraction ("= ( 1Φ1, 1Φ2, 2Φ1, 2Φ2)" instead of "(ψ1Φ1, ψ1Φ2, ψ2Φ1, ψ2Φ2)").
- [ ] Slide 66 — leading Ψ symbol lost in the entangled-state example (" AB = (1, 0, 0, 1)" instead of "ΨAB = (1, 0, 0, 1)").

## bootcamp/b05 — Modelo de Ising (slides, `s02.md`) — Jose Alfredo de León

Pattern: blank gaps where a math expression should appear (no corrupted characters, no image marker) — distinct from b01/s02's garbled-text pattern.

- [ ] Slide 5 — missing Pauli matrices σx, σy, σz (block ends at a colon with nothing after it). Cross-check: s01.notes.md [~00:00] notes the presenter mentioned the original slide had a typo (repeated "sigma x" three times instead of σx, σy, σz) — possibly related to this gap.
- [ ] Slide 6 — three gaps: (a) eigenvalue spectrum; (b) quantum-dynamics equation (likely Schrödinger); (c) bra-ket notation for the ground state (possibly |ψ₀⟩).
- [ ] Slide 8 — missing interaction-term expression (e.g., −J Σ ZᵢZⱼ). Also has a stray invisible private-use Unicode character (U+E092) in the title "Término 1␣Interacción".
- [ ] Slide 9 — missing transverse-field-term expression (e.g., −h Σ Xᵢ). Same U+E092 artifact in "Término 2␣El Campo Transverso".
- [ ] Slide 11 — two gaps: classical ground-state notation (e.g., |↑↑↑...⟩) and quantum-disorder ground-state notation (e.g., tensor product of |+⟩). Same U+E092 artifact in "Extremo 1␣El Orden Clásico".
- [ ] Slide 16 — missing explicit ground-state bitstring. Per s01.notes.md [~40:00], this should correspond to 010 or 101.

Slide 17 uses inline LaTeX ($Z_i Z_j$, $X_i$, $h/J$) that extracted correctly — no flag needed there.

## bootcamp/b06 — Quantum Machine Learning y Trotterización, Trotterización half (slides, `s02.md`) — William Aguilar

Same blank-gap pattern as b05/s02.

- [ ] Slide 8 — missing commutator expression (e.g., [A,B] = AB − BA). Cross-check: s01.notes.md [~00:00] has the presenter define the commutator verbally as AB − BA and work the example [X,Z] = XZ − ZX = −2Y ≠ 0.

(Also note, not an equation issue: Slide 9's title reads "Caso 1: Hamiltoniano necesita Trotter" but likely should read "Caso 2" given Slides 3/7 use "Caso 1" for the simple Hamiltonian — probably a typo in the original deck, not an extraction artifact.)

## bootcamp/b06 — Quantum Machine Learning y Trotterización, QSVM half (slides, `s03.md`) — William Aguilar

Same blank-gap pattern as b05/s02 and b06/s02.

- [ ] Slide 21 — missing kernel-matrix expression (N×N pairwise-similarity matrix). Cross-check: s01.notes.md [~80:00] describes it verbally as built by comparing each point to its neighbors via dot product, diagonal always 0.
- [ ] Slide 33 — missing dense-angle-encoding formula/notation (rotation angle + phase on a single qubit). Cross-check: s01.notes.md [~80:00] describes the construction verbally via an angle ω and a second variable, without a closed formula.
- [ ] Slide 36 — missing "product state" notation (e.g., |ψ⟩⊗|φ⟩).
- [ ] Slide 37 — two gaps: (a) ZZ-interaction expression; (b) typical ZZ feature-map circuit/schema. Partial cross-check: s01.notes.md [~80:00] describes the ZZ feature map verbally (Hadamards + ZZ interactions) without a closed formula.
- [ ] Slide 40 — two gaps: (a) bra-ket notation for the encoding's output states; (b) quantum-kernel similarity-measure expression. Cross-check: s01.notes.md [~80:00] describes this measure as the probability of measuring |0⟩ after applying the feature map φ and its conjugate.

## bootcamp/b07 — Introducción a Quantum Singular Value Transformation (slides, `s02.md`) — Daniela Angulo

- [ ] Slide 4 — "Encuentra el polinomio en el siguiente ejemplo sencillo (escalar)": the worked scalar example/equation is not extracted.
- [ ] Slide 6 — SVD decomposition ("siempre existe una descomposición:") — equation (M = UΣV*) missing, only the prose description of U/Σ/V* survived.
- [ ] Slide 8 — duplicate of slide 4's prompt; same missing worked example.
- [ ] Slide 13 — "Después de una iteración" — the resulting matrix-element expression is missing.
- [ ] Slide 14 — "Polinomios impares de Chebyshev del primer tipo:" — polynomial expressions not extracted.
- [ ] Slide 15 — same Chebyshev reference plus the cost-function quantity — expressions missing.
- [ ] Slide 16 — QSP: three expected equations (scalar encoding, adjustable rotation, resulting polynomial) all missing.
- [ ] Slide 18 — QSVT: three expected equations (operator encoding, adjustable rotation, resulting even/odd polynomial) all missing.
- [ ] Slide 20 — "que el polinomio resultante se aproxime a 1" — condition/interval possibly truncated.
- [ ] Slide 22 — target function for Hamiltonian simulation ("aproxime la función:") missing.
- [ ] Slide 24 — target function + sum-combination equation ("para que correspondan a una suma:") both missing.
- [ ] Slide 25 — matrix-inverse definition ("encontrar la matriz inversa... asumiendo que existe:") missing.
- [ ] Slide 26 — three equations (SVD of A, singular-value interval, inverse existence) all missing.
- [ ] Slide 27 — **literal blank-space gap mid-sentence**: "la matriz ​ ​ ​ ​ ​ ​ contiene los recíprocos de los valores singulares" — a symbol (likely Σ⁻¹) was dropped inline, not just omitted after a colon; the polynomial-approximation equation later on the same slide is also missing.
- [ ] Slide 28 — inverse formula and its condition ("La inversa se obtiene: con") both missing.
- [ ] Slide 29 — "Encontrar un polinomio que aproxime [target dropped] en el rango de los valores singulares de A" — target function (likely 1/x) dropped mid-sentence.
