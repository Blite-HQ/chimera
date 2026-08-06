# Contract Freeze — los contratos del mes (CONGELADO)

> **Estado: CONGELADO (2026-07-18, cierre S-E).** Este documento fija los contratos de datos y
> puertos del mes. Fuentes incorporadas: las 8 notas de `knowledge/trust/` (2026-07-02/03), las
> 9 notas de `knowledge/execution/` (ítems **[ejecución]**, merge completado en este cierre), el
> veredicto de convergencia ([`convergencia-diseno-v32.md`](convergencia-diseno-v32.md)), los
> P0/P1 del stress test S-D y el enunciado oficial de la Quantathon CR 2026. El **vocabulario
> normativo** es el de la [spec de confianza v3.2 / `cal-2.4`](spec-confianza-v3-2.md) (clases
> decisorias + AL0–AL4 + criticidad C0–C3; Certificate/Bundle; predicates por clase).
> La semilla ejecutable es la [Especificación de Contratos v2](especificacion-contratos-v2.md) +
> [Esquema de Datos v2](esquema-datos-v2.md); la verdad final es su traducción a Python/Pydantic
> (S-G, TDD, gates verdes).
>
> **Reglas del congelamiento.** (1) La base lógica ([`invariants.md`](invariants.md),
> [`base-logica-formal.md`](base-logica-formal.md)) **nunca está bajo revisión**: si algo aquí la
> contradijera, eso es dato sobre este documento. (2) Todas las decisiones están **tomadas** —
> "decidido — ratificación final del dueño" marca revisión final del dueño (ajustable bajo su
> criterio), no una decisión abierta. (3) Cambios post-freeze = supersesión con causa registrada
> (L2), jamás edición silenciosa; todo delta pasa control de constitucionalidad (spec §2).
>
> Convención de dueño: **[confianza]** = Dylan · **[ejecución]** = Steven · **[frontera]** =
> contrato de Dylan, mecánica de Steven · **[ciencia]** = Sebas · **[infra]** = Geovanni.
>
> **Supersesiones S-F (2026-07-20, auditoría de ratificación · portadas 2026-07-22 tras veredicto
> CONVERGEN — ver `docs/research/convergencia-simulada-real-sf.md` y el Registro de convergencia al
> final).** Las marcas **[S-F]** provienen de la auditoría adversarial de la ratificación — acta
> simulada + validación a profundidad (rama de ejercicio, read-only) — y de la **ratificación
> verbal de Geovanni (19-jul)**: local-first confirmado, stretch = Fargate **o EKS**, modelos
> por **API keys** (nadie corre un modelo local). Ninguna supersesión [S-F] reabre una decisión
> de diseño congelada: corrigen letra-vs-realidad (el freeze afirmaba estados del repo que no
> existían), completan semillas contra lo ya congelado y cierran reglas que S-G no podía
> inventar. Causas y detalle: **Registro de cierre (S-F)** al final.

---

## 1 · `CapabilityManifest` v2 **[frontera]** — notas trust/06, execution/04/06/08

> **[MEJORADO · 2026-07-30] Nota de estado (censo §1.7-B):** este § habla en
> presente («se agregan») pero el SDK real sigue en v1 — los 4 campos de la
> tabla NO existen en `sdk/src/blite_capability/manifest.py` (el DDL sí los
> tiene). El contrato congelado queda intacto; su implementación es el ítem
> **C1** del backlog (`docs/mejorado/04-consolidacion.md` — «el desbloqueador»).
> Promesa vencida registrada, mismo patrón que las marcas [S-F] corrigen.

Al stub actual (`sdk/src/blite_capability/manifest.py`) se agregan:

| Campo                 | Tipo                                                            | Por qué                                                                       |
| --------------------- | --------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `side_effects`        | `Literal["pure","reversible-external","irreversible-external"]` | Eje de riesgo de la verificación (PR2/PR4); lo consume la Policy (§6)         |
| `required_permission` | `str`                                                           | AX1/authz; lo chequea la etapa 2 del gateway contra los claims (§8)           |
| `interaction`         | `Literal["request_response","job","stream"]`                    | Semántica del contrato — qué maneja el caller                                 |
| `execution_profile`   | `Literal["in-process","service","remote-job"] = "in-process"`   | Hint de empaquetado; la **distribución** puede sobreescribirlo por despliegue |

El campo `protocol` de la semilla **se elimina** del manifest: el protocolo es del adapter, no de la capability (ADR-013; corrección C1 aplicada a la semilla v2 al importarla). ADR-029 (genericidad) aplica sin cambios a los campos nuevos.

**[ejecución] Refinamientos incorporados (decididos — ratificación final de Steven):**

- **Registry (execution/04):** descubrimiento por entry points (`importlib.metadata`, grupo `blite.capabilities`), **tolerante a fallos** — excepción capturada POR entry point (jamás try/except global), fallidas acumuladas y visibles; `Registry.list()` expone el manifest **completo** (los 4 campos nuevos incluidos) para que el mapeo a MCP tool no requiera llamadas extra. Forma: `Registry(Protocol).list() -> tuple[CapabilityManifest, ...] / get(capability_id) -> Capability`.
- **Eventos del registry (execution/04, pregunta cerrada):** se adoptan `registry.loaded {capability_ids[], failed[]}` y `registry.capability_load_failed {entry_point, error_kind}` con `actor_id = "service:runtime"` (§8). "Deshabilitada intencionalmente" ≠ "falló al cargar": lo primero es ausencia en el `DistributionManifest`, lo segundo va en `failed`.
- **Versiones duplicadas de un `id` (execution/04+08, cerrado):** resolución por **pin del `DistributionManifest`** por despliegue, con default **determinista** (jamás `latest` — semántica validada contra Composio en execution/08).
- **Despacho por `execution_profile` (execution/06):** `DispatchStrategy(Protocol).execute(capability, inputs) -> Result | JobRef`; `Dispatcher.resolve(execution_profile)`; en Fase 1 solo `InProcessStrategy` es real; `remote-job` retorna **`JobRef`, jamás `Result` síncrono**; perfil no soportado ⇒ `NotImplementedError` explícito, **nunca fallback silencioso** a in-process. El default del perfil lo fija el autor del manifest; la distribución lo sobreescribe.
- **[S-F] Regla de validez `interaction` × `execution_profile` (el override sin condición podía romper el contrato del caller):** la matriz completa se valida **al cargar el `DistributionManifest`** — fail-closed en deploy, jamás en la primera invocación. Override a `remote-job` solo si `interaction: job` (a una capability `request_response` no se le puede prometer `JobRef` donde su semántica promete `Result`); `interaction: stream` ⇒ `NotImplementedError` en Fase 1 (valor congelado sin semántica de despacho aún); par incompatible ⇒ `NotImplementedError` — la misma doctrina anti-fallback del despacho.

## 2 · `Event` + esquema `events` + puerto `EventStore` **[confianza]** — nota trust/01

- **`Event`** (reemplaza el dataclass de `engine/src/blite/events/writer.py`): `id: UUID`, `stream_id`, `seq`, `global_seq`, `type`, **`actor_id` obligatorio**, `domain_id`, `payload`, `occurred_at: datetime`, `prev_hash/hash: str | None` (vacíos = semilla del hash-chain Fase 2).
- **Esquema SQL (semilla v2 ya corregida):** `+ global_seq BIGINT GENERATED ALWAYS AS IDENTITY` (cursor global para SSE/proyecciones); append-only **que falla fuerte** (REVOKE + trigger que lanza excepción — jamás reglas silenciosas); concurrencia optimista documentada (`expected_seq` → INSERT `seq = expected_seq + 1`, el UNIQUE rechaza conflictos).
- **Puerto:** `EventStore.append(stream_id, type, actor_id, domain_id, payload, expected_seq) / read_stream(stream_id, from_seq) / read_all(from_global_seq)`. El writer in-memory se reemplaza detrás del mismo puerto; INV-5 y sus gates intactos.
- **Convención de stream (decidida — cierra la pregunta №1 de execution/07):** `stream_id = run_id`, **un stream por run**; los sub-runs (§13) tienen su propio stream y la correlación padre-hijo viaja por `parent_run_id`, no por streams anidados. Dentro de un stream, la correlación step/job va en el `payload` (`step_id`, `job_id`).
- **[S-F] Streams de sistema (N2 — el walking skeleton no podía escribir su primer `registry.loaded` sin inventar una convención):** los eventos que no pertenecen a ningún run (`registry.*`, `○PolicyChanged`, `●AnchorRegistered/…`, `●VerifierRegistered/…`) usan `stream_id = "system:<componente>"` (`system:registry`, `system:policy`, `system:trust-registry`), mismo append-only, `actor_id = service:*`. El `provenance_hash` de un certificado cubre **solo streams de run** (el raíz + los sub-runs pinneados vía `●ClaimEmitted`, §13); los streams de sistema jamás entran a ese hash.
- **[S-F] Escritura post-terminal = RECHAZO:** tras el evento terminal de un run (`run.completed|failed|cancelled`), el `EventStore` **rechaza** appends de `run.step.*`/`capability.job.*` de ese run — jamás "aceptar marcado late": un append post-terminal cambia los bytes del stream y rompe el recompute del `provenance_hash` de un certificado ya emitido. La regla "un step RUNNING no recibe evento terminal" pasa de convención de lectura a regla de escritura. **[stress-final · 2026-07-22] Corte del `provenance_hash` (dos implementaciones honestas divergían):** el hash cubre los eventos del stream **desde `run.created` hasta el evento terminal del run, inclusive** — nada después. Post-terminal se admiten SOLO las familias de cierre (`run.metrics.recorded` y los ● de cierre del case: `●CaseClosed`, `●CertificateIssued`), que quedan **FUERA del hash** (así `●CertificateIssued` no se auto-referencia); el rechazo aplica a `run.step.*`/`capability.job.*` como arriba. **Reserva de namespace:** ningún `run_id` puede empezar con `system:` (los streams de sistema son disjuntos de los de run por construcción — el alcance del hash lo asume).
- **SSE:** patrón **notify-then-catchup** (NOTIFY como pista, la tabla como verdad, catch-up por `global_seq`).
- **[ejecución] Proyección `RunState` (execution/03):** resumen derivable del último `run.step.*` conocido, regenerable por replay — patrón de consumo del puerto, cero almacén nuevo. Durabilidad del mes = replay del log (ni Temporal, ni checkpointing externo: una sola fuente de verdad).
- **Hash-first (spec v3.2):** los payloads grandes van por digest a `Artifact` (§12); el payload embebido queda para eventos chicos. El hash-chain completo es Fase 2 **sin cambio de forma**.

## 3 · Vocabulario de eventos del run **[frontera]** — trust/06 + execution/02/07 + catálogo v3.2

`invoke()` sync-only queda descartado. El vocabulario completo (forma alineada al task lifecycle de A2A; máquinas de estado de execution/07, decididas — ratificación final de Steven):

- **Run:** `run.created {run_id, actor_id, domain_id, max_steps, policy_digest, parent_run_id?, agent_definition_digest?, workflow_definition_digest?}` **[S-F: el guard viaja en el evento fundacional — las semillas no lo cargaban] [stress-final · 2026-07-22: el payload carga TODO lo que `runs_projection` necesita para regenerarse por replay — `policy_digest` (pinning SO6; y el fail-closed de herencia §13 se comprueba contra el del evento de creación del sub-run) y `parent_run_id` (la correlación padre-hijo de §2 necesitaba portador); sin esto la doctrina "un replay de events regenera la proyección" era falsa]** → `run.started` → (`run.completed {output_digest?}` | `run.failed {error_kind}` | `run.cancelled {reason}` — `reason: "parent_cancelled"` cuando la emite la cascada de §13). Estados `CREATED → RUNNING → {COMPLETED | FAILED | CANCELLED}`; sin transiciones entre terminales. `run.created` estampa `actor_id` (AX1). **[S-F] `awaiting-verification` (unificación §3↔§13):** NO es estado de la máquina de eventos ni tiene evento propio — es **sub-estado de proyección** derivado de `●VerificationStarted` sin su `●VerificationCompleted` correspondiente, misma doctrina que `interrupted`.
- **Step:** `run.step.started` → (`run.step.completed` | `run.step.failed`) — `RunStep {step_id, run_id, kind, input_digest, output_digest?, status}` viaja como payload; `status ∈ {pending, running, completed, failed}` (conjunto cerrado); `input_digest` refiere contenido recuperable byte a byte (§12). **Relación step↔job = 1:1 en Fase 1** (paralelismo = varios steps). Al `run.cancelled`, un step en RUNNING no recibe evento terminal propio: la proyección lo reporta `interrupted` (regla de proyección, no evento nuevo).
- **Job de capability:** `capability.job.submitted` (ANTES de ejecutar — PR1, etapa provenance:pre) → `capability.job.progress`* → `capability.job.completed | capability.job.failed`. `interaction: request_response` es el caso degenerado que completa de inmediato — mismo rastro.
- **Llamada de modelo (decidida — cierra la pregunta §4.5 de execution/09):** `model.call.requested {backend_id, local, prompt_digest}` → `model.call.completed {response_digest} | model.call.failed {error_kind}` — rastro propio (precedente AGT `pre/post_model_call`), prompts/respuestas como `Artifact` por digest. Habilita el backend `replay` del router (§15.7).
- **Registry:** `registry.loaded` / `registry.capability_load_failed` (§1).
- **Capa de confianza:** el catálogo ● completo (§14).
- **`max_steps` obligatorio a nivel de `Run`** (execution/02) — el guard del loop es contrato, no cortesía. **[S-F]** Corrección de semillas: `Run.maxSteps` (contratos v2 §3) y `runs_projection.max_steps NOT NULL` (esquema v2 §5) existen desde este barrido; viaja en el payload de `run.created` (arriba).
- **[S-F] Métricas por run (N3 — el evento de §6 no tenía tipo y era inemitible):** `run.metrics.recorded {verification_latency_ms, attestations_total, inconclusive_count, false_reject_proxy, cost_per_verification?, ms_por_clase?}` — se emite al cerrar el run, `actor_id: service:runtime`.

> **[MEJORADO · 2026-07-30] Supersedes registrados de §3 (aplicados con causa):**
> **(a) #104 — skip honesto en la ruta de LECTURA:** `GET /runs` descarta streams
> envenenados y expone `discarded_streams` (extensión aditiva del wire E↔D + Zod +
> fixture + test con la píldora #96) — supersede PARCIAL de la letra fail-loud
> SOLO para lectura; escritura/certificados/provenance siguen fail-loud intactos.
> **(b) C-4/#106 — payload de `run.metrics.recorded` EXTENDIDO aditivo:** los
> campos de confianza de arriba se mantienen; entran `variant` (enum de 4:
> `quantum|classical|mitigated|zne`) + campos científicos opcionales; dos brazos
> de ablación = sub-runs (§13); el evento post-terminal sigue FUERA del hash, como
> está congelado. Implementación = ítem V2/M19.
> **(c) Ceremonia #66 (`docs/specs/harness-agentico.md`):** `run.created` ganó
> `max_turns` (default 30) y `budget` — extensión aditiva registrada en esa spec
> (§Guardas), nunca portada a esta letra hasta esta marca.
> **(d) #123 — `run.created` gana `thread_id?`/`project_id?` (aditivos, S-A):**
> el enhebrado conversacional post-terminal y la pertenencia a proyecto viajan en
> el evento fundacional (`thread_id` = run raíz del hilo; `project_id` = fila
> relacional FUERA del event store — M15). Forma y semántica:
> `docs/specs/chat-conversacion.md`. Implementación = ítems P3/P6.

## 4 · `Verifier` / `Attestation` — clases decisorias y niveles **[confianza]** — trust/03/04/10/11/12 + spec v3.2 §3

**La escalera 1–7 queda SUPERSEDIDA por los tres ejes de la spec v3.2** (mapa completo en convergencia §2.1; trust/03 lleva la marca): la **clase** dice el método, el **AL** dice la fuerza (con techos), la **criticidad** dice cuánta fuerza se exige.

- **`VerifierClass`** = `formal_exact (→AL4 con checker independiente; AL3 sin él) · execution (→AL3, reproducer obligatorio) · ground_truth (→AL3, sujeto a tope del ancla) · property_rule (→AL2) · consensus_replication (→AL2, SOLO procesos no-modelo — S7) · human_expert (→AL3 condicionado)`. Sin `"model"` **por construcción** (no existe el valor — INV-2/PR2 verificado por el gate de tipos).
- **`AnchorKind` de la Base (`solver|execution|dataset|rule|human`) NO cambia** — es el gate constitucional anti-modelo (invariants.md). El `Anchor.kind` de la v3.2 (`reference_dataset · benchmark · curated_corpus · …` con `authority_basis` y topes: ad_hoc ⇒ máx AL2, curated_internal ⇒ máx AL3) es la **taxonomía del registro de anclas** — metadata sobre el gate, no su reemplazo.
- **`Verifier`** (Protocol): `verifier_class`, `determinism` (`deterministic|nondeterministic` — en no-deterministas la rerun_policy aplica a ambos veredictos), `verify(claim, ctx) -> Attestation`. El campo `rung: int` **desaparece** (los badges del Studio migran de escalón a clase+AL — trust/18).
- **`Attestation`**: verdict tri-estado `pass·fail·inconclusive(reason tipada — la lista completa de la v3.2, incl. no_applicable_anchor · anchor_requires_unauthorized_egress · undermined_premise · budget_exhausted)`, `scope` (ScopeExpr decidible), **binding a 4 digests** (`claim_digest`, `verifier_binary_digest`, `verifier_params_digest`, `anchor_digest`), `evidence_digests[]` → Artifacts (§12) con reproducer si aporta AL3, `issued_at` con semántica VALID_AS_OF. La `evidence` deja de ser unión embebida: son **refs content-addressed** con predicates por clase (los perfiles los extienden — Perfil STEM).
- **Adapters del mes re-etiquetados:** CP-SAT + brute-force checker = `formal_exact` → **AL4 en instancias con checker** (la doble ancla del corpus ES el habilitador); pandapower = `execution` → AL3; corpus IEEE/CR = `ground_truth` → AL3 (ancla `curated_internal`); Hypothesis/metamórficas = `property_rule` → AL2; réplicas con seeds pinned = `consensus_replication` → AL2 decisorio (es proceso no-modelo; la concordancia entre modelos sigue siendo Signal — ajuste estampado en quantum/04 §4).
- **Refinamientos aditivos de los adapters (decididos — ratificación final de Dylan; diseño interno en trust/10/11/12):** enum real de CP-SAT en el predicate `differential` (`OPTIMAL|FEASIBLE|INFEASIBLE|MODEL_INVALID|UNKNOWN`, con `MODEL_INVALID`/`INFEASIBLE` → **error de proceso**, no verdict); campos del backend formal en `property` (`backend`/`status`/`unsat_core`); `timed_out` en `execution`; la distinción dura **`error` (falla de proceso — no emite `Attestation`) vs `verdict: "fail"`** (veredicto sobre el claim).
- **R-V2 / AcceptanceAuthority:** la elegibilidad de un verificador para claims C3 exige registro firmado por la AcceptanceAuthority del perfil; en la distribución Chimera la Policy designa al **PI del programa (`user:dylan`)** — decidido, ratificación final del equipo. **Limitación Fase 1 declarada [S-F]:** Dylan diseña los verificadores Y los acepta — separación de deberes pendiente, análoga al S2 de llaves; va en `assumptions` del certificado.
- **[S-F] Endurecimientos del binding (auditoría del plano de confianza — el certificado prometía más de lo que sus semillas podían probar):** (i) `anchor_digest` nullable **solo** si `verdict = inconclusive` — un `pass` sin ancla es irrepresentable (D10; CHECK en la semilla SQL); (ii) **`independence_group` obligatorio en la `Attestation`** — el conteo de patas de C3 es por grupo de independencia (spec v3.2) y sin el campo "2 patas" era incomputable ante un auditor; (iii) el predicate por clase carga lo que su AL exige: `formal_exact` a **AL4 exige `proof {certificate_ref, checker_id, checker_verdict}`** (la re-validación del checker vive DENTRO del bundle — sin esto el titular AL4 del pitch no se puede demostrar offline); `coverage`/`reruns` donde la clase los pide.

## 5 · `Detector` / `Signal` (antes `GuardrailSignal`) **[confianza]** — trust/04/16 + spec v3.2 S1

`Signal = {detector, target, score/label, non_decisional: true}` — tipo **disjunto** de `Attestation` por firma de función (S1): lo probabilístico informa, jamás verifica ni satisface egreso (D18/D21/Inv-E hechos tipo). La numeración "rung 5/6" desaparece con la escalera; el kind usa la convención `{etapa}.{mecanismo}` (trust/16), catálogo abierto (incl. `unclaimed_assertion`). **[ejecución] Refuerzo estructural (execution/01):** la firma de la etapa de egreso acepta `AuthzDecision`, **no puede recibir `Signal`** — un `{flagged: false}` no equivale a un `pass` ni por descuido de tipos.

## 6 · `Policy` (antes `VerificationPolicy`) **[confianza]** — trust/05 + spec v3.2 §3.2

Política declarativa (Pydantic + YAML versionado en `distributions/chimera/`), **forma monotónica** ("deny unless proven"), **fijada por digest al crear el case (R-Pol1)** — no hay etapa `policy` en el pipeline (C2): la etapa de verificación LEE la Policy pinneada.

- **Matriz por criticidad** (hereda el default del kernel): C0 declarado/0 patas · C1 AL1/1 · C2 AL2/1 · C3 AL3/2 patas/ancla ≥ `curated_internal`/≥1 pata no-self_generated/formalización nativa o revisada. Pisos por flags (PR2/PR4): `world` ⇒ C2; `irreversible ∧ affects_third_party` ⇒ C3 con gate **bloqueante** (la esquina se satisface por no-acción).
- Campos v3.2 adoptados: `max_attestation_age` (frescura por claim_type/criticidad), `trusted_signer_roots`, `audience_profiles`, escalation (vía tareas; resolución registrada), retention.
- `policy_id` + digest se estampan en cada `verification.completed` (procedencia de la exigencia). `on_inconclusive` afecta el estado del run, **jamás el egreso** (Inv-E).
- Métricas por run como evento: `{verification_latency_ms, attestations_total, inconclusive_count, false_reject_proxy}` + **$/verificación y ms por clase decisoria** (P1-14 — la primera tabla real de unit economics sale del propio demo). Tipo del evento: `run.metrics.recorded` (§3, [S-F]).
- **[S-F] La Policy del repo habla este vocabulario (T1 — P1-alto de la auditoría):** `distributions/chimera/policies/verification-default.yaml` se supersede a la matriz C0–C3 (**versión 0.2.0**; la 0.1.0 hablaba `min_rung`, vocabulario que §4 eliminó — un `policy_digest` estampado hoy habría pinneado política de vocabulario supersedido). El seed Pydantic completo de la Policy (matriz + pisos por flags + campos v3.2) es S-G con dueño Dylan.
- **[S-F · EX-5 — porte tardío 2026-07-22] Palanca compensatoria de R-Pol1 (B-Obj7 del track simulado):** R-Pol1 pinnea por digest y la revocación en Fase 1 es `"none"` — si una Policy se endurece por vulnerabilidad descubierta, los cases en vuelo correrían bajo la exigencia vieja sin alarma. Regla: al aplicar un `○PolicyChanged` que **endurece**, el runtime abre `●EscalationOpened` (§14) sobre los cases en vuelo cuyo `policy_digest` pinneado quedó por debajo de la nueva exigencia — misma maquinaria de escalación vía tareas de esta sección, sin infra nueva. El pin no cambia: la palanca es alarma, jamás revocación ni re-pin.
- **[S-F stress · SF-P1-2] Portadores de las dimensiones de match (el evaluador de la Policy 0.2.0 no era construible — stress test del track simulado, resumen en `docs/research/convergencia-simulada-real-sf.md`):** la Policy 0.2.0 casa sobre `claim_type`, pero ningún artefacto Fase 1 lo carga en el claim y sus valores `solution`/`intermediate` no están en el registro de claim_types (`simulation_result`…) ni son criticidad. **Decisión para el seed de S-G:** el claim carga **`claim_type`** (registro) **+ `is_conclusion`** en el payload de `●ClaimEmitted` (§14) y en `conclusions[]` (§7); la matriz casa por **criticidad computada** (la matriz de §6 ya es "por criticidad": `is_conclusion ∧ flags` → criticidad, spec v3.2 §1), y los valores `solution`/`intermediate` del YAML se re-expresan a `C3`/`C1`. El `required_anchors` (AnchorKind) se comprueba contra el **`anchor_kind`** de la attestation (ya presente en `engine/verification/attestation.py`; la semilla v2 §5 lo suma). **[stress-final · 2026-07-22]** Los flags de piso (`world`, `irreversible ∧ affects_third_party`) tampoco tienen portador Fase 1: viajan en el MISMO payload de `●ClaimEmitted` (el manifest ya porta `side_effects` como proxy de `irreversible`); su materialización es el mismo seed. Dueño Dylan; se materializa al escribir el seed Pydantic.

## 7 · `Certificate` / `Bundle` **[confianza]** — trust/02/15 + spec v3.2 §3.2 + P0-2/P1-2/P1-3

De objeto plano a **Statement in-toto + envelope DSSE firmado**, con la **letra chica como parte del mínimo del mes** (P0-2 — un nivel sin alcance es pasivo legal, no diferenciador):

- `statement.subject = [{name: "run:<id>", digest: {sha256: provenance_hash}}]`; `predicateType` versionado.
- **Predicate mínimo del mes:** `{run_id, actor, conclusions[{claim_digest, canonical_statement, scope, verdict, level}], titular_level (mínimo del camino crítico incluidas derivaciones — jamás promedio), assumptions[{statement, ref?{name, digest}}], deliverables[{artifact_ref, digest}] (anti-TOCTOU), unanchored_steps/coverage_stats, policy_digest, calculus_version, valid_as_of, revocation: "none"}`.
- **`assumptions` obligatorias del caso demo:** versión+digest del modelo del simulador de dominio, digest del corpus usado, el SC3 verbatim ("se verifica contra anclas declaradas, no contra la realidad última") y las limitaciones por soberanía (Inv-E). **La UX abre con el alcance, no con el número** (trust/18 §2.3 corregido: la línea 1 de `CertificateView` es la conclusión + su scope; clase+AL como badge, no como titular).
- **[frontera · nota 10 (ejecución), 2026-07-22] Contenido recuperado (RAG) jamás es evidencia:** si un claim depende de contenido recuperado de la base de conocimiento (nota 10 de ejecución — fragmentos como `Artifact` §12, retrieval como `RunStep`), ese contenido entra al certificado como `assumptions[{statement, ref{name, digest}}]` — **jamás como `Attestation` ni dentro de `conclusions`** (extensión del mismo principio S1/Inv-E: lo probabilístico informa, no verifica; un digest legítimo no convierte un fragmento en sustento de veredicto). Alcance del mes: soporte de investigación del equipo / POC S-G paralelo — **fuera del camino dorado del demo (§15.4)**. Delta a ratificar por Steven al portar el mecanismo: bajo `MODEL_ROUTER_BACKEND=replay` (día D), la llamada de embeddings del retrieval también es llamada de modelo → necesita fixtures propios o retrieval precomputado/pinneado (la nota 10 no lo cubre; mismo patrón del contrato replay §15.7).
- **`VALID_AS_OF` + revocación honesta (P1-2):** todo veredicto vale a su instante (S5); el certificado **autodeclara** `revocation: "none"` en Fase 1 (StatusList/Receipt/Merkle/RFC 3161 = Fase 2 declarada; Sigstore/Fulcio/Rekor descartados este mes — rompen air-gap; Rekor = opción de transparencia Fase 2).
- **Firma:** Ed25519 local (lib `cryptography`), PAE de DSSE tal cual; verificable **offline**. La firma se pide por el puerto **`KeyProvider`** (trust/15): `keyid = "<purpose>:v<version>"`. **Escalera de custodia (P1-3, decidida):** escalón 1 = env/archivo (hoy) → escalón 2 = OpenBao Transit (Fase 2) → **escalón 3 = PKCS#11/HSM — mismo Protocol, declarado desde ya**. Doctrina: **"el keypair del certificado pertenece a la organización operadora, no al software"** — quién firma es dato del despliegue. Separación S2 (Signer ≠ Verifier) en el diseño del puerto.
- `provenance_hash` = SHA-256 del stream canónico del run (bytes exactos: **[anexo de canonicalización](contract-freeze-anexo-canonicalizacion.md)**, CONGELADO junto con este doc); en Fase 2 lo sustituye el head del hash-chain **sin cambiar la forma**.
- **Bundle mínimo** = certificate + attestations + descriptores (digests+proveniencia) de anclas/verificadores **+ la Policy pinneada (bytes exactos del YAML, verificables contra `policy_digest`) [stress-final · 2026-07-22: sin ella, el conteo de patas del punto 7 del checklist no es computable offline]**. **[S-F] Forma de las attestations del bundle (T6 — cuatro documentos decían cuatro cosas, ninguna firma persistida):** Fase 1 = las attestations van **embebidas en el payload DSSE del certificado** — una sola firma ampara certificado + attestations, la verificación offline queda intacta; DSSE por attestation individual = Fase 2; la separación S2 (Signer ≠ Verifier) se declara limitación Fase 1 en `assumptions`. **`scripts/verify-bundle.py` es seed NO recortable de S-G** (P1-11): ~50 líneas, PAE + verify offline en segunda máquina — EL beat anti-ceremonia. **[S-F] Checklist del script (T11 — sin lista explícita degrada a "firma válida"; ampliado a 7 puntos por el stress test S-F: SF-P0-1/P1-4/P2-4 — track simulado, resumen en `docs/research/convergencia-simulada-real-sf.md`):** (1) firma/PAE del envelope, (2) recompute del `provenance_hash` contra el stream, (3) digests de `deliverables` contra los bytes, (4) `titular_level = mín(conclusions[].level_efectivo)`, con `level_efectivo := AL0` si `verdict ∈ {refuted, inconclusive, not_required_declared}` (**[S-F stress · SF-P2-4]** — un claim no-verificado del camino crítico no sostiene titular alto), (5) `pass ⇒ anchor_digest` presente **y que resuelve contra un descriptor de ancla empaquetado en el Bundle** (**[S-F stress · SF-P0-1]** — presencia no basta: sin esto un `pass` con `anchor_digest` fabricado pasa, rozando D10), (6) **recompute de cada `conclusions[].claim_digest = SHA-256("blite/claim/v1\n" ‖ C(view(claim)))`** contra el valor firmado (**[S-F stress · SF-P1-4]** — sin esto `view(claim)`/V6 son letra muerta y el enunciado del titular se cree a fe del firmante), (7) **cada conclusión del camino crítico con `verdict ∈ {verified, refuted}` mapea a attestations embebidas con el mismo `claim_digest`, verdict correspondiente (pass↔verified, fail↔refuted) y nivel dentro del techo de su `verifier_class`; si el nivel es AL4, la attestation DEBE cargar `proof {certificate_ref, checker_id, checker_verdict}` (§4-iii); y el número de attestations con `independence_group` DISTINTO satisface las patas que la Policy pinneada exige para la criticidad de esa conclusión** (**[S-F stress · SF-P1-4; stress-final · 2026-07-22: sin el conteo de patas por `independence_group`, un C3 con una sola pata pasaba los 7 puntos — el campo existía y el auditor jamás lo usaba; el verificador obtiene la regla de la Policy referida por `policy_digest`, que el Bundle empaqueta como descriptor**]). Las conclusiones `not_required_declared` quedan EXENTAS del mapeo (no tienen attestation por definición; su `level_efectivo` ya es AL0 por el punto 4). Los puntos 6-7 honran la intención T4/T7 y el beat "auditable sin confiar en nosotros" (D20).
- **[S-F] `titular_level` computable (T2 — "mínimo del camino crítico" sin grafo de claims no se podía computar):** en Fase 1, `titular_level := mín(conclusions[].level_efectivo)`, con **`level_efectivo := AL0` cuando `verdict ∈ {refuted, inconclusive, not_required_declared}`** (**[S-F stress · SF-P2-4]** — regla de socavamiento spec v3.2 §125: un claim no-verificado del camino crítico no sostiene nivel positivo, aunque su `level` estructural sea alto); el camino crítico **DEBE** listarse completo en `conclusions[]` (omitir un claim débil infla el titular — eso es fraude de cálculo, no redondeo); `conclusions[] = []` ⇒ `titular_level = AL0`, jamás un AL vacuo por mínimo de conjunto vacío.
- **[S-F] Formato de `run_id` (cerraba dos convenciones en silencio):** `run_id` NO lleva prefijo (`stream_id = run_id` crudo); el prefijo `run:` existe SOLO en `subject.name = "run:<run_id>"` del Statement. El `"run:8f2c1a9b"` del vector V1 del anexo es dato arbitrario del gate de hashing, no forma normativa (ídem `"rung": 1` de V2 — los vectores no se regeneran sin romper hashes).
- **[S-F] Emisión (T14):** Fase 1 = **una emisión por run** (PK `run_id` en `trust_certificates`); `●CertificateReissued/Revoked` quedan como Fase 2 declarada — coherente con `revocation: "none"`.
- Tabla `trust_certificates` (semilla v2): conclusions/assumptions/deliverables JSONB + `certificate JSONB` (envelope completo) + `keyid` + `valid_as_of` + `revocation`.
- **Modo amortizado de primera clase (P0-5):** el "case de certificación de capability" (spec §1) usa este MISMO certificado — case cuyo run raíz es la evaluación de una capability contra corpus (GROUND_TRUTH, techo AL3, controles negativos); patrón del certificado del corrector (quantum/09).

> **[MEJORADO · 2026-07-30] Supersedes registrados de §7 (aplicados con causa):**
> **(a) Checklist = OCHO puntos (censo D-N1):** al «checklist de 7 puntos» de
> arriba se sumó el **punto 8 — fidelidad de replay** (FALLA el bundle si el
> stream contiene cualquier `replay.divergence`), entrado por la ceremonia #66
> (`docs/specs/harness-agentico.md` §Contrato-5) e implementado en
> `engine/src/blite/certificate/bundle_check.py` (los 8 puntos corren). La letra
> «7 puntos» quedó atrás del código; esta marca la reconcilia sin reescribirla.
> **(b) #105 — Rekor RE-ENTRA:** el descarte «Sigstore/Fulcio/Rekor descartados
> este mes — rompen air-gap» se supersede con causa: el fundamento era la emisión
> keyless con Fulcio; **Rekor v2 GA con backend POSIX + stapled inclusion proof**
> mantiene la verificación 100% offline. Entra como transparency-witness OPCIONAL,
> pieza 5 del orden incremental de M8 (hash-chain → DSSE/VSA → StatusList →
> OpenBao → Rekor). SPIFFE queda fuera de M8 (gate = multi-nodo).
> **(c) C-6/#106 — regla nueva del conteo de patas:** las attestations por isla
> de una MISMA corrida comparten `independence_group` (extensión del punto 7 —
> jamás inflan patas); el puerto gana `verify_all() -> tuple[Attestation, ...]`
> con default `= (verify(),)` (compat total). Implementación = ítem C4/M4.
>
> **[MEJORADO · sesión CONFIANZA-2 · 2026-08-05] Supersedes de §7 aplicados con
> causa (ítems C5–C7; ceremonia registrada en `docs/mvp/decisiones.md`):**
> **(d) Checklist = DIEZ puntos.** Entran el **9 — recompute del
> `sub_run_provenance_hash`** de cada sub-run aportante (lo MANDA el anexo de
> canonicalización §4 desde que se congeló; era letra muerta porque el stream
> del sub-run no viajaba en el Bundle y el hash se computaba con otra fórmula —
> M28 lo reconcilió) y el **10 — recompute del hash-chain** contra el
> `provenance_chain_head` firmado. Ninguno puede reprobar un Bundle emitido
> antes de existir: el 9 solo mira claims de sub-run y el 10 solo verifica si
> el certificado DECLARA un head. **Bundle mínimo extendido (aditivo):**
> `sub_run_streams` (los streams de los sub-runs que aportaron claims) y, en
> el predicate firmado, `provenance_chain_head`.
> **(e) El hash-chain de Fase 2 se implementa (C5/M8 pieza 1).** Las columnas
> `prev_hash`/`hash` de §2 dejan de estar vacías: el writer único encadena cada
> evento con la fórmula del anexo §4. **El `provenance_hash` NO se sustituye
> todavía** — la promoción del head a `subject.digest` («sin cambiar forma»)
> cambiaría el digest de todo certificado ya emitido, así que el head viaja
> como campo propio y la promoción queda como ceremonia aparte, con el
> sustrato ya puesto.
> **(f) T6 SUPERSEDIDO — DSSE por attestation deja de ser Fase 2 (C6/M8 pieza
> 2).** El Bundle puede traer `attestation_envelopes`: un sobre DSSE por
> constancia con predicate modelado sobre **SLSA VSA** (`verifier`,
> `timeVerified`, `policy`, `verificationResult` + los campos propios
> `assuranceLevel`/`verifierClass`/`anchor`/`independenceGroup`), `subject` =
> el claim, y `resourceUri` = `run/<id>[/step/<island>]`. Las attestations
> SIGUEN embebidas en el payload del certificado (compat total); el punto 7
> exige que las dos vistas coincidan EXACTAMENTE — un sobre sin constancia
> embebida es evidencia por fuera del payload firmado, y una constancia sin
> sobre cuando el resto los trae es una firma que alguien decidió no dar.
> Con `attestation_public_keys` (anillo opcional keyid→llave), la separación
> **S2 (Signer ≠ Verifier) deja de ser limitación declarada**: cada verificador
> puede firmar SU constancia. La `assumption` correspondiente se mantiene solo
> mientras la distribución siga firmando todo con la llave del certificado.

## 8 · `Identity` + JWT + intersección de permisos **[confianza / frontera en la etapa 1]** — trust/08

- **`Identity`**: `id` = URN estable estilo SPIFFE (`user:dylan`, `agent:planner-7`, regex validada), `kind`, `domain_id`, `permissions: frozenset[str]`, `spiffe_id?` (Fase 2).
- **JWT** emitido/verificado por el engine con llave local: claims `iss/sub/kind/domain_id/permissions/act/iat/exp`; **`act` (RFC 8693)** = cadena de delegación en el token. Firma **Ed25519/EdDSA** (no HS256), vía el mismo puerto `KeyProvider` del §7.
- **Derivación con intersección garantizada**: `derive(parent, requested)` — el delegado solo atenúa, jamás amplía (mismo principio que el gate de sub-agentes del repo) + property-test. `InvocationContext.invocation_chain` + `effective_permissions` (∩ de toda la cadena — SO1, la computa el gateway y nadie más).
- **Ruta del flip AX1**: `Event.actor_id` obligatorio (§2) → etapa identity estampa **[frontera]** → el xfail se voltea a aserción real (nunca se borra). Eventos fuera de request usan `service:*`.
- **Orden congelado del pipeline (C2, resolución por unión):** `identity → authorization → guardrails → provenance:pre → mediation → verification → provenance:post → egress` — 8 etapas; la etapa `policy` de execution/01 se disuelve (§6). **[ejecución]** El pipeline es **explícito e in-process** (tupla fija de `Stage`, test de orden como tupla única — execution/01/08); los transversales HTTP van como middleware **ASGI puro** (jamás `BaseHTTPMiddleware`); fail-closed. **Reautorización a mitad de pipeline (pregunta §8.4 de execution/01, cerrada):** no existe — si el despacho revela que la capability exige un permiso distinto al evaluado en la etapa 2, es **error de contrato fail-closed** (el run falla y se re-invoca completo), jamás re-evaluación en vuelo.

> **[MEJORADO C-5/#106 · 2026-07-30] Supersede ADITIVA de `GatewayContext` (con la
> MISMA ceremonia que lo congeló):** el contexto gana `run_id`/`step_id`/`domain_id`
> **opcionales**. Granularidad registrada como interpretación de «cada step cruza»
> (§13): **un cruce por invocación de capability** (resolve es parte de mediation).
> El `Pipeline` se INYECTA en `execute_run` (como `proposer`); un contrato
> `layers` nuevo vigila la dirección gateway↛runtime. Implementación = ítem C2/M2
> del backlog (hoy el pipeline no se construye fuera de tests — censo §8.1).

## 9 · Contrato SSE Studio↔Engine **[confianza / frontera en la ruta]** — trust/07

- `GET /runs/{run_id}/events` (SSE): `id = global_seq`, `event = type`, reanudación `Last-Event-ID`; el Studio consume **proyecciones**, jamás la tabla cruda.
- **Payloads por vista** congelados (trust/07 §1.3); regla de forma: **ningún payload de resultado sin su bloque `verification`** (verdict + **clase+AL** embebidos — la honestidad como contrato de datos); el resultado de partición lleva `verification` POR ISLA (validado por el spike).
- Decisión de streaming: **SSE simple** (AG-UI descartado este mes; candidato Fase 2).
- **Decisiones del walking skeleton (P1-9, cerradas):** autenticación del stream por **JWT en cookie** (decidido ya — no inventar query params firmados bajo presión); el **modo replay del Studio** (`usePlaybackReveal` + fixtures) es camino de demo de primera clase — si el stream muere, F5 + catch-up por `global_seq` ES la feature "cero eventos perdidos".
- Stack Studio validado por spike: Cytoscape.js (API directa, MIT) + Tailwind v4 + convención shadcn.

## 10 · `OverrideEvent` / `OverridePayload` **[confianza]** — trust/01/05/08 + P1-5

No es tabla nueva: `override.applied` es una fila más de `events` (§2). Forma confirmada del `payload`:

- `target: str` — `"principle:PR2"` | `"guardrail:<name>"` | `"subsystem:logging"`.
- `reason: str`.
- `authorizedBy: str` — URN restringido a **`user:*`** (AX2: la relajación exige responsable humano identificable). **Autoridad graduada (P1-5, decidida):** el autorizador debe portar el permiso **`override:apply:<scope>`** en su intersección efectiva (§8) — un `user:*` cualquiera ya NO puede relajar PR2 con alcance global; el eslabón de autoridad usa la maquinaria de permisos existente, cero infra nueva.
- `scope: Literal["run","domain","global"]`.
- `policy_id: str | None` — enlaza el override con la regla de Policy relajada (cruza con el estampado de §6).

**Regla dura (AX2):** desactivar el propio registro de overrides es, a su vez, un override — se escribe _antes_ de surtir efecto (mismo `events` append-only con REVOKE+trigger, sin excepción para este tipo). **[ejecución]** El `Stage` que aplica un override emite su evento él mismo, vía `EventStore`, antes de aplicarlo (INV-4 — execution/01).

---

## 11 · Evidencia del plano cuántico — campos del claim proponente **[confianza / ciencia]** — quantum/03/04/05/09

> Reubicación v3.2 (convergencia §2.3): `seeds.*` y `circuit_digest` viven en el **schema del claim `simulation_result`** del Perfil STEM (lado proponente); `approximation_ratio`/`se_estimado`/`exact` son **extensión de predicate** de la attestation (lado verificador). Todos aditivos; ninguno debilita formas existentes. **Decididos — ratificación final de Sebas.**

- `circuit_digest: str` — SHA-256 del OpenQASM 3 exacto ejecutado (`qasm3.dumps` → hash; Regla 1 del anexo). El circuito deja de ser anécdota (quantum/03).
- `approximation_ratio: float` — `r = C(candidato)/C_óptimo`; con CP-SAT `OPTIMAL` el denominador es exacto ⇒ r es un hecho (quantum/04). **Regla anti-cherry-picking del enunciado:** r se reporta como media ± std de ≥5 corridas con seeds pinned, por cada p — jamás "la mejor".
- `se_estimado: float` — error estándar por shots (quantum/04). · `exact: bool` — statevector vs muestral.
- `seeds.*` — semillas del proponente (primitive, optimizador, numpy) para replay (quantum/04).
- **Campos de reparación (quantum/05 M.3, registrados — viven en la extensión de limitaciones/constraint-mixers, no en el core Max-Cut):** `repair.method (M.1–M.5)`, `repair.flips`, `repair.pre_value`/`repair.post_value`, `connectivity_violations`.
- **Campos multi-backend (quantum/08 §4, registrados):** `transpiled_circuit_digest` por pata (el circuito rebaseado al gate set nativo — QASM del circuito pytket compilado, o bytes del HUGR en la ruta Guppy — es un artefacto derivado DISTINTO del fuente; sin esto "el mismo circuito en dos emuladores" no es verificable), `backend_id` + versiones por pata de consenso (`aer@x.y`, `selene-sim@x.y`, `H2-emulator`), y `noise_config_digest` (parámetros de error efectivos o `ideal`, canonicalizados — dos corridas con ruido distinto no son comparables; el gate del corrector evalúa contra pares identificados por este digest).
- **Bloque `mitigation.{method, model_digest, training_digest, noise_model_digest, baseline}`** (quantum/09) en el claim proponente cuando el resultado pasó por el corrector AI-QEM. **El corrector propone, jamás verifica (S7/INV-2);** su performance se certifica aparte contra el corpus (modo amortizado §7, techo AL3, controles negativos obligatorios).
- Consenso de muestreo con seeds pinned = pata `consensus_replication` decisoria (AL2); la self-consistency ENTRE MODELOS sigue siendo `Signal` con la convención `{etapa}.{mecanismo}` (§5; ajuste estampado en quantum/04 §4).

## 12 · `Artifact` + `ContentStore` **[confianza / frontera]** — contratos v2 §3.b (ADOPTADO, convergencia §4.1)

Contrato y tabla **nuevos** — el sustrato de `Evidence`, `deliverables` y payloads grandes (hash-first):

- `Artifact {digest (sha256 de la forma canónica — RFC 8785 JCS + NFC), domain_id, media_type, size_bytes, storage_ref, created_at}`; PK `(digest, domain_id)`.
- `ContentStore.put(bytes, media_type, ctx) -> Artifact / get(digest, ctx) / stat(digest, ctx)` — `put()` devuelve el digest: el contenido define su identidad (O3/L3).
- **SO2 — particionado por dominio:** un digest es visible solo dentro de su dominio salvo `Channel` con `read`; la dedup física es optimización interna, **jamás canal de visibilidad** (AX1b/Inv-E). Mismo contenido en dos dominios = dos filas, cero fuga.
- **Alcance del mes (P0-3):** el mínimo que la demo exige — `put/get/stat` sobre Postgres/disco local para evidencia y deliverables del bundle. El resto del diseño (GC, tiering, S3) NO va (lista NO-va, §15.4).

## 13 · `Run` jerárquico + pinning por digest **[frontera]** — contratos v2 §3 (ADOPTADO, convergencia §4.2) + execution/02/03/07

> **[MEJORADO #102 · 2026-07-30] Supersede explícito con causa (cierra C-1):** la
> letra «pipeline fijo Fase 1» de este § quedó reemplazada por el **loop
> agéntico** de la ceremonia #66 (`docs/specs/harness-agentico.md`): el proposer
> decide los steps; la rama sin proposer («pipeline fijo») sobrevive como modo
> de ejecución y de test, no como LA arquitectura. El **criterio step-vs-sub-run
> permanece intacto** (es sub-run la unidad que produce claims propios que el
> certificado citará); el set «formular / QAOA / baseline / verificar» pasa de
> conjunto congelado a **ejemplo del Reto 1**. Todo lo demás de §13 (jerarquía,
> pinning, las 3 reglas [S-F], reintentos) sigue vigente sin cambio. La regla del
> índice de specs («una spec jamás contradice el freeze») vuelve a ser cierta.

- **`Run.parent_run_id?`** — ausente = run raíz. **El case de confianza y el certificado cuelgan SIEMPRE del run raíz (D5);** los sub-runs (formular, QAOA, baseline, verificar) **aportan claims al raíz**. Ajuste sobre execution/07 (que adoptó un stream sin jerarquía): **los streams por run se mantienen** — un stream por run (raíz o sub), la jerarquía viaja en `parent_run_id`, no en streams anidados.
- **Pinning (SO6):** un Run fija por digest todo lo que lo definió al iniciar — `agent_definition_digest?`, `workflow_definition_digest?`, `policy_digest` (obligatorio; mismo patrón R-Pol1). Editar una definición crea versión nueva y no afecta runs en vuelo — precondición de reproducibilidad (D16/AX2).
- Estados del Run: `created → running → {awaiting-verification} → completed | failed | cancelled` (máquina de execution/07; `awaiting-verification` es **sub-estado de proyección**, no de la máquina de eventos — unificación [S-F] de §3). Proyección `runs_projection` con `parent_run_id` + pinning.
- **El runtime es dueño del loop; el gateway es dueño del cruce:** el loop (pipeline fijo en Fase 1 — execution/02; **[MEJORADO #102]** hoy: loop agéntico, ver la marca de arriba) secuencia steps y cada step cruza el gateway completo (§8). `max_steps` obligatorio.
- **Reintentos e idempotencia (execution/03, decidido):** `side_effects` es entrada obligatoria de la lógica de reintento; `pure` se reintenta libre; para `reversible/irreversible-external` **sin idempotencia garantizada NO hay reintento automático en Fase 1** — escala a humano (`human_expert` + override registrado antes, INV-4). El mecanismo fino de idempotencia (keys por `step_id`, verificación activa) queda **declarado como diseño de S-G con dueño Steven** — el contrato del mes es la regla de arriba, que es segura sin él. _(El porqué del endurecimiento sobre execution/03 §1.4 quedó estampado como addendum en la nota — [S-F], regla de oro de la guía.)_
- **[S-F] Las 3 reglas del run jerárquico (sin ellas `parent_run_id` es un puntero decorativo con huérfanos — cierre obligatorio pre-S-G):**
  1. **Cascada de cancelación:** al `run.cancelled` del raíz, el runtime emite `run.cancelled {reason: "parent_cancelled"}` en cada sub-run activo con `actor_id: service:runtime`; los appends post-terminales se **rechazan** (§2) y el job en cola se barre con `JobQueue.cancel(ref)` (infra/02) — el barrido es best-effort; el rechazo de appends es la garantía dura.
  2. **Aporte de claims al raíz:** se materializa como evento en el stream del RAÍZ — **`●ClaimEmitted {claim_digest, sub_run_id, sub_run_provenance_hash}`** — así el `provenance_hash` del raíz ampara transitivamente el trabajo del sub-run (encadenado estilo Merkle). Sin el hash encadenado, `sub_run_id` es un puntero sin integridad y el certificado referenciaría trabajo fuera de su propio hash.
  3. **Herencia de `policy_digest`:** el sub-run **hereda** el del raíz al crearse; divergencia = error de contrato **fail-closed** (mismo espíritu que la reautorización de §8) — un certificado jamás se compone de claims verificados bajo policies distintas.
- **[S-F] Criterio step-vs-sub-run (la pregunta de una línea que los seeds debían responder):** es sub-run SOLO la unidad que produce **claims propios que el certificado citará** (formular / QAOA / baseline / verificar); todo lo demás son steps del loop fijo. Sin árboles profundos (lista NO-va, §15.4).

## 14 · Catálogo de eventos de la capa de confianza ● **[confianza]** — spec v3.2 §3.2 (ADOPTADO, convergencia C4)

Extensión del vocabulario de §3 (● = propiedad de la capa de confianza; ○ = del Engine, consumido):

`●ClaimEmitted · ●PlanCreated · ●PolicyPinned · ●VerificationStarted/Completed · ●AttestationRecorded · ●SignalRecorded · ●ConflictDetected · ●EscalationOpened/Resolved · ●HumanOverrideRecorded · ●CaseClosed · ●CertificateIssued/Reissued/Revoked · ●AnchorRegistered/Superseded/Deprecated/Revoked · ●VerifierRegistered/Superseded/Deprecated/Revoked · ●AttestationSuperseded · ●ExternalCertificateImported · ○PolicyChanged (no afecta cases en vuelo — R-Pol1; endurecimiento ⇒ ●EscalationOpened sobre los cases en vuelo — §6 EX-5)`

**Mapeo con la semilla v2 (C4):** `tool.invoked` ≡ `capability.job.submitted` (el evento de provenance:pre del job); `verification.completed` se conserva tal cual. **Claims como digests en Fase 1 (convergencia §4.3 — acota el scope del mes):** no hay entidad `Claim` ni tabla `claims`; el claim existe como digest en attestations y conclusions del certificado (el claim `derivation` de la demo se emite como digest + attestation). El grafo completo de claims/derivaciones es Fase 2.

**[S-F]** `●ClaimEmitted` lleva el payload de §13 (`claim_digest`, `sub_run_id`, `sub_run_provenance_hash`) **+ los portadores de §6 (`claim_type`, `is_conclusion`, flags de piso) [stress-final]**; `●CertificateReissued/Revoked` = Fase 2 declarada (§7). El `claim_digest` tiene vista canónica propia en el anexo (`view(claim)`, vector V6 — T7: sin ella, dos implementaciones honestas producían digests distintos). Nota de numeración (T16): las referencias `D#` de este documento apuntan a la **base lógica formal** (D1–D22); la spec v3.2 usa una numeración `D1–D5` interna propia — no son el mismo espacio.

> **[MEJORADO #102 · 2026-07-30] Extensión ADITIVA del catálogo — los eventos de
> la ceremonia #68 que el código YA emite (§14 nunca se declaró conjunto
> cerrado):** `●PlanItemUpdated` (`plan.item_updated` — `engine/src/blite/runtime/plan.py`;
> `●PlanCreated` ya estaba en el catálogo) · `●ReplayDivergenceDetected`
> (`replay.divergence` — `engine/src/blite/runtime/replay.py`; lo consume el
> punto 8 del checklist §7) · `●ApprovalRequested` / `●ApprovalResponded`
> (`approval.requested`/`approval.responded` — `engine/src/blite/gateway/approval.py`).
> Reservado: `●MissionMessage` (`mission.message`) entra cuando M1/P3 lo traiga.

## 15 · Decisiones de cierre S-E (todas tomadas — ratificación final por dueño)

### 15.1 Doctrina de soberanía y egreso de datos de red **[confianza]** (P1-1)

**El QUBO con pesos `flujo` ES la topología con MW reales** — relabelar buses no anonimiza (isomorfismo). Doctrina congelada: **los datos de red del cliente jamás egresan; el emulador/QPU cloud solo ve instancias sintéticas o públicas** (IEEE, cr8 desde datos abiertos oficiales del ICE). La clasificación de dato es aplicable por Policy (clase de dato → egreso permitido; **default deny** para datos de red reales); un ancla/backend que exigiera egreso no autorizado no es seleccionable (`anchor_requires_unauthorized_egress` — Inv-E en el plan). `audience_profile: redacted` = **Fase 2 declarada** (el certificado full embebe evidencia ⇒ puede portar la instancia; se dice en el pitch antes de que lo pregunten). Modo 100% local: Selene + Aer (quantum/08).

### 15.2 Posición operativa declarada **[equipo/pitch]** (P1-4)

**Chimera es análisis y verificación fuera de línea; no se conecta a SCADA/EMS ni actúa sobre la red; su salida es un expediente certificado que alimenta el procedimiento de aprobación vigente del cliente.** El humano de `human_expert` es el ingeniero responsable del procedimiento del cliente (planeamiento/protecciones), no el despachador en el lazo. PR4 bloquea lo irreversible por construcción; el sistema solo propone.

### 15.3 Corpus: mapeo `dataset_id`↔digest + segunda ancla de ieee30 **[ciencia]** (cierra el punto 2 del freeze anterior)

**Regla de identidad (decidida):** `dataset_id = "islanding-corpus/<instancia>-<convencion>@v1"`; el digest es el **embebido** en cada JSON (SHA-256 del JSON canónico sin el campo `digest` — islanding/01 §1.6; el archivo congelado manda: una regeneración que no reproduzca el digest se reporta, no se sobreescribe). El `dataset_id` + digest identifican el ancla en `evidence`/`anchor_binding`.

| `dataset_id`                          | digest (sha256)                                                    |
| ------------------------------------- | ------------------------------------------------------------------ |
| `islanding-corpus/ieee6-uniforme@v1`  | `bcce660e0dac057db322999496612bb48b1f51e947180b7f8c77af5b4bca2928` |
| `islanding-corpus/ieee6-flujo@v1`     | `0e29de1161f14dcdd5a9ffe3e9620f52868197e46b931e35a39b04611411a9e5` |
| `islanding-corpus/ieee9-uniforme@v1`  | `dee38cdeea9bb35305de94308169368216838503673d3be57f0e7bea42677520` |
| `islanding-corpus/ieee9-flujo@v1`     | `59fb22e6ec0afd3b3caf34fb4e46b2f8003c1ea8524fcd8b06dabd3f1c52477b` |
| `islanding-corpus/ieee14-uniforme@v1` | `fb9c3780d9cf06a25910b631e92c83f3c6ce5272192f216fee6101b12dd32bd4` |
| `islanding-corpus/ieee14-flujo@v1`    | `c7880bb0d254d2d5f91c21cfd7cf0a5ac1cb9c88261c15b94cb7b22d6fd896ad` |
| `islanding-corpus/ieee30-uniforme@v1` | `a864122e83585d19921fcb00857aea1b8f4f4248a291a7a6f9d98e1b2df25a5b` |
| `islanding-corpus/ieee30-flujo@v1`    | `a3aed52a8c59cc2a1e44073995eb755e75e04725e997729d0fc8f662ad08c600` |

**`ieee6` (D5, 2026-07-23):** instancia REAL de 6 nodos derivada de `pandapower.networks.case6ww` por la MISMA receta congelada (script §1.9 sin cambios de forma; doble ancla CP-SAT + fuerza bruta, `n=6 ≤ 14`) — stand-in reproducible mientras la instancia ICE "provincia" (P0-7 abajo) sigue diferida; ver `docs/mvp/decisiones.md` fila D5.

**`ieee14-topology@v1` (D3/D4, Task 2, 2026-07-23) — dato eléctrico para `ExecutionVerifier` (formato buses/slack/branches/loads + limits, NO el formato Max-Cut de la tabla de arriba):** `dataset_id = "ieee14-topology@v1"`, digest = `5f2725a9fa2e4dbc61f5a4ad9757da7c24c2a19ce5245419469895ce589ce637`. Vive en `knowledge/islanding/ieee14-topology.json` (fuera de `corpus/` a propósito — no cuenta para el guard de 8 archivos de `verify_corpus_digests.py`), generado por `scripts/gen_ieee14_topology.py`. Modelo declarado single-voltage (`V0=110kV` uniforme en los 14 buses) — grafo (20 aristas) y cargas SÍ son de `case14()`; slack = los 5 buses-fuente `[0,1,2,5,7]` (convención slack-por-isla); impedancias por rama son UNIFORMES declaradas (`r=0.5, x=1.5 ohm`) porque la derivación fiel per-rama de case14 (líneas nativas + trafos `vk_percent→z_ohm`) no converge para la red completa (`pandapower.diagnostic`: 13/20 ramas con impedancia casi nula al reescalar sobre 110kV) — fallback honesto del brief, documentado en `provenance` del JSON y en `docs/mvp/decisiones.md` fila D4. Verificado con `ExecutionVerifier` real (pandapower, sin mocks) en `tests/integration/verification/test_ieee14_topology.py`: red completa → `pass`, bipartición válida `{0..5}|{6..13}` (ambos lados conexos, cada uno con fuente) → `pass`, bipartición inválida `{0..6}|{7..13}` (isla `{7..13}` desconectada) → `fail` por `island_connectivity`. PENDIENTE ratificación Sebas (misma fila #5 de `decisiones.md`).

IDs **reservados** para las instancias de P0-7 (dueño Sebas — datos abiertos del ICE): `islanding-corpus/cr8-{uniforme,flujo}@v1` y `islanding-corpus/cr6-{uniforme,flujo}@v1`; sus digests se estampan aquí al congelar los JSON (misma regla, doble ancla, fail-loud). **[MEJORADO C-10]** La variante `-flujo` nunca se materializó: los archivos reales son `-voltaje` (suma de kV de circuitos paralelos como peso) — estampado abajo.

> **[MEJORADO C-10/#106 · 2026-07-30] Estampado de la realidad — cr6/cr8/ice
> (cierra el ex-PENDIENTE §1.9 con la identidad decidida `-voltaje@v1`):** los 6
> archivos que faltaban en la tabla, con el digest **embebido** de cada JSON
> (misma regla de identidad de arriba). **Nota de procedencia (variante
> declarada, jamás regenerar sobreescribiendo):** cr6/cr8 traen doble ancla
> `bruteforce+spectrum` **del espejo** `reto1-vanilla` (≠ receta §1.9
> CP-SAT+bruteforce — la procedencia del ancla difiere y se DECLARA, no se
> esconde; su `criterio_corredor` cita `scripts/build_cr_instances.py`, script
> que vive en el espejo, no en este repo). Las `ice-*` (red ICE-70 real) tienen
> `optimo: null` — sin ancla de óptimo; quedan fuera del endpoint rvsp (C-9).
>
> | `dataset_id`                       | digest (sha256)                                                    |
> | ---------------------------------- | ------------------------------------------------------------------ |
> | `islanding-corpus/cr6-uniforme@v1` | `e8b2121c61399aa758a356835f1e849e435377ebc2eadf0dd08356c702b680db` |
> | `islanding-corpus/cr6-voltaje@v1`  | `aab9f07fd8e7f6be84d90fc97493de3603b82b3dec80627699051dc706e3dd0c` |
> | `islanding-corpus/cr8-uniforme@v1` | `66bb6c5ae0eadb1c697436ea36c069b3bf3c3a4ef436d1eda9540a3e79f91392` |
> | `islanding-corpus/cr8-voltaje@v1`  | `0af00267250f0838ce5445659238c180fe88771383001aa4c745e36462d1aa5b` |
> | `islanding-corpus/ice-uniforme@v1` | `0078d201ff590345598ab0d7698a724cc642eaec4dca660a4ec66361402485a7` |
> | `islanding-corpus/ice-voltaje@v1`  | `7bcda6747ac19bda4f8ef9cedc87a5d8c1185a459a08c5c6beb9662ee12d9d0d` |
>
> El re-estampado de **ieee30** (identidad tras la 2ª ancla, N13) y el análisis
> de flips §15.5 repetido para cr6/cr8 siguen en el backlog (ítem O6/M30) — esta
> marca no los resuelve.

**Segunda ancla de ieee30 (decidida):** **enumeración exhaustiva vectorizada** (numpy por bloques, x₀=0, 2²⁹ asignaciones — cero dependencias nuevas, independiente de CP-SAT), integrada al script de islanding/01 §1.9 **(⚠ [S-F-real]: aún NO integrada; forma de identidad pendiente — ver supersesión abajo)** con presupuesto explícito. **[S-F] Presupuesto medido CON spec de máquina:** 11.5 s por bloque de 2²⁴ ⇒ **~6.1 min/convención, ~12.3 min ieee30 completo** (Intel i7-10510U @ 1.80 GHz, numpy 2.5.1 mono-hilo, ~0.3 GiB; otras máquinas midieron 11.4–13.5 s/bloque — el presupuesto se cita siempre con la máquina). La cota superior del SDP de Goemans-Williamson (cvxpy, ya obligatoria por Δ6) se registra como **chequeo de cordura adicional** (UB ≥ óptimo), no como ancla. Ratificación final de Sebas = correr y comparar digests.

> **[S-F-real · 2026-07-21] Segunda ancla de ieee30 — corrida registrada; re-estampado PENDIENTE (ratificación Sebas §1.3).** La enumeración exhaustiva vectorizada se corrió y se confirmó por auditoría independiente (2²⁹, x₀=0): **uniforme=35, flujo=32170** (== óptimos congelados). Integrarla al script §1.9 muta `metodos`→`["cpsat","bruteforce_vectorized"]` ⇒ cambian los 2 digests de ieee30 y **dejan de coincidir con la tabla `@v1` de arriba**. **NO se re-estampa aquí:** (a) la identidad es decisión de Sebas; (b) el enumerador aún **no** está integrado a §1.9 (`FUERZA_BRUTA_MAX_N=14` salta n=30). Falla sembrada (§15.5) confirmada por recompute: ieee14-flujo **bus 1** (0-based; Bus 2 en IEEE 1-based) → corte 32597, gap 24473; buses prohibidos por degeneración [7] (flujo) / [0,1,11] (uniforme).
>
> **[convergencia EC-3 · 2026-07-22] La identidad tiene TRES formas candidatas — la decide Sebas, ninguna se aplica hasta su palabra:** (a) **re-estampar `@v1`** con los digests nuevos (la dirección del aviso real de Sebas — "este reporte ES el aviso" honra "se reporta, no se sobreescribe"); (b) **`@v2`** con supersesión registrada (identidad nueva, tabla gana dos filas); (c) **attestation externa sobre el MISMO digest** (la forma que argumentó la auditoría simulada: `metodos` describe los métodos del **generador** y la historia de verificación vive en attestations, no en la identidad del ancla — doctrina VALID_AS_OF; los JSON no se mutan).

**[S-F] Cumplimiento del rango oficial (E1 — lo primero que un juez técnico cazaría):** el enunciado pide "red regional REAL de 6–12 nodos" y NINGUNA instancia actual lo satisface (ieee9 = 9 pero sintética; ieee14/30 fuera de rango) — cr8/cr6 dejan de ser deseables: son **P1 con gate de fecha ~25-jul y fallback declarado**. Los datos ArcGIS del ICE dan topología ⇒ **`cr8-uniforme`/`cr6-uniforme` son construibles solo-topología** (la convención `uniforme` no exige caso de flujo corrible); si el caso de flujo no se modela a tiempo, cr8/cr6 nacen solo `uniforme` con assumptions declaradas y el opener del demo cae a ieee9. El análisis de flips de §15.5 se repite al congelarlos (E5). _(Gate, modelado del caso de flujo y fallback: ratificación de Sebas — convergencia EC-6; su ratificación real reporta "datos ICE validados; falta corredor + peso".)_

**Estratificación de claims del Reto 1 (Δ1 — el corpus NO se regenera):** el core = optimalidad **Max-Cut** (formulación oficial) con ancla `formal_exact` contra el corpus tal como está; los chequeos físicos (`island_connectivity`, `power_balance`) se re-scopean como **análisis de limitaciones + extensión oficial "constraint mixers"** — sus claims son de la extensión, no del camino crítico del core. Escalera de instancias del demo: **cr8 (core, en vivo) → ieee9 (verificación QUBO) → ieee14 (escalado, instancia viva pinneada) → ieee30 (SOLO clásico / extrapolación honesta — el H2 topa en 26 qubits)**.

### 15.4 Camino dorado P0 del demo + lista NO-va **[equipo]** (P0-3)

**Camino dorado congelado (se protege hasta el final):** run → claim → verificación (CP-SAT + pandapower + corpus) → certificado DSSE → CLI verificador offline (`scripts/verify-bundle.py`) → Studio SSE con badges por isla — sobre **ieee14 en vivo** (+ cr8 al llegar), compose air-gapped, **falla sembrada refutada con `fail`** (15.5), video de respaldo integrado.

**Lista NO-va del mes (cortada EN el freeze — el diseño queda, la construcción no):** Artifact/ContentStore completo (solo el mínimo §12) · Run jerárquico completo (solo `parent_run_id` + claims al raíz; sin árboles profundos) · grafo de claims/derivaciones completo (§14 — digests) · MCP de salida (semana 3/bonus si sobra) · Fase-2 entera (hash-chain, StatusList, Receipt, redacted, OpenBao/HSM, SPIFFE, Rekor) · **Fargate o EKS [S-F]** (stretch: solo si el local quedó verde el 27 — P1-10; ratificación verbal de Geovanni 19-jul: **todo el mes se trabaja LOCAL**) · LLM generando en vivo (`MODEL_ROUTER_BACKEND=replay` es config de primera clase — P1-8; los backends vivos son por API, §15.7 [S-F]) · emulador Quantinuum en vivo (patas pre-corridas con digests; en vivo solo Aer+seed — P1-7) · IEEE-30 como corrida cuántica (P1-6) · corrector AI-QEM en vivo (panel pre-entrenado con gate de fechas — P2-2).

**Walking skeleton obligatorio en 48h post-freeze** (compose postgres+api+studio con UN evento real de punta a punta — dueño Steven) + **todas las deps (Python y npm) en un solo PR de S-G** (la cuarentena npm de 14 días bloquearía la semana de integración — P2-4).

**[S-F] Compose canónico del mes (O6 — ningún documento normativo lo fijaba):** `postgres + api + worker + studio` (worker = misma imagen que api, proceso `procrastinate worker`; `ollama` queda SOLO como perfil opcional heredado, fuera del camino por defecto — §15.7). El walking skeleton (`postgres+api+studio`, sin worker) es el primer hito, **no** el compose del mes.

### 15.5 La falla sembrada como fixture determinista **[confianza + ciencia]** (P0-4)

El clímax del demo es contrato, no improvisación: **fixture determinista** — mover 1 bus de isla en la partición verificada ⇒ recompute clásico + CP-SAT dan **`fail` en milisegundos** con ratio degradado visible; **seed pinned; regla dura: el vector JAMÁS aterriza en `inconclusive`** (se elige el bus para que la refutación sea inequívoca). Entra a S-G como **seed de test con su vector congelado** (dueños: Dylan diseño/guion, Sebas vector). Guion: partición verificada por isla → certificado emitido → verify OFFLINE en segunda máquina → trampa sembrada → refutada en vivo.

**[S-F] Vector CONGELADO (el bus NO se elige a ojo — el cómputo real de los 14 flips lo probó):** instancia = **ieee14**, convención = **flujo**, bus = **1** (0-indexed; bus de generación — "mover un generador de isla" se cuenta solo): corte degradado **32 597** vs óptimo **57 070** (ratio **0.5712** — visualmente dramático), respeta x₀=0, refutación = recompute contra el corpus en milisegundos, `fail` inequívoco. **Minas documentadas:** en ieee14-flujo el flip del bus 7 degrada **CERO** (óptimo degenerado — daría "mismo valor", exactamente el escenario que esta sección prohíbe; el guion gana una línea: "hasta el óptimo tiene testigos múltiples"); en ieee14-uniforme los buses 0, 1 y 11 también degradan cero — por eso la **convención queda pinneada**, no solo la instancia. Evitar bus 0 siempre (rompe x₀=0). **E5:** el análisis de flips es parte del procedimiento de congelamiento de cr8/cr6 — si el clímax migra a cr8, la mina puede reaparecer. Ratificación final del vector: Sebas (el criterio narrativo del bus es suyo; el matemático ya está computado y verificado 2×).

### 15.6 Regla de umbral + modo amortizado **[confianza]** (P0-5 — resuelto en la spec y el perfil)

La 3ª condición ("existe ancla decisoria dentro de presupuesto; si no ⇒ gap declarado"), la cláusula de cartera (riesgo agregado) y el patrón nombrado **"case de certificación de capability"** quedaron congelados en la [spec v3.2 §1](spec-confianza-v3-2.md); la cláusula STEM ("sin ancla ex ante ⇒ certificación amortizada + Signal en operación, jamás por-resultado") en el [Perfil STEM §4.7](perfil-stem-v1-0.md). El anti-slop es doctrina ejecutable: en C0 el sistema dice "no verifiques".

### 15.7 Egress del model router: `ModelPort` / `ModelServer` **[frontera]** (execution/09 — decidido, ratificación final Steven + Dylan)

> **[MEJORADO N12 · 2026-07-30] Nota de reconciliación de nombre (aplica a TODO
> este doc):** la letra congelada dice `MODEL_ROUTER_BACKEND` (aquí, en §7 y en
> §15.4); el nombre REAL implementado es **`CHIMERA_MODEL_BACKEND`**
> (`api/src/chimera_api/runs.py`, `compose.yaml`) — el código jamás usó el nombre
> viejo. Toda aparición de `MODEL_ROUTER_BACKEND` en este doc se lee como
> `CHIMERA_MODEL_BACKEND` (con `CHIMERA_MODEL_SESSION_DIR`/`CHIMERA_MODEL_ID`
> como acompañantes del modo replay). La letra congelada no se reescribe; esta
> marca la reconcilia.

- **`ModelPort`** (Protocol) vive en `blite.serving` — router puro, cero red (AX3 por construcción, incluida la cadena transitiva `litellm → httpx`); forma = la de la semilla v2 §7 (`id`, `local: boolean` — D19 local-first, `complete()`).
- **`ModelServer`** = el adapter que lo implementa, vive en `blite.protocols` — hereda el contrato de layers **INV-6 (protocols exige authz)** sin gate nuevo; envuelve **LiteLLM SDK (`Router`)** con un solo `model_list` seleccionado por el `DistributionManifest` — mismo router en todos los entornos, **más el backend `replay`** (P1-8: prompt fijo + respuesta cacheada) como config de primera clase.
- **[S-F] Backends del mes = modelos por API con keys (supersesión — ratificación verbal de Geovanni, 19-jul):** nadie del equipo tiene máquina para servir un modelo local con potencia útil ⇒ el `model_list` real son **modelos por API** (Anthropic + modelos abiertos servidos por API), con keys como **secretos del despliegue** (file-based en compose, jamás en la imagen ni en el repo — infra/03); `local: false` en esos backends dice la verdad de D19 y el certificado no la esconde. `ollama_chat/` queda como **perfil opcional archivado** (la forma no cambia: mismo Router, mismo puerto — si Fase 2 exige serving propio, se reactiva). **El día D no cambia:** `replay` sigue siendo la config de primera clase del demo air-gapped; los fixtures se **graban en los ensayos** contra las APIs.
- **[S-F] Contrato del backend `replay` (P0 — la config del día D no era construible con lo escrito):** (1) **miss ⇒ `model.call.failed {error_kind: "replay_miss"}`, JAMÁS passthrough a red** — un fallback silencioso a API en pleno demo air-gapped es exactamente lo que este freeze prohíbe para el despacho; (2) clave del fixture = digest **Regla 2** (anexo) sobre el request canónico **incluyendo `backend_id`/modelo**, con prefijo de dominio versionado `blite/model-replay/v1` — dos backends con el mismo prompt no colisionan; (3) fixtures **content-addressed en el `ContentStore` con `domain_id`** (SO2); (4) el SET de fixtures del día D se pinnea por digest en un **manifest de replay** — el modo grabación no puede mutar la config del demo en silencio; (5) modo grabación (`record`) explícito y separado del modo demo (`replay`).
- **[S-F] Contratos citados sin semilla (N5 — registro, no cambio):** `Registry`, `DispatchStrategy`/`Dispatcher`/`JobRef`, `RunStep`, `KeyProvider` van **directo a Python en S-G**; la semilla v2 no se amplía retroactivamente.
- El gateway cablea: la etapa `mediation` ejecuta la decisión de `serving.route()` a través del puerto inyectado. Eventos: `model.call.*` (§3). Endurecimiento opcional del gate AX3 (agregar `litellm`/`openai`/`anthropic` a forbidden) = tarea de S-G.
- Descartados: LiteLLM Proxy este mes (proceso extra fuera del import-linter; candidato Fase 2 — la delimitación de sus features enterprise queda como chequeo previo si Fase 2 lo retoma), vLLM (producción self-hosted), OpenRouter (cede la mediación soberana), modelos dentro del Registry de capabilities (PR2).

> **[S-F-real · 2026-07-21] Supersesión del modelo del demo — ratificación Geovanni ítem-4 + decisión cruzada Steven+Dylan (resuelta).** El LLM local `llama3.2:3b` se reemplaza por **Ollama Cloud passthrough** (tag cloud, p. ej. `gpt-oss:20b-cloud`) por límite de hardware: el binario `ollama` proxea a la nube; se suma `OLLAMA_API_KEY` (custodia escalón 1, §7) + salida a internet. Esto **rompe el air-gap** ⇒ el **recinto air-gapped/offline queda como Fase 2** (§15.8); la **soberanía-lógica sigue activa** — el cloud solo ve instancias sintéticas/públicas (§15.1), no dato de red real. El día D corre `MODEL_ROUTER_BACKEND=replay` (§15.4: LLM en vivo = NO-va). **LiteLLM se MANTIENE** (aval de Steven + requisito de Dylan: router multi-proveedor Anthropic+Ollama, delegación por tarea); "Ollama Cloud" es **una entrada del `model_list`**, no una razón para dropear el router. `ModelPort`/`ModelServer` + `replay` intactos. Endurecimiento aplicado: contrato import-linter **AX3-b** (SDK de modelo importable solo por `blite.protocols`). Licencias del árbol multi-proveedor verificadas limpias (openai/anthropic Apache-2.0/MIT; cero copyleft).

### 15.8 Huecos declarados (no son decisiones abiertas — son trabajo futuro con dueño)

| Hueco                                                                | Fase        | Dueño            |
| -------------------------------------------------------------------- | ----------- | ---------------- |
| Mecanismo fino de idempotencia para pasos external (§13)             | S-G diseño  | Steven           |
| Ciclo de vida del recinto air-gapped (bundles firmados en frontera)  | Fase 2      | Geovanni (P3-2)  |
| Historia de procurement CR (entidad, ARESEP/CGR/Ley 8968) + ⚠️ PyJWT | pre-flip    | Dylan (P3-1)     |
| README pre-flip (una línea que subordine identidades)                | pre-flip    | Dylan (P3-4)     |
| North-star "certificados re-verificados por terceros"                | post-evento | Geovanni + Dylan |
| Vocabulario común `workspace_id`/`principal_id` (infra/01 §I) [S-F]  | S-G diseño  | Dylan + Geovanni |
| Fórmula oficial de r citada verbatim del enunciado (E2) [S-F]        | pre-S-G     | Sebas + Dylan    |
| `replication_protocol` versionado con digest (E3) [S-F]              | S-G seed    | Sebas            |

---

## Dependencias nuevas que este freeze implica

| Dependencia                          | Licencia                                                                                                                                                                                                                  | Rol                                                        |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| ortools (CP-SAT)                     | Apache-2.0                                                                                                                                                                                                                | ancla `formal_exact`                                       |
| pandapower                           | BSD-3 — **floor `>=3.5.4` [S-F-real]** (la sim fijó `>=3.3` tras el crash 3.1.2+numpy 2.5.1 en `runpp`; el real endureció a `>=3.5.4` en engine y `capabilities/sim` — receta §1.9 re-verificada 6/6 con el lock vigente) | ancla `execution`                                          |
| hypothesis                           | MPL-2.0 (no vendorizar)                                                                                                                                                                                                   | `property_rule` + property-tests de contratos              |
| cryptography (Ed25519)               | Apache-2.0/BSD                                                                                                                                                                                                            | firma del certificado                                      |
| **cvxpy**                            | Apache-2.0                                                                                                                                                                                                                | **Goemans-Williamson — baseline oficial obligatorio (Δ6)** |
| **litellm** (SDK `Router`)           | MIT — carve-out: jamás importar `enterprise/`; pinear                                                                                                                                                                     | adapter `ModelServer` (§15.7)                              |
| PyJWT                                | MIT ⚠️ verificación en vivo en el checklist pre-flip                                                                                                                                                                      | identidad lite                                             |
| mcp python-sdk                       | MIT — **pinear v1.x** (v2 beta rompe)                                                                                                                                                                                     | adapter MCP de salida (semana 3/bonus)                     |
| cytoscape 3.34.0 / tailwindcss 4.3.1 | MIT                                                                                                                                                                                                                       | Studio (ya instaladas)                                     |

(Las deps del walking skeleton — fastapi, uvicorn, procrastinate, psycopg, etc. — van TODAS en el PR único de S-G, §15.4.)

## Qué NO cambia

- `docs/invariants.md` y `docs/base-logica-formal.md` — congelados; **nunca bajo revisión**. Todas las notas reconcilian contra ellos sin excepciones; el set v3.2 los cita como su constitución y aporta el **control de constitucionalidad** (adoptado como práctica de todo delta futuro).
- `AnchorKind` sin `"model"`; INV-1…6, AX1/AX3, Inv-E, ADR-008/029 y sus gates.
- Tablas semilla `domains`, `channels`, `identities` — confirmadas tal cual (v2).
- Los diseños internos de los adapters (trust/10/11/12), el registry (execution/04), el serving (execution/06), la cola/infra (infra/01–03), el corpus (islanding/01 — gana metadata de `Anchor` y la segunda ancla §15.3) y el SSE (trust/07).
- Nada de SPIRE/OPA/Cedar/in-toto-lib/Sigstore/microVM se integra este mes: **formas estudiadas, lites propios**.

## Registro de cierre (S-E, 2026-07-18)

1. **Merge [ejecución] completado** — las 9 notas del plano de ejecución incorporadas arriba (§1, §2, §3, §5, §8, §13, §15.7); las preguntas que dejaban abiertas quedan decididas o declaradas con dueño (§15.8). El encabezado histórico "pendiente merge con las correcciones de Steven" queda satisfecho.
2. **Ratificaciones finales por dueño** (marcas de revisión, no decisiones abiertas — modelo de operación del roadmap): Steven → §1/§3/§8/§13/§15.7 · Sebas → §11/§15.3/§15.5 (correr script del corpus + digests) · Geovanni → escalón HSM §7 (frontera infra/secretos) + §15.8 · equipo → §15.2/§15.4.
3. **Traducción a Pydantic/SQL real = S-G** (seeds de specs/tests por plano; `challenge1/reproduce.py` + fixture de la falla sembrada + `scripts/verify-bundle.py` + PR único de deps), TDD, gates verdes.

## Registro de cierre (S-F, 2026-07-20 — auditoría de ratificación · PORTADO 2026-07-22 tras veredicto CONVERGEN)

> Las supersesiones [S-F] de este documento nacieron en el track simulado (rama de ejercicio,
> read-only) y se portaron a esta rama el 2026-07-22 tras el veredicto **CONVERGEN** de la matriz
> simulada↔real (`docs/research/convergencia-simulada-real-sf.md`) — ver el Registro de convergencia
> al final. Donde el track real decidió distinto, **el real manda** (adaptaciones listadas allá).

1. **Causa y fuentes.** Auditoría adversarial de la ratificación: acta simulada por dueño + validación a profundidad con postura de refutación (rama de ejercicio — todos los hallazgos confirmados contra evidencia primaria del repo), **más la ratificación verbal de Geovanni (19-jul, registrada por Dylan 20-jul):** todo el mes se trabaja **local**; cloud solo si sobra tiempo (confirma y amplía P1-10); modelos **por API keys** (nadie corre modelo local). _La ratificación real ESCRITA de Geovanni (ítem-4, 21-jul) supersede el detalle del modelo: **Ollama Cloud passthrough** — ver Registro S-F-real._ Ninguna supersesión [S-F] reabre una decisión de diseño congelada.
2. **Aplicado en este barrido:** semillas v2 completadas contra la máquina congelada (`cancelled` en union y CHECK, `max_steps`, `awaiting-verification` como sub-estado de proyección, `unanchored_steps`/`coverage_stats`, CHECK `pass ⇒ ancla`, `independence_group`, `run_id` en attestation, `Detector`/`Signal`, `AuthzDecision` en egreso, `anchor_kind`) · 3 reglas del run jerárquico (§13) · matriz `interaction × execution_profile` al cargar el DistributionManifest (§1) · streams de sistema + rechazo post-terminal (§2) · contrato `replay` de 5 puntos (§15.7) · fixture de la falla sembrada congelado: ieee14-flujo bus 1 (§15.5) · segunda ancla ieee30: corrida ejecutada + presupuesto medido (§15.3 — la FORMA de identidad quedó ABIERTA, la decide Sebas) · Policy del repo a vocabulario C0–C3, versión 0.2.0 (§6) · titular computable + DSSE Fase 1 + checklist de `verify-bundle` de 7 puntos + una-emisión-por-run (§7) · compose canónico (§15.4) · `view(claim)` + V6 en el anexo · fallback `cr8/cr6-uniforme` con gate ~25-jul (§15.3).
3. **Asignaciones corregidas del punto 2 del registro S-E (supersesión cosmética única):** equipo → §15.2/§15.4 **+ §4-AcceptanceAuthority** · Steven → además de lo listado, los ítems [ejecución] de §2 (durabilidad = replay del log), §5 (egress solo `AuthzDecision`), §10 (el Stage del override emite su evento) y §12 (frontera del ContentStore) · Geovanni → "§15.8 (sus filas)", no la tabla completa · el modelo del router (§15.7, antes "Ollama ~3B") es decisión Steven+Geovanni — resuelta en la ratificación real (Ollama Cloud + LiteLLM se mantiene).
4. **Solo los dueños reales cierran** (la auditoría no los sustituye): **Sebas** — forma de identidad de ieee30 (3 opciones, §15.3) · criterio físico/narrativo del bus 1 · modelado de cr8 desde datos GIS · si 5 corridas seeds-pinned bastan como independencia AL2. **Steven** — cascada de cancelación (su runtime) · el fail-closed de `replay` por escrito · matriz `interaction×profile` (su Dispatcher) · el endurecimiento del reintento (addendum ya estampado en su nota 03). **Geovanni** — ¿el "baseline Terraform externo" (infra/01 §R.2) existe? · expectativas sobre Pulumi · fechas 27/29 vs disponibilidad real · tabla de licencias L · spec del equipo del demo (RAM). **Equipo** — posición operativa VERBATIM (§15.2, con "del cliente") · corte camino-dorado/NO-va · firma de AcceptanceAuthority.
5. **Proceso (parches a silencio=ratificación) — VENCIDO por los hechos (21-jul):** los tres dueños respondieron dentro de la ventana y Sebas ejecutó sus ítems (corpus 6/6 ×2, enum ieee30, flips). Queda como doctrina para futuras ratificaciones: ack mínimo obligatorio, escalación de Dylan al día-menos-uno, ítems ejecutables jamás ratificables por silencio.

## Registro de cierre (S-F-real, 2026-07-21)

> Supersesión con causa de las ratificaciones **reales** (auditoría en
> `docs/research/ratificacion-real-sf.md`; stress test pre-B: **GO condicional**). Aplicada en la rama
> `ratificacion/consolidacion-sf`. **No re-litiga lo congelado**; `docs/invariants.md` y
> `docs/base-logica-formal.md` quedan intactos. La comparación simulada↔real y la convergencia son el
> paso POSTERIOR.

1. **Ratificado — código ya aplicado por los dueños (verificado por corrida):** deps del walking
   skeleton + endurecimiento de AX3 (`0f74343`); fix utf-8 de tests (`a1cd49e`). Gates:
   import-linter **10/10**, pytest **101 passed**, ruff, `tsc` 0. Corpus **6/6 digests** reproducen con
   la receta oficial; ieee30 **35/32170** por enumeración independiente.
2. **Modelo del demo (§15.7):** Ollama Cloud passthrough + `OLLAMA_API_KEY`; **LiteLLM se mantiene**
   (multi-proveedor). Causa: ratificación Geovanni ítem-4 + cruzada Steven+Dylan resuelta.
3. **Segunda ancla ieee30 (§15.3):** corrida registrada (35/32170); **re-estampado pendiente de Sebas**
   (identidad @v1/@v2), **no automático**.
4. **Endurecimientos del stress test pre-B (aplicados):** contrato import-linter **AX3-b** (SDK de
   modelo solo vía `blite.protocols`); `encoding="utf-8"` completo en tests; `secrets/` +
   `.dockerignore` + `OLLAMA_API_KEY` pre-flip; floor `capabilities/sim` `pandapower>=3.5.4`.
5. **MARCADO (no cerrado por el auditor):** 4 `[COMPLETÁ VOS]` de Geovanni (custodia §7, demo dual §3,
   calendario §5, huecos Fase 2 §15.8); identidad @v1/@v2 de ieee30 (Sebas); cr8/cr6 (trabajo, CORE del
   demo en vivo); fusión `kb2-05`→`quantum/08`; **flip del `xfail` de AX1** (cuando el gateway estampe
   identidad — `invariants.md` lo condiciona así); bugs operativos del compose de diseño
   (`DATABASE_URL` sin credencial, SSE sin `proxy_buffering off`) → parte del demo-dual de Geovanni.
6. **Riesgo dominante → S-G (lo gritó el stress test):** el **plano de confianza vive pre-freeze en
   código** — vocabulario `rung` muerto (engine/Studio/`policy.py`/`verification-default.yaml`), forja
   de `pass` sin ancla (`anchor_digest` nullable, sin CHECK), `scripts/verify-bundle.py`/`api`/compose
   inexistentes. **Es el diferenciador indefenso en código; prioridad #1 de S-G.** Ninguna decisión
   congelada quedó invalidada; lo profundo (anti-inyección, canonicalización, INV-2, falla sembrada)
   aguantó el ataque. _(Actualización 2026-07-22: la parte "vocabulario muerto en `policy.py`/YAML" y
   la banda de `C(x)` quedaron CERRADAS por el porte de convergencia; el Studio, `attestation.py`,
   `verify-bundle.py`/api/compose siguen siendo la prioridad #1 de S-G.)_

## Registro de cierre (convergencia S-F, 2026-07-22)

> Veredicto **CONVERGEN** de la matriz simulada↔real (`docs/research/convergencia-simulada-real-sf.md`):
> cero conflictos sin resolver · cero P0 nuevo sin fix aplicable · ninguna decisión congelada
> invalidada · la sustancia del freeze sobrevivió ambas fuentes (doble GO adversarial + re-stress).
> Este barrido **porta a esta rama el cuadrante C-verificable** — fixes ya escritos y verificados con
> gates verdes en la rama de ejercicio (read-only) — como manda el protocolo ("la sim es el piso").

1. **Portado — código:** Policy **0.2.0** (vocabulario C0–C3; YAML + schema + `policy.py` + tests) ·
   `C(x)` **ECMAScript-conforme** en la banda `[1e-6, 1e-4)` (notación fija) + vectores V5 de banda +
   generador de vectores deduplicado hacia el engine. Gates: pytest **112 passed**, V1–V6 intactos.
2. **Portado — spec/docs:** semillas v2 completas · supersesiones [S-F] de este documento (§1, §2,
   §3, §4, §6, §7, §13, §14, §15.3–§15.5, §15.7, §15.8, deps) · anexo `view(claim)`/V6 · guía ·
   `deployment.md` · KB (islanding/01, infra/03, execution/03/08, quantum/02/04, trust/15).
3. **Adaptaciones del porte (el real manda — cuadrante D y C-dueño de la matriz):** la identidad de
   ieee30 queda **ABIERTA** con 3 formas candidatas y la decide Sebas (§15.3 — la sim proponía
   attestation-externa; el aviso real de Sebas apuntaba a re-estampar; convergencia EC-3) · el modelo
   del demo es **Ollama Cloud passthrough** (ratificación real ítem-4; supersede el detalle de la
   verbal del 19-jul) · floor pandapower **`>=3.5.4`** (el real, más estricto que el `>=3.3` de la
   sim) + `pandas<3` · C-dueño escalado sin aplicar: spec del equipo del demo (EG-5), egress/ALB del
   stretch cloud (EG-7).
4. **Pendiente S-G (sin cambios — lista priorizada en la convergencia §10):** Studio a clase+AL +
   fixture/generador del certificado + `engine/verification/{attestation,verifier,evidence}.py`
   (aún en vocabulario viejo — el barrido cubre los TRES, no solo attestation) · `scripts/verify-bundle.py`
   (checklist de 7 puntos) + api/compose reales · seed Pydantic de la Policy (materializa §6 +
   portadores + flags) · Registry/Pipeline reales · seeds de tests (falla sembrada, proyección
   `cancelled`, matriz interaction×profile, replay fail-closed).
5. **Stress test FINAL post-porte (2026-07-22 — panel de 4 atacantes frescos, registro en la
   convergencia §12):** veredicto **GO — cero P0**; los 11 P1 de letra/spec que cazó quedaron
   CERRADOS en este mismo barrido (payload de `run.created` completo, corte del `provenance_hash`,
   patas por `independence_group` en el checklist, CHECK nullable-solo-inconclusive,
   `level_efectivo` en semillas, guía/índice re-derivados, modo `record` del compose) y los P2
   quedan registrados con disposición. Deuda de gate para S-G: sumar `chimera_api`/`blite_cap_*`
   al import-linter cuando nazcan (hoy fuera de `root_packages`) · fusión `kb2-05`→`quantum/08`
   (dueño Dylan, pre-27).
