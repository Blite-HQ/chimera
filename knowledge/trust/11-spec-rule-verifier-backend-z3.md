# Nota 11 — Spec del `RuleVerifier`: backend intercambiable (Python / Z3), unsat core como evidencia, ruta de upgrade `property_rule` → `formal_exact`

**Ítem del plan (§4 Dylan / ficha A1):** Anclas duras — de decisión a diseño de adapter. Parte 2: el constraint-checker genérico (corrección #4 de Arquitectura-Python).
**Fecha:** 2026-07-07 · **Estado:** **VIGENTE — spec de diseño interno traducida a clase+AL por decisión #103 (2026-07-30)**. Sello previo conservado: **SIGUE SIN IMPLEMENTAR (verificado 2026-07-24, post-MVP)** — no existe `RuleVerifier` en el engine; el único vestigio es el stub `capabilities/smt` (`NotImplementedError`). Su implementación es el ítem **C3/M3** del backlog (#103, `docs/mejorado/04-consolidacion.md`). La escalera 1–7 en que esta nota nació quedó supersedida (freeze §4; mapa de traducción en `docs/convergencia-diseno-v32.md` §2.1) — el campo `rung` desapareció del contrato.
**Rango (#108):** «diseño interno citado por código» — NO es spec de costura; promoción a spec = Fase 0 si hace falta.
**Fuentes:** nota 03 §1.2 (`property`/`metamorphic`) y §1.4 (tri-estado) — SUPERSEDIDA; el contrato vigente es `contract-freeze.md` §4 · nota 04 §1.1 (Z3 como adapter futuro del mismo puerto), §4 item 3 (reglas del dominio como DATOS) · anexo de canonicalización §5 (digest de artefacto) · docs Z3 (`assert_and_track`/`unsat_core`, estados `sat|unsat|unknown`) · decisión #103 (ruta `formal_exact`+proof: cvc5→Alethe→Carcara).

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
    verifier_class: Literal["formal_exact", "property_rule"]
    #   formal_exact si hubo prueba formal (techo AL4 CON checker independiente,
    #   AL3 sin él); property_rule si chequeo/muestreo (techo AL2) — freeze §4
    counterexample: JsonValue         # asignación concreta que viola (Z3 model)
    unsat_core: list[str]             # nombres de las reglas en conflicto (Z3)
    status: Literal["sat", "unsat", "unknown"]   # crudo del backend Z3
    examples_run: int                 # camino muestreado (Hypothesis)
    seed: int
```

- **Backend `python` (la v1):** la regla es un predicado Python (o una forma declarativa chica) evaluado directo sobre el candidato — o, para propiedades universales, muestreado con **Hypothesis** (nota 03). Determinista, rápido, **clase `property_rule` (techo AL2)**. Emite el predicate `property_rule` (`PropertyRulePredicate`, `engine/src/blite/verification/evidence.py:120-130`).
- **Backend `z3` (cuando la regla lo amerite):** la regla se expresa en un fragmento decidible (aritmética lineal, bitvectors, booleana) y **Z3 la descarga formalmente** → ruta hacia **clase `formal_exact`** (AL4 SOLO con checker independiente empaquetado — `proof {certificate_ref, checker_id, checker_verdict}`, freeze §4-iii; AL3 sin él). Es el "terreno if-then/SMT" de nota 04 (el hueco de AWS AR §1.2), pero soberano y self-host.

El **mismo `RuleVerifier`** elige backend según la regla y **la clase/nivel que emite depende del resultado**, no del adapter: una regla formal-elegible se intenta primero por el backend formal (`formal_exact`) y **degrada a Hypothesis (`property_rule`, AL2) si el prover no decide** (§1.3). La `verifier_class` y el `level` son por-`Attestation` (freeze §4), no por-adapter.

### 1.2 `property_rule` (AL2) vs `formal_exact` (AL4): qué prueba realmente cada backend

La distinción es la diferencia entre _"no encontré contraejemplo"_ y _"no existe contraejemplo"_ — el corazón de por qué la distinción de clases y niveles importa:

- **`property_rule` (Python/Hypothesis, techo AL2):** _"la propiedad se sostuvo en `examples_run` casos muestreados, `seed=S`"_. Es evidencia de **ausencia-de-contraejemplo-en-la-muestra**, no prueba. `verdict:"pass"` = "no encontré contraejemplo" — podría existir uno fuera de la muestra. El `seed` la hace _replayable_ (nota 03 §1.2). Es la afirmación AL2 honesta.
- **`formal_exact` (Z3):** para probar que una propiedad `P` vale para TODA entrada, se le pide a Z3 que la **negación** sea insatisfacible: `check(∃ entrada. ¬P(entrada))`.
  - `unsat` ⇒ **no existe** entrada que viole `P` ⇒ `P` es teorema en la teoría ⇒ **`formal_exact` `pass`** (prueba, no muestra). El **nivel** que ese pass alcanza depende del empaque: AL4 solo si el certificado de prueba viaja con checker independiente (§1.3, freeze §4-iii); AL3 si la prueba no es re-validable offline.
  - `sat` ⇒ Z3 devuelve un **model**: una entrada concreta que viola `P` ⇒ **`formal_exact` `fail`** con el model como **contraejemplo** en la evidencia.
  - `unknown` ⇒ Z3 no pudo decidir (no lineal, cuantificadores duros) ⇒ **`inconclusive`** a nivel formal → §1.3.

### 1.3 La ruta de upgrade `property_rule` (AL2) → `formal_exact` (AL4 con proof empaquetado) — y la degradación honesta

> **[MEJORADO · 2026-07-30 · decisión #103] El diseño vigente de M3:** el puerto
> `RuleBackend` se diseña desde el día 1 con salida de **certificado de prueba** —
> cvc5 → formato **Alethe** → checker **Carcara** empaquetado en el bundle: el
> `formal_exact` resultante es **AL4 verificable offline** por un tercero (freeze
> §4-iii, `proof {certificate_ref, checker_id, checker_verdict}` — la re-validación
> vive DENTRO del bundle). La **v1 con Z3** emite **`property_rule` AL2 honesto**,
> con presupuesto por **`rlimit`** — jamás timeout wall-clock: el determinismo del
> replay exige que el punto de corte no dependa de la máquina (mismo principio que
> `max_deterministic_time` en la nota 10 §1.4). Cero techos rotos.

Un solo adapter, comportamiento graduado y **registrado con honestidad**:

1. Si la regla es formal-elegible → intentar el **backend formal primero**.
2. `unsat`/`sat` → verdict `formal_exact` (`pass`/`fail`) con prueba/contraejemplo — AL4 si el proof empaquetado viaja con checker independiente; AL3 si no.
3. `unknown` (o `rlimit` agotado) → **caer a Hypothesis (`property_rule`)**, y registrar en la evidencia que **el intento formal fue `unknown`** y que el resultado descansa sobre muestreo. La `Attestation` queda en `property_rule`/AL2; el Studio muestra "no se pudo probar formalmente; N casos sin contraejemplo".

Así la exigencia sube sola cuando el problema lo permite (`property_rule` AL2 hoy → `formal_exact` con proof cuando la regla se formaliza y el checker viaja en el bundle) sin cambiar el contrato ni el llamador: es la misma `Attestation`, con `verifier_class`/`level` distintos. El upgrade es **aditivo y transparente** — se re-expresa como "cambiar de clase" (convergencia §2.1), nunca un salto silencioso.

### 1.4 El unsat core de Z3 como evidencia explicable ("QUÉ restricción falla")

El diferenciador frente a un `fail` opaco: no basta decir "el candidato es infactible", queremos **cuál** conjunto de reglas viola. Dos mecanismos de Z3:

- **Model (contraejemplo):** al comprobar que la negación de una propiedad es `sat`, Z3 devuelve la asignación concreta que la viola — legible por humano, ya cubierto por `counterexample`.
- **Unsat core:** se asertan las reglas con **tracker nombrado** (`assert_and_track`, o _assumptions_ nombradas). Al resultar `unsat`, `unsat_core()` devuelve el **subconjunto de reglas nombradas que están en conflicto**. Para CHIMERA: para explicar por qué un candidato viola el dominio, se codifica _"el candidato está fijo"_ + cada regla del dominio como aserción rastreada; el unsat core = exactamente las reglas que el candidato rompe → `["constraint:power_balance", "constraint:connectivity"]`. El Studio pinta esos nombres, no un "fail" pelado. Eso es evidencia **explicable**: QUÉ falla, no solo QUE falla.

Limitación documentada: el core de Z3 es un subconjunto insatisfacible **pequeño**, no garantizado mínimo-mínimo. Si se necesita minimalidad estricta (menor conjunto), se itera reduciendo (alcance diferido). Para el pitch/demo, "pequeño y correcto" alcanza.

### 1.5 Forma del `evidence`

Camino muestreado (backend `python`) → predicate `property_rule` (la unión real de `evidence.py`):

```python
{"method": "property_rule",
 "properties": [{"name": "cut_cost_nonnegative", "passed": true, "examples_run": 200, "counterexample": null}],
 "seed": 42, "generator_version": "hypothesis-6.x",
 "backend": "python", "rule_set_id": "islanding-rules@0.1.0", "rule_digest": "<sha256>"}
```

Camino formal (backend `z3`):

```python
{"method": "property_rule",       # ver §4: el arm `property_rule` ya carga los campos del backend formal
 "properties": [{"name": "power_balance", "passed": false, "counterexample": {"island": 2, "imbalance": 3.1}}],
 "backend": "z3", "status": "sat",
 "unsat_core": [],                # poblado cuando status=="unsat" sobre reglas nombradas
 "rule_set_id": "islanding-rules@0.1.0", "rule_digest": "<sha256>"}
```

Nota de forma ([S3] 2026-07-30): el congelado real es `PropertyRulePredicate` con `backend`/`status`/`unsat_core` tipados (`engine/src/blite/verification/evidence.py:120-130`); `rule_set_id`/`rule_digest` son campos aditivos propuestos por este diseño para el ítem C3/M3 (el `RuleSet` versionado con digest de #103). Cuando la prueba formal alcanza AL4, el predicate es `formal_exact` con `proof` (§4-iii). Los campos de correlación van **PLANOS** en la `Attestation` (`run_id`, `step_id?`, `claim_digest` — `engine/src/blite/verification/attestation.py:67-89`; el `subject` anidado no existe). `rule_digest = SHA-256` sobre los **bytes exactos del artefacto de reglas** distribuido en `knowledge/islanding/` — Regla 1 del anexo (artefacto versionado, como `policy_digest`), **no** `C()`: comentarios y formato del archivo son parte de lo distribuido.

---

## 2 · Decisión

| Referencia                                                | Decisión                                                               | Racional                                                                                                    |
| --------------------------------------------------------- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Backend Python + Hypothesis (`property_rule` AL2, v1)     | **integrar** (Hypothesis MPL-2.0, nota 03)                             | El backend de la v1; determinista con seed                                                                  |
| **Z3 (SMT)** como backend formal (ruta `formal_exact`)    | **inspirar hoy / adapter del ítem C3-M3** (acá se especifica la FORMA) | MIT; el if-then/SMT no es el hot-path del reto (nota 04 §2). La forma del puerto hace el upgrade un drop-in |
| Regla-como-dato (`knowledge/islanding/`)                  | **portar** (corrección #4)                                             | El verifier es genérico; el umbral eléctrico es conocimiento versionado, no código                          |
| `assert_and_track` + `unsat_core()` para explicabilidad   | **portar** (patrón de uso de Z3)                                       | La explicabilidad ("QUÉ falla") es el punto — evidencia, no adorno                                          |
| Degradación `formal_exact`→`property_rule` ante `unknown` | **portar** (patrón propio)                                             | Honestidad de nota 03 §1.4 aplicada al backend formal                                                       |
| Casbin / Cedar / OPA como motor de reglas                 | **descartar acá**                                                      | Son policy-as-code de authz/gobernanza (ficha A2/nota 05), no verificación de resultados de cómputo         |

## 3 · Licencias

| Pieza             | Licencia    | Verificado                      | Implicación                                              |
| ----------------- | ----------- | ------------------------------- | -------------------------------------------------------- |
| Z3 (v4.16.0)      | **MIT**     | ✅ nota 04 (en vivo 2026-07-02) | Adapter del ítem C3/M3; sin restricción                  |
| Hypothesis (v6.x) | **MPL-2.0** | ✅ nota 03 (en vivo)            | Copyleft de archivo: OK como dep sin vendorizar/parchear |

## 4 · Impacto en contrato

**Diseño detrás del puerto (sin acción de freeze):** el `RuleVerifier` es un adapter del `Verifier` congelado; el `RuleBackend` es un puerto **interno** del adapter (como `ExecutionHarness` en nota 12), no un contrato del engine. El engine no conoce Z3 (ADR-008).

**Coordinación con el freeze — RESUELTA ([S3] 2026-07-30; lo que esta nota pedía ya es contrato y código):**

1. **La unión `evidence` ya tiene el arm del backend formal.** La unión vigente es `ClassPredicate`, discriminada por `method ∈ {formal_exact, execution, ground_truth, property_rule, consensus_replication, human_expert}` (`engine/src/blite/verification/evidence.py:200-208`) — la unión de métodos que esta nota citaba (`differential`/`known_truth`/`property`/…) murió con la escalera. La opción (a) que esta nota prefería GANÓ y es código: el arm `property_rule` carga `backend`, `status` (`sat|unsat|unknown`) y `unsat_core` como campos tipados (`evidence.py:128-130`; freeze §4, refinamientos aditivos).
2. **Clase/AL variables por `Attestation` del mismo adapter** (`formal_exact` si el backend formal prueba; `property_rule` AL2 si Hypothesis/degradación). Soportado por el freeze §4 — la `verifier_class` y el `level` son por-attestation, con techos validados por tipo (`attestation.py:55-62,101-111`); conviene un test de que un solo adapter emite ambas clases.
3. **`rule_digest`** entra como Regla 1 del anexo (artefacto), consistente con `policy_digest`; sin cambio de esquema (vive en la evidencia del ítem C3/M3, junto al `RuleSet` versionado de #103).

## 5 · Reconciliación contra la base lógica

- **PR2 / INV-2 (el verificador nunca es un modelo):** INTACTO — Z3 es un prover determinista, no un modelo; `formal_exact` legítimo. El adapter vive en `verification/`, no importa `serving`.
- **Nota 03 §1.4 (tri-estado):** REALIZADO por partida doble — `unknown` de Z3 → `inconclusive`/degradación a `property_rule`; "no encontré contraejemplo" (`property_rule`, AL2) jamás se disfraza de "no existe" (`formal_exact`).
- **Inv-E:** INTACTO — un `pass` de regla no autoriza egreso; informa.
- **Nota 04 §4 item 3 (reglas como datos):** REALIZADO — el adapter recibe `constraints`; el `rule_digest` ancla la versión de las reglas usadas, haciendo la verificación reproducible.
- **Ninguna referencia contradice la base lógica.** El hallazgo original (la unión `evidence` no preveía un backend SMT) era dato sobre la semilla del contrato, no sobre la lógica — y se resolvió aditivamente como esta nota pedía: los campos `backend`/`status`/`unsat_core` viven hoy en `PropertyRulePredicate` sin tocar invariantes.
