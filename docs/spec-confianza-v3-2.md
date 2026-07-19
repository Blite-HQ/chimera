# Especificación de la Capa de Confianza — el Engine

## Versión 3.2 · documento normativo del kernel · calculus_version: `cal-2.4`

> **Estado: CONGELADO (importada 2026-07-18, barrido S-E).** Fuente única de verdad del
> vocabulario de la capa de confianza; `contract-freeze.md` la referencia como norma. Importada
> del working set externo con dos normalizaciones: (1) sanitización de marca (el motor se
> nombra "el Engine"); (2) el bloque **"Regla de aplicabilidad y los dos modos"** de §1,
> agregado en el cierre S-E por el P0-5 del stress test S-D (doctrina de despliegue — cero
> cambios al cálculo; `cal-2.4` intacto). Cambios al kernel exigen versión mayor +
> re-ejecución del análisis estructural + control de constitucionalidad (§2).
>
> **Estado original.** Fuente única de verdad de la capa de confianza del Engine. Consolida la v2.1 y el delta aprobado del stress test v3 bajo la reorganización de la auditoría de scope/complejidad: **cero cambios semánticos adicionales** — solo el delta R3 y reestructura. La **v3.1** incorpora el delta de reconciliación con la **Base Lógica Formal** (hallazgos B1–B7 → S7, restricción de consenso, Inv-E en el router, flags PR2/PR4, renombre SC): `cal-2.3`. La **v3.2** pliega el delta del stress test v4 (semántica de cuantificación, socavamiento, cobertura de scope en derivaciones, conformidad de reutilización, frescura de gates, raíces de firma, revocación granular de lotes): `cal-2.4`. Cuatro estratos: **Kernel** (este documento) · **Capabilities** (módulos empaquetados del catálogo del Engine) · **Distribución/Perfil** (framing por dominio; el Perfil STEM v1.0 de Chimera es el primero) · **Shell** (operación, anexo no normativo). Cambios al kernel exigen versión mayor + re-ejecución del análisis estructural. Decisiones vigentes: D1–D5 (§12).

---

## §1 · Misión y Non-Goals

**Misión:** dado un run que produce afirmaciones, establecer con qué fuerza cada afirmación fue verificada contra anclas no-IA, agregar esa fuerza sin mentir, y dejar un registro que un tercero pueda comprobar sin confiarnos.

**Los cuatro estratos y sus dueños:**

| Estrato             | Naturaleza                                                                        | Dueño                                         |
| ------------------- | --------------------------------------------------------------------------------- | --------------------------------------------- |
| Kernel              | Mecanismo agnóstico (esta spec)                                                   | Engine                                        |
| Capabilities        | Herramientas agnósticas empaquetadas (solvers, motores, sandboxes, verificadores) | Catálogo del Engine (el flywheel las fabrica) |
| Distribución/Perfil | Framing por dominio: curación + configuración + metodología                       | La distribución (Chimera = Perfil STEM)       |
| Shell               | Operación: salud, colas, detectores concretos, UI                                 | Ops de la instancia                           |

**Non-Goals (la cerca — esto NUNCA es kernel):** (1) seguridad de contenido/alignment; (2) identidad/autenticación (se referencia WIMSE/SPIFFE/VC); (3) proveniencia de inferencia (se referencia TEE/lifecycle-attestation); (4) autorización de acciones; (5) reputación/economía de confianza; (6) juicio de verdad última — se verifica _contra anclas declaradas_ (supuesto de carga SC3); (7) workflow/gestión de tareas (Engine); (8) el harness (esta capa provee el paso de verificar; los gates leen sus gap_reports).

**Regla de aplicabilidad y los dos modos (agregado S-E 2026-07-18 — P0-5 del stress test S-D; doctrina de despliegue, no cambio del cálculo):**

- La capa se aplica donde: (1) el costo del error no-detectado es alto; (2) el error es invisible de inmediato **o** un tercero necesita confiar sin creerle al emisor; y (3) **existe un ancla decisoria dentro del presupuesto — si no existe, el sistema lo declara como gap (`no_applicable_anchor`), jamás simula cobertura** (anti-teatro-de-abstención).
- La heterogeneidad de los resultados **no** decide si la capa aplica — decide el **modo**: resultados heterogéneos ⇒ verificación **por-resultado** (el flujo normal de esta spec); tarea uniforme ⇒ **certificación amortizada de la capability**. En C0 la Policy dice "no verifiques": el anti-slop está integrado.
- **Cláusula de cartera (riesgo agregado):** cuando decisiones individualmente baratas suman riesgo material (C0/C1 por unidad, catastrófico en agregado), la Policy puede exigir el modo amortizado sobre la población (eval + muestreo + drift) aunque la regla por-resultado diga "no verifiques". El C0 exime a la unidad, no a la cartera.
- **Patrón nombrado del kernel — "case de certificación de capability" (el modo amortizado):** un case cuyo run raíz es la **evaluación** de una capability/verificador/modelo contra un ancla (corpus `GROUND_TRUTH`, techo AL3; controles negativos obligatorios); sus conclusiones hablan de la capability ("en esta familia/scope, reduce el error X%±Y"), no de un resultado individual; en operación, la vigencia se acompaña de Signals de deriva (shell, §7) y re-certificación programada. Es el mismo `Certificate`/`Bundle` de §3.2 — ninguna entidad nueva; D5 se satisface porque el run de evaluación ES el run raíz del case.

---

## §2 · Las Tres Leyes, el Principio y los Invariantes Estructurales

**L1 · No-amplificación.** La garantía se conserva o se pierde al componer; jamás se crea componiendo. La _selección_ del mejor testigo directo (máx. entre attestations pass que cubren el scope completo del mismo claim) no es composición: cada testigo justifica su base por sí solo.

**L2 · Inmutabilidad monótona.** Nada se borra; nada mejora por omisión; la contradicción jamás produce pass; toda corrección es supersesión con causa registrada.

**L3 · Canonicidad.** Sin forma canónica no hay identidad; sin identidad no hay binding. Todo digest se computa solo sobre formas canónicas (RFC 8785 JCS + Unicode NFC + números normados).

**P1 · Todo lo que porta confianza es un claim.** Derivaciones, formalizaciones e importaciones son objetos verificables del propio sistema, no metadatos de fe.

**Invariantes estructurales (esqueleto de tipos y roles, no derivables de las leyes):**

| S      | Invariante                                                                                                                                                                                                                                                                 |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S1     | `Signal` es tipo disjunto de `Attestation`; el cálculo acepta `Set<Attestation>` por firma de función — lo probabilístico no puede decidir, por imposibilidad de tipo                                                                                                      |
| S2     | Signer ≠ Verifier: identidades y claves separadas                                                                                                                                                                                                                          |
| S3     | AL4 ⇒ objeto de prueba re-validado por checker independiente (mitigación de SC5)                                                                                                                                                                                           |
| S4     | El contenido ingerido jamás escribe claims, criticidad, Policy ni planes (separación instrucción-dato)                                                                                                                                                                     |
| S5     | Semántica temporal honesta: todo vale `VALID_AS_OF(T, checkpoint)`; la vigencia actual exige status online                                                                                                                                                                 |
| S6     | `calculus_version` acompaña todo veredicto y nivel; todo claim termina en exactamente una disposición visible (el certificado trivial —cero claims— es válido)                                                                                                             |
| **S7** | **Anclaje no-modelo (D9/D18 de la Base):** toda clase decisoria establece su veredicto por contraste contra un ancla ¬modelo. La concordancia entre modelos —cualquier número, cualquier familia— es coherencia, no verificación: vive como Signal, jamás como attestation |

**Tabla de corolarios (criterio de admisión para toda regla, presente o futura: debe ser corolario de una ley, invariante de tipo/rol (S-\*), o mitigación declarada de un supuesto de carga (§12) — lo que no encaje en las tres categorías se rechaza; y todo delta pasa además **control de constitucionalidad**: trazabilidad contra la Base Lógica Formal (AX1–AX3, D9–D22, PR1–PR4, Inv-E), re-corrida en cada cambio, no una vez):**

| Ley | Corolarios                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| L1  | AL titular = mín. del camino crítico (antes I5) · topes de ancla (R-A1) · cap de formalización (R-F1) · importación ≤ importado + ciclos prohibidos (R-A2) · composición de scopes al mín. (R-S1) · independencia insuficiente demota (Paso 3) · modificadores solo descienden (D2) · la reutilización hereda, no mejora (D5) · **los perfiles solo pueden elevar exigencias, nunca rebajar mínimos del kernel**                                                 |
| L2  | Log append-only (I7) · conflicto → inconclusive, jamás resuelto por jerarquía (I12/D3) · conflicto se limpia **solo por supersesión con causa**, nunca por dictamen (E5) · fail exige rerun_policy; en verificadores no deterministas, el pass también (I11/E6) · cierre plan↔resultado: toda selección termina en desenlace registrado y el bundle lo prueba (I16) · Policy monotónica ("deny unless proven") y **fijada por digest al crear el case** (R-Pol1) |
| L3  | Binding a 4 digests: claim, binario, **parámetros**, ancla (I8/N4) · álgebra de scope decidible (§3.1) · prohibición de deixis: artefactos solo por digest (E4) · grafo de claims es DAG por invariante (E2) · aristas `premise_of` no disparan derivaciones (E3)                                                                                                                                                                                                |
| P1  | La derivación es un claim en el camino crítico (R-D1) · la formalización es objeto con provenance y cap · las importaciones entran como ancla-certificado · estratificación: los subjects son externos al cómputo de assurance en curso (E9)                                                                                                                                                                                                                     |

---

## §3 · El Kernel: tipos y entidades

### §3.1 Tipos base

**`VerifierClass`** (6 clases decisorias) con techos: FORMAL_EXACT → **AL4** (solo con proof-carrying; sin certificado checkeable, AL3) · EXECUTION → AL3 (reproducer obligatorio) · GROUND_TRUTH → AL3 (sujeto a tope del ancla) · PROPERTY_RULE → AL2 · CONSENSUS_REPLICATION → AL2 (**solo procesos no-modelo**: ejecuciones, mediciones, simulaciones con seeds pinned — S7; patas = clases de independencia; la concordancia entre modelos, de cualquier familia, es Signal) · HUMAN_EXPERT → AL3 (independiente ∧ en especialidad ∧ Policy lo admite; si no, AL2). Lo probabilístico no es clase: es `Detector`/`Signal` (S1).

**`ScopeExpr`** — álgebra **decidible por construcción**: solo intervalos cerrados + enumeraciones + digests + **dimensión temporal estándar** (ausente ⇒ "en el instante de verificación", declarado). Cuatro operaciones normadas y polinomiales: equivalencia (igualdad canónica), subsunción, intersección, partición/cubrimiento. Scope no canonicalizable ⇒ inadmisible como evidencia decisoria.

**Niveles:** AL0–AL4. **Criticidad:** C0–C3 (computada por propagación estructural desde conclusiones + piso de plantilla del perfil + override humano registrado; el contenido jamás la escribe — S4).

**Veredicto:** `pass · fail · inconclusive(reason: timeout · undecidable · ambiguous_formalization · conflict · undermined_premise · no_applicable_anchor · anchor_requires_unauthorized_egress · budget_exhausted)`.

### §3.2 Las nueve entidades

**1 · `Claim`** — {id, digest (canonical_statement+scope), run_ref, emitted_by, claim_type (registro extensible por perfiles: `numeric · comparative · logical · executable · constraint_satisfaction · citation · statistical · existential · procedural · derivation`; cada tipo declara schema, **semántica de cuantificación** (`universal_sobre_scope` · `existencial`) y **techo estructural de AL**), canonical_statement (sin deixis: artefactos por digest), scope (ScopeExpr), **formalization** {method: generated_native · extracted · template; formalizer; assumptions[]; agreement_score∅; review_attestation_ref∅} — `extracted` sin revisión atestada capa a AL2; C3 exige nativa o revisada —, is_conclusion, **flags** {world, irreversible, affects_third_party} (PR2/PR4 de la Base), criticality {computed — incorpora estructura y flags: world ⇒ piso C2; irreversible ∧ affects_third_party ⇒ piso C3 —, floor, override∅, effective}, disposition (`pending · verified · refuted · inconclusive · not_required_declared`), assurance {level, detalle del cálculo}}. **Grafo:** aristas `derives_from · supports · part_of · premise_of`, DAG por invariante, serializa a PROV-O. **Camino crítico:** unión de caminos de dependencia desde cada conclusión hasta sus hojas, **incluyendo el claim `derivation` de cada paso de inferencia del camino** (solo ahí se generan — no en toda arista). La verificación de todo claim `derivation` incluye **compatibilidad de scopes**: el scope de la conclusión debe estar cubierto por la función de scopes de las premisas según la plantilla — una premisa angosta jamás sostiene una conclusión ancha (corolario de L1 aplicado al alcance). Subjects externos al cómputo en curso (E9).

**2 · `Attestation`** — in-toto Statement (subject = claim digest; predicateType URI versionada por clase) + predicate común {verdict, inconclusive_reason∅, scope, coverage, evidence_refs[], anchor_binding∅ {id, digest}, verifier_binding {id, version, binary_digest}, **verifier_params_digest**, reruns, proof∅ {certificate_ref, checker_id, checker_verdict}, tiempos, costo} + envelope DSSE (S2). Content-addressed; **reutilización exige coincidencia de los 4 digests y conformidad con la Policy consumidora** (rerun_policy, holdout, basis de ancla, frescura — el digest iguala identidad; la Policy pinned decide admisibilidad), y hereda `VALID_AS_OF` + revocaciones. Estados: `active · superseded · invalidated_by_revocation`. Los perfiles extienden predicates por claim_type (p. ej. procedimiento estadístico — Perfil STEM). _Encoding por lotes (no cambia el modelo):_ un Statement multi-subject con `results[{subject_digest, verdict, scope, evidence_refs…}]` — cada (subject, verdict) es una attestation lógica.

**3 · `Evidence`** — {id content-addressed, kind (`execution_transcript · measurement · proof_object · citation_extract · dataset_slice · review_document · replication_record`), content_ref (Artifact del Engine), content_digest, origin (`external · curated · self_generated` + producer_ref) — self_generated no cuenta como pata de independencia y C3 exige ≥1 pata external/curated (R-E1) —, reproducer (obligatorio para contribuir AL3)}.

**4 · `Verifier`** (entrada de registry; el módulo ejecutable es una **Capability** — §7) — {id, class, version, claim_types[], binary_digest + provenance SLSA, **determinism** (`deterministic · nondeterministic`: en no-deterministas la rerun_policy aplica a ambos veredictos), cost_model, independence_group + independence_of[], checker_id∅, status (`active · deprecated · revoked`)}. **R-V2 (mitigación de SC6):** la elegibilidad para claims C3 exige registro firmado por AcceptanceAuthority. Los cambios de estatus son eventos y disparan re-verificación dirigida.

**5 · `Anchor`** — {id, kind (`reference_dataset · benchmark · knowledge_base · constants_table · spec_document · oracle_service · curated_corpus · external_certificate`), content_digest, version, uri, curator, authority_basis (`standards_body · peer_reviewed · curated_internal · ad_hoc`), provenance_attestation_ref, validity, status}. **Topes intrínsecos:** ad_hoc ⇒ máx AL2 · curated_internal ⇒ máx AL3 · peer_reviewed/standards ⇒ techo de clase. **`external_certificate` = importación cross-case** (propio o ajeno): verificación del bundle al importar (evento), AL local ≤ AL de la conclusión importada, ciclos prohibidos.

**6 · `VerificationPlan`** — {claim_ref, policy_digest fijado, required_AL = **mín(objetivo por criticidad, techo del claim_type)**, required_legs, min_anchor_basis, selections[{verifier, anchor∅, scope, holdout, budget, orden}], rationale (objetivo: cerrar la brecha al menor costo; superar solo si es gratis; **Inv-E de la Base:** la selección respeta la autorización de egreso del dominio — un ancla que exigiría egreso no autorizado no es seleccionable y la salida se declara `anchor_requires_unauthorized_egress`), gap_report {achieved, required, met, gap_kind: `subsanable · techo_estructural`}, status}. Registrado **antes** de ejecutar; toda selección termina en desenlace registrado (L2/I16).

**7 · `Policy`** — {scope tenant/project, version, calculus_version, matriz por criticidad (default: C0 declarado/0 legs · C1 AL1/1 · C2 AL2/1 · C3 **AL3/2 legs/ancla ≥ curated_internal/≥1 pata no-self_generated/formalización nativa o revisada**), escalation (vía tareas del Engine; resolución registrada + E5), retention (≥ 6 meses Art. 19; default superior), **max_attestation_age** por claim_type/criticidad (frescura exigible por los gates), **trusted_signer_roots** (qué firmas acepta el case — delega en las raíces de identidad del Engine), audience_profiles, forma monotónica, **PR4 (Base):** claims con flags `irreversible ∧ affects_third_party` portan piso C3 y gate **bloqueante** — si el AL exigido no se alcanza, la acción no se ejecuta (la esquina se satisface por no-acción); probar reversibilidad (un claim más) demota el flag}. Fijada por digest al crear el case; `PolicyChanged` no afecta cases en vuelo.

**8 · `Certificate` / `Bundle` / `Receipt`** — Certificate: {case_ref, run_ref (case por run raíz — D5), conclusions[{claim, verdict, AL, gap}] + titular = mín entre conclusiones, **deliverables[{artifact_ref, digest}]** (todo entregable debe ser subject —directo o vía claims— de las conclusiones; el verificador del bundle recomputa), coverage_stats (disposiciones + afirmaciones no reclamadas, leídas del anexo de señales), limitaciones por soberanía (Inv-E) registradas como Assumptions del case, signals_annex_ref, policy_digest, calculus_version, validity + status_ref, supersedes/superseded_by, audience_profile (`full · redacted · regulator`), firmas (plataforma + AcceptanceAuthority según Policy)}. Receipt: {inclusion proof Merkle (RFC 6962), checkpoint firmado, timestamp RFC 3161 — multi-TSA configurable por Policy}. Bundle: certificate + planes + attestations DSSE + receipts + evidencias (según perfil de audiencia) + descriptores (digests+proveniencia) de anclas/verificadores + versión del algoritmo de verificación + status_ref. **El verificador del bundle valida: firmas, inclusión, digests de deliverables, y el cierre plan↔resultado.** Offline ⇒ `VALID_AS_OF`; online ⇒ `CURRENT`.

**9 · `StatusList`** — {entries[{target_kind: attestation · certificate · anchor · verifier, target_digest, status, reason, at}], checkpoints}. Los lotes se revocan a granularidad de **attestation lógica**: target = (envelope_digest, subject_digest) — 40 celdas afectadas no matan 1 960 sanas. Revocar identifica afectados por digest → supersesión + recertificación.

**Tipos acompañantes:** `Detector`/`Signal` — disjuntos (S1); Signal = {detector, target, score/label, non_decisional: const true}; kinds abiertos (catálogo de producto, no norma) incluida `unclaimed_assertion` (afirmación asertiva sin claim: se lista en coverage_stats, nunca bloquea). `EventLog` — append-only, hash-encadenado, Merkle, **hash-first** (payloads por digest; contenido en store privado). Catálogo (● = propiedad de esta capa; ○ = del Engine, consumido): ○RunStarted/Finished · ●ClaimEmitted · ●PlanCreated · ●PolicyPinned · ●VerificationStarted/Completed · ●AttestationRecorded · ●SignalRecorded · ●ConflictDetected · ●EscalationOpened/Resolved · ●HumanOverrideRecorded · ●CaseClosed · ●CertificateIssued/Reissued/Revoked · ●Anchor/Verifier Registered/Superseded/Deprecated/Revoked · ●AttestationSuperseded · ●ExternalCertificateImported · ○PolicyChanged.

---

## §4 · El cálculo `cal-2.2`

**Paso 1 — Veredicto** (entrada: attestations activas; señales inadmisibles por tipo — S1):

1. Canonicalizar scopes; computar relaciones (equivalencia/subsunción/intersección).
2. **Conflicto por solapamiento:** pass(A) y fail(B) con A∩B ≠ ∅ ⇒ conflicto _escopado a la intersección_ → `inconclusive(conflict)`, AL0, escalada; fuera de la intersección la evidencia queda como parcial — y mientras el conflicto esté abierto, el veredicto del claim completo es `inconclusive(conflict)`: el resto no contestado no puede componer un pass. (La equivalencia es el caso de intersección total; la fuerza relativa solo ordena el triaje — D3.)
3. `fail` (con reruns satisfechos) sin pass solapante ⇒ **refuted** si la semántica del tipo es `universal_sobre_scope` (el contraejemplo refuta); para tipos `existencial`, la refutación exige un fail cuyo scope **subsuma** el del claim (exhaustividad) — un fail parcial sobre un existencial aporta cobertura negativa, no veredicto.
4. `pass` presente ⇒ **verified** → Paso 2.
5. Nada decisorio ⇒ `inconclusive(reason)` o `not_required_declared` según Policy (D1).
   _Un conflicto solo se limpia por supersesión con causa de al menos una de las partes — jamás por dictamen (E5)._

**Paso 2 — Nivel de evidencia:** `base(att)` = techo de clase ∘ tope de ancla ∘ condición proof (S3) ∘ condición HUMAN_EXPERT. **Selección directa:** AL_evidence = máx. base entre passes cuyo scope **subsume** el del claim. (`scope` = dominio que la attestation aborda; `coverage` = fracción efectivamente ejercitada: los métodos exhaustivos declaran coverage=1; los muestrales —property-based testing, instantes sobre ventanas temporales— subsumen por scope y su coverage aplica descenso registrado.) **Composición por casos (R-S1):** passes parciales cuya unión canónica **cubre** el scope componen un pass virtual al **mín.** de sus bases. Solo parciales sin cubrimiento, o evidencia indirecta ⇒ AL1 (D4). Capas registradas (formalización, ancla, importación); **ningún operador sube nivel**.

**Paso 3 — Independencia (D2):** legs = nº de `independence_group` distintos entre los passes que sostienen el nivel; si legs < requeridos ⇒ AL_effective = mín(AL_evidence, AL2), downgrade registrado.

**Paso 4 — Agregación (L1):** por conclusión, AL = **mín** AL_effective sobre su camino crítico **incluidas las derivaciones**; titular = mín entre conclusiones. El mínimo es despiadado por diseño — un `not_required_declared` en camino crítico arrastra a AL0, por lo que la Policy obliga a planificar todo el camino. **Socavamiento (A2):** si un claim del camino queda `refuted`, todo claim que dependa de él pasa a `inconclusive(undermined_premise)` con AL0 y re-planificación — el argumento cae; la falsedad **no** se propaga (negar el antecedente sería inválido).

**Paso 5 — Cierre:** gap_report (con gap_kind), disposiciones visibles, calculus_version en todo, cierre plan↔resultado verificado.

---

## §5 · Vistas derivadas (no normativas)

El **assurance case** (SACM/GSN: Goal←Claim, Strategy←plan, Solution←Attestation, Assumption←formalization.assumptions, Context←scope/anclas) es una **proyección generada** de claims+planes+attestations — cero estado propio; el cálculo jamás la lee. El **panel de señales** es la vista cotidiana del anexo no-decisorio.

---

## §6 · Formatos

Attestation → in-toto Statement v1 + DSSE · proveniencia → PROV-O · receipts/log → RFC 6962 + SCITT + RFC 3161 · certificate/bundle → manifest estilo C2PA + Sigstore bundle · identidad humana → W3C VC 2.0 · canonicalización → RFC 8785 + NFC + números normados · lotes → Statement multi-subject con results[].

---

## §7 · Interfaces entre estratos

**Kernel ↔ Capabilities.** Un verificador ejecutable es una **Capability** del catálogo del Engine: módulo con binary_digest + proveniencia SLSA + declaración de clase/claim_types/determinism. La entrada `Verifier` del registry es el registro kernel de esa capability; **la configuración la fija el perfil** vía `verifier_params_digest` (la curación hecha criptografía). Elegibilidad C3 = R-V2. El flywheel Artifact→Capability alimenta el catálogo; la capa de confianza es su consumidora más exigente.

**Kernel ↔ Perfil (distribución).** Un perfil **puede**: registrar claim_types con schemas y techos; curar capabilities (qué módulos, con qué params pinned); definir plantillas de Policy y pisos de criticidad; aportar verificadores metodológicos y doctrina de granularidad de claims. Un perfil **no puede**: alterar leyes, cálculo, tipos ni formatos; rebajar mínimos del kernel (los perfiles solo elevan — corolario de L1). Los perfiles se versionan y la Policy los referencia por digest.

**Kernel ↔ Shell.** La shell observa y propone (salud, analítica, colas vía tareas del Engine, detectores); solo actúa a través de eventos gobernados (cambios de estatus, escaladas); **jamás escribe veredictos ni niveles**. Anexo no normativo: VerifierHealth {tasa de conflicto, tasa de inconclusive, deriva, **correlación de veredictos por pares** — el backstop estadístico del supuesto de carga SC6} con umbrales que auto-deprecan pendiente de revisión.

**Kernel ↔ Engine.** Claim/Case/Certificate cuelgan de `Run` · Evidence = `Artifact` · EventLog = el espinazo append-only único · Verifier = caso de `Tool/Capability` · VerificationPlan = nodo DAG (los gates PEV del harness leen gap_report) · escalación = sistema de tareas · Policy/identidades/firmas = seguridad tenant-scoped · Detector/Signal = observabilidad.

---

## §8 · Trazabilidad v2.1 → v3.0

| Antes                                                     | Ahora                                                                                                                                                                                                                                                     |
| --------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| I14, I5, R-A1, R-F1, R-A2, R-S1, D2, D5                   | Corolarios de **L1**                                                                                                                                                                                                                                      |
| I2, I7, I11, I12, I16, R-Pol1, E5, E6                     | Corolarios de **L2**                                                                                                                                                                                                                                      |
| I15, I8, N4, N5, E2, E3, E4                               | Corolarios de **L3**                                                                                                                                                                                                                                      |
| R-D1, E9, formalización, importación                      | Corolarios de **P1**                                                                                                                                                                                                                                      |
| I1, I9, I4, I3, I10, I13, I6                              | Invariantes estructurales **S1–S6**                                                                                                                                                                                                                       |
| Entidad `Formalization`                                   | Embebida en `Claim.formalization`                                                                                                                                                                                                                         |
| `UnclaimedAssertion`                                      | Signal kind `unclaimed_assertion`                                                                                                                                                                                                                         |
| `EscalationItem`                                          | Tareas del Engine + eventos + E5                                                                                                                                                                                                                          |
| `AssuranceLevel`/`Criticality` standalone                 | Campos de `Claim`                                                                                                                                                                                                                                         |
| `ArgumentNode`                                            | Vista derivada (§5)                                                                                                                                                                                                                                       |
| Campos estadísticos (E8/U4) y catálogo de detectores      | **Perfil STEM v1.0** / catálogo de producto                                                                                                                                                                                                               |
| VerifierHealth analítica                                  | Shell (§7, anexo)                                                                                                                                                                                                                                         |
| Kernel K1–K6 y supuestos de carga (antes "axiomas" A1–A5) | Intactos; +**SC6**; renombrados **SC1–SC6** para no colisionar con los axiomas AX1–AX3 de la Base                                                                                                                                                         |
| **Base Lógica Formal (v3.1)**                             | **S7** (D9/D18: anclaje ¬modelo) · Inv-E en el router y razones de inconclusive · flags PR2/PR4 en Claim y Policy · control de constitucionalidad en el criterio (§2)                                                                                     |
| **Stress test v4 (v3.2)**                                 | Semántica de cuantificación en claim_types · socavamiento (`undermined_premise`) · compatibilidad de scopes en derivaciones · reutilización conforme a Policy · `max_attestation_age` · `trusted_signer_roots` · revocación granular de lotes · multi-TSA |

---

## §9 · Compuertas a implementación

1. Property-based tests del agregador cal-2.2 (determinismo, monotonía, no-amplificación, conflict-safety — incluida la semántica de intersección). 2. Demo de inyección de falla. 3. CLI verificador del bundle (firmas, inclusión, deliverables, cierre). 4. Segunda implementación independiente del verificador (post-evento). 5. AssuranceBench con fallas sembradas (post-evento).

## §10 · Fuera de alcance (parqueado)

ZK selective disclosure · TEE del pipeline · feeds de retractación · API wire del protocolo (v3 del protocolo, post-evento) · mecanización Lean (interina: spec ejecutable + property tests).

## §11 · Registro de decisiones

**D1** disposición universal, verificación proporcional · **D2** independencia como requisito, no bono · **D3** conflicto → inconclusive, jamás por jerarquía · **D4** AL1 = decisorio incompleto; señales sin nivel · **D5** case por run raíz; attestations content-addressed reutilizables.

## §12 · Supuestos de carga (SC1–SC6)

_(Antes "axiomas de carga" — renombrados para no colisionar con los **axiomas AX1–AX3 de la Base Lógica Formal**, que son invariantes inviolables del sistema; estos, en cambio, son supuestos sobre el mundo en los que el sistema descansa.)_
**SC1** la criptografía estándar resiste · **SC2** las claves no están comprometidas (transparencia como detección) · **SC3** el universo de anclas refleja la realidad (el oráculo: acotado, declarado) · **SC4** la formalización es suficientemente fiel (convertida en objeto verificable; residual declarado) · **SC5** el checker de AL4 es correcto (TCB mínimo, de Bruijn) · **SC6** las declaraciones de independencia son veraces — jamás probado criptográficamente; mitigado por gobernanza R-V2 + correlación de salud (shell) + transparencia del certificado para juicio de terceros.
