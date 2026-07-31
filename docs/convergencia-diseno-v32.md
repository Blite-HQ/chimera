# Convergencia — diseño vigente ↔ spec de confianza v3.2 (cal-2.4)

> **Estado: VIGENTE — veredicto EJECUTADO en el cierre S-E (2026-07-18).** Las acciones de §6
> quedaron aplicadas: freeze reescrito al vocabulario v3.2 con §12–§15 nuevos y CONGELADO; el
> set nuevo importado sanitizado a `docs/` ([spec v3.2](spec-confianza-v3-2.md),
> [Perfil STEM](perfil-stem-v1-0.md), [contratos v2](especificacion-contratos-v2.md) y
> [esquema v2](esquema-datos-v2.md) como SEMILLA; v1 supersedidas); marcas aplicadas en
> `knowledge/` (trust/03 supersedida, ajustes quantum/04 §4, execution/01/07, trust/18).
> Este documento se conserva como **mapa de traducción** (§2) y registro de resolución de
> conflictos (§3). Comparaba el set nuevo (entonces en el working set externo) contra lo
> vigente: `docs/invariants.md` (congelado), `docs/contract-freeze.md` (entonces DRAFT §1–§11,
> hoy CONGELADO) y las notas de `knowledge/`.
> Convención de veredictos: **CONVERGE** (sin acción) · **SUPERSEDE** (el nuevo reemplaza, con
> mapa) · **GANA-FREEZE** (lo vigente gana; el doc nuevo no vio esa investigación) ·
> **ADOPTAR** (pieza nueva sin contraparte) · **AJUSTAR** (nota puntual a corregir).
> **[S3 2026-07-30]** Función residual confirmada por el censo S1: registro ejecutado, sin
> acciones pendientes; su §2.1 sigue vivo como EL mapa de traducción escalera→clases
> (`rung`→clase de verificador + AL), citado por la decisión #103.

---

## 0 · El veredicto en una línea

**Convergen.** El diseño nuevo se construyó SOBRE la base lógica congelada (control de
constitucionalidad incluido) y su apéndice de reconciliación ya mapea el vocabulario viejo al
nuevo. No hay contradicción constitucional. Los conflictos reales son 4, todos de frontera entre
el set nuevo (que no vio la investigación del plano de ejecución) y el freeze (que no vio la
spec v3.2) — se resuelven por unión, no por rediseño.

## 1 · Convergencias exactas (sin acción)

| Tema                                 | Vigente                                    | Nuevo                                                              | Nota                                                                          |
| ------------------------------------ | ------------------------------------------ | ------------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| Verdict tri-estado                   | freeze §4                                  | `pass·fail·inconclusive(reason)`                                   | idéntico; el nuevo agrega razones tipadas (adoptar la lista completa)         |
| Guardrail ≠ Attestation              | INV-3, trust/04/16                         | S1 (tipos disjuntos)                                               | convergencia exacta — ahora imposibilidad de tipo                             |
| Anclas no-modelo                     | INV-2, ADR-027, `AnchorKind` sin `"model"` | S7 (constitucionalizado, D9/D18)                                   | el hallazgo estrella: dos caminos independientes llegaron al mismo invariante |
| Event sourcing append-only           | freeze §2, trust/01                        | esquema v2 §1 + EventLog hash-first                                | ver conflicto C3 por los 3 endurecimientos                                    |
| Nivel agregado = mínimo del camino   | trust/03                                   | cal-2.2 Paso 4 (+ derivaciones, socavamiento)                      | conservado y endurecido                                                       |
| Certificado in-toto + DSSE + Ed25519 | trust/02, freeze §7                        | Attestation = in-toto Statement + DSSE; Certificate/Bundle         | trust/02 ya había elegido los mismos formatos                                 |
| Chimera = distribución               | ADR-029, `distributions/`                  | Perfil STEM v1.0 (4 estratos)                                      | el perfil ES el DistributionManifest madurado; "solo eleva, jamás rebaja"     |
| Verificación adaptativa              | trust/05 `VerificationPolicy`              | Policy + criticidad C0–C3 + VerificationPlan                       | la heurística se volvió teorema (PR2/PR4 → pisos)                             |
| Identidad: intersección de permisos  | trust/08                                   | `InvocationContext.invocationChain` + `effectivePermissions` (SO1) | mismo mecanismo; el nuevo lo tipa en el contrato                              |
| params del verificador como digest   | trust/10 `params_digest`                   | `verifier_params_digest` (binding a 4 digests, L3)                 | la idea de trust/10 ahora es norma del kernel                                 |

## 2 · Supersesiones (el nuevo reemplaza; mapa de traducción)

### 2.1 Escalera 1–7 (`rung`) → **clases decisorias + AL0–AL4 + criticidad C0–C3**

La escalera se desdobla en tres ejes: la **clase** dice el método, el **AL** dice la fuerza
(con techos), la **criticidad** dice cuánta fuerza se exige. Mapa para nuestro material:

| Vigente (escalón)                                   | Nuevo (clase → techo)                                                      | Impacto en el repo                                                                                                                                                                                     |
| --------------------------------------------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1 · solver exacto (trust/10)                        | FORMAL_EXACT → **AL4 con checker independiente**, AL3 sin él               | **la doble ancla del corpus (CP-SAT + brute force) es exactamente el habilitador de AL4** — el corpus de `islanding/` ya cumple el requisito sin saberlo                                               |
| 2 · ejecución (trust/12)                            | EXECUTION → AL3 (reproducer obligatorio)                                   | el `ExecutionHarness` de trust/12 gana el requisito de reproducer                                                                                                                                      |
| 3 · corpus/verdad conocida (trust/17, islanding/01) | GROUND_TRUTH → AL3 (tope del ancla: corpus = `curated_internal` ⇒ máx AL3) | corpus necesita metadata de `Anchor` (authority_basis, digest — el digest ya existe)                                                                                                                   |
| 4 · property/regla (trust/11)                       | PROPERTY_RULE → AL2                                                        | la ruta de upgrade 4→1 de trust/11 se re-expresa como "cambiar de clase"                                                                                                                               |
| 5 · consenso                                        | CONSENSUS_REPLICATION → AL2 **solo procesos no-modelo** (seeds pinned)     | **AJUSTE a quantum/04 §4**: el consenso de muestreo QAOA con seeds pinned SÍ es decisorio (AL2) bajo la nueva spec — es proceso no-modelo; lo que sigue siendo Signal es la concordancia entre modelos |
| 6–7 · humano/formal                                 | HUMAN_EXPERT → AL3 · FORMAL_EXACT con proof → AL4                          | sin material vigente afectado                                                                                                                                                                          |

Archivos a actualizar en el barrido del freeze: `contract-freeze.md` §4 (`rung: int` → `verifier_class` +
niveles calculados), trust/03 (marcar SUPERSEDIDA por la spec v3.2 con este mapa), trust/10/11/12
(re-etiquetar clase/techo — el diseño interno de los adapters NO cambia), quantum/04 y
islanding/README (vocabulario), trust/18 + Studio (badges: escalón → clase+AL).

### 2.2 `TrustCertificate` v0 → **Certificate + Bundle + Receipt**

Crece: + `deliverables[{artifact_ref, digest}]` (anti-TOCTOU), + `conclusions[]` por claim con
disposición, + `coverage_stats`, + `VALID_AS_OF`/StatusList, + perfiles de audiencia, +
`calculus_version`. Para el mes: **Certificate + Bundle mínimo** (el CLI verificador es compuerta
de implementación); Receipt/Merkle/RFC 3161/StatusList = Fase 2 declarada. freeze §7 se
reescribe con esta forma.

### 2.3 `evidence` por método (freeze §4/§11) → **Evidence content-addressed + predicates por clase**

Los campos aditivos del §11 se re-ubican así: `seeds.*` y `circuit_digest` → schema del claim
`simulation_result` del Perfil STEM (lado proponente); `approximation_ratio`/`se_estimado`/`exact`
→ extensión de predicate de la attestation (lado verificador); `evidence` deja de ser unión
embebida y pasa a refs content-addressed (`Artifact`, ver §3-ADOPTAR).

## 3 · Conflictos reales y su resolución (decisiones tomadas — ratificación final por dueño)

**C1 · `CapabilityManifest.protocol`** — la Especificación v2 lo conserva; el freeze §1 lo
eliminó (ADR-013: el protocolo es del adapter) y agregó `interaction` + `execution_profile`
(validados por execution/06/09). **GANA-FREEZE:** manifest v2 sin `protocol`, con `interaction`
y `execution_profile`; corregir contratos v2 y la tabla `capabilities` del esquema v2 al importar.
La spec v2 se escribió sin ver la investigación del plano de ejecución — es drift de sesión
paralela, no desacuerdo de fondo.

**C2 · Pipeline del gateway: 7 vs 8 etapas** — la spec v2 trae `identity → authorization →
guardrails → provenance:pre → mediation → verification → provenance:post → egress`; execution/01
tenía 7 con una etapa `policy`. **Resolución por unión:** se adoptan las 8 etapas (provenance
pre/post explícitas — PR1 lo exige), y la etapa `policy` de execution/01 se disuelve: la Policy
se fija por digest al crear el case (`PolicyPinned`, R-Pol1) y la etapa `verification` la lee —
no es una etapa por invocación. Egress gobernado SOLO por authorization (Inv-E) — ambos diseños
ya coincidían.

**C3 · Esquema `events`** — la v2 mantiene reglas silenciosas `DO INSTEAD NOTHING` y no trae
`global_seq`. **GANA-FREEZE §2** (trust/01): REVOKE + trigger que lanza excepción (append-only
que falla fuerte), `+ global_seq IDENTITY` (cursor SSE), semántica `expected_seq`. El esquema v2
aporta lo demás (ver ADOPTAR).

**C4 · Vocabulario de eventos** — la v2 (Fase 1 mínima) trae `tool.invoked`/`verification.completed`;
el freeze §3 + execution/07 traen `run.*`/`run.step.*`/`capability.job.*` (más rico, validado).
**GANA-FREEZE con mapeo:** `tool.invoked` ≡ el evento de provenance:pre del job
(`capability.job.submitted`); `verification.completed` se conserva tal cual. El catálogo de
eventos ● de la capa de confianza (ClaimEmitted, PlanCreated, PolicyPinned, AttestationRecorded,
CaseClosed, CertificateIssued…) **se adopta** como extensión del vocabulario.

## 4 · Piezas nuevas a ADOPTAR (sin contraparte vigente)

1. **`Artifact` + `ContentStore`** (O3/SO2: content-addressed, particionado por dominio) — puerto
   y tabla nuevos; sustrato de Evidence y deliverables. Entra al freeze como contrato nuevo.
2. **`Run` jerárquico** (`parent_run_id`; case/certificado cuelgan del run raíz — D5) + **pinning
   por digest** (`agent_definition_digest`, `workflow_definition_digest`, `policy_digest`).
   **AJUSTE a execution/07:** streams por run se mantienen; los sub-runs aportan claims al raíz.
3. **Claims como digests en Fase 1** — la propia Especificación v2 NO trae entidad `Claim` ni
   tabla `claims`: en Fase 1 el claim existe como digest en attestations y conclusions del
   certificado. El grafo de claims/derivaciones completo es Fase 2. **Esto acota el scope del
   mes** — adoptar tal cual, con el claim `derivation` de la demo emitido como digest + attestation.
4. **Tablas nuevas del esquema v2:** `domains`, `channels`, `identities`, `artifacts`,
   `runs_projection` (con parent + pinning), `attestations` (forma nueva), `trust_certificates`.
5. **`ScopeExpr` decidible** + razones tipadas de `inconclusive` + flags `world/irreversible/
affects_third_party` con pisos de criticidad (PR2/PR4).
6. **Perfil STEM v1.0 como contenido de `distributions/chimera/`** — el DistributionManifest
   madurado: claim_types, curación por `verifier_params_digest`, plantillas de Policy, doctrina
   §4, instanciación Quantathon §5.
7. **`ModelServer` con `local: boolean` (D19)** — compatible con execution/09 (`ModelPort` en
   serving + adapter en protocols): unificar nombres en el freeze; la forma de la v2 es el puerto,
   la ubicación de la red la fijó execution/09.

## 5 · Qué NO cambia

- `docs/invariants.md` y la base lógica formal — el set nuevo las cita como su constitución y
  agrega el **control de constitucionalidad** (adoptarlo como práctica del freeze en adelante).
- Los diseños internos de los adapters (trust/10/11/12), el registry (execution/04), el serving
  (execution/06), la cola/infra (infra/01–03), el corpus (islanding/01 — solo gana metadata de
  `Anchor`) y el SSE (trust/07).
- La regla de importación: los docs nuevos de contratos/esquema son **SEMILLA v2 en TS/SQL** — la
  verdad ejecutable sigue siendo la traducción a Python/Pydantic en el freeze (igual que la
  semilla v1).

## 6 · Acciones que este veredicto dispara (van al barrido del freeze, S-E)

1. Reescribir `contract-freeze.md` §4/§7/§11 al vocabulario nuevo (clase+AL+criticidad,
   Certificate/Bundle, predicates) y agregar §12 (`Artifact`/`ContentStore`), §13 (Run jerárquico
   - pinning) y §14 (catálogo de eventos ●).
2. Importar sanitizados a `docs/` (sin la marca; "el Engine"): spec v3.2, Perfil STEM v1.0,
   contratos v2 (SEMILLA), esquema v2 (SEMILLA); actualizar el índice de autoridad — la v1 de
   contratos/esquema pasa a SUPERSEDIDA. Los docs de visión/estrategia NO se importan (internos).
3. Marcar trust/03 como supersedida (con el mapa §2.1) y aplicar los AJUSTES puntuales
   (quantum/04 §4 consenso; execution/07 jerarquía; execution/01 etapa policy; trust/18 badges).
4. Las compuertas de implementación de la spec (property tests del cálculo, demo de falla
   sembrada, CLI verificador del bundle) entran al plan de seeds de specs/tests como piezas de
   primera clase — son la conversión de papel a prueba.
