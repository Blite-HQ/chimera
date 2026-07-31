# Ratificaciones S-F — índice

> **Estado: HISTÓRICO (2026-07-30, archivado por #112).** El proceso de ratificación por
> dueños que este índice documenta fue abolido por la decisión #94 (gobernanza Dylan+Claude
> vía ledger). Su valor restante es la trazabilidad del contract-freeze.

Respuestas de los 3 dueños al checklist de `docs/guia-ratificacion.md` sobre el diseño
congelado (`docs/contract-freeze.md`, CONGELADO 2026-07-18). Cada archivo es el documento
del dueño **tal cual lo entregó**, sin editar — este índice solo describe, no evalúa ni
resuelve nada.

| Archivo                                                              | Dueño · plano                                | Fecha      | Veredicto global (declarado por el propio documento)                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| -------------------------------------------------------------------- | -------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`steven-plano-ejecucion.md`](steven-plano-ejecucion.md)             | Steven · ejecución                           | 2026-07-19 | **RATIFICADO.** 8 secciones del checklist sin objeciones bloqueantes. 3 acciones derivadas (refuerzos de bajo costo, no objeciones) + 1 gap de código esperado (pre-construcción), documentadas para S-G.                                                                                                                                                                                                                                                                                   |
| [`geovanni-plano-infra.md`](geovanni-plano-infra.md)                 | Geovanni · infra                             | 2026-07-20 | **OK CON OBJECIONES.** 1 objeción con causa (ítem 4: modelo Ollama local no corre en su hardware) + 5 ítems marcados `[COMPLETÁ VOS]` sin cerrar (custodia de llaves §7, demo dual §3, calendario dry-runs §5, reconciliación `infra/01 §R` vs `invariants.md` §6 — **aún no ejecutada**, huecos Fase 2 §7) + 1 propuesta fuera de checklist (dropear LiteLLM, pisa el plano de Steven, pendiente de su aval).                                                                              |
| [`sebas-plano-quantum-final.md`](sebas-plano-quantum-final.md)       | Sebas · ciencia/cuántica — **versión FINAL** | 2026-07-21 | **OK CON MATICES.** Corpus ratificado con 3 anclas independientes en 2 entornos (6/6 digests). Segunda ancla de ieee30 ejecutada (cambia el campo `metodos` y 2 digests — pendiente re-estampar en freeze §15.3). Vector de falla sembrada elegido y calculado. `cr8`/`cr6` sigue **PENDIENTE** (trabajo real, no ratificación) — prioridad subida por ser CORE del demo en vivo. 3 hallazgos accionables (deps faltantes, pin `pandas<3`, verificación por digest en vez de `git status`). |
| [`sebas-plano-quantum-borrador.md`](sebas-plano-quantum-borrador.md) | Sebas · ciencia/cuántica — **borrador**      | 2026-07-20 | Versión de trabajo previa a la FINAL, **superada por ella** — se conserva solo por trazabilidad; no revisar como si fuera la vigente.                                                                                                                                                                                                                                                                                                                                                       |

## Fuera de este directorio

- **`knowledge/quantum/kb2-05-plataforma-quantinuum-h2.md`** — nota nueva de KB que Sebas envió
  junto con su ratificación, pero **no es un documento de ratificación**: es contenido de
  conocimiento (brief de la plataforma Quantinuum H2/TKET/Nexus) con solape fuerte con
  `knowledge/quantum/08-ruta-quantinuum-guppy.md`. Queda en `knowledge/quantum/` fuera de la
  numeración 00-09 a propósito, para marcar que **todavía no está integrada** a la nota 08 —
  decidir cómo fusionarla es trabajo de la próxima sesión, no de esta.

## Qué falta para cerrar S-F (sin resolver acá, solo para orientar la próxima sesión)

- Objeción de Geovanni sobre el modelo de Ollama (local vs cloud) y su impacto en el air-gap.
- Propuesta de Geovanni de dropear LiteLLM — necesita aval explícito de Steven.
- Reconciliación real de `infra/01 §R` contra `invariants.md` (Geovanni la dejó sin ejecutar).
- Los 4 ítems `[COMPLETÁ VOS]` restantes de Geovanni (custodia de llaves, demo dual, calendario
  de dry-runs, huecos Fase 2).
- La FORMA de identidad de ieee30 (re-estampar `@v1` vs `@v2` vs attestation externa) — la decide
  Sebas; ninguna se aplica hasta su palabra (freeze §15.3, convergencia EC-3).
- Decidir el corredor de `cr8`/`cr6` (trabajo pendiente de Sebas, CORE del demo en vivo).
- Integrar `kb2-05` a `knowledge/quantum/08-ruta-quantinuum-guppy.md`.
