# Knowledge — Nexus (evidencia externa de Quantinuum Nexus)

> **Estado: VIGENTE (2026-07-30, #109).** README descriptivo creado en el saneamiento
> documental. **La autoridad normativa vive FUERA de knowledge**: la spec es
> `docs/specs/evidencia-externa.md` y la decisión de importación es la #76 del ledger —
> este README solo describe lo que hay, no gobierna nada.

## Qué es

Evidencia externa de **Quantinuum Nexus** (19 corridas QAOA cacheadas: backends `H2-1LE` y
`H2-Emulator`, instancias del corpus de islanding, p1–p3, seed 0) importada al repo el
2026-07-24 por `scripts/import_nexus_runs.py` (decisión #76). Son **40 JSON, sin `.md`**:

| Pieza            | Qué contiene                                                                                                                                                              |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `index.json`     | Una fila por import con la cadena de digests + `digest_coverage_notes` (la honestidad estampada)                                                                          |
| `consensus.json` | Los 4 grupos de consenso multi-backend (`ConsensusReplicationPredicate` con legs, agreement)                                                                              |
| `normalized/`    | 19 archivos — counts normalizados (`NormalizedCounts`, `bit_order` explícito verificado empíricamente: msb-left 19/19)                                                    |
| `statements/`    | 19 archivos — attestations de importación **in-toto Statement v1** (predicado `https://blite.dev/ExternalImport/v1`) sobre el digest de los counts normalizados de su job |

Cada import queda **encadenado por digests** en `index.json`: el blob crudo
(`raw_blob_digest`) → los counts normalizados (`normalized_digest`) → el statement in-toto
(`statement_digest`) → y la identidad declarada del circuito (`circuit_digest`, con
`transpiled_circuit_digest` y `noise_config_digest` como dependencias resueltas del
statement). La **honestidad está estampada** en `index.json` → `digest_coverage_notes`:
declara explícitamente que `circuit_digest`/`transpiled_circuit_digest` cubren la definición
determinista del circuito lógico (instance/p/betas/gammas), NO bytes de circuito
post-transpilación, y que `noise_config_digest` de H2-Emulator es un descriptor declarativo
(patrón «ingerido ≠ ancla», freeze §11).

## Línea roja

**NADA de este directorio se re-digesta ni se regenera.** Son datos estampados de un import
determinista (`retrieved_at`/`imported_at` anclados, nunca wall-clock): la custodia in-toto
certifica LA IMPORTACIÓN, jamás sustituye la `Attestation` científica (spec
`evidencia-externa.md`, sección Ortogonalidad). Una discrepancia se reporta, no se
sobreescribe — misma regla de soberanía del digest que `../islanding/`.

## Hueco conocido

Este directorio **no tiene guard de digests en CI** — no existe el equivalente de
`scripts/verify_corpus_digests.py` para `nexus/`. Registrado como ítem del backlog por
decisión #117 (dominio O, guards de datos estampados).
