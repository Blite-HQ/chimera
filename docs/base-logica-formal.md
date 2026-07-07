# Base Lógica Formal del Engine

_Primitivos · Axiomas · Conceptos fundamentales · Principios · Teoremas · Pruebas_
_Registro explícito, sin analogías ni ejemplos ilustrativos_

> **Estado: CONGELADO.** Constitución lógica de Chimera — ya reflejada en [`invariants.md`](invariants.md) (los axiomas/principios AX/PR/D de este documento son la fuente de los INV-\*/AX-\* ahí enforzados). No está bajo revisión: toda nota de investigación que la contradiga es dato sobre la referencia, no motivo para cambiarla. Ver [`README.md`](README.md) para el índice de autoridad documental.
>
> **Qué es esto.** El sistema formal que constituye el _core_ lógico del Engine: las verdades que el sistema cumple siempre, en cualquier implementación, y de las que se deriva todo lo demás. Cristaliza la tesis del Engine —qué _son_ la soberanía, la verificación y la confianza, y cómo se garantizan— en el registro de un sistema axiomático.
>
> **Estructura (orden formal estricto):** Primitivos (2) → Axiomas (3) → Conceptos fundamentales (4) → Principios (5) → Teoremas (6) → Pruebas de independencia y consistencia (7–8).
>
> **Separación lógica/implementación.** La lógica define _propiedades_ (qué debe cumplirse siempre); la implementación elige _mecanismos_ (cómo). "Todo deja rastro" es lógica; el mecanismo concreto que almacena ese rastro es implementación. Self-host, cloud e integraciones nativas son implementación; soberanía, verificación y confianza son lógica. Este documento contiene solo lógica.

---

## 1 · El criterio de admisión al núcleo inviolable

Un invariante es **inviolable** (axioma) o **relajable-con-traza** (principio). El criterio que decide cuál es cuál, derivado de la tesis de soberanía (el dueño puede relajar todo lo que se confine a su dominio):

> **Criterio (relajación no localizable).** Un invariante `P` es inviolable sii no existe override que relaje `P` cuyo efecto quede confinado al dominio de quien lo ejecuta. Equivalentemente, toda relajación de `P` necesariamente: (1) restringe o daña a una entidad fuera del dominio que relaja [**externalidad**], o (2) impide detectar que `P` fue relajada [**opacidad**], o (3) elimina una precondición que otro invariante requiere para tener significado [**fundación**].

La cardinalidad del núcleo **se deriva** de aplicar el criterio, no se postula (derivación en Sección 3): **3 axiomas**. Un núcleo pequeño es _requerido_ por la soberanía: "inviolable" significa "no relajable ni en el propio dominio", y un núcleo grande contradiría que el dueño manda en su dominio. Nada importante se pierde por ser principio: un principio está encendido por defecto y solo se relaja con traza inmutable.

---

## 2 · Primitivos indefinidos y términos básicos

### 2.1 Sortes y relaciones primitivas (indefinidos)

- **𝓔** entidades · **𝓥** eventos · **𝓓 ⊆ 𝓔** datos · **(T, <)** tiempo lineal.
- **τ : 𝓥 → T** (instante) · **perf : 𝓥 ⇀ 𝓔** (ejecutor, parcial) · **in, out : 𝓥 → 𝒫(𝓓)** (consumidos, producidos).
- **via ⊆ 𝓥 × 𝓔** (`via(v,i)`: ocurrió a través de `i`) · **contains ⊆ 𝓔 × 𝓔** (clausura transitiva `contains*`) · **owner : 𝓔 ⇀ 𝓔**.
- Predicados: **model(e)**, **world(v)**, **irreversible(v)**, **affects-third-party(v)**, **grants(e,a,k)@t**.

### 2.2 Términos básicos definidos

> **D1 (Acción).** `v ∈ 𝓐 :⇔ perf(v)↓`. **D2 (Actor).** `a` es actor `:⇔ ∃ v ∈ 𝓐 : perf(v)=a`. **D3 (Salida/Entrada).** `out(v)` salidas, `in(v)` entradas. **D4 (Efecto en el mundo).** `v` world-effecting `:⇔ v ∈ 𝓐 ∧ world(v)`. **D5 (Interfaz).** `i` interfaz `:⇔ ∃ v: via(v,i)`.
>
> **D6 (Dominio/Frontera).** Dominio `D :⇔ owner(D)↓`. `inside(D) := {e : contains*(D,e)}`. `d` cruza la frontera de `D` en `v` `:⇔ d ∈ out(v) ∧ d ∈ inside(D) ∧ destino(v) ∉ inside(D)`. **D7 (Canal).** `channel(i,D₁,D₂)` (declarado en el estado).
>
> **D8 (Registro).** `r` registro de `v` `:⇔ ∃ δ: δ(r)=⟨perf(v),op(v),in(v),out(v),τ(v)⟩`. `r` **inmutable** `:⇔ ¬∃ v'∈𝓐: r∈out(v') con δ(r) alterado`.
>
> **D9 (Ancla).** `α` ancla para `d` `:⇔ ¬model(α) ∧ ∃ check_α:𝓓→{pass,fail}` función solo de `d` y del estado de `α`. **D10 (Verificada, atómica).** `d` verificada `:⇔ ∃ α: check_α(d)=pass ∧ ese check está registrado`. `basis(v)` := salidas de las que depende `v`.
>
> **D11 (Mediada).** `v` mediada `:⇔ ∃ i: via(v,i)`. **D12 (Autorizada).** `v` autorizada por `e` `:⇔ grants(e,perf(v),op(v))@τ(v)`. **D13 (Override).** `v` override `:⇔ su post-estado relaja el guard de algún principio en algún dominio`.

---

## 3 · Axiomas (inviolables) — y su derivación

Cada axioma se admite porque su relajación es no localizable (Sección 1). Se indica el criterio que lo admite.

> **AX1 — Identidad + Aislamiento.** _(Admitido por fundación (3) + externalidad (1).)_
> (a) `∀ v ( v ∈ 𝓐 → ∃! a ∈ 𝓔 : perf(v)=a )`.
> (b) `∀ v ∈ 𝓐, ∀ D₁≠D₂ ( perf(v) ∈ inside(D₁) ∧ ∃ d (d ∈ in(v)∪out(v) ∧ d ∈ inside(D₂)) → ∃ i (channel(i,D₁,D₂) ∧ via(v,i)) )`.
>
> **AX2 — Meta-auditabilidad.** _(Admitido por opacidad (2).)_
> `∀ v ( override(v) → ∃ r (registro(r,v) ∧ inmutable(r)) )`, y `∀ v ( "v desactiva un registro" → override(v) )` (cierre: desactivar un registro es a su vez un override registrado).
>
> **AX3 — Mediación.** _(Admitido por fundación (3): sin interposición no hay dónde aplicar los demás invariantes.)_
> `∀ v ( v ∈ 𝓐 ∧ model(perf(v)) → ∃ i : via(v,i) )`.

**Por qué exactamente estos tres** (derivación): Observabilidad, Verificación y Soberanía resultan **localizables** (relajarlas en el propio dominio, con la relajación registrada por AX2, es detectable por terceros) → son principios, no axiomas. Mediación, en cambio, es la precondición de la _enforzabilidad_ de todos los demás → inviolable. Identidad y Meta-auditabilidad son el suelo y el guardián → inviolables. La esquina irreversible-que-afecta-a-tercero de la verificación se trata como principio reforzado (PR4, Sección 5), no como axioma, porque sigue siendo localizable.

---

## 4 · Conceptos fundamentales (la tesis del Engine, formalizada)

Estos conceptos se **construyen** sobre los primitivos y axiomas. Son lo que el Engine _afirma que son_ la soberanía, la verificación y la confianza.

### 4.1 Procedencia

> **Contribución causal.** `contribuye(v,d) :⇔ d ∈ out(v) ∨ ∃ d'∈out(v) ∃ v'' (d'∈in(v'') ∧ contribuye(v'',d))`.
> **D14 (Procedencia).** `prov(d) := { r : ∃ v (registro(r,v) ∧ contribuye(v,d)) }`.
> **D15 (Procedencia completa).** `d` tiene procedencia completa `:⇔ ∀ v (contribuye(v,d) → ∃ r (registro(r,v) ∧ inmutable(r) ∧ r ∈ prov(d)))`.
> **D16 (Reconstruible).** `d` es reconstruible `:⇔ ∃ ρ : ρ(prov(d)) = d` (la procedencia determina unívocamente la derivación de `d`).

La procedencia es más que "existe un registro": es la **historia causal completa, inmutable y suficiente para reconstruir** un resultado. "Todo deja rastro" es, formalmente, _procedencia completa de toda salida con efecto en el mundo_.

### 4.2 Verificación

> **D17 (Establecido por ancla).** `establecido_por_ancla(d,α) :⇔ ¬model(α) ∧ check_α(d)=pass`.
> **Verificación** (concepto): la propiedad por la cual la corrección de una salida se establece **por contraste contra un ancla no-modelo** (D9), no por su plausibilidad. `d` verificada ⇔ D10.
> **D18 (Coherencia, lo que NO es verificación).** `coherente(d) :⇔ ∀ m ∈ Modelos: m asigna alta probabilidad a d`. **Coherencia ≠ verificación**: la coincidencia entre modelos no consulta ningún ancla no-modelo, luego no establece corrección. Esta distinción es la médula del Engine.

### 4.3 Soberanía

> **D19 (Soberanía).** Un dominio `D` es **soberano** `:⇔` se cumplen tres componentes:
>
> - **(i) Custodia.** `∀ v, ∀ d ∈ out(v) ( d cruza la frontera de D → autorizada(v, owner(D)) )`.
> - **(ii) Control.** `owner(D)` es la autoridad de política sobre `inside(D)`: la autorización de toda acción con efecto sobre `inside(D)` se rige por una política cuyo autor es `owner(D)`.
> - **(iii) Autonomía operativa.** `∀` función esencial `f` de `D`, `∃` ejecución de `f` tal que `∀` acción `v` en ella: `perf(v) ∈ inside(D)` (D puede operar sin requerir un actor externo).
>
> **Soberanía = custodia ∧ control ∧ autonomía.** Las tres son propiedades lógicas. La lógica exige _autonomía operativa_ (que el dominio pueda operar sin depender de un actor externo); no exige ninguna forma particular de lograrla.

### 4.4 Confianza (la tesis central)

> **D20 (Confiable).** Un resultado `d` es **confiable** `:⇔ identificado(productor(d)) [AX1] ∧ procedencia_completa(d) [D15] ∧ verificada(d) [D10]`.
>
> **La tesis, formalizada.** La confianza es una propiedad del **proceso** que produjo `d` —identidad de quién lo produjo + historia reconstruible + verificación contra ancla no-modelo—, **no** una propiedad de la plausibilidad de `d` ni del modelo que lo generó.
> **D21 (Plausibilidad).** `plausible(d) :⇔ ∃ m ∈ Modelos: m asigna alta probabilidad a d`.
> **Confiable ⊥ Plausible** (independientes): existe `d` plausible y no confiable (coherente sin ancla), y existe `d` confiable sin que ningún modelo lo juzgue plausible. Esto es lo que distingue al Engine de un sistema de IA que solo produce salidas plausibles.

### 4.5 Integridad

> **D22 (Integridad).** El sistema tiene **integridad** en `t` `:⇔` (i) AX1, AX2, AX3 se cumplen hasta `t`, y (ii) `∀` principio `P`, `∀ v` (`P(v)` ∨ existe override registrado que lo relajó en `dominio(v)`).
> Integridad = **ninguna garantía fue subvertida sin registro**. AX2 es su guardián: vuelve la integridad _auditable_ (toda relajación de un principio dejó rastro; toda violación de un axioma es imposible por construcción del núcleo).

### 4.6 Conceptos ya cubiertos

**Mediación** = D11, elevada a inviolable para modelos por AX3. **Identidad** = AX1(a). No se redefinen; se referencian.

---

## 5 · Principios (por defecto, relajables-con-traza)

> **Esquema de principio.** Para todo principio `P`: `∀ v ∈ 𝓐 ( P(v) ∨ ∃ o (override(o) ∧ relaja(o,P,dominio(v)) ∧ τ(o)<τ(v) ∧ ∃ r (registro(r,o) ∧ inmutable(r))) )`. La traza la fuerza AX2.
>
> **PR1 — Observabilidad.** `P_obs(v) := ∃ r (registro(r,v) ∧ inmutable(r))`. _Relación:_ PR1 sobre todas las acciones causantes de `d` produce la **procedencia completa** de `d` (D15).
>
> **PR2 — Verificación.** `P_ver(v) := world(v) → ∀ d ∈ basis(v): verificada(d)` (D10, 4.2).
>
> **PR3 — Soberanía (componente custodia).** `P_sov(v) := ∀ d ∈ out(v) (d cruza la frontera de D → autorizada(v, owner(D)))`. _Relación:_ PR3 **es** la componente (i) de la soberanía (D19); las componentes (ii) control y (iii) autonomía son los otros dos conjuntos de condiciones de D19.
>
> **PR4 — Verificación reforzada de lo irreversible.** `P_ver⁺(v) := world(v) ∧ irreversible(v) ∧ affects-third-party(v) → ∀ d ∈ basis(v): verificada(d)`. Esquina reforzada de PR2: su relajación admite solo las vías seguras de la Sección 5.1. Permanece principio (no axioma) porque sigue siendo localizable: su relajación deja rastro, y la acción no se ejecuta cuando no puede verificarse.

### 5.1 Vías seguras de relajación de la verificación

La relajación de PR2/PR4 sobre un conjunto de acciones es segura cuando elimina la **repetición** de la verificación, no la verificación misma. Dos hechos lógicos la habilitan:

> **(1) Equivalencia plan–acción.** Si un plan `P` genera determinísticamente `{a₁…aₙ}`, entonces `verificada_plan(P) ∧ ∀ i conforma(aᵢ,P) ⊢ ∀ i verificada(aᵢ)`. Verificar el plan y la conformidad de las acciones equivale a verificar cada acción.
> **(2) Reversibilidad demota irreversibilidad.** Si existe una acción que deshace el efecto de `v`, entonces `¬irreversible(v)`, y `v` sale del alcance de PR4.
>
> **Condición sobre el override.** Toda relajación de PR2/PR4 es, por el esquema de principio, un override acotado (a una operación y un conjunto de acciones), no perpetuo, y registrado (AX2).

### 5.2 Inv-E — El egreso lo gobierna solo la autorización

> **Inv-E.** `∀ v, ∀ d ∈ out(v) ( d cruza la frontera de D → autorizada(v, owner(D)) )`, **y ninguna otra propiedad —en particular la verificación— satisface el antecedente de un egreso.** Si no hay ancla interna y el dueño no autorizó egreso, la salida se marca no verificada (relaja PR2 con traza) o la acción se bloquea — nunca se exporta.
> **Consecuencia.** Como el egreso depende exclusivamente de autorización previa del dueño, ninguna instrucción presente en el contexto puede provocar egreso invocando una "verificación". Proteger a un tercero se logra **no ejecutando** la acción (sin egreso), no exportando datos: soberanía y protección-del-tercero se satisfacen ambas por no-acción.

---

## 6 · Teoremas

> **TH1 — Integridad del catálogo.** Toda capacidad cuya invocación tiene efecto en el mundo es atribuible, mediada (si es/usa modelo) y verificada antes del efecto.
> _Demostración._ Sea `v` invocación de capacidad `c` con `world(v)`. AX1(a) ⇒ `perf(v)↓` único (atribuible). AX3 ⇒ si `model(perf(v))`, `∃ i: via(v,i)` (mediada). PR2 ⇒ `∀ d ∈ basis(v): verificada(d)` (verificada). ∎ _Corolario:_ "revisar toda capacidad antes de que actúe" es teorema, no axioma.
>
> **TH2 — Necesidad conjunta de la confianza.** Cada uno de {identidad, procedencia, verificación} es necesario para la confianza: existe `d` que cumple dos pero no es confiable.
> _Demostración (por testigos)._ (a) `d` verificada + procedencia completa pero `perf` anónimo ⇒ no atribuible ⇒ no confiable. (b) `d` identificada + verificada sin procedencia completa ⇒ no reconstruible ⇒ no auditable ⇒ no confiable. (c) `d` identificada + procedencia completa pero no verificada ⇒ puede ser coherente sin ancla ⇒ no confiable. Los tres son independientes y conjuntamente necesarios. ∎
>
> **TH3 — La confianza no se deriva de la plausibilidad.** `confiable(d)` no implica ni es implicado por `plausible(d)`.
> _Demostración._ Por D20 y D21, `confiable` se define sobre identidad/procedencia/ancla-no-modelo; `plausible` sobre el juicio de un modelo. Un ancla no-modelo (D9) puede pasar un `d` que ningún modelo juzga probable, y un modelo puede juzgar probable un `d` que ningún ancla pasa. ∎ Este teorema _es_ la diferencia del Engine respecto de un sistema de IA convencional.

---

## 7 · Independencia (pruebas)

Un axioma es independiente si existe un modelo donde _él_ falla y los demás se sostienen.

> **M₁ (¬AX1, AX2∧AX3).** Acciones de modelo mediadas y overrides registrados, pero existe acción anónima (`perf↓` falla). AX3 vacuo para ella; AX2 intacto. **AX1 independiente.**
> **M₂ (¬AX2, AX1∧AX3).** Ejecutor único y mediación plena, pero existe override sin registro. **AX2 independiente.**
> **M₃ (¬AX3, AX1∧AX2).** Ejecutor único y overrides registrados, pero un modelo ejecuta acción world-effecting sin interfaz (acceso directo). La acción tiene ejecutor; los overrides siguen registrados. **AX3 independiente.**

Ningún axioma se deriva de los otros.

---

## 8 · Consistencia (prueba + resolución de conflictos)

> **Lema (consistencia incondicional).** {AX1, AX2, AX3, PR1, PR2, PR3, PR4} es consistente. _Demostración._ Ningún invariante es existencial: ninguno obliga a que una acción ocurra; todos son universales-condicionales sobre acciones que ocurren. Por tanto cualquier ejecución que no realice las acciones conflictivas (en el límite, la vacía) los satisface vacuamente. ∎

**El choque soberanía-vs-verificación** (PR2 exige contrastar `d` contra un ancla; PR3 prohíbe que `d` cruce la frontera) se resuelve así:

- **Caso blando** (verificación como PR2): tres salidas consistentes — (1) el dueño autoriza el cruce; (2) existe ancla `α ∈ inside(D)` y se verifica adentro; (3) `d` se marca no verificada (relaja PR2 con traza). Sin contradicción.
- **Caso duro** (ancla solo externa, dueño no autoriza egreso): se **marca no verificada**, o en la esquina PR4 (irreversible que afecta a un tercero) se **bloquea** `v`. La no ocurrencia satisface PR4 (antecedente falso) y la soberanía (nada cruzó).
- **No hay precedencia que decidir.** Por **Inv-E** (Sección 5.2) el egreso lo gobierna _solo_ la autorización, y la verificación nunca lo fuerza. Proteger a un tercero es **no ejecutar** la acción irreversible — lo cual no requiere egreso. Por tanto soberanía y verificación **nunca chocan**: ambas se satisfacen por no-acción.

---

> Este documento es el _core_ lógico del Engine. La arquitectura debe ser su reflejo verificable: cada axioma, concepto y principio debe corresponder a un componente que lo garantiza.
