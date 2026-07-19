# Perfil STEM v1.0 — Chimera

## Perfil de dominio sobre la Capa de Confianza del Engine (spec v3.2 · cal-2.4) · manifiesto de curación

> **Estado: CONGELADO (importado 2026-07-18, barrido S-E).** Primera distribución de la capa de
> confianza. Importado del working set externo con dos normalizaciones: (1) sanitización de
> marca ("el Engine"); (2) el ítem 7 de la doctrina §4, agregado en el cierre S-E por el
> **P0-5(d)** del stress test S-D (modo amortizado sin ancla ex ante). La referencia de spec se
> actualizó de v3.0 a v3.2 (mismo contrato de perfil, hoy [`spec-confianza-v3-2.md`](spec-confianza-v3-2.md) §7).
> Evolución por versionado propio (§6) — jamás toca `cal-*`.
>
> **Qué es este documento.** Chimera es la **distribución "Laboratorio de Investigación"** del Engine: no es dueña de los módulos — los **cura, configura y enmarca** para investigación y trabajo STEAM. Este perfil es ese framing hecho norma: los schemas de claim del dominio, la curación de capabilities con configuración fijada por digest, las plantillas de Policy de investigación y la doctrina metodológica. **Contrato de perfil (spec v3.2 §7):** solo puede agregar y elevar; jamás altera leyes, cálculo, tipos o formatos, ni rebaja mínimos del kernel. Se versiona y las Policies lo referencian por digest.

---

## §1 · Schemas de claim del dominio (registro de claim_types)

| claim_type                            | Campos clave del schema                                                                                                                  | Techo estructural                                         | Notas                                                                                                        |
| ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `statistical`                         | estadístico, estimando, **family_size** (obligatorio: tamaño de la familia de comparaciones), **preregistration_ref∅**, datos por digest | AL3                                                       | Sin `family_size` el claim no se emite (contrato del harness) — el anti-p-hacking vive aquí, no en el kernel |
| `numeric_measured`                    | valor, incertidumbre, **unidades obligatorias** (SI/QUDT)                                                                                | AL3                                                       | Un número sin unidad no es un claim STEM                                                                     |
| `constraint_satisfaction`             | solution_ref (digest), constraint_set (digest)                                                                                           | AL4                                                       | El tipo de la demo Quantathon                                                                                |
| `comparative`                         | métrica, objeto, **baseline_ref obligatorio**                                                                                            | AL4                                                       | La plantilla de derivación exige el claim del baseline entre las premisas                                    |
| `citation_existence`                  | source (digest), quote, char_location                                                                                                    | AL3                                                       | "La cita existe donde dice" — decisorio por chequeo anclado                                                  |
| `source_support`                      | statement_ref, source (digest), passage                                                                                                  | AL3 (techo humano)                                        | "La fuente respalda X" — decisorio solo por HUMAN_EXPERT; el NLI es señal (doctrina §4)                      |
| `simulation_result`                   | modelo (digest), params (digest), seeds, output (digest)                                                                                 | AL3                                                       | Replicabilidad por construcción                                                                              |
| `derivation` (extiende el del kernel) | plantillas de inferencia científica registradas                                                                                          | AL4 (formal) / AL3 (experto)                              | —                                                                                                            |
| `ethical_soundness`, `novelty`        | descriptor + rúbrica                                                                                                                     | **AL3 (techo humano: experto independiente; típico AL2)** | Declarados `techo_estructural` — el gap honesto, sin fatiga de alarmas                                       |

**Extensiones de predicate** (para attestations sobre estos tipos): `statistical_procedure {test, alpha, power∅, corrections}` — sin procedimiento declarado, el veredicto estadístico no es auditable y no se emite.

## §2 · Curación de capabilities (el manifiesto)

Cada fila: módulo del catálogo del Engine → clase → **configuración fijada** (verifier_params_digest) → propósito. La curación es criptográfica: cambiar un parámetro cambia el digest y rompe la reutilización — a propósito.

| Capability (módulo)                                                            | Clase                 | Config fijada (ejemplos)                                                             | Propósito en el perfil                                                                                                          |
| ------------------------------------------------------------------------------ | --------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| Solver exacto (OR-Tools/CP-SAT; brute-force checker para instancias diminutas) | FORMAL_EXACT          | límites de tiempo, gap=0; el brute-force como **checker independiente** habilita AL4 | Optimalidad/factibilidad exacta (Reto 1)                                                                                        |
| Simulador de dominio (p. ej. pandapower)                                       | EXECUTION             | versión pinned por digest, tolerancias, `determinism` declarado                      | "Lo corrimos de verdad"                                                                                                         |
| Checker de restricciones                                                       | PROPERTY_RULE         | conjunto de restricciones por digest                                                 | Validez estructural barata                                                                                                      |
| Verificador de unidades (estilo pint)                                          | PROPERTY_RULE         | sistema de unidades                                                                  | Higiene dimensional                                                                                                             |
| Verificador de consistencia estadística (estilo statcheck)                     | PROPERTY_RULE         | reglas APA/recomputación de p                                                        | Errores estadísticos reportados                                                                                                 |
| **Verificador de multiplicidad**                                               | PROPERTY_RULE         | corrección exigida según family_size                                                 | El diente metodológico anti-p-hacking                                                                                           |
| Runner de replicación                                                          | CONSENSUS_REPLICATION | n seeds, entornos; `independence_basis` declarada                                    | Domar el ruido (incl. muestreo cuántico) — **solo procesos no-modelo (S7)**: la concordancia entre modelos jamás entra por aquí |
| Chequeo de cita anclada                                                        | GROUND_TRUTH/PROPERTY | fuente por digest + char_location                                                    | La cita **existe donde dice** (decisorio)                                                                                       |
| Entailment NLI de citas                                                        | **Detector (Signal)** | modelo/versión                                                                       | ¿La cita **respalda** el claim? — probabilístico: informa, jamás decide; para C3, el respaldo lo decide HUMAN_EXPERT            |
| Panel de revisión experta                                                      | HUMAN_EXPERT          | especialidades, independencia por run                                                | Peritaje firmado                                                                                                                |

## §3 · Plantillas de Policy de investigación

- **Pisos de criticidad por rol del claim:** conclusión de reporte/paper → C3 · resultado intermedio del camino → C2 · contexto/literatura de apoyo → C1 · comentario → C0.
- **Matriz (hereda el default del kernel y eleva):** C3 exige además — verificador de multiplicidad presente si hay claims `statistical` en el camino; unidades verificadas en todo `numeric_measured`; derivaciones con plantilla registrada o experto; `preregistration_ref` ausente ⇒ se registra como Assumption visible del case (jamás modifica nivel — L1).
- **Retención:** default largo (los datos de investigación viven años; el mínimo legal ≥ 6 meses queda muy atrás).
- **Escalación:** conflictos y gaps C3 → AcceptanceAuthority del proyecto (PI o quien la Policy designe).

## §4 · Doctrina de granularidad de claims (guía normativa del perfil)

1. **Existencia ≠ fidelidad:** "el archivo/ticket/resultado existe" (débil, casi siempre trivial) es un claim distinto de "refleja fielmente X" (el que importa) — las plantillas fuerzan a emitir el segundo.
2. **Cita ≠ respaldo:** la existencia de la cita es decisoria; el respaldo semántico es señal + experto (ver §2).
3. **Todo universal lleva scope acotado:** "para toda instancia" sin conjunto por digest no es emitible; el álgebra de scope exige rangos cerrados/enumeraciones.
4. **Sin deixis** (kernel L3): nada de "este run/lo anterior" — digests siempre.
5. **La conclusión declara su baseline:** claims `comparative` sin baseline_ref no compilan; la derivación lo exigirá de todas formas (mejor fallar temprano).
6. **Equivalencia plan–acción (plantilla bendita — 5.1(1) de la Base):** verificar el plan (FORMAL/PROPERTY) + la conformidad de cada acción con el plan (PROPERTY barato) compone, vía claim de derivación, la verificación de cada acción al **mín.** de las bases — la justificación formal de la amortización por gates del PEV y del reuse content-addressed.
7. **Sin ancla decisoria ex ante, el modo correcto es la certificación amortizada de la capability + Signal en operación — jamás la verificación por-resultado** _(agregado S-E 2026-07-18, P0-5(d) del stress test S-D)_: donde la verdad solo llega con el desenlace (p. ej. mantenimiento predictivo — la verdad llega con la falla), exigir verificación por-resultado degenera en `no_applicable_anchor` perpetuo (teatro de abstención). El perfil manda: certificar la **capability** contra corpus histórico (patrón del kernel "case de certificación de capability", spec §1 — GROUND_TRUTH, techo AL3, controles negativos obligatorios) y acompañar la operación con Signals de deriva, jamás con veredictos fingidos. Es el mismo patrón del certificado del corrector (`knowledge/quantum/09` §1.4).

## §5 · Instanciación Quantathon (Reto 1)

El caso de la demo usa este perfil tal cual: claims `constraint_satisfaction` + `numeric_measured` + `comparative` + `derivation`; capabilities curadas: solver exacto (+brute-force checker → AL4 en instancias diminutas), pandapower pinned, checker de restricciones, runner de seeds; Policy de investigación con conclusión C3/AL3/2 patas. El titular AL3 con la derivación verificada — y la solución trampa refutada en vivo — salen de este manifiesto sin una sola regla ad-hoc.

## §6 · Versionado y evolución

El perfil se versiona independiente del kernel; agregar schemas/capabilities/plantillas = versión menor; cambiar techos o endurecer plantillas = versión mayor del perfil (jamás toca cal-*). Perfiles futuros de la casa (finanzas, legal, ingeniería) siguen este mismo molde — el Engine no se entera.
