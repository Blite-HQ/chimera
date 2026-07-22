# Guía — el flujo pre-S-G: auditar una ratificación contra el estado congelado y aplicar lo que mejora

> **Estado: VIGENTE (proceso).** Es el relato fiel de lo que se hizo en la sesión del 2026-07-20
> con los resultados de la ratificación **simulada** (S-F), convertido en una guía corta para
> hacer lo mismo con las ratificaciones **reales** cuando lleguen. **No** es la comparación
> simulada↔real, ni la convergencia, ni el stress test: eso viene DESPUÉS (§5). Este documento
> cubre solo el flujo de **auditar-y-aplicar** una ratificación contra el diseño congelado —
> "hacer S-E otra vez, pero focalizado en los resultados de la ratificación".

---

## 0 · El flujo en una línea

Tomar los resultados de una ratificación (ya formateados), auditarlos uno por uno contra el estado
**actual** del proyecto, decidir para cada hallazgo **si gana la ratificación o lo que ya está
definido — y por qué**, y aplicar lo que mejora como supersesión fechada.

## 1 · El insumo y la vara

- **Insumo:** los resultados de la ratificación ya en formato — el acta (veredictos + lista
  priorizada P0/P1/P2 + anexo por dueño) y, si existe, su validación adversarial.
- **La vara:** el estado congelado **actual** — `contract-freeze.md` (+ su Registro de cierre), las
  semillas v2 (`especificacion-contratos-v2.md`, `esquema-datos-v2.md`), el anexo de
  canonicalización, `knowledge/`, y el **código real** (`engine/`, `distributions/`, `uv.lock`,
  `tests/`). Un hallazgo no se juzga en abstracto: se juzga contra lo que el repo dice HOY.

## 2 · El paso central — por cada hallazgo, ¿quién es mejor: la ratificación o lo ya definido?

Se lee el hallazgo **y** lo que el repo dice hoy, lado a lado, con **evidencia primaria**
(`archivo:línea` o una **corrida real** — nunca de memoria). Y se clasifica la relación:

| Relación con lo congelado    | Qué significa                                             | Quién gana                                                                          |
| ---------------------------- | --------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| **Letra-vs-realidad**        | el freeze AFIRMA un estado del repo que no existe (drift) | la ratificación — se corrige la letra                                               |
| **Semilla incompleta**       | la semilla no carga algo que lo congelado exige           | la ratificación — se completa la semilla                                            |
| **Regla faltante**           | S-G no podría inventar la regla sin decidir un contrato   | la ratificación — se agrega la regla                                                |
| **Contradice una decisión**  | el hallazgo choca con una decisión de diseño congelada    | lo congelado, **salvo** que el hallazgo PRUEBE que es mejor (evidencia, no opinión) |
| **Redundante / ya resuelto** | ya está en el repo                                        | ninguno — se descarta (no es hallazgo)                                              |

Dos reglas duras que hacen esto reproducible y no opinión:

- **Ejecutar lo ejecutable.** Los cierres más fuertes salieron de CORRER: el re-lock que reprodujo
  6/6 digests del corpus, la enumeración de ieee30 que confirmó los óptimos, los flips que fijaron
  el bus del fixture, la Policy contra su schema. La corrida ES la prueba de que la ratificación
  mejora — no la afirmación de que mejora.
- **No se re-litiga lo congelado ni la base lógica** (`invariants.md` / `base-logica-formal.md`): una
  contradicción con ellos es dato contra el hallazgo. **El dueño manda EN SU plano** — si el hallazgo
  toca una decisión que es del dueño y no verificable contra el repo (una identidad de ancla, un
  criterio narrativo, una firma), **no se cierra por cuenta propia**: se aplica lo verificable y se
  **marca lo demás para la ratificación del dueño**.

## 3 · Aplicar lo que sobrevive (el "S-E focalizado")

Lo que gana se aplica como **supersesión fechada con causa** — marca propia (en esta sesión, `[S-F]`),
**jamás** edición silenciosa, **jamás** marca retroactiva. Se toca lo que corresponda: freeze,
semillas, anexo, KB, `uv.lock`, código, Policy. Se agrega un bloque **"Registro de cierre"** con la
causa por cada cambio, y se lista qué queda para el dueño real.

Prioridad al aplicar: **P0** = rompe seeds o el demo, o invalida algo congelado (cerrar antes de S-G)
· **P1** = cerrar en la ventana de ratificación · **P2** = registrar.

## 4 · Verificar y cerrar

- **Verificación por ejecución** de cada fix ejecutable, con la evidencia guardada.
- **Tests nuevos que prueban el valor del fix** — un fix sin test que lo ancle es una promesa.
- **Gates verdes** antes de cada commit:
  ```
  uv sync --all-packages --extra pandapower --extra ortools --extra networkx
  uv run lint-imports        # 9/9 KEPT
  uv run pytest tests/ -q     # verde
  uv run ruff check <tocados>
  pnpm -s exec tsc --noEmit -p apps/studio
  # + hook de la marca: "Blite"+"Engine" juntas = 0 hits repo-wide
  ```
- **Commits temáticos** con causa (deps / semillas / freeze / infra…).

## 5 · Lo que viene DESPUÉS (no es parte de este flujo)

Una vez este flujo cerrado sobre una ratificación, en este orden:

1. **Stress test brutal** del diseño resultante — panel de destrucción que intenta botarlo; si
   sobrevive, sigue (se hizo en otra sesión: `stress-test-sf-pre-sg.md`, veredicto GO).
2. **Comparación y convergencia** — cuando existan AMBAS ratificaciones (la **simulada** como
   contrapeso y la **real**), se aplica este mismo flujo a la real y luego se **comparan las dos**
   para medir convergencia; si convergen, se unifica y se pasa a **S-G oficial** con el set validado.

Este documento cubre solo el paso 0: auditar una ratificación contra el estado congelado y aplicar
lo que mejora. Los pasos 1 y 2 son posteriores.
