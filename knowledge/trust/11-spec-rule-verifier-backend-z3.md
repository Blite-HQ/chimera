# Nota 11 — Spec del `RuleVerifier`: backend intercambiable (Python / Z3), unsat core como evidencia, ruta rung 4→1

**Ítem del plan (§4 Dylan / ficha A1):** Anclas duras — de decisión a diseño de adapter. Parte 2: el constraint-checker genérico (corrección #4 de Arquitectura-Python).
**Fecha:** 2026-07-07 · **Estado:** spec de diseño — insumo de la sesión 11. **SOLO diseño; nada implementado.**
**Fuentes:** nota 03 §1.2 (`property`/`metamorphic`) y §1.4 (tri-estado) · nota 04 §1.1 (Z3 como adapter futuro del mismo puerto), §4 item 3 (reglas del dominio como DATOS) · `contract-freeze.md` §4 · anexo de canonicalización §5 (digest de artefacto) · docs Z3 (`assert_and_track`/`unsat_core`, estados `sat|unsat|unknown`).

---

## 1 · Patrón / mecanismo

### 1.1 Un adapter, dos backends, una regla-como-dato

El `RuleVerifier` es el adapter genérico que verifica que un candidato **cumple un conjunto de reglas del dominio**. Corrección #4 (nota 04 §4): las reglas del dominio eléctrico NO se hardcodean — entran como **conocimiento versionado** (`knowledge/islanding/`) y el verifier las recibe como `constraints`; el adapter es agnóstico al dominio. Su `anchor_kind = "rule"`.

La clave del diseño es un **backend intercambiable** detrás de un puerto interno:

```python
class RuleBackend(Protocol):
    name: Literal["python", "z3"]
    def check(self, rule_set: RuleSet, subject: JsonValue) -> RuleResult: ...

class RuleResult(TypedDict, total=False):
    holds: bool                       # ¿el candidato satisface el conjunto?
    backend: Literal["python", "z3"]
    rung: Literal[1, 4]               # 1 si prueba formal; 4 si chequeo/muestreo
    counterexample: JsonValue         # asignación concreta que viola (Z3 model)
    unsat_core: list[str]             # nombres de las reglas en conflicto (Z3)
    status: Literal["sat", "unsat", "unknown"]   # crudo del backend Z3
    examples_run: int                 # camino muestreado (Hypothesis)
    seed: int
```

- **Backend `python` (hoy, lo que embarca el hackathon):** la regla es un predicado Python (o una forma declarativa chica) evaluado directo sobre el candidato — o, para propiedades universales, muestreado con **Hypothesis** (nota 03). Determinista, rápido, **rung 4**. Emite `evidence.method = "property"` (o `"metamorphic"`).
- **Backend `z3` (cuando la regla lo amerite):** la regla se expresa en un fragmento decidible (aritmética lineal, bitvectors, booleana) y **Z3 la descarga formalmente** → **rung 1**. Es el "terreno if-then/SMT" de nota 04 (el hueco de AWS AR §1.2), pero soberano y self-host.

El **mismo `RuleVerifier`** elige backend según la regla y **el `rung` que emite depende del resultado**, no del adapter: una regla formal-elegible se intenta primero por Z3 (rung 1) y **degrada a Hypothesis (rung 4) si Z3 no decide** (§1.3). El `rung` es por-`Attestation` (freeze §4), no por-adapter.

### 1.2 rung 4 vs rung 1: qué prueba realmente cada backend

La distinción es la diferencia entre _"no encontré contraejemplo"_ y _"no existe contraejemplo"_ — el corazón de por qué la escalera importa:

- **rung 4 (Python/Hypothesis):** _"la propiedad se sostuvo en `examples_run` casos muestreados, `seed=S`"_. Es evidencia de **ausencia-de-contraejemplo-en-la-muestra**, no prueba. `verdict:"pass"` = "no encontré contraejemplo" — podría existir uno fuera de la muestra. El `seed` la hace _replayable_ (nota 03 §1.2). Es la afirmación rung 4 honesta.
- **rung 1 (Z3):** para probar que una propiedad `P` vale para TODA entrada, se le pide a Z3 que la **negación** sea insatisfacible: `check(∃ entrada. ¬P(entrada))`.
  - `unsat` ⇒ **no existe** entrada que viole `P` ⇒ `P` es teorema en la teoría ⇒ **rung 1 `pass`** (prueba, no muestra).
  - `sat` ⇒ Z3 devuelve un **model**: una entrada concreta que viola `P` ⇒ **rung 1 `fail`** con el model como **contraejemplo** en la evidencia.
  - `unknown` ⇒ Z3 no pudo decidir (no lineal, cuantificadores duros) ⇒ **`inconclusive`** a nivel formal → §1.3.

### 1.3 La ruta de upgrade rung 4→1 (degradación honesta)

Un solo adapter, comportamiento graduado y **registrado con honestidad**:

1. Si la regla es formal-elegible → intentar **Z3 primero**.
2. `unsat`/`sat` → verdict rung 1 (`pass`/`fail`) con prueba/contraejemplo.
3. `unknown` → **caer a Hypothesis (rung 4)**, y registrar en la evidencia que **el intento formal fue `unknown`** y que el resultado descansa sobre muestreo. El `rung` de la `Attestation` baja a 4; el Studio muestra "no se pudo probar formalmente; N casos sin contraejemplo".

Así la exigencia sube sola cuando el problema lo permite (rung 4 hoy → rung 1 cuando la regla se formaliza) sin cambiar el contrato ni el llamador: es la misma `Attestation`, con `rung` distinto. El upgrade es **aditivo y transparente**, nunca un salto silencioso.

### 1.4 El unsat core de Z3 como evidencia explicable ("QUÉ restricción falla")

El diferenciador frente a un `fail` opaco: no basta decir "el candidato es infactible", queremos **cuál** conjunto de reglas viola. Dos mecanismos de Z3:

- **Model (contraejemplo):** al comprobar que la negación de una propiedad es `sat`, Z3 devuelve la asignación concreta que la viola — legible por humano, ya cubierto por `counterexample`.
- **Unsat core:** se asertan las reglas con **tracker nombrado** (`assert_and_track`, o _assumptions_ nombradas). Al resultar `unsat`, `unsat_core()` devuelve el **subconjunto de reglas nombradas que están en conflicto**. Para CHIMERA: para explicar por qué un candidato viola el dominio, se codifica _"el candidato está fijo"_ + cada regla del dominio como aserción rastreada; el unsat core = exactamente las reglas que el candidato rompe → `["constraint:power_balance", "constraint:connectivity"]`. El Studio pinta esos nombres, no un "fail" pelado. Eso es evidencia **explicable**: QUÉ falla, no solo QUE falla.

Limitación documentada: el core de Z3 es un subconjunto insatisfacible **pequeño**, no garantizado mínimo-mínimo. Si se necesita minimalidad estricta (menor conjunto), se itera reduciendo (Fase 2). Para el pitch/demo, "pequeño y correcto" alcanza.

### 1.5 Forma del `evidence`

Camino muestreado (backend `python`) → `method:"property"` (nota 03 §1.2, tal cual):

```python
{"method": "property",
 "properties": [{"name": "cut_cost_nonnegative", "passed": true, "examples_run": 200, "counterexample": null}],
 "seed": 42, "generator_version": "hypothesis-6.x",
 "backend": "python", "rule_set_id": "islanding-rules@0.1.0", "rule_digest": "<sha256>"}
```

Camino formal (backend `z3`):

```python
{"method": "property",            # ver §4: NO se inventa un método nuevo sin freeze
 "properties": [{"name": "power_balance", "passed": false, "counterexample": {"island": 2, "imbalance": 3.1}}],
 "backend": "z3", "status": "sat",
 "unsat_core": [],                # poblado cuando status=="unsat" sobre reglas nombradas
 "rule_set_id": "islanding-rules@0.1.0", "rule_digest": "<sha256>"}
```

`subject = {run_id, step_id?, claim_digest}` (anexo §5). `rule_digest = SHA-256` sobre los **bytes exactos del artefacto de reglas** distribuido en `knowledge/islanding/` — Regla 1 del anexo (artefacto versionado, como `policy_digest`), **no** `C()`: comentarios y formato del archivo son parte de lo distribuido.

---

## 2 · Decisión

| Referencia                                              | Decisión                                                       | Racional                                                                                                    |
| ------------------------------------------------------- | -------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Backend Python + Hypothesis (rung 4, hoy)               | **integrar** (Hypothesis MPL-2.0, nota 03)                     | El backend que embarca el hackathon; determinista con seed                                                  |
| **Z3 (SMT)** como backend formal (rung 1)               | **inspirar hoy / adapter Fase 2** (acá se especifica la FORMA) | MIT; el if-then/SMT no es el hot-path del reto (nota 04 §2). La forma del puerto hace el upgrade un drop-in |
| Regla-como-dato (`knowledge/islanding/`)                | **portar** (corrección #4)                                     | El verifier es genérico; el umbral eléctrico es conocimiento versionado, no código                          |
| `assert_and_track` + `unsat_core()` para explicabilidad | **portar** (patrón de uso de Z3)                               | La explicabilidad ("QUÉ falla") es el punto — evidencia, no adorno                                          |
| Degradación rung 1→4 ante `unknown`                     | **portar** (patrón propio)                                     | Honestidad de nota 03 §1.4 aplicada al backend formal                                                       |
| Casbin / Cedar / OPA como motor de reglas               | **descartar acá**                                              | Son policy-as-code de authz/gobernanza (ficha A2/nota 05), no verificación de resultados de cómputo         |

## 3 · Licencias

| Pieza             | Licencia    | Verificado                      | Implicación                                              |
| ----------------- | ----------- | ------------------------------- | -------------------------------------------------------- |
| Z3 (v4.16.0)      | **MIT**     | ✅ nota 04 (en vivo 2026-07-02) | Adapter Fase 2; sin restricción                          |
| Hypothesis (v6.x) | **MPL-2.0** | ✅ nota 03 (en vivo)            | Copyleft de archivo: OK como dep sin vendorizar/parchear |

## 4 · Impacto en contrato

**Diseño detrás del puerto (sin acción de freeze):** el `RuleVerifier` es un adapter del `Verifier` congelado; el `RuleBackend` es un puerto **interno** del adapter (como `ExecutionHarness` en nota 12), no un contrato del engine. El engine no conoce Z3 (ADR-008).

**A ratificar en el freeze** (operación regla 4 — coordinación, NO se editó el freeze):

1. **El backend formal NO cae limpio en la unión `evidence`.** El freeze §4 / nota 03 §1.2 discrimina por `method ∈ {differential, execution, known_truth, property, metamorphic, human}` — **no hay arm `rule`/`smt`**. Dos opciones, es **decisión de freeze**, no unilateral:
   - (a) **reusar `method:"property"`** con campos aditivos opcionales `backend`, `status` (`sat|unsat|unknown`) y `unsat_core` (el arm `property` ya tiene `counterexample`). Preferida: mantiene la unión de 6 arms.
   - (b) agregar un arm `method:"rule"` nuevo — cambio mayor de la unión.
     Esta nota asume (a) y lo marca como el ítem de coordinación.
2. **`rung` variable por `Attestation` del mismo adapter** (1 si Z3 prueba, 4 si Hypothesis/degradación). Ya soportado por el freeze §4 (rung es por-attestation), pero conviene un test de que un solo adapter emite ambos.
3. **`rule_digest`** entra como Regla 1 del anexo (artefacto), consistente con `policy_digest`; sin cambio de esquema (vive en `evidence`).

## 5 · Reconciliación contra la base lógica

- **PR2 / INV-2 (el verificador nunca es un modelo):** INTACTO — Z3 es un prover determinista, no un modelo; rung 1 legítimo. El adapter vive en `verification/`, no importa `serving`.
- **Nota 03 §1.4 (tri-estado):** REALIZADO por partida doble — `unknown` de Z3 → `inconclusive`/degradación a rung 4; "no encontré contraejemplo" (rung 4) jamás se disfraza de "no existe" (rung 1).
- **Inv-E:** INTACTO — un `pass` de regla no autoriza egreso; informa.
- **Nota 04 §4 item 3 (reglas como datos):** REALIZADO — el adapter recibe `constraints`; el `rule_digest` ancla la versión de las reglas usadas, haciendo la verificación reproducible.
- **Ninguna referencia contradice la base lógica.** El hallazgo (la unión `evidence` no previó un backend SMT) es dato sobre la semilla del contrato, no sobre la lógica — se resuelve aditivamente en el freeze, sin tocar invariantes.
