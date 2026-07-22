# Protocolo de auditoría de ratificaciones — someter las ratificaciones REALES al mismo proceso que la simulación

> **Estado: VIGENTE (proceso — caduca al cierre de la ratificación real).** Rama de ejercicio
> `ejercicio/sf-ratificacion-simulada`. Este documento fija, paso a paso, el proceso EXACTO que
> se aplicó a la ratificación **simulada** (S-F) para poder aplicárselo, sin improvisar, a las
> ratificaciones **reales** de Sebas/Steven/Geovanni cuando lleguen — auditarlas, validarlas,
> aplicar sus cambios con tests, estandarizarlas — y después **comparar simulación ↔ realidad**
> para medir convergencia. Si convergen, se unifica y se pasa a **S-G oficial** con el set
> validado. La simulación es el **contrapeso y la guía**: igual de importante que la real, porque
> es la vara contra la cual se mide.

---

## 0 · El objetivo en una línea

Correr las ratificaciones reales por el mismo molino que la simulada (auditoría → validación
adversarial → aplicación con tests → estandarización), producir una **matriz de convergencia**
simulación↔realidad, y usar esa convergencia como la luz verde (o roja) para S-G.

## 1 · Los cuatro artefactos que YA existen (la vara de comparación)

La ratificación real no parte de cero: se compara contra lo que la simulación ya produjo.

| Artefacto                                                                          | Qué es                                                                                | Rol en la comparación                                                                           |
| ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| [`../guia-ratificacion.md`](../guia-ratificacion.md)                               | El orden de lectura + checklist por dueño                                             | Lo que a cada dueño se le pidió ratificar (el mismo insumo para el real)                        |
| [`ratificacion-simulada-sf.md`](ratificacion-simulada-sf.md)                       | El **acta simulada** (4 agentes: 3 dueños + equipo/completitud)                       | El anexo por dueño = el **piso** y el espejo del real                                           |
| [`ratificacion-simulada-sf-validacion.md`](ratificacion-simulada-sf-validacion.md) | La **validación adversarial** (refutación + barrido extendido) + lista consolidada §4 | El estándar de rigor: así se audita un hallazgo                                                 |
| [`stress-test-sf-pre-sg.md`](stress-test-sf-pre-sg.md)                             | El **stress test brutal** (5 atacantes, veredicto GO)                                 | El diseño post-S-F ya sobrevivió destrucción — el real no lo debilita, lo confirma o lo corrige |
| [`../contract-freeze.md`](../contract-freeze.md) → "Registro de cierre (S-F)"      | Lo YA aplicado como supersesiones `[S-F]`                                             | El estado actual del diseño: sobre esto ratifican los reales                                    |

**Regla de arranque:** no enviar el acta simulada a los compañeros antes de su pasada (contamina
la independencia — es la premisa del contrapeso). El acta se usa DESPUÉS, para comparar.

## 2 · Reglas de oro (invariantes del proceso — idénticas a la simulación)

Estas nueve reglas gobiernan CADA fase; son lo que hace la auditoría reproducible y no opinión:

1. **Contexto fresco por revisor.** Cada auditor/validador/atacante arranca sin el sesgo de quien
   escribió el diseño. En agentes: `subagent` nuevo por rol, en paralelo.
2. **Postura de refutación en la validación.** Asumir que cada hallazgo (real o simulado) está MAL
   hasta que la **evidencia primaria** lo confirme: `archivo:línea` o una **corrida real**.
3. **Ejecutar lo ejecutable.** Los mejores hallazgos salieron de CORRER cosas (el crash del lock,
   los flips del fixture, la enumeración de ieee30, la Policy contra su schema). Todo en
   scratchpad, **cero escrituras al repo durante la auditoría**.
4. **Nada se aplica sin verificación por ejecución + gates verdes** (§6).
5. **Todo cambio = supersesión fechada con causa**, jamás edición silenciosa. Marca propia
   **`[S-F-real]`** (nunca `[S-F]` retroactiva, nunca `[S-E]`) — el registro no se falsea.
6. **No se re-litiga lo congelado ni la base lógica.** `invariants.md` / `base-logica-formal.md`
   nunca están bajo revisión: una contradicción es dato contra el hallazgo. **El dueño manda EN SU
   plano** — si el real contradice una decisión de su propia área, gana el dueño (es suya).
7. **Prioridad P0/P1/P2.** P0 = invalida algo congelado o mata el demo (cerrar ANTES de S-G) · P1
   = cerrar en la ventana (antes del 23-jul) · P2 = registrar.
8. **Gates obligatorios** antes de cada commit de aplicación (§6).
9. **Rama, jamás `main` directo.** Ver la decisión de rama en §7.

## 3 · Fase A — Intake: normalizar cada ratificación real

Las respuestas reales llegan en formas dispares (un "OK", un mensaje, un PR, una llamada). Antes de
auditarlas hay que **normalizarlas a la misma forma que un anexo de la simulación**, para que sean
comparables 1:1.

Por cada dueño, producir un registro con esta forma (un ítem por fila del checklist de la guía):

```
Dueño · Ítem del checklist · Veredicto{RATIFICA | RATIFICA CON OBJECIONES | OBJETA}
      · Cambio propuesto (si lo hay) · Porqué · ¿Ejecutable? (sí/no)
```

- **Ack seco ("OK mi plano").** Cuenta como `RATIFICA` en todos sus ítems. El anexo simulado de ese
  dueño pasa a ser el **piso**: sus objeciones P0/P1 simuladas son verificables contra el repo, así
  que se incorporan igual (no son opinión), y sus ítems "solo dueño" (§5, cuadrante D) quedan a la
  espera de decisión explícita del dueño.
- **Sin respuesta al 22-jul.** Igual que ack seco pero se dispara la escalación de Dylan; el anexo
  simulado es el piso completo de ese plano.
- **Objeción / PR.** Se transcribe verbatim al registro y entra a Fase B.

Salida de la fase: `docs/research/ratificacion-real-sf.md` (acta real, misma estructura que la
simulada: veredictos globales + tabla por ítem + anexo por dueño).

## 4 · Fase B — Auditoría + validación adversarial (dos pasadas)

Cada objeción/cambio real pasa por las **dos pasadas** que corrimos en la simulación:

- **Pasada 1 — Auditoría.** ¿Es verificable contra el repo? Confirmar/refutar contra evidencia
  primaria; **ejecutar** lo ejecutable. Clasificar: `CONFIRMADO` / `MATIZADO` / `REFUTADO`.
- **Pasada 2 — Refutación.** Un segundo revisor de contexto fresco intenta **tumbar** el hallazgo
  confirmado. Solo sobrevive lo que resiste evidencia primaria hostil.

Prompt copy-paste (sesión fresca, modelo Fable), por cada tanda de ratificaciones reales que llegue:

```
Auditá las ratificaciones REALES de Chimera con el MISMO proceso que la simulada (S-F).
Rama: ejercicio/sf-ratificacion-simulada. Insumo: docs/research/ratificacion-real-sf.md
(las respuestas reales ya normalizadas — Fase A). Vara: docs/contract-freeze.md +
"Registro de cierre (S-F)", docs/especificacion-contratos-v2.md, docs/esquema-datos-v2.md,
docs/contract-freeze-anexo-canonicalizacion.md, docs/invariants.md + base-logica-formal.md
(CONGELADOS — no se tocan), README de knowledge/.

Por cada objeción/cambio real, DOS pasadas:
(1) Auditoría — ¿verificable contra el repo? Confirmá/refutá con evidencia primaria
    (archivo:línea o corrida en scratchpad); EJECUTÁ lo ejecutable (receta del corpus,
    flips, Policy vs schema, vectores del anexo). Clasificá CONFIRMADO/MATIZADO/REFUTADO.
(2) Refutación — un 2º revisor de contexto fresco intenta TUMBAR cada CONFIRMADO con
    evidencia primaria hostil; solo sobrevive lo que resiste.

Reglas duras: cero escrituras al repo (todo en scratchpad); no re-litigar lo congelado ni la
base lógica (el dueño manda EN SU plano); la marca JAMÁS en ningún archivo; no tocar main.
Prioridad P0/P1/P2 (P0 = invalida algo congelado o mata el demo). Cada hallazgo: severidad,
evidencia primaria, a qué decisión/documento pega, fix propuesto, dueño.

Salida: actualizá docs/research/ratificacion-real-sf.md con la tabla de veredictos por ítem
(CONFIRMADO/MATIZADO/REFUTADO + evidencia) y la lista priorizada de cambios que sobreviven.
```

## 5 · Fase C — Comparación con la simulación (la matriz de convergencia)

El corazón del ejercicio. Para cada ítem/hallazgo se cruza **qué dijo el real** contra **qué dijo la
simulación**. Cuatro cuadrantes:

```
                        │  LA SIMULACIÓN LO CAZÓ      │  LA SIMULACIÓN NO LO CAZÓ
────────────────────────┼─────────────────────────────┼───────────────────────────────
 EL REAL LO LEVANTÓ      │  (A) CONVERGENCIA           │  (B) GANANCIA REAL
                        │  máxima confianza — aplicar │  el dueño vio algo que la sim no
                        │  (dos fuentes indep. igual) │  — auditar (Fase B) y aplicar
────────────────────────┼─────────────────────────────┼───────────────────────────────
 EL REAL NO LO LEVANTÓ   │  (C) SILENCIO SOBRE UN       │  (D) — (nadie lo vio; queda para
 (o dio ack seco)        │  HALLAZGO SIMULADO          │   el stress test / S-G)
                        │  si es verificable contra   │
                        │  repo ⇒ aplicar (la sim es  │
                        │  el piso); si es "solo      │
                        │  dueño" ⇒ escalar al dueño  │
                        │  antes del 23-jul           │
```

Reglas por cuadrante:

- **(A) Convergencia.** Real y simulación coinciden en sustancia. Es la señal más fuerte: dos
  fuentes independientes cazaron lo mismo. Se aplica con confianza máxima. **Cuenta para el
  veredicto de convergencia** (§7).
- **(B) Ganancia real.** El dueño real levantó algo que la simulación no vio — el valor irremplazable
  de la ratificación humana. Se audita (Fase B) y se aplica. Se registra como aprendizaje sobre los
  **puntos ciegos de la simulación** (útil para calibrar futuras simulaciones).
- **(C) Silencio sobre un hallazgo simulado.** El dueño no lo mencionó. Dos sub-casos:
  - Es **verificable contra el repo** (no opinión) ⇒ se aplica igual: el anexo simulado es el piso.
  - Es una decisión **"solo el dueño puede cerrar"** (§ lista de abajo) ⇒ **no** se aplica por
    silencio; se escala al dueño antes del 23-jul (el silencio no decide una identidad de ancla ni
    firma una AcceptanceAuthority).
- **(D) Conflicto (sub-caso de B con signo opuesto).** El real **contradice** la simulación o una
  decisión congelada de su propio plano ⇒ **gana el dueño real** (regla de oro 6). Se documenta por
  qué la simulación divergió — es el hallazgo más valioso sobre la fiabilidad del contrapeso.

**Los ítems "solo el dueño real puede cerrar"** (freeze → Registro de cierre S-F, punto 4 — el
silencio NO los ratifica, y por eso son el corazón del cuadrante C):

- **Sebas:** attestation-externa vs `@v2` para ieee30 · criterio físico/narrativo del bus 1 ·
  modelado de cr8 desde datos GIS · si 5 corridas seeds-pinned bastan como independencia AL2.
- **Steven:** cascada de cancelación (su runtime) · fail-closed de `replay` por escrito · matriz
  `interaction×profile` (su Dispatcher) · aceptar el endurecimiento del reintento.
- **Geovanni:** ¿existe el "baseline Terraform externo"? · expectativas de Pulumi · fechas 27/29 vs
  disponibilidad · tabla de licencias L · **spec del equipo del demo (qué laptop, cuánta RAM)**.
- **Equipo:** posición operativa VERBATIM ("del cliente") · corte camino-dorado/NO-va · firma de
  AcceptanceAuthority.

Prompt copy-paste (una vez que TODAS las ratificaciones reales están auditadas — Fase B cerrada):

```
Construí la MATRIZ DE CONVERGENCIA simulación↔realidad de Chimera (S-F). Rama:
ejercicio/sf-ratificacion-simulada. Insumos: docs/research/ratificacion-simulada-sf.md +
ratificacion-simulada-sf-validacion.md (la simulación) vs docs/research/ratificacion-real-sf.md
(el real, ya auditado en Fase B). Vara congelada: docs/contract-freeze.md.

Por cada ítem/hallazgo, clasificá en un cuadrante:
(A) CONVERGENCIA  — real y sim lo cazaron → aplicar, cuenta para convergencia
(B) GANANCIA REAL — solo el real → auditar y aplicar; registrar como punto ciego de la sim
(C) SILENCIO      — solo la sim → si es verificable contra repo, aplicar (sim = piso); si es
                    "solo dueño" (lista en freeze Registro de cierre S-F pt.4), escalar al dueño
(D) CONFLICTO     — el real contradice la sim/lo congelado en SU plano → gana el dueño; documentar
                    por qué la sim divergió

Cuantificá la convergencia (X de Y ítems en el cuadrante A; cuántos B/C/D). Emití un
VEREDICTO: CONVERGEN (cero conflictos sin resolver, cero P0 nuevo sin fix, la sustancia del
freeze sobrevive AMBAS pasadas) o DIVERGEN (hay que iterar con los dueños antes de S-G).

Salida: docs/research/convergencia-ratificacion-sf.md con la matriz, los conteos y el veredicto.
```

## 6 · Fase D — Aplicación de sobrevivientes (con tests)

Idéntico a lo que se hizo con la simulación:

1. **Supersesiones fechadas `[S-F-real]`** con causa registrada, en freeze / semillas / anexo / KB /
   lock / código. Nunca edición silenciosa. Se añade una subsección al **"Registro de cierre"** del
   freeze: _"Ratificación real (S-F, <fecha>)"_ con causa por cambio.
2. **Verificación por ejecución.** Todo fix ejecutable se corre y se registra la evidencia (misma
   disciplina que el re-lock 6/6, la enumeración de ieee30, los flips, la Policy vs schema).
3. **Tests nuevos que prueban el valor de cada fix** (TDD — como los que dejó el stress test): un fix
   sin test que lo ancle es una promesa, no un cierre.
4. **Gates verdes obligatorios** antes de cada commit:
   ```
   uv sync --all-packages --extra pandapower --extra ortools --extra networkx
   uv run lint-imports            # 9/9 KEPT
   uv run pytest tests/ -q        # verde
   uv run ruff check <tocados>
   pnpm -s exec tsc --noEmit -p apps/studio
   # + hook de la marca: "Blite"+"Engine" juntas = 0 hits repo-wide
   ```
5. **Commits temáticos** (uno por naturaleza: deps / semillas / freeze / infra…), mensaje con causa,
   `Co-Authored-By: Claude`.

## 7 · Fase E — Veredicto de convergencia y luz verde a S-G

El veredicto sale de la matriz (§5) y del estado de los gates (§6):

- **CONVERGEN** ⇒ se unifican simulación y realidad en un solo set validado, se aplica (Fase D), y
  se pasa a **S-G OFICIAL**. Criterio duro: **cero conflictos (D) sin resolver · cero P0 nuevo sin
  fix aplicable antes del 23-jul · ninguna decisión congelada invalidada · la sustancia del freeze
  sobrevivió las dos fuentes**.
- **DIVERGEN** ⇒ hay un conflicto de plano sin resolver o un P0 nuevo real. Se itera **con los
  dueños** (no en solitario — un conflicto en el plano de Steven lo cierra Steven), se re-corre la
  matriz, y solo entonces S-G.

**Decisión de rama (de Dylan — recomendación, no la ejecuto sin tu OK):** el ejercicio vive en
`ejercicio/sf-ratificacion-simulada` y NO se mergea. Para las ratificaciones reales, recomiendo una
rama propia off `main` (p. ej. `sf-ratificacion`) donde aterrizan la Fase A→D reales; el
`convergencia-ratificacion-sf.md` puede copiarse/portarse del ejercicio como insumo. La unificación
llega a `main` **solo tras el veredicto CONVERGEN**. Así el contrapeso (ejercicio) y el oficial
(rama real) quedan separados y auditables, y `main` recibe únicamente el set validado.

## 8 · Checklist de ejecución (resumen operable)

```
[ ] A. Intake: normalizar cada respuesta real → ratificacion-real-sf.md (mismo shape que la sim)
       · ack seco = RATIFICA (anexo sim = piso) · sin respuesta 22-jul = escalación Dylan
[ ] B. Auditoría + refutación (2 pasadas, contexto fresco, ejecutar, evidencia primaria)
       · clasificar CONFIRMADO/MATIZADO/REFUTADO · cero escrituras al repo
[ ] C. Matriz de convergencia (A/B/C/D) → convergencia-ratificacion-sf.md · cuantificar
[ ] D. Aplicar sobrevivientes: supersesiones [S-F-real] + tests + gates verdes + commits temáticos
[ ] E. Veredicto CONVERGEN/DIVERGEN → S-G oficial | iterar con dueños
```

**El invariante que hace todo esto valer:** la simulación no reemplaza la ratificación real —
la **precede como vara**. La real no reemplaza la simulación — la **confirma o la corrige**. La
convergencia entre ambas es lo que convierte "Dylan+Claude decidieron" en "el equipo ratificó", con
evidencia de las dos fuentes. Ese es el diferenciador del proyecto (confiable ≠ plausible) aplicado
al propio proceso de diseño.
