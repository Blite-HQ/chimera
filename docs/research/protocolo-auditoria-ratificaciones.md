# Guía — el flujo pre-S-G de ratificación (arco completo: simular → auditar/decidir → aplicar)

> **Estado: VIGENTE (proceso).** Es el relato fiel del **arco S-F completo**, que abarcó **dos
> sesiones**: el **2026-07-19** se simularon las ratificaciones y se auditaron contra el estado
> congelado decidiendo cuál era mejor; el **2026-07-20** se aplicó lo que sobrevivió. Convertido en
> guía corta para replicar el mismo flujo con las ratificaciones **reales**. **No** incluye el
> stress test ni la comparación simulada↔real ni la convergencia: eso viene DESPUÉS (§5).

---

## 0 · El flujo en una línea

**Producir la ratificación en formato** → **auditarla contra el estado congelado actual y decidir,
por hallazgo, si gana la ratificación o lo ya definido — y por qué** → **aplicar lo que mejora como
supersesión fechada, verificando por corrida**. Es "hacer S-E otra vez, pero focalizado en los
resultados de la ratificación".

## 1 · Paso 1 — Producir la ratificación en formato · sesión del 19-jul (acta)

Cuatro revisores independientes de contexto fresco (uno por dueño + uno de equipo/completitud)
siguen `guia-ratificacion.md` **exacto**. Salida: `ratificacion-simulada-sf.md` — veredictos
globales + lista priorizada P0/P1/P2 + anexo por dueño. Reglas: **cero escrituras al repo**;
**ejecutar lo ejecutable** en scratchpad (el ítem ejecutable de Sebas se corrió de verdad).

_Para las ratificaciones reales:_ este paso es **normalizar** las respuestas de los dueños (ack,
mensaje, PR) a esta misma forma, para que sean comparables 1:1 con el anexo simulado.

## 2 · Paso 2 — Auditar contra el estado actual y decidir cuál es mejor · sesión del 19-jul (validación)

Segunda pasada con postura de **refutación**: asumir cada hallazgo **mal** hasta que la **evidencia
primaria** (`archivo:línea` o una **corrida real**) lo confirme. Por cada hallazgo se lee lo que dice
el hallazgo **y** lo que el repo dice **hoy**, lado a lado, y se decide **quién gana**:

| Relación con lo congelado    | Qué significa                                             | Quién gana                                                                          |
| ---------------------------- | --------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| **Letra-vs-realidad**        | el freeze AFIRMA un estado del repo que no existe (drift) | la ratificación — se corrige la letra                                               |
| **Semilla incompleta**       | la semilla no carga algo que lo congelado exige           | la ratificación — se completa la semilla                                            |
| **Regla faltante**           | S-G no podría inventar la regla sin decidir un contrato   | la ratificación — se agrega la regla                                                |
| **Contradice una decisión**  | el hallazgo choca con una decisión de diseño congelada    | lo congelado, **salvo** que el hallazgo PRUEBE que es mejor (evidencia, no opinión) |
| **Redundante / ya resuelto** | ya está en el repo                                        | ninguno — se descarta (no es hallazgo)                                              |

Se barre **más allá del checklist** (así salieron los P1 del plano de confianza que ningún checklist
de la guía cubría). Salida: `ratificacion-simulada-sf-validacion.md` — cada hallazgo
`CONFIRMADO/MATIZADO/REFUTADO` con su evidencia, + la **lista consolidada §4** y los ajustes a los
fixes. **Aquí es donde vive el juicio "cuál es mejor y por qué"** — no en la aplicación.

## 3 · Paso 3 — Aplicar lo que sobrevive · sesión del 20-jul (el "S-E focalizado")

Los hallazgos que ganaron se aplican como **supersesión `[S-F]` fechada con causa** —
**jamás** edición silenciosa, **jamás** marca retroactiva — en lo que corresponda: freeze, semillas,
anexo, KB, `uv.lock`, código, Policy. En este paso también:

- se **decide en firme** lo que la validación dejó como opción (p. ej. ieee30 = _attestation externa
  sobre el mismo digest_, no `@v2`);
- se **marca lo que solo el dueño real puede cerrar** (identidad de ancla, criterio narrativo, firma);
- se **integra lo que llegó por fuera** de la simulación (la ratificación verbal de Geovanni:
  local-first, modelos por API keys);
- se añade un bloque **"Registro de cierre"** con la causa por cada cambio.

Prioridad: **P0** rompe seeds/demo o invalida algo congelado (antes de S-G) · **P1** cerrar en la
ventana · **P2** registrar.

## 4 · Verificar y cerrar · sesión del 20-jul

- **Verificación por corrida** de cada fix ejecutable, con la evidencia guardada — es lo que probó
  que la ratificación mejora: el re-lock que reprodujo 6/6 digests del corpus, la enumeración de
  ieee30 que confirmó los óptimos (35 / 32 170), los flips que fijaron el bus del fixture, la Policy
  contra su schema.
- **Tests:** se actualizan/agregan **donde el fix toca código testeable** — en esta corrida, solo la
  Policy (`test_verification_policy.py`, +28/−5). El resto de la verificación fue **por corrida
  reproducible en scratchpad**; la **batería completa de tests de valor** (que un `run.cancelled` es
  proyectable, la matriz `interaction×profile`, los flips como test) **queda para S-G**.
- **Gates verdes** antes de cada commit:
  ```
  uv sync --all-packages --extra pandapower --extra ortools --extra networkx
  uv run lint-imports        # 9/9 KEPT
  uv run pytest tests/ -q     # verde
  uv run ruff check <tocados>
  pnpm -s exec tsc --noEmit -p apps/studio
  # + hook de la marca: "Blite"+"Engine" juntas = 0 hits repo-wide
  ```
- **Commits temáticos** con causa (deps / Policy / freeze…). En esta corrida: `3f49ab7` re-lock,
  `7dbb57e` Policy 0.2.0, `02fa06d` supersesiones de docs.

## 5 · Lo que viene DESPUÉS (no es parte de este flujo)

En este orden, una vez cerrado el flujo sobre una ratificación:

1. **Stress test brutal** del diseño resultante — panel de destrucción que intenta botarlo (se hizo
   en otra sesión: `stress-test-sf-pre-sg.md`, veredicto GO).
2. **Comparación y convergencia** — cuando exista la ratificación **real**, se le corren los Pasos
   1–4 y luego se **comparan** simulada↔real para medir convergencia; si convergen, se unifica y se
   pasa a **S-G oficial** con el set validado.
