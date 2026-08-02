# Reto 3 — TFIM + Trotterizacion, resuelto EN la plataforma

Regenerar: `uv run python challenges/reto3/run_all.py`

## 1 · Malla del enunciado (Trotter orden 1, r=16, vs ED del corpus C3)

| instancia     | N   | h/J | err ⟨Zᵢ⟩ | err ⟨ZᵢZᵢ₊₁⟩ | ≤5% |
| ------------- | --- | --- | -------- | ------------ | --- |
| chain-n12-h05 | 12  | 0.5 | 0.00060  | 0.00102      | si  |
| chain-n12-h10 | 12  | 1.0 | 0.00442  | 0.00321      | si  |
| chain-n12-h20 | 12  | 2.0 | 0.00903  | 0.00496      | si  |
| chain-n6-h05  | 6   | 0.5 | 0.00060  | 0.00101      | si  |
| chain-n6-h10  | 6   | 1.0 | 0.00429  | 0.00295      | si  |
| chain-n6-h20  | 6   | 2.0 | 0.00903  | 0.00489      | si  |
| chain-n8-h05  | 8   | 0.5 | 0.00060  | 0.00102      | si  |
| chain-n8-h10  | 8   | 1.0 | 0.00442  | 0.00321      | si  |
| chain-n8-h20  | 8   | 2.0 | 0.00903  | 0.00496      | si  |

Peor punto de la malla: **chain-n12-h20** (err ⟨Zᵢ⟩ = 0.00903, err ⟨ZᵢZᵢ₊₁⟩ = 0.00496) — margen ~5.5x bajo el criterio.

## 2 · Control negativo (r=2, dt=0.5) — DEBE fallar

| instancia    | err ⟨Zᵢ⟩ | err ⟨ZᵢZᵢ₊₁⟩ |
| ------------ | -------- | ------------ |
| chain-n8-h05 | 0.04569  | 0.07867      |
| chain-n8-h10 | 0.32550  | 0.23746      |
| chain-n8-h20 | 1.03393  | 0.40682      |

Un error de 0.0000 con dt grande seria sospecha de codigo compartido entre
proponente y ancla (receta §4.3), no un exito. Notese `chain-n8-h05`: la
serie ⟨Zᵢ⟩ **pasaria** el 5% y solo el correlador lo caza — por eso se
verifican las dos series, no una.

## 3 · Barrido de dt (N=8, h/J=1)

| pasos | dt     | err ⟨Zᵢ⟩ | razon vs anterior |
| ----- | ------ | -------- | ----------------- |
| 2     | 0.5000 | 0.32550  | —                 |
| 4     | 0.2500 | 0.07305  | 4.46              |
| 8     | 0.1250 | 0.01780  | 4.10              |
| 16    | 0.0625 | 0.00442  | 4.03              |
| 32    | 0.0312 | 0.00110  | 4.01              |

Razon ≈ 4 al partir dt ⇒ O(dt²). **Esto NO prueba que la formula sea de
orden 2**: aqui el orden 1 tambien converge O(dt²) porque la correccion
BCH lider es puramente imaginaria y se anula sobre estados reales
(receta §1.5, con su control).

## 4 · Certificado (chain-n8-h10)

- Nivel titular: **AL3**
- Anclas: ['dataset', 'solver']
- Veredicto de la conclusion: **verified**
- Verificado offline: `uv run python scripts/verify-bundle.py results/reto3/certificado_chain-n8-h10.json`

## 5 · Honestidad

- El certificado se emite en **N=8** (el punto de referencia del enunciado).
  A N=12 el verificador de diagonalizacion densa declara
  `inconclusive`/`budget_exhausted` en vez de cambiar de algoritmo en
  silencio — el experimento cubre la malla, el certificado cubre lo que el
  ancla puede sostener.
- Las dos patas (ED recomputada + serie congelada) son independientes por
  **algoritmo** (eigh denso vs Krylov disperso) e **inmutabilidad**, no por
  metodo fisico. La diversidad metodologica real llega con el ancla
  analitica de fermiones libres (G6), que cubre ⟨ZᵢZᵢ₊₁⟩ pero **no** ⟨Zᵢ⟩.
