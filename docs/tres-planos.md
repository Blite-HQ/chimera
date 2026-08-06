# Los tres planos — verificación ≠ guardrail ≠ evaluación

> **Estado: VIGENTE (2026-08-05).** Marco transversal de referencia, promovido a
> `docs/` por O8 desde `knowledge/trust/17-evaluacion-inspect-tres-planos.md`
> §1.6 (rescate #116). No cambia ningún contrato: nombra explícitamente una
> separación que el contrato ya asumía, para que ninguna herramienta futura se
> presente por error como si reforzara la verificación.

Chimera opera con tres planos **deliberadamente separados**. La confusión entre
ellos es la confusión estándar del mercado, y es exactamente la que esta
plataforma existe para no cometer.

| Plano            | ¿Qué responde?                                                         | ¿Cuándo actúa?                           | Produce                        | ¿Gatea egreso?                                                                                 |
| ---------------- | ---------------------------------------------------------------------- | ---------------------------------------- | ------------------------------ | ---------------------------------------------------------------------------------------------- |
| **Verificación** | ¿Este claim ESPECÍFICO es correcto, probado contra un ancla no-modelo? | por-claim, en el camino crítico del run  | `Attestation` (clase + AL, §4) | Es lo único que `required_anchors` puede exigir — y ni aun así decide sola (Inv-E: solo authz) |
| **Guardrail**    | ¿Esta salida, ahora mismo, luce sospechosa según un detector?          | por-paso, informativo                    | `Signal`                       | **Nunca** — informa, eleva fricción, jamás decide                                              |
| **Evaluación**   | ¿Qué tan bueno es el sistema EN AGREGADO, a través de muchas corridas? | batch, offline, fuera del camino crítico | KPIs                           | **Nunca** — es medición retrospectiva                                                          |

## La regla que los mantiene separados

**Ningún resultado agregado, por alto que sea su score, sustituye una
`Attestation` faltante en un run individual.** Y ninguna `Signal`, por alta que
sea su confianza, tampoco.

Un framework de evaluación que reporta «94 % de faithfulness» suena a una
prueba, pero es un promedio de juicios probabilísticos: es D18 (coherencia ≠
verificación) aplicado a escala de sistema en vez de a un claim. Por eso
RAGAS/TruLens/DeepEval-faithfulness **parecen** relevantes y no lo son
(descartes uno a uno en trust/17 §1.5): no son peores, son de otro plano.

## Dónde vive cada uno en el código

| Plano        | Código                                                      | Gate que lo sostiene                                  |
| ------------ | ----------------------------------------------------------- | ----------------------------------------------------- |
| Verificación | `blite.verification` (engine)                               | INV-2 (un verificador jamás es un modelo)             |
| Guardrail    | `blite.guardrails` (engine)                                 | INV-3 (informa, no decide) · Inv-E                    |
| Evaluación   | `chimera_eval` (`tools/corpus-runner/`, FUERA de `blite.*`) | contrato import-linter «O8: evaluation is downstream» |

El contrato de imports dice la parte estructural: **nada importa
`chimera_eval`**. La flecha inversa sí es legítima — la tarea
`chimera_eval.tasks.verification_plane` importa el plano de verificación para
medirlo. Si algún día la flecha se invirtiera, una métrica retrospectiva habría
entrado al camino crítico de un run.

## El KPI que el tercer plano existe para dar

`over_refusal_rate` = `count(N) / scored`, sobre un corpus donde la respuesta
correcta se conoce (trust/05 §1.3: en un mundo cerrado el falso rechazo es
medible con precisión). Se lee SIEMPRE junto a `decisive_error_rate`:

- **sobre-rechazo alto** → la verificación se abstiene de más: cuesta utilidad
  sin ganar corrección;
- **error decisivo alto** → se pronunció y se equivocó: cuesta lo único que esta
  plataforma vende.

Una métrica escalar de acierto no distingue las dos cosas — `I` y `N` pesan
igual en cualquier promedio. Ese es el motivo entero de portar el vocabulario
`C/I/P/N` de Inspect (UK AISI) en vez de inventar una escala propia.

### Cómo se corre

```bash
uv run python scripts/run_eval_corpus.py
```

Detalle de la herramienta: `tools/corpus-runner/README.md`.

## Qué encontró la primera corrida (2026-08-05)

Sobre el corpus C3 (9 instancias × 2 polaridades = 18 muestras), contra los
verificadores REALES:

| KPI                   | valor     |
| --------------------- | --------- |
| `scored`              | 18        |
| `process_errors`      | 0         |
| `accuracy`            | 0.667     |
| `over_refusal_rate`   | **0.333** |
| `decisive_error_rate` | 0.0       |

**Cero errores decisivos** — el sistema nunca se pronunció y se equivocó, ni
aceptando una serie perturbada ni refutando una fiel. Y un sobre-rechazo del
33 % **enteramente concentrado en `N = 12`**: `verifier:ed-dense` se abstiene
con `budget_exhausted` porque la dimensión densa (2¹² = 4096) supera su
presupuesto declarado (`_DEFAULT_MAX_DENSE_DIMENSION = 1024`).

La abstención es HONESTA y está diseñada así (rehúso explícito antes que un
cambio silencioso de algoritmo). Pero tiene una consecuencia que ningún test
mostraba: **en `N = 12` los claims del reto 3 quedan sostenidos por UNA sola
pata** (el corpus congelado), no por las dos independientes que la receta
promete. La propiedad de independencia se degrada justo en las instancias más
grandes — que son las que más importan.

Eso es el tercer plano haciendo su trabajo: no es un bug de nadie, es una
medición que antes no existía.
