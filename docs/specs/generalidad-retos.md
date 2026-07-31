# Spec de costura — Generalidad: los retos 2/3 EN la plataforma (costura B↔A↔confianza)

**Gobernada por:** freeze **§4** (`Verifier`/`Attestation`, clases y techos; C-14 vía #106) +
**§6** (Policy 0.2.0, matriz por criticidad, portadores SF-P1-2) + **§15.3** (regla de
identidad de corpus) + **§14** (`●ClaimEmitted` con portadores) ·
[`../perfil-stem-v1-0.md`](../perfil-stem-v1-0.md) §1 (registro de claim_types) y §4.7
(certificación amortizada) — CONGELADO: esta spec lo extiende por ANEXO aditivo (abajo),
jamás lo edita · **Insumo:** `knowledge/quantum/02-recetario-formulacion-por-reto.md` §2
(receta C2; su §3 de química está SUPERSEDIDA) · `knowledge/quantum/11-receta-c3-tfim-trotter.md`
(STUB C3 — lo completa G1) · `docs/mejorado/03-research.md` R1.
**Costura:** B↔A↔confianza · **Estado:** SPEC (Fase 0 Mejorado, 2026-07-31, decisión #125) ·
**Consumen:** G1–G4 (y G5/G7 indirectos).

> La llave 1 del cierre de fase (criterio #101) exige que un reto NO-MaxCut corra punta a
> punta: misión → plan → capabilities → verificación → certificado → informe. Esta spec fija
> los contratos que eso necesita — claim_types, predicates extendidos, verificadores nuevos,
> identidad de corpus, policies y dispatch — sin implementar ninguno (Fase 1 = sesión G).
> ADR-029 intacto: las capabilities son SIEMPRE genéricas (la denylist
> `tests/invariants/scenario_denylist.txt` bloquea vocabulario de escenario en manifests);
> el conocimiento de reto vive en `knowledge/` y en los DATOS.

## Contrato

**1 · claim_types por reto — reuso del registro STEM (perfil §1), no invención.**

| Reto | Conclusión (C3 del run)                                                 | `claim_type`        | Techo estructural | Verificadores (punto 3)                                |
| ---- | ----------------------------------------------------------------------- | ------------------- | ----------------- | ------------------------------------------------------ |
| C3   | series ⟨Zᵢ⟩/⟨ZᵢZᵢ₊₁⟩ del circuito Trotter dentro de ≤5% de la ED        | `simulation_result` | AL3 (perfil §1)   | `ExactDiagonalizationVerifier` + `GroundTruthVerifier` |
| C2   | desempeño del clasificador kernel-cuántico frente al baseline (McNemar) | `statistical`       | AL3 (perfil §1)   | `GroundTruthVerifier` + `PropertyRuleVerifier`         |

Los claims intermedios de ambos retos siguen el vocabulario runtime (`intermediate` ⇒ C1 por
`computed_criticality`, freeze §6). El lenguaje de conclusión de C2 es el de la nota
quantum/04 §"McNemar": «competitivo», jamás «supera» sin significancia. `ClaimEmittedPayload`
(`blite.verification.claim`) ya porta `claim_type` como `str` — cero cambio de modelo;
el enforcement del registro sigue siendo doc-level (tensión SF-P1-2 registrada en el freeze
§6 — NO se resuelve aquí).

**2 · C-14 — extensión aditiva de `FormalExactPredicate` (detalle de #106, forma #125).**
`Differential` (`blite.verification.evidence`) gana:

- el literal **`EXACT_DIAGONALIZATION`** en `status` (aditivo a la unión CpSat — un status
  que NO es de proceso: mapea a verdict por comparación, como `OPTIMAL`);
- **`relative_tolerance: float | None = None`** — el criterio oficial C3 (≤5% ⇒ `0.05`);
  `None` para CP-SAT (que sigue exacto, `abs_tol: 0`). La tolerancia **entra al
  `verifier_params_digest`** del verificador que la usa (mismo mecanismo que
  `max_deterministic_time` en `exact_solver.py::_params`) — dos corridas con tolerancia
  distinta jamás comparten digest de params.

Cero techos rotos (decisión #103): `formal_exact` sin `proof` sigue topando AL3; el AL4 de
C3 solo llega con checker independiente (G6, `tfim_freefermion` — patrón del reto 1).

**3 · Verificadores nuevos — homes y techos (predicates YA congelados sin adapter).**

| Verificador                    | Módulo propuesto                           | `verifier_class` | `anchor_kind` | Predicate (ya existe)   |
| ------------------------------ | ------------------------------------------ | ---------------- | ------------- | ----------------------- |
| `ExactDiagonalizationVerifier` | `blite.verification.exact_diagonalization` | `formal_exact`   | `solver`      | `FormalExactPredicate`  |
| `GroundTruthVerifier`          | `blite.verification.ground_truth`          | `ground_truth`   | `dataset`     | `GroundTruthPredicate`  |
| `PropertyRuleVerifier`         | `blite.verification.property_rule`         | `property_rule`  | `rule`        | `PropertyRulePredicate` |

- ED recomputa VIVO (ancla `solver`, mismo patrón que CP-SAT); `GroundTruthVerifier`
  contrasta contra series/casos CONGELADOS del corpus (ancla `dataset`, `curated_internal`
  ⇒ techo AL3). **Dos patas C3 por construcción**: recompute ED + series congeladas son
  grupos de independencia DISTINTOS (`independence_group` propio cada una — la regla C-6 de
  «islas de una corrida comparten grupo» no aplica: son métodos distintos, no islas).
- Implementaciones proponente/verificador INDEPENDIENTES (espejo fail-loud del research R1:
  error 0.0000 con `dt` grande = sospecha de código compartido — el control negativo es
  parte del contrato de G1, no opcional).
- `PropertyRuleVerifier` v1 corre los checks de `PropertyCheck`/`MetamorphicRelation` ya
  congelados; el backend Z3/`RuleSet` con digest es el ítem C3/M3 (#103, sesión C-2) — esta
  spec NO lo duplica.

**4 · Identidad de corpus GENERALIZADA + folds sellados.**

- La regla de identidad islanding (§1.6 / freeze §15.3) se generaliza:
  **`dataset_id = "<corpus>/<instancia>[-<convencion>]@v<n>"`**, digest **EMBEBIDO**
  self-consistente (SHA-256 del JSON canónico sin el campo `digest` — mismo algoritmo,
  misma doctrina «se reporta, no se sobreescribe»). C3 usa el prefijo `tfim-corpus/`,
  C2 `tabular-corpus/`; los ids y digests CONCRETOS los estampan G1/G2 al congelar los
  JSON (tabla nueva en el freeze §15.3 con su ceremonia — jamás esta spec).
- **Corpus C3**: un JSON por punto de la malla (N ∈ {6,8,12} × h/J ∈ {0.5,1,2}) con las
  series de ED de referencia (⟨Zᵢ⟩, ⟨ZᵢZᵢ₊₁⟩), los parámetros que las definen y el método
  declarado — la forma exacta interna la fija G1 al completar la nota 11 (frontera).
- **Corpus C2**: CSV CC0 sellado con digest + caveats de proveniencia DECLARADOS en el
  registro (research R1: proveniencia indocumentada ⇒ `curated_internal`, techo AL3).
  **Folds sellados por compromiso previo**: la asignación de folds se canonicaliza
  (`blite.certificate.canonical`, la única puerta) y su **`folds_digest`** se emite ANTES
  de cualquier `fit` (en el plan / claim scope) — el patrón anti-fuga de Dwork citado por
  el research; todo `fit` ocurre dentro del fold de train y el pipeline ajustado es parte
  de la evidencia (KB2-02 §2).

**5 · Policies por reto — plantillas (G4).**
Archivos nuevos versionados en `distributions/chimera/policies/` (mismo esquema
`VerificationPolicy` 0.2.0; el YAML es artefacto — `policy_digest` = bytes exactos):

- **Reto 2**: regla `{claim_type: statistical}` ⇒ `criticality: C3` (conclusión),
  `min_level: AL3`, `required_legs: 2`, `required_anchors: [dataset, rule]` — el techo
  GROUND_TRUTH AL3 del plan; sin ancla ex ante para generalización futura ⇒ certificación
  amortizada (perfil §4.7), jamás verificación por-resultado.
- **Reto 3**: regla `{claim_type: simulation_result}` ⇒ `criticality: C3`,
  `min_level: AL3`, `required_legs: 2`, `required_anchors: [solver, dataset]` (recompute
  ED + series congeladas).
- Las reglas `solution`/`intermediate` existentes NO se tocan (aditivo puro; una policy
  por distribución sigue siendo la forma — las plantillas por reto se COMPONEN en la
  policy de la distro que las use, decisión de G4 con registro).

**6 · Dispatch por clase (G3) — el registro que mata el Reto-1-only.**
`resolve_verifiers(*, claim_type, instance_id)` (`chimera_api.instance_verifiers`) CONSERVA
su firma y su fail-closed (resolución vacía ⇒ 400); lo que cambia es la fuente: el hardcode
(`_OPTIMALITY_CLAIM_TYPES = {"solution"}` + `ELECTRICAL_DATA` de un slug) se reemplaza por
un **registro declarativo por `claim_type`** (`CLAIM_TYPE_VERIFIERS`) donde cada entrada
declara constructor de verificadores + descriptores de ancla, y la resolución de instancia
(qué corpus, qué datos eléctricos/series) es DATO del registro — la misión resuelve por
CLASE de problema, no por slug del corpus de islanding. Reto 1 se re-expresa como la
primera entrada del registro (compat total, mismos ids `verifier:cpsat-differential`/
`verifier:pandapower-islanding`).

**7 · Anexo aditivo del perfil STEM (v1.0 → v1.1, perfil §6: versión menor).**
El perfil (CONGELADO) no se edita — ESTA sección es el anexo (mismo patrón que
`capability-ingesta.md` declaró): la instanciación Quantathon se EXTIENDE de «solo reto 1»
(perfil §5) a los tres retos con las filas del punto 1; ningún techo baja, ningún schema
del kernel cambia, `statistical_procedure` (ya previsto en perfil §1) es el vehículo del
McNemar de C2. Cualquier claim_type genuinamente nuevo que un reto futuro exija = fila
nueva AQUÍ con registro en el ledger.

## Eventos / payloads nuevos

Ninguno: los claims de los retos viajan por `●ClaimEmitted` (portadores ya congelados —
`claim_type`, `is_conclusion`, flags); los resultados por `verification.completed`; las
métricas por `run.metrics.recorded` (S-D §9). La generalidad entra como DATOS/capabilities,
jamás como wire nuevo.

## Interfaces con otros dominios

| Interfaz                                                                           | Dominio            | Estado                                                    |
| ---------------------------------------------------------------------------------- | ------------------ | --------------------------------------------------------- |
| `Differential` + `EXACT_DIAGONALIZATION`/`relative_tolerance`                      | confianza (engine) | SPEC — seed xfail; implementa G1 (C-14)                   |
| Verificadores `exact_diagonalization`/`ground_truth`/`property_rule`               | confianza (engine) | SPEC — seeds xfail; implementa G1/G2                      |
| Registro `CLAIM_TYPE_VERIFIERS` en `instance_verifiers`                            | E (api)            | SPEC — seed xfail; implementa G3                          |
| Plantillas de policy por reto                                                      | distribución       | SPEC — forma fijada; los YAML los escribe G4 con registro |
| Corpus C2/C3 (identidad + digests)                                                 | knowledge/datos    | SPEC — ids/digests los estampa G1/G2 con ceremonia §15.3  |
| Capabilities `trotter_evolve`/`exact_evolve`/`fidelity_kernel`/`svm_precomputed`/… | B (capabilities)   | Fuera de esta spec (manifests = S-E v2; ciencia = KB)     |

## Fronteras (qué NO decide esta spec)

- **La matemática de C3** (Hamiltoniano, descomposición de Trotter, cotas de error, forma
  interna de las series) — la nota 11 la completa G1; esta spec solo fija identidad,
  claim_type, verificadores y patas.
- **La ciencia de C2** (pipeline de features, presupuesto de shots, reparación PSD) — KB2-02
  §2 + research R1; aquí solo folds sellados, claim_type y anclas.
- **El backend Z3/`RuleSet`** — decisión #103, sesión C-2 (`trust/11` como spec).
- **Los manifests v2 de las capabilities nuevas** — S-E (`manifest-v2-sdk.md`).
- **Los ids/digests concretos de corpus** — G1/G2 con la ceremonia §15.3.

## Tests de contrato (fixtures de costura)

Generador NUEVO `scripts/gen-contract-fixtures-generalidad.py` (modelos que YA existen):

- `tests/fixtures/contract/generalidad/claim-c3-simulation-result.json` — desde
  `ClaimEmittedPayload` (`claim_type: "simulation_result"`, `is_conclusion: true`, con
  `sub_run_id`/`sub_run_provenance_hash` poblados — el patrón §13).
- `.../claim-c2-statistical.json` — ídem con `claim_type: "statistical"`.
- `.../predicate-ground-truth.json` — desde `GroundTruthPredicate` (dataset_id con la
  identidad generalizada del punto 4, `tolerance: 0.05`).
- `.../predicate-property-rule.json` — desde `PropertyRulePredicate` (un `PropertyCheck`
  PSD + una `MetamorphicRelation` de simetría — los checks canónicos de C2).

Espejo byte-idéntico en `apps/studio/src/fixtures/contract/generalidad/` verificado por el
test Python (mismo precedente que ingesta/informe: sin consumidor Zod todavía — el Studio
gana schema cuando una vista los consuma). Anti-drift:
`tests/unit/contract/test_generalidad_contract_fixtures.py` (3 aserciones estándar).

## Tests semilla

- `tests/seeds/test_seed_generalidad_retos.py` — **SEED, xfail(strict=False)**:
  `Differential` acepta `EXACT_DIAGONALIZATION` + `relative_tolerance`; los 3 módulos de
  verificadores importan con su `verifier_class`/`anchor_kind` correctos;
  `CLAIM_TYPE_VERIFIERS` registra `simulation_result` y `statistical`. Verde pieza por
  pieza con G1/G2/G3.
